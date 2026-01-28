from pydantic import BaseModel, Field
from typing import Optional

class GeneratedSQL(BaseModel):
    """The SQL code produced by the generator."""
    sql: str = Field(..., description="The executable SQL query. Markdown formatting is allowed.")
    explanation: str = Field(..., description="Brief explanation of how the code matches the blueprint.")

class ValidationResult(BaseModel):
    """Output of the syntax/logic check."""
    is_valid: bool
    error_message: Optional[str] = None
    fixed_suggestion: Optional[str] = None