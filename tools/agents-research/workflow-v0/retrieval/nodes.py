import json
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from retrieval.states import RetrievalState
from retrieval.tools import (
    search_datasources,
    search_tables,
    search_columns,
    search_edges,
    search_metrics,
    search_synonyms,
    search_context_rules,
    search_low_cardinality_values,
    search_golden_sql,
)

from retrieval.prompts import create_search_text_prompt

# Setup Model
model = ChatOpenAI(model="gpt-4o", temperature=0)

async def create_search_texts_node(state: RetrievalState):
    prompt = create_search_text_prompt
    user_prompt = state["user_prompt"]
    
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=user_prompt)
    ]
    
    response = await model.ainvoke(messages)
    content = response.content.replace("```json", "").replace("```", "").strip()
    
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        print("Failed to parse JSON from LLM")
        return {}
        
    return {
        "search_text_datasources": data.get("search_text_datasources", []),
        "search_text_tables": data.get("search_text_tables", []),
        "search_text_columns": data.get("search_text_columns", []),
        "search_text_metrics": data.get("search_text_metrics", []),
        "search_text_edges": data.get("search_text_edges", []),
        "search_text_context_rules": data.get("search_text_context_rules", []),
        "search_text_synonyms": data.get("search_text_synonyms", []),
        "search_text_low_cardinality_values": data.get("search_text_low_cardinality_values", []),
        "search_text_golden_sqls": data.get("search_text_golden_sqls", [])
    }


async def execute_search_node(state: RetrievalState):
    tasks = []
    
    # helper to run tool for each query in list
    async def run_tool_for_queries(tool, queries):
        if not queries: return []
        results = await asyncio.gather(*(tool(q) for q in queries))
        # results is a list of lists (or list of dicts), flatten it if needed?
        # Our tools return List[str] or List[dict].
        # gather returns [ [item1, item2], [item3] ]
        flat = []
        for r in results:
            flat.extend(r)
        return flat

    # Datasources
    tasks.append(run_tool_for_queries(search_datasources, state.get("search_text_datasources", [])))
    # Tables
    tasks.append(run_tool_for_queries(search_tables, state.get("search_text_tables", [])))
    # Columns
    tasks.append(run_tool_for_queries(search_columns, state.get("search_text_columns", [])))
    # Edges
    tasks.append(run_tool_for_queries(search_edges, state.get("search_text_edges", [])))
    # Metrics
    tasks.append(run_tool_for_queries(search_metrics, state.get("search_text_metrics", [])))
    # Synonyms
    tasks.append(run_tool_for_queries(search_synonyms, state.get("search_text_synonyms", [])))
    # Context Rules
    tasks.append(run_tool_for_queries(search_context_rules, state.get("search_text_context_rules", [])))
    # Low Cardinality
    tasks.append(run_tool_for_queries(search_low_cardinality_values, state.get("search_text_low_cardinality_values", [])))
    # Golden SQL
    tasks.append(run_tool_for_queries(search_golden_sql, state.get("search_text_golden_sqls", [])))
    
    results = await asyncio.gather(*tasks)
    
    return {
        "found_datasources": results[0],
        "found_tables": results[1],
        "found_columns": results[2],
        "found_edges": results[3],
        "found_metrics": results[4],
        "found_synonyms": results[5],
        "found_context_rules": results[6],
        "found_low_cardinality_values": results[7],
        "found_golden_sqls": results[8],
    }

# --- Consolidator Node (The Brain) ---

