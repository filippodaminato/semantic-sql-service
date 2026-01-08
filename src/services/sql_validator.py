"""Service for validating SQL syntax"""
import sqlglot
from sqlglot.errors import ParseError
from typing import Tuple, Optional, Dict
from enum import Enum


class SQLEngine(str, Enum):
    """Supported SQL engines"""
    POSTGRES = "postgres"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"
    TSQL = "tsql"
    MYSQL = "mysql"


class SQLValidator:
    """Service for validating SQL expressions"""
    
    @staticmethod
    def validate_sql(
        sql_expression: str,
        dialect: str = "postgres"
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL syntax
        
        Args:
            sql_expression: SQL expression to validate
            dialect: SQL dialect (postgres, bigquery, snowflake, tsql, mysql)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Try to parse the SQL
            sqlglot.parse(sql_expression, read=dialect)
            return True, None
        except ParseError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    @staticmethod
    def normalize_sql(
        sql_expression: str,
        dialect: str = "postgres"
    ) -> Optional[str]:
        """
        Normalize SQL expression (can be used for validation)
        
        Args:
            sql_expression: SQL expression to normalize
            dialect: SQL dialect
            
        Returns:
            Normalized SQL or None if invalid
        """
        try:
            parsed = sqlglot.parse_one(sql_expression, read=dialect)
            return parsed.sql(dialect=dialect)
        except Exception:
            return None


sql_validator = SQLValidator()
