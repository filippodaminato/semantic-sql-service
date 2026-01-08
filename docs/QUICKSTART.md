# Quick Start Guide

Guida rapida per iniziare con il Semantic SQL Engine Management API.

## Prerequisiti

- Docker & Docker Compose
- OpenAI API Key (ottieni da https://platform.openai.com/api-keys)

## Setup in 5 Minuti

### 1. Configurare Environment

```bash
# Copiare template
cp .env.example .env

# Modificare .env e inserire la tua OpenAI API Key
# OPENAI_API_KEY=sk-your-key-here
```

### 2. Avviare Servizi

```bash
docker-compose up -d
```

Attendi che i container siano pronti (circa 30 secondi).

### 3. Verificare Stato

```bash
# Health check
curl http://localhost:8000/health

# Oppure apri nel browser
open http://localhost:8000/docs
```

### 4. Creare Prima Entità

```bash
# Creare un datasource
curl -X POST http://localhost:8000/api/v1/ontology/datasources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Database",
    "engine": "postgres"
  }'
```

Salva l'`id` restituito per i prossimi step.

### 5. Creare Tabella con Colonne

```bash
# Sostituisci <DATASOURCE_ID> con l'id del passo precedente
curl -X POST http://localhost:8000/api/v1/ontology/tables \
  -H "Content-Type: application/json" \
  -d '{
    "datasource_id": "<DATASOURCE_ID>",
    "physical_name": "customers",
    "semantic_name": "Customers Table",
    "description": "Tabella clienti del sistema e-commerce",
    "columns": [
      {
        "name": "id",
        "data_type": "INT",
        "is_primary_key": true,
        "semantic_name": "Customer ID",
        "description": "Identificativo univoco cliente"
      },
      {
        "name": "email",
        "data_type": "VARCHAR(255)",
        "is_primary_key": false,
        "semantic_name": "Email Address",
        "description": "Indirizzo email del cliente"
      }
    ]
  }'
```

## Utilizzo con Makefile

```bash
# Avviare servizi
make up

# Visualizzare logs
make logs

# Eseguire test
make test

# Creare migrazione
make migrate-create MESSAGE="Initial migration"

# Applicare migrazioni
make migrate

# Shell Python
make shell

# Shell Database
make db-shell

# Health check
make health

# Fermare servizi
make down
```

## Esempi Pratici

### Workflow Completo

```bash
# 1. Creare datasource
DATASOURCE_ID=$(curl -s -X POST http://localhost:8000/api/v1/ontology/datasources \
  -H "Content-Type: application/json" \
  -d '{"name": "E-commerce DB", "engine": "postgres"}' | jq -r '.id')

# 2. Creare tabella
TABLE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/ontology/tables \
  -H "Content-Type: application/json" \
  -d "{
    \"datasource_id\": \"$DATASOURCE_ID\",
    \"physical_name\": \"orders\",
    \"semantic_name\": \"Orders\",
    \"description\": \"Tabella ordini\",
    \"columns\": [
      {\"name\": \"id\", \"data_type\": \"INT\", \"is_primary_key\": true},
      {\"name\": \"total\", \"data_type\": \"DECIMAL(10,2)\", \"is_primary_key\": false}
    ]
  }")

TABLE_ID=$(echo $TABLE_RESPONSE | jq -r '.id')
COLUMN_ID=$(echo $TABLE_RESPONSE | jq -r '.columns[1].id')

# 3. Creare sinonimi
curl -X POST http://localhost:8000/api/v1/semantics/synonyms/bulk \
  -H "Content-Type: application/json" \
  -d "{
    \"target_id\": \"$TABLE_ID\",
    \"target_type\": \"TABLE\",
    \"terms\": [\"Ordini\", \"Acquisti\", \"Transazioni\"]
  }"

# 4. Creare metrica
curl -X POST http://localhost:8000/api/v1/semantics/metrics \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Total Sales\",
    \"description\": \"Vendite totali\",
    \"sql_expression\": \"SUM(orders.total)\",
    \"required_table_ids\": [\"$TABLE_ID\"]
  }"

# 5. Aggiungere golden SQL example
curl -X POST http://localhost:8000/api/v1/learning/golden-sql \
  -H "Content-Type: application/json" \
  -d "{
    \"datasource_id\": \"$DATASOURCE_ID\",
    \"prompt_text\": \"Quanto abbiamo venduto in totale?\",
    \"sql_query\": \"SELECT SUM(total) FROM orders\",
    \"complexity\": 1,
    \"verified\": true
  }"
```

## Documentazione Interattiva

Una volta avviato il servizio:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Troubleshooting

### Container non si avvia

```bash
# Verificare logs
docker-compose logs api

# Verificare che PostgreSQL sia attivo
docker-compose ps
```

### Errore "OpenAI API key not found"

Assicurati di aver impostato `OPENAI_API_KEY` nel file `.env`:
```bash
echo $OPENAI_API_KEY  # Deve essere impostato
```

### Errore di connessione database

```bash
# Verificare che il database sia pronto
docker-compose exec db psql -U semantic_user -d semantic_sql -c "SELECT 1"

# Se necessario, ricreare il database
docker-compose down -v
docker-compose up -d
```

### Porta già in uso

Se la porta 8000 è occupata, modifica `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Cambia 8001 con una porta libera
```

## Prossimi Passi

1. Leggi [API_DOCUMENTATION.md](API_DOCUMENTATION.md) per dettagli completi delle API
2. Leggi [ARCHITECTURE.md](ARCHITECTURE.md) per capire l'architettura
3. Leggi [DEPLOYMENT.md](DEPLOYMENT.md) per setup produzione
4. Esplora i test in `tests/` per esempi d'uso

## Supporto

- Documentazione API: `/docs`
- Issues: GitHub
- Logs: `docker-compose logs -f`
