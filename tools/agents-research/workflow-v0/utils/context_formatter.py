from typing import Any, Dict, List, Union

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
    def datasource_to_markdown(cls, datasource: Union[Dict, Any]) -> str:
        """
        Converts a Datasource object/dict to a Markdown representation.
        """
        if not datasource:
            return "No Datasource Selected."
            
        name = cls._get_val(datasource, "name", "Unknown")
        slug = cls._get_val(datasource, "slug", "unknown-slug")
        tables = cls._get_val(datasource, "tables", [])
        
        md = f"# Datasource: {name} (Slug: {slug})\n\n"
        
        if not tables:
            md += "No tables found.\n"
            return md
            
        for t in tables:
            t_name = cls._get_val(t, "name")
            t_cols = cls._get_val(t, "columns", [])
            md += f"## Table: {t_name}\n"
            if t_cols:
                md += "| Column | Type | Description |\n"
                md += "|---|---|---|\n"
                for c in t_cols:
                    c_name = cls._get_val(c, "name")
                    c_type = cls._get_val(c, "data_type", "N/A")
                    c_desc = cls._get_val(c, "description", "")
                    md += f"| {c_name} | {c_type} | {c_desc} |\n"
            else:
                md += "No columns info.\n"
            md += "\n"
            
        # Add Enrichment Notes
        notes = cls._get_val(datasource, "enrichment_notes", [])
        if notes:
            md += "### Enrichment Notes:\n"
            for note in notes:
                md += f"- {note}\n"
                
        return md

    @classmethod
    def entity_to_markdown(cls, entity: Any) -> str:
        """
        Formats a single entity (table/column/metric search result) to Markdown.
        """
        # Simplistic implementation
        return str(entity)
