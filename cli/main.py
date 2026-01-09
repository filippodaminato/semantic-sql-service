import sys
import argparse
from cli.core.config import settings
from cli.commands.discovery import add_discovery_commands

def main():
    parser = argparse.ArgumentParser(
        description="Semantic SQL Service Enterprise CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  semantic-cli datasources "billing"
  semantic-cli metrics "revenue" --ds cloudbill
  SEMANTIC_CLI_OUTPUT=json semantic-cli tables "users"
        """
    )
    
    # Global args
    parser.add_argument("--url", help="Override API URL", default=settings.api_url)
    parser.add_argument("--format", choices=["json", "table"], default=settings.output_format, help="Output format")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    # parser.add_argument("query", ... ) removed to avoid conflict with subcommands

    subparsers = parser.add_subparsers(dest="command", title="Commands")
    
    # Register commands
    add_discovery_commands(subparsers)

    # Parse
    args = parser.parse_args()

    # Apply overrides
    if args.url:
        settings.api_url = args.url.rstrip("/")
    if args.format:
        settings.output_format = args.format
    if args.debug:
        settings.debug = True

    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if not args.query and args.command not in []: # Add commands that don't need query if any
         # For discovery API, query IS required by most schemas, but let's allow empty string if handled
         pass

    # Execute
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