def consolidator_node(state: RetrievalState):
    """
    Consolidates the flat lists of found entities into a hierarchical JSON structure.
    Structure:
    Datasource -> Tables -> Columns
                                     -> Context Rules
                                     -> Low Cardinality Values
               -> Metrics
               -> Golden SQLs
    """
    
    # helper for deduplication
    def dedup(items, key_field='id'):
        seen = set()
        unique = []
        for i in items:
            k = i.get(key_field)
            if k not in seen:
                seen.add(k)
                unique.append(i)
        return unique

    found_datasources = dedup(state.get("found_datasources", []))
    found_tables = dedup(state.get("found_tables", []))
    found_columns = dedup(state.get("found_columns", []))
    found_metrics = dedup(state.get("found_metrics", []))
    found_golden_sqls = dedup(state.get("found_golden_sqls", []))
    found_synonyms = dedup(state.get("found_synonyms", []))
    found_context_rules = dedup(state.get("found_context_rules", []))
    found_low_cardinality_values = dedup(state.get("found_low_cardinality_values", []))
    
    result = []

    

    # 1. Index everything by helper keys
    datasources_map = {d['id']: d for d in found_datasources}
    tables_map = {t['id']: t for t in found_tables}
    
    # 2. Enrich Columns with child info (rules, values)
    # We need to map rules/values to their column_id (or slug)
    
    # Group context rules by column_slug (since search_context_rules returns column_slug)
    
    rules_by_col_slug = {}
    for r in found_context_rules:
        c_slug = r.get('column_slug')
        if c_slug:
            rules_by_col_slug.setdefault(c_slug, []).append(r['rule_text'])

    values_by_col_slug = {}
    for v in found_low_cardinality_values:
        c_slug = v.get('column_slug')
        if c_slug:
            values_by_col_slug.setdefault(c_slug, []).append(v.get('value_label') or v.get('value_raw'))

    # Group Columns by table_slug (ColumnSearchResult has table_slug)
    columns_by_table_slug = {}
    for c in found_columns:
        c_slug = c.get('slug')
        # Attach children
        c['context_rules'] = rules_by_col_slug.get(c_slug, [])
        c['low_cardinality_values'] = values_by_col_slug.get(c_slug, [])
        
        t_slug = c.get('table_slug')
        if t_slug:
            columns_by_table_slug.setdefault(t_slug, []).append(c)

    # Enrich Tables with synonyms?
    # Synonyms target can be TABLE, COLUMN, etc.
    synonyms_by_table_slug = {}
    for s in found_synonyms:
        if s.get('target_type') == 'TABLE':
             t_slug = s.get('maps_to_slug')
             if t_slug and t_slug != "unknown":
                 synonyms_by_table_slug.setdefault(t_slug, []).append(s['term'])
    
    # 3. Build Tables hierarchy
    # We iterate over found tables and attach columns
    final_tables_map = {} # slug -> table_dict
    
    for t in found_tables:
        t_slug = t.get('slug')
        
        # Attach columns
        t['columns'] = columns_by_table_slug.get(t_slug, [])
        
        # Attach synonyms
        t['synonyms'] = synonyms_by_table_slug.get(t_slug, [])
        
        final_tables_map[t_slug] = t
        
    # Handle "orphaned" columns (columns found but their table wasn't in found_tables)
    
    for t_slug, cols in columns_by_table_slug.items():
        if t_slug not in final_tables_map:
            # Create a placeholder table
            final_tables_map[t_slug] = {
                "slug": t_slug,
                "name": t_slug, # Fallback
                "description": "Inferred from found columns",
                "columns": cols,
                "synonyms": synonyms_by_table_slug.get(t_slug, []),
                "is_inferred": True
            }

    # 4. Build Datasource hierarchy
    # Group tables by datasource_id.
    
    tables_by_ds_id = {}
    for t_slug, t in final_tables_map.items():
        ds_id = t.get('datasource_id')
        if ds_id:
            tables_by_ds_id.setdefault(str(ds_id), []).append(t)
        else:
             tables_by_ds_id.setdefault("unknown", []).append(t)

    # Metrics by datasource
    metrics_by_ds_id = {}
    for m in found_metrics:
        ds_id = m.get('datasource_id')
        if ds_id:
             metrics_by_ds_id.setdefault(str(ds_id), []).append(m['name'])

    # Golden SQLs by datasource
    gsql_by_ds_id = {}
    for g in found_golden_sqls:
        ds_id = g.get('datasource_id')
        if ds_id:
             gsql_by_ds_id.setdefault(str(ds_id), []).append(g['prompt'])

    # Construct final list of datasources
    final_datasources = []
    
    for ds in found_datasources:
        ds_id = str(ds.get('id'))
        ds['tables'] = tables_by_ds_id.get(ds_id, [])
        ds['metrics'] = metrics_by_ds_id.get(ds_id, [])
        ds['golden_sqls'] = gsql_by_ds_id.get(ds_id, [])
        final_datasources.append(ds)
        
        # Remove processed tables/metrics so we can see what's left
        if ds_id in tables_by_ds_id: del tables_by_ds_id[ds_id]
    
    # Handle orphaned tables (tables whose datasource wasn't found)
    if tables_by_ds_id:
        for ds_id, tables in tables_by_ds_id.items():
             final_datasources.append({
                 "slug": "unknown_datasource",
                 "name": "Unknown Datasource",
                 "description": "Container for tables with missing datasource info",
                 "tables": tables,
                 "metrics": [],
                 "golden_sqls": []
             })
             
    return {"final_context": final_datasources}