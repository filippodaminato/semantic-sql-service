import json
import shutil
from typing import List, Dict, Any, Union
from cli.core.config import settings

class Formatter:
    """
    Handles output formatting (JSON or Table).
    """

    @staticmethod
    def print(data: Union[List[Dict], Dict], title: str = "Results"):
        if settings.output_format == "json":
            print(json.dumps(data, indent=2))
        else:
            Formatter._print_table(data, title)

    @staticmethod
    def _print_table(data: Union[List[Dict], Dict], title: str):
        if not data:
            print("No results found.")
            return

        # Normalize to list
        if isinstance(data, dict):
            data = [data]

        if not data:
            print("No results found.")
            return

        # Get headers from first item keys
        headers = list(data[0].keys())

        # Calculate widths
        widths = {h: len(h) for h in headers}
        processed_data = []

        for row in data:
            processed_row = {}
            for h in headers:
                val = str(row.get(h, ""))
                # Truncate long values for table view
                if len(val) > 50:
                    val = val[:47] + "..."
                processed_row[h] = val
                widths[h] = max(widths[h], len(val))
            processed_data.append(processed_row)

        # Create separator
        separator = "+" + "+".join(["-" * (widths[h] + 2) for h in headers]) + "+"

        # Print Title
        print(f"\n📁 {title} ({len(data)} items)")
        
        # Print Header
        print(separator)
        header_row = "|" + "|".join([f" {h.upper().ljust(widths[h])} " for h in headers]) + "|"
        print(header_row)
        print(separator)

        # Print Rows
        for row in processed_data:
            data_row = "|" + "|".join([f" {row[h].ljust(widths[h])} " for h in headers]) + "|"
            print(data_row)
        
        print(separator + "\n")

formatter = Formatter()
