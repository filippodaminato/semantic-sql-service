# Semantic SQL Engine - Management API

Microservizio Enterprise per la gestione della conoscenza semantica per la generazione di query SQL.

## 🏗️ Architettura

Il sistema implementa un'architettura a 4 domini principali:

1. **Physical Ontology**: Gestione schema fisico (tabelle, colonne, relazioni)
2. **Business Semantics**: Astrazione semantica (metriche, sinonimi)
3. **Context & Values**: Intelligenza contestuale (valori nominali, regole)
4. **Learning**: Apprendimento few-shot (golden SQL examples)

## 🚀 Quick Start

### Prerequisiti

- Docker & Docker Compose
- Python 3.11+ (per sviluppo locale)
- OpenAI API Key

### Setup

1. **Configurare variabili d'ambiente**:
```bash
cp .env.example .env
# Modificare .env con le tue credenziali
```

2. **Avviare i servizi**:
```bash
docker-compose up -d
```

3. **Inizializzare il database**:
```bash
# IMPORTANTE: Esegui sempre Alembic dentro Docker, non localmente!
# Il database Docker ha l'utente 'semantic_user' che non esiste nel DB locale
docker-compose exec api alembic upgrade head
# Oppure usa il Makefile:
make migrate
```

4. **Verificare lo stato**:
```bash
curl http://localhost:8000/health
```

## 📚 Documentazione API

Una volta avviato il servizio, la documentazione interattiva è disponibile a:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Testing

```bash
# Eseguire tutti i test
docker-compose exec api pytest

# Eseguire con coverage
docker-compose exec api pytest --cov=src --cov-report=html

# Eseguire test specifici
docker-compose exec api pytest tests/test_ontology.py
```

## 📦 Struttura del Progetto

```
semantic-sql-service/
├── src/
│   ├── api/              # FastAPI routers
│   ├── core/             # Configurazione e utilities
│   ├── db/               # Database models e migrations
│   ├── services/         # Business logic
│   ├── schemas/          # Pydantic DTOs
│   └── __init__.py
├── tests/                # Test suite
├── alembic/              # Database migrations
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## 🔧 Configurazione

### Variabili d'Ambiente

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:password@db:5432/semantic_sql` |
| `OPENAI_API_KEY` | OpenAI API key (richiesto) | - |
| `OPENAI_MODEL` | Modello embedding OpenAI | `text-embedding-3-small` |
| `LOG_LEVEL` | Livello di log | `INFO` |

## 🏢 Enterprise Features

- ✅ Validazione DTO rigorosa con Pydantic
- ✅ Idempotenza e gestione duplicati
- ✅ Transazioni atomiche per Deep Writes
- ✅ Vettorializzazione automatica con OpenAI
- ✅ Validazione SQL con sqlglot
- ✅ Bulk operations per performance
- ✅ Test coverage completa
- ✅ Documentazione OpenAPI/Swagger

## 📖 Esempi d'Uso

### Creare una tabella con colonne (Deep Create)

```bash
curl -X POST http://localhost:8000/api/v1/ontology/tables \
  -H "Content-Type: application/json" \
  -d '{
    "datasource_id": "550e8400-e29b-41d4-a716-446655440000",
    "physical_name": "t_sales_2024",
    "semantic_name": "Sales Transactions",
    "description": "Tabella principale contenente tutte le transazioni e-commerce confermate.",
    "ddl_context": "CREATE TABLE t_sales_2024 (id INT, amount DECIMAL(10,2))",
    "columns": [
      {
        "name": "amount_total",
        "data_type": "DECIMAL(10,2)",
        "is_primary_key": false,
        "context_note": "Include IVA. Se null, transazione fallita."
      }
    ]
  }'
```

### Creare una metrica semantica

```bash
curl -X POST http://localhost:8000/api/v1/semantics/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Average Basket Size",
    "description": "Valore medio del carrello per ordini completati",
    "sql_expression": "AVG(t_sales.amount_total)",
    "required_table_ids": ["uuid-table-sales"],
    "filter_condition": "t_sales.status = '\''COMPLETED'\''"
  }'
```

## 🔍 Monitoring

- Health check: `GET /health`
- Metrics: `GET /metrics` (se configurato Prometheus)

## 📝 License

MIT
