# Deployment Guide

Guida completa per il deployment del Semantic SQL Engine Management API.

## Prerequisiti

- Docker e Docker Compose installati
- OpenAI API Key
- PostgreSQL con estensione pgvector (gestita automaticamente tramite immagine `pgvector/pgvector`)

## Setup Locale

### 1. Clonare il Repository

```bash
git clone <repository-url>
cd semantic-sql-service
```

### 2. Configurare Variabili d'Ambiente

```bash
cp .env.example .env
```

Modificare `.env` con le tue credenziali:

```env
DATABASE_URL=postgresql://semantic_user:semantic_pass@db:5432/semantic_sql
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=text-embedding-3-small
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### 3. Avviare i Servizi

```bash
docker-compose up -d
```

Questo avvierà:
- PostgreSQL con pgvector su porta 5432
- FastAPI application su porta 8000

### 4. Inizializzare il Database

```bash
# Creare le tabelle (se non usi Alembic)
docker-compose exec api python -c "from src.core.database import Base, engine; Base.metadata.create_all(bind=engine)"

# Oppure con Alembic (consigliato)
docker-compose exec api alembic upgrade head
```

### 5. Verificare lo Stato

```bash
# Health check
curl http://localhost:8000/health

# Documentazione API
open http://localhost:8000/docs
```

## Setup Produzione

### Docker Compose per Produzione

Modificare `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  api:
    build:
      context: .
      dockerfile: Dockerfile
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      DATABASE_URL: ${DATABASE_URL}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      OPENAI_MODEL: ${OPENAI_MODEL:-text-embedding-3-small}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      ENVIRONMENT: production
    depends_on:
      - db
    restart: unless-stopped
    ports:
      - "8000:8000"

volumes:
  postgres_data:
```

### Variabili d'Ambiente Produzione

```env
DATABASE_URL=postgresql://user:password@postgres-host:5432/semantic_sql
OPENAI_API_KEY=sk-...
OPENAI_MODEL=text-embedding-3-small
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Migrazioni Database

```bash
# Creare una nuova migrazione
docker-compose exec api alembic revision --autogenerate -m "Description"

# Applicare migrazioni
docker-compose exec api alembic upgrade head

# Rollback
docker-compose exec api alembic downgrade -1
```

## Testing

### Eseguire Test

```bash
# Tutti i test
docker-compose exec api pytest

# Con coverage
docker-compose exec api pytest --cov=src --cov-report=html

# Test specifici
docker-compose exec api pytest tests/test_ontology.py

# Test in modalità verbose
docker-compose exec api pytest -v
```

### Setup Test Database

Creare un database separato per i test:

```bash
docker-compose exec db psql -U semantic_user -d postgres -c "CREATE DATABASE semantic_sql_test;"
docker-compose exec db psql -U semantic_user -d semantic_sql_test -c "CREATE EXTENSION vector;"
```

Impostare variabile d'ambiente:

```env
TEST_DATABASE_URL=postgresql://semantic_user:semantic_pass@db:5432/semantic_sql_test
```

## Monitoring e Logs

### Visualizzare Logs

```bash
# Tutti i servizi
docker-compose logs -f

# Solo API
docker-compose logs -f api

# Solo database
docker-compose logs -f db
```

### Health Check

```bash
curl http://localhost:8000/health
```

Risposta attesa:
```json
{
  "status": "healthy",
  "service": "semantic-sql-management-api",
  "version": "0.1.0"
}
```

## Backup Database

### Backup Manuale

```bash
docker-compose exec db pg_dump -U semantic_user semantic_sql > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore

```bash
docker-compose exec -T db psql -U semantic_user semantic_sql < backup.sql
```

## Scaling

### Horizontal Scaling (API)

Aumentare il numero di worker:

```yaml
command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Oppure usare Gunicorn:

```yaml
command: gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Database Connection Pooling

Configurare il pool in `src/core/database.py`:

```python
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=20,  # Aumentare per più connessioni
    max_overflow=40,
)
```

## Sicurezza

### 1. Autenticazione

Aggiungere middleware di autenticazione (es. JWT):

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.middleware("http")
async def verify_token(request: Request, call_next):
    # Verifica token
    pass
```

### 2. HTTPS

Usare reverse proxy (nginx) con certificati SSL.

### 3. Rate Limiting

Implementare rate limiting:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.get("/api/v1/...")
@limiter.limit("100/minute")
def endpoint():
    pass
```

## Troubleshooting

### Database non si connette

```bash
# Verificare che il container sia up
docker-compose ps

# Verificare logs
docker-compose logs db

# Testare connessione
docker-compose exec db psql -U semantic_user -d semantic_sql
```

### OpenAI API Errors

Verificare:
- API key valida
- Limiti di rate limiting
- Quota disponibile

### Errori di Embedding

Se gli embedding non vengono generati:
- Verificare API key OpenAI
- Controllare logs per errori specifici
- Verificare che il testo non sia vuoto

## Supporto

Per problemi o domande:
- Aprire un issue su GitHub
- Consultare la documentazione API: `/docs`
- Controllare i logs: `docker-compose logs`
