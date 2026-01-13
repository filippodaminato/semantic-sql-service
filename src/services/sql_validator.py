"""
SQL Validation Service using sqlglot.

This service provides SQL syntax validation and normalization for multiple
SQL dialects. It's used to validate SQL expressions before storing them
in the database (e.g., for metrics, golden SQL examples).

The service uses sqlglot, a SQL parser that supports multiple dialects
and can validate syntax without executing queries (dry-run validation).
"""

import sqlglot
from sqlglot.errors import ParseError
from typing import Tuple, Optional
from enum import Enum


class SQLEngine(str, Enum):
    """
    Supported SQL engine dialects.
    
    These correspond to the SQL dialects supported by sqlglot and
    match the SQLEngineType enum in the database models.
    """
    POSTGRES = "postgres"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"
    TSQL = "tsql"
    MYSQL = "mysql"


class SQLValidator:
    """
    Service for validating and normalizing SQL expressions.
    
    This service provides SQL syntax validation without executing queries,
    making it safe to validate user-provided SQL before storage. It supports
    multiple SQL dialects to match different database engines.
    
    Use Cases:
    - Validate metric SQL expressions before saving
    - Validate golden SQL examples
    - Normalize SQL for consistent storage
    - Prevent SQL injection in stored expressions
    
    Example:
        ```python
        is_valid, error = SQLValidator.validate_sql("SELECT * FROM users", "postgres")
        if not is_valid:
            print(f"SQL Error: {error}")
        ```
    """
    
    @staticmethod
    def validate_sql(
        sql_expression: str,
        dialect: str = "postgres"
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL syntax for a specific dialect.
        
        This method parses the SQL expression using sqlglot to check for
        syntax errors. It does not execute the query, making it safe for
        validating user-provided SQL.
        
        Args:
            sql_expression: SQL expression to validate (e.g., "SELECT * FROM users")
            dialect: SQL dialect to validate against. Must be one of:
                     "postgres", "bigquery", "snowflake", "tsql", "mysql"
        
        Returns:
            Tuple[bool, Optional[str]]:
                - (True, None) if SQL is valid
                - (False, error_message) if SQL is invalid
        
        Example:
            >>> is_valid, error = SQLValidator.validate_sql("SELECT * FROM users", "postgres")
            >>> is_valid
            True
            >>> is_valid, error = SQLValidator.validate_sql("SELCT * FROM users", "postgres")
            >>> is_valid
            False
            >>> error
            "Invalid expression. Unexpected keyword 'SELCT'"
        
        Note:
            - This validates syntax only, not semantics (e.g., table existence)
            - Does not execute the query (safe for user input)
            - Returns False for any parsing error, including unexpected exceptions
        """
        try:
            # Parse SQL expression using sqlglot
            # This validates syntax without executing the query
            sqlglot.parse(sql_expression, read=dialect)
            return True, None
        except ParseError as e:
            # SQL syntax error: return error message
            return False, str(e)
        except Exception as e:
            # Unexpected error: return generic error message
            return False, f"Unexpected error during SQL validation: {str(e)}"
    
    @staticmethod
    def normalize_sql(
        sql_expression: str,
        dialect: str = "postgres"
    ) -> Optional[str]:
        """
        Normalize SQL expression to standard format.
        
        This method parses and reformats SQL, which can be useful for:
        - Consistent storage format
        - SQL formatting/pretty-printing
        - Validation (if normalization fails, SQL is invalid)
        
        Args:
            sql_expression: SQL expression to normalize
            dialect: SQL dialect (postgres, bigquery, snowflake, tsql, mysql)
        
        Returns:
            Optional[str]: Normalized SQL string, or None if SQL is invalid
        
        Example:
            >>> SQLValidator.normalize_sql("select * from users", "postgres")
            'SELECT * FROM users'
            >>> SQLValidator.normalize_sql("invalid sql", "postgres")
            None
        
        Note:
            - Returns None if SQL cannot be parsed (invalid syntax)
            - Normalization may change formatting but preserves semantics
        """
        try:
            # Parse and reformat SQL
            parsed = sqlglot.parse_one(sql_expression, read=dialect)
            return parsed.sql(dialect=dialect)
        except Exception:
            # Parsing failed: SQL is invalid
            return None


# Global validator instance
# Import this in other modules: from .services.sql_validator import sql_validator
sql_validator = SQLValidator()
