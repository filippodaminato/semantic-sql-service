import argparse
from typing import List
from cli.core.client import client
from cli.core.formatter import formatter

def add_discovery_commands(subparsers):
    # Common arguments parser
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("query", help="Search query")
    common_parser.add_argument("--limit", type=int, default=10, help="Max results")

    ds_parser = subparsers.add_parser("datasources", parents=[common_parser], help="Search datasources")
    ds_parser.set_defaults(func=search_datasources)

    tbl_parser = subparsers.add_parser("tables", parents=[common_parser], help="Search tables")
    tbl_parser.add_argument("--ds", dest="datasource_slug", help="Filter by Datasource Slug")
    tbl_parser.set_defaults(func=search_tables)

    col_parser = subparsers.add_parser("columns", parents=[common_parser], help="Search columns")
    col_parser.add_argument("--ds", dest="datasource_slug", help="Filter by Datasource Slug")
    col_parser.add_argument("--table", dest="table_slug", help="Filter by Table Slug")
    col_parser.set_defaults(func=search_columns)

    met_parser = subparsers.add_parser("metrics", parents=[common_parser], help="Search metrics")
    met_parser.add_argument("--ds", dest="datasource_slug", help="Filter by Datasource Slug")
    met_parser.set_defaults(func=search_metrics)

    edge_parser = subparsers.add_parser("edges", parents=[common_parser], help="Search edges (relationships)")
    edge_parser.add_argument("--ds", dest="datasource_slug", help="Filter by Datasource Slug")
    edge_parser.add_argument("--table", dest="table_slug", help="Filter by Table Slug")
    edge_parser.set_defaults(func=search_edges)

    syn_parser = subparsers.add_parser("synonyms", parents=[common_parser], help="Search synonyms")
    syn_parser.set_defaults(func=search_synonyms)

    rule_parser = subparsers.add_parser("rules", parents=[common_parser], help="Search context rules")
    rule_parser.add_argument("--ds", dest="datasource_slug", help="Filter by Datasource Slug")
    rule_parser.set_defaults(func=search_rules)

    val_parser = subparsers.add_parser("values", parents=[common_parser], help="Search low cardinality values")
    val_parser.add_argument("--ds", dest="datasource_slug", help="Filter by Datasource Slug")
    val_parser.add_argument("--table", dest="table_slug", help="Filter by Table Slug")
    val_parser.set_defaults(func=search_values)


def _build_payload(args):
    payload = {"query": args.query, "limit": args.limit}
    if hasattr(args, "datasource_slug") and args.datasource_slug:
        payload["datasource_slug"] = args.datasource_slug
    if hasattr(args, "table_slug") and args.table_slug:
        payload["table_slug"] = args.table_slug
    return payload

def search_datasources(args):
    data = client.post("/datasources", _build_payload(args))
    formatter.print(data, "Datasources")

def search_tables(args):
    data = client.post("/tables", _build_payload(args))
    formatter.print(data, "Tables")

def search_columns(args):
    data = client.post("/columns", _build_payload(args))
    # Flatten structure for better display if needed, but formatter handles dicts
    formatter.print(data, "Columns")

def search_metrics(args):
    data = client.post("/metrics", _build_payload(args))
    formatter.print(data, "Metrics")

def search_edges(args):
    data = client.post("/edges", _build_payload(args))
    formatter.print(data, "Edges")

def search_synonyms(args):
    data = client.post("/synonyms", _build_payload(args))
    formatter.print(data, "Synonyms")

def search_rules(args):
    data = client.post("/context_rules", _build_payload(args))
    formatter.print(data, "Context Rules")

def search_values(args):
    data = client.post("/low_cardinality_values", _build_payload(args))
    formatter.print(data, "Values")
