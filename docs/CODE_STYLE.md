# Code Style Guide

This document defines the coding standards for the Semantic SQL Engine backend.

## Python Style Guide

We follow [PEP 8](https://pep8.org/) with some project-specific modifications.

### General Rules

- **Line Length**: Maximum 100 characters (not 79)
- **Indentation**: 4 spaces (no tabs)
- **Trailing Whitespace**: Remove all trailing whitespace
- **Blank Lines**: 
  - 2 blank lines between top-level definitions (classes, functions)
  - 1 blank line between methods in a class
  - No blank lines at end of file

### Imports

Order imports as follows:

1. Standard library imports
2. Third-party imports
3. Local application imports

Separate each group with a blank line.

```python
# Standard library
import os
from typing import List, Dict, Optional

# Third-party
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# Local
from ..core.database import get_db
from ..db.models import TableNode
```

### Naming Conventions

#### Classes
Use PascalCase:
```python
class TableNode(Base):
    pass

class EmbeddingService:
    pass
```

#### Functions and Variables
Use snake_case:
```python
def create_table():
    pass

table_name = "users"
```

#### Constants
Use UPPER_SNAKE_CASE:
```python
MAX_RETRIES = 3
DEFAULT_LIMIT = 10
OPENAI_API_KEY = "sk-..."
```

#### Private Methods/Attributes
Use leading underscore:
```python
def _compute_hash(text: str) -> str:
    pass

class MyClass:
    _private_attribute = None
```

### Type Hints

Always use type hints for function signatures:

```python
def process_data(
    table_id: UUID,
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    pass
```

### Docstrings

Use Google-style docstrings for all public functions, classes, and methods.

#### Function Docstring Format

```python
def function_name(param1: str, param2: int) -> Dict[str, Any]:
    """
    Brief one-line description.
    
    Longer description that explains the function's purpose, behavior,
    use cases, and important considerations. Can span multiple paragraphs.
    
    Args:
        param1: Description of first parameter. Include type and constraints.
               Can span multiple lines if needed.
        param2: Description of second parameter.
        
    Returns:
        Description of return value. Include structure if returning
        a dictionary or complex object.
        
    Raises:
        ValueError: When and why this exception is raised.
        HTTPException: With status code (e.g., 404 Not Found).
        
    Example:
        >>> result = function_name("test", 42)
        >>> print(result)
        {'key': 'value'}
        
    Note:
        Additional considerations, limitations, or important notes.
    """
```

#### Class Docstring Format

```python
class MyClass:
    """
    Brief one-line description of the class.
    
    Longer description explaining the class's purpose, when to use it,
    and important design decisions.
    
    Attributes:
        attribute1: Description of attribute1
        attribute2: Description of attribute2
        
    Example:
        >>> obj = MyClass()
        >>> obj.method()
        'result'
        
    Note:
        Important notes about the class.
    """
```

#### Module Docstring Format

```python
"""
Module-level docstring.

This module provides [brief description of module purpose].

Key Features:
- Feature 1
- Feature 2

Example:
    ```python
    from .module import function
    result = function()
    ```
"""
```

### Comments

#### Inline Comments

Use comments to explain **why**, not **what**:

```python
# Good: Explains why
# Use RRF to combine vector and FTS results for better relevance
scores = calculate_rrf(vector_results, fts_results)

# Bad: Explains what (code is self-explanatory)
# Calculate RRF scores
scores = calculate_rrf(vector_results, fts_results)
```

#### Block Comments

For complex algorithms or non-obvious logic:

```python
# Step 1: Generate embedding for query
# This converts natural language to vector space for similarity search
vector = embedding_service.generate_embedding(query)

# Step 2: Perform vector similarity search
# L2 distance gives us semantic similarity ranking
results = session.query(TableNode).order_by(
    TableNode.embedding.l2_distance(vector)
).limit(limit)
```

### Code Organization

#### Function Length
- Keep functions under 50 lines when possible
- Break complex functions into smaller, focused functions
- Use helper functions for repeated logic

#### Class Organization
Order class elements as follows:

1. Class docstring
2. Class variables
3. `__init__` method
4. Public methods
5. Private methods
6. Special methods (`__str__`, `__repr__`, etc.)

```python
class MyClass:
    """Class docstring."""
    
    # Class variables
    DEFAULT_VALUE = 10
    
    def __init__(self, value: int):
        """Initialize instance."""
        self.value = value
    
    def public_method(self):
        """Public method."""
        pass
    
    def _private_method(self):
        """Private method."""
        pass
    
    def __str__(self) -> str:
        """String representation."""
        return f"MyClass(value={self.value})"
```

### Error Handling

#### Use Specific Exceptions

```python
# Good
if not datasource:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Datasource {datasource_id} not found"
    )

# Bad
if not datasource:
    raise Exception("Not found")
```

#### Log Before Raising

```python
logger.error(f"Datasource {datasource_id} not found")
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail=f"Datasource {datasource_id} not found"
)
```

### Database Code

#### Use Transactions

```python
try:
    db.add(item)
    db.commit()
    db.refresh(item)
except Exception as e:
    db.rollback()
    logger.error(f"Error creating item: {e}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error creating item: {str(e)}"
    )
```

#### Use Query Filters

```python
# Good: Clear and readable
tables = db.query(TableNode).filter(
    TableNode.datasource_id == datasource_id
).all()

# Bad: Complex one-liner
tables = [t for t in db.query(TableNode).all() if t.datasource_id == datasource_id]
```

### API Endpoints

#### Endpoint Documentation

Always include comprehensive docstrings:

```python
@router.post("/tables", response_model=TableResponseDTO)
def create_table(
    table_data: TableCreateDTO,
    db: Session = Depends(get_db)
):
    """
    Create a new table with optional columns.
    
    This endpoint implements deep create, allowing creation of a table
    and all its columns in a single atomic transaction.
    
    Args:
        table_data: Table creation data
        db: Database session
        
    Returns:
        TableResponseDTO: Created table
        
    Raises:
        HTTPException 404: If datasource not found
        HTTPException 409: If table name already exists
    """
```

### Testing Style

#### Test Function Names

Use descriptive names that explain what is being tested:

```python
def test_create_table_with_columns_succeeds():
    """Test that creating a table with columns works correctly."""
    pass

def test_create_table_with_duplicate_name_raises_409():
    """Test that duplicate table names raise 409 conflict."""
    pass
```

#### Test Organization

```python
def test_functionality():
    """
    Test description.
    
    Arrange: Set up test data
    Act: Perform the action
    Assert: Verify the results
    """
    # Arrange
    datasource = create_test_datasource()
    
    # Act
    response = client.post("/api/v1/ontology/tables", json={...})
    
    # Assert
    assert response.status_code == 201
    assert response.json()["physical_name"] == "test_table"
```

## Tools

### Linting

We use `flake8` for linting:

```bash
flake8 src/ --max-line-length=100
```

### Formatting

We use `black` for code formatting (optional, but recommended):

```bash
black src/ --line-length=100
```

### Type Checking

We use `mypy` for type checking:

```bash
mypy src/
```

## Examples

### Good Example

```python
"""
Service for generating embeddings using OpenAI.

This service provides functionality to convert text into dense vector
embeddings for semantic search.
"""

from typing import List
from openai import OpenAI
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger("embedding_service")


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI API.
    
    Attributes:
        client: OpenAI API client instance
        model: OpenAI model name
        dimensions: Vector dimensions
    """
    
    def __init__(self):
        """Initialize the embedding service."""
        api_key = settings.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required")
        
        self.client = OpenAI(api_key=api_key)
        self.model = settings.openai_model
        self.dimensions = settings.embedding_dimensions
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text string.
        
        Args:
            text: Text string to embed
            
        Returns:
            List[float]: Embedding vector (1536 dimensions)
        """
        if not text or not text.strip():
            return [0.0] * self.dimensions
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text.strip()
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * self.dimensions
```

### Bad Example

```python
# No module docstring
from openai import OpenAI

class EmbeddingService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)  # No error handling
    
    def generate_embedding(self, text):  # No type hints
        response = self.client.embeddings.create(model=settings.openai_model, input=text)
        return response.data[0].embedding  # No error handling, no docstring
```
