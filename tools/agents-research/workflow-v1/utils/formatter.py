from typing import Any, List, Union

class AgentContextFormatter:
    """
    Formatter for DataSources and Entities to Markdown for LLM consumption.
    """
    
    @staticmethod
    def _get_val(obj: Any, key: str, default: Any = None) -> Any:
        # Helper to get value from dict or object (pydantic)
        if isinstance(obj, dict):
            return obj.get(key, default)
        elif hasattr(obj, key):
            return getattr(obj, key)
        return default

    @classmethod
    def format_resolved_context(cls, response: Any) -> str:
        """
        Converts the hierarchical context response into a clean, token-efficient 
        Markdown format optimized for LLM ingestion.
        """
        blocks = []
        
        # Access 'graph' from response (could be dict or object)
        graph = cls._get_val(response, "graph", [])
        if not graph:
            return "No Datasources Found."

        for ds in graph:
            ds_block = []
            
            # 1. Livello Datasource
            name = cls._get_val(ds, "name", "Unknown")
            slug = cls._get_val(ds, "slug", "")
            description = cls._get_val(ds, "description", "")
            
            ds_block.append(f"# Datasource: `{name}`")
            ds_block.append(f"- **Slug**: {slug}")
            if description:
                ds_block.append(f"- **Usage**: {description} \n")
            
            # 1b. Enrichment Notes (Added by Refinement Agent)
            enrichment_notes = cls._get_val(ds, "enrichment_notes", [])
            if enrichment_notes:
                ds_block.append("### 🧠 Refinement Notes (Absolute Truths):")
                for note in enrichment_notes:
                    ds_block.append(f"- {note}")
                ds_block.append("\n")
            
            # 2. Livello Tabelle
            tables = cls._get_val(ds, "tables", [])
            if tables:
                ds_block.append(f"## Founded Tables:")
                for table in tables:
                    t_phys_name = cls._get_val(table, "physical_name")
                    t_slug = cls._get_val(table, "slug")
                    t_desc = cls._get_val(table, "description")
                    
                    ds_block.append(f"### Table: `{t_phys_name}` ")
                    ds_block.append(f"- **Slug**: `{t_slug}`")
                    ds_block.append(f"- **Usage**: {t_desc or 'No description available.'}")
                    
                    # 3. Livello Colonne (Mostriamo solo se ci sono colonne rilevanti)
                    columns = cls._get_val(table, "columns", [])
                    if columns:
                        ds_block.append(f"\n#### Founded Columns:")
                        for col in columns:
                            c_name = cls._get_val(col, "name")
                            c_slug = cls._get_val(col, "slug")
                            c_type = cls._get_val(col, "data_type")
                            c_desc = cls._get_val(col, "description")
                            c_note = cls._get_val(col, "context_note")
                            c_nom = cls._get_val(col, "nominal_values")
                            c_rules = cls._get_val(col, "context_rules")

                            # Costruiamo la riga della colonna in modo compatto
                            ds_block.append(f"##### Column: `{c_name}` ")
                            ds_block.append(f"- **Slug**: `{c_slug}`")

                            if c_type:
                                ds_block.append(f"- **Type**: `{c_type}`")
                            
                            if c_desc:
                                ds_block.append(f"- **Desc**: `{c_desc}`")

                            if c_note:
                                ds_block.append(f"- **Notes**: `{c_note}`")

                            # 4a. Nominal Values (Low Cardinality)
                            if c_nom:
                                vals = [cls._get_val(v, "value_raw") for v in c_nom]
                                # Limita a 5 valori per evitare bloat
                                val_str = ", ".join([str(v) for v in vals[:5]])
                                if len(vals) > 5:
                                    val_str += ", ..."
                                ds_block.append(f"> Nominal Values: {val_str}")

                            # 4b. Context Rules
                            if c_rules:
                                for rule in c_rules:
                                    r_text = cls._get_val(rule, "rule_text")
                                    ds_block.append(f"> Context Rule: {r_text}")
                            ds_block.append("\n")
                

            # 5. Metrics
            metrics = cls._get_val(ds, "metrics", [])
            if metrics:
                ds_block.append("\n### Semantic Metrics")
                for metric in metrics:
                    m_name = cls._get_val(metric, "name")
                    m_desc = cls._get_val(metric, "description")
                    m_sql = cls._get_val(metric, "calculation_sql")
                    
                    ds_block.append(f"- **{m_name}**")
                    if m_desc:
                        ds_block.append(f"- Desc : {m_desc}")
                    ds_block.append(f"- SQL: `{m_sql}`")
                ds_block.append("\n---")
            
            # 6. Edges / Relationships
            edges = cls._get_val(ds, "edges", [])
            if edges:
                ds_block.append("\n### Relationships")
                for edge in edges:
                    e_src = cls._get_val(edge, "source")
                    e_tgt = cls._get_val(edge, "target")
                    e_type = cls._get_val(edge, "relationship_type")
                    e_desc = cls._get_val(edge, "description")
                    
                    ds_block.append(f"- `{e_src}` -> `{e_tgt}` ({e_type})")
                    if e_desc:
                         ds_block.append(f"- _{e_desc}_")
                ds_block.append("\n---")

            # 7. Golden SQL
            golden_sqls = cls._get_val(ds, "golden_sqls", [])
            if golden_sqls:
                ds_block.append("\n### Golden SQL Examples")
                for gs in golden_sqls:
                    gs_prompt = cls._get_val(gs, "prompt")
                    gs_sql = cls._get_val(gs, "sql")
                    ds_block.append(f"- **Prompt**: \"{gs_prompt}\"")
                    ds_block.append(f"- `SQL`: {gs_sql}")
                ds_block.append("\n---")

            blocks.append("\n".join(ds_block))
            
        return "\n\n".join(blocks)
            
    @classmethod
    def to_markdown(cls, datasource: Any) -> str:
        """
        Formats a single datasource object/dict to Markdown.
        """
        # We can reuse the logic by wrapping it in a fake graph structure
        # or extracting the loop body. For simplicity, let's extract logic if possible
        # but wrapping is faster for now to reuse code.
        
        # However, to be robust, let's copy the logic or refactor.
        # Let's wrap it since format_resolved_context expects {graph: [ds]}
        
        wrapper = {"graph": [datasource]}
        return cls.format_resolved_context(wrapper)

