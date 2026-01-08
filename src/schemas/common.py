"""Common DTOs and utilities"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = datetime.now()


class SuccessResponse(BaseModel):
    """Standard success response"""
    message: str
    timestamp: datetime = datetime.now()
