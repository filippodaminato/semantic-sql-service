# Developer Guide

This guide provides information for developers working on the Semantic SQL Engine backend.

## Table of Contents

- [Setup](#setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Code Conventions](#code-conventions)
- [Testing](#testing)
- [Debugging](#debugging)
- [Common Tasks](#common-tasks)

## Setup

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- PostgreSQL 14+ (or use Docker)
- OpenAI API key

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd semantic-sql-service
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Run database migrations**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

5. **Verify setup**
   ```bash
   curl http://localhost:8000/health
   ```

### IDE Setup

**VS Code / Cursor:**
- Install Python extension
- Install Pylance for type checking
- Configure `.vscode/settings.json`:
  ```json
  {
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black"
  }
  ```

**PyCharm:**
- Configure Python interpreter (Python 3.11+)
- Enable type checking
- Configure code style (PEP 8)

## Project Structure

```
semantic-sql-service/
├── src/
│   ├── api/              # FastAPI route handlers
│   │   ├── ontology.py  # Physical schema management
│   │   ├── semantics.py # Business semantics
│   │   ├── context.py   # Context & values
│   │   ├── learning.py  # Few-shot learning
│   │   ├── retrieval.py # Retrieval API for agents
│   │   └── admin.py     # Admin operations
│   ├── core/            # Core utilities
│   │   ├── config.py    # Configuration management
│   │   ├── database.py  # Database connection
│   │   ├── logging.py    # Logging setup
│   │   └── searchable_mixin.py  # Search functionality
│   ├── db/              # Database models
│   │   └── models.py    # SQLAlchemy models
│   ├── schemas/         # Pydantic DTOs
│   │   ├── ontology.py
│   │   ├── semantics.py
│   │   └── ...
│   ├── services/        # Business logic
│   │   ├── embedding_service.py
│   │   └── sql_validator.py
│   └── main.py          # Application entry point
├── tests/               # Test suite
├── alembic/             # Database migrations
├── docs/                # Documentation
└── scripts/             # Utility scripts
```

## Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow code style guidelines (see [Code Conventions](#code-conventions))
   - Add comprehensive docstrings
   - Write tests for new functionality

3. **Run tests**
   ```bash
   docker-compose exec api pytest
   ```

4. **Check linting**
   ```bash
   docker-compose exec api flake8 src/
   ```

5. **Commit changes**
   ```bash
   git commit -m "feat: add new feature"
   ```

6. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Database Migrations

When modifying models:

1. **Create migration**
   ```bash
   docker-compose exec api alembic revision --autogenerate -m "description"
   ```

2. **Review migration file**
   - Check `alembic/versions/XXXX_description.py`
   - Verify changes are correct

3. **Apply migration**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

4. **Test migration**
   - Verify schema changes
   - Test data integrity

## Code Conventions

### Python Style

- Follow PEP 8 style guide
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use 4 spaces for indentation

### Docstrings

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> Dict[str, Any]:
    """
    Brief description in one line.
    
    Longer description explaining behavior, use cases, and important
    considerations.
    
    Args:
        param1: Description of parameter with type and constraints
        param2: Description of second parameter
        
    Returns:
        Description of return value with structure
        
    Raises:
        ValueError: When and why this exception is raised
        HTTPException: With status code and details
        
    Example:
        >>> result = function_name("test", 42)
        >>> print(result)
        {'key': 'value'}
        
    Note:
        Additional considerations or limitations
    """
```

### Naming Conventions

- **Classes**: PascalCase (`TableNode`, `EmbeddingService`)
- **Functions/Methods**: snake_case (`create_table`, `get_embedding`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_RETRIES`, `DEFAULT_LIMIT`)
- **Private methods**: Leading underscore (`_compute_hash`, `_apply_filters`)

### Import Organization

```python
# Standard library imports
import os
from typing import List, Dict

# Third-party imports
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# Local application imports
from ..core.database import get_db
from ..db.models import TableNode
```

## Testing

### Running Tests

```bash
# Run all tests
docker-compose exec api pytest

# Run specific test file
docker-compose exec api pytest tests/test_ontology.py

# Run with coverage
docker-compose exec api pytest --cov=src --cov-report=html

# Run specific test
docker-compose exec api pytest tests/test_ontology.py::test_create_table
```

### Writing Tests

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_create_table(client: TestClient, db: Session):
    """
    Test table creation endpoint.
    
    Verifies that:
    - Table is created with correct data
    - Columns are created in same transaction
    - Embeddings are generated
    """
    response = client.post(
        "/api/v1/ontology/tables",
        json={
            "datasource_id": "test-id",
            "physical_name": "test_table",
            "semantic_name": "Test Table",
            "columns": [...]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["physical_name"] == "test_table"
```

### Test Structure

- Use descriptive test names
- One assertion per test (when possible)
- Use fixtures for common setup
- Mock external services (OpenAI API)

## Debugging

### Logging

Use structured logging:

```python
from ..core.logging import get_logger

logger = get_logger(__name__)

logger.info("Operation started", extra={"table_id": table.id})
logger.error("Operation failed", exc_info=True)
```

### Debug Mode

Enable debug logging:

```bash
# Set in .env
LOG_LEVEL=DEBUG
```

### Database Inspection

```bash
# Connect to database
docker-compose exec db psql -U semantic_user -d semantic_sql

# Query tables
SELECT * FROM table_nodes LIMIT 10;

# Check embeddings
SELECT id, semantic_name, embedding IS NOT NULL as has_embedding 
FROM table_nodes;
```

### Common Issues

**Issue: Embeddings not generating**
- Check OpenAI API key is set
- Verify API key has credits
- Check logs for API errors

**Issue: Database connection errors**
- Verify DATABASE_URL in .env
- Check database is running: `docker-compose ps`
- Verify network connectivity

**Issue: Migration errors**
- Check migration file syntax
- Verify model changes match migration
- Rollback if needed: `alembic downgrade -1`

## Common Tasks

### Adding a New Endpoint

1. **Define schema** in `src/schemas/`
   ```python
   class NewEntityCreateDTO(BaseModel):
       name: str
       description: Optional[str] = None
   ```

2. **Add route handler** in appropriate `src/api/` file
   ```python
   @router.post("/entities", response_model=EntityResponseDTO)
   def create_entity(data: NewEntityCreateDTO, db: Session = Depends(get_db)):
       # Implementation
   ```

3. **Add tests** in `tests/`
4. **Update API documentation**

### Adding a New Model

1. **Define model** in `src/db/models.py`
   ```python
   class NewEntity(SearchableMixin, Base):
       __tablename__ = "new_entities"
       # Fields
   ```

2. **Create migration**
   ```bash
   alembic revision --autogenerate -m "add new_entities table"
   ```

3. **Apply migration**
   ```bash
   alembic upgrade head
   ```

### Modifying Search Behavior

1. **Override search mode** in model:
   ```python
   class MyModel(SearchableMixin, Base):
       _search_mode = "fts_only"  # or "hybrid"
   ```

2. **Customize search content**:
   ```python
   def get_search_content(self) -> str:
       return f"{self.name} {self.description}"
   ```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
