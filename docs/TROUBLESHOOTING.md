# Troubleshooting Guide

## Errore: database "semantic_user" does not exist

### Problema
Quando PostgreSQL cerca di connettersi, potrebbe cercare un database con il nome dell'utente invece del database configurato.

### Soluzione

1. **Rimuovere i volumi esistenti** (questo eliminerà i dati, ma ripartirà da zero):
```bash
docker-compose down -v
```

2. **Ricreare i container**:
```bash
docker-compose up -d
```

3. **Verificare che il database sia stato creato**:
```bash
docker-compose exec db psql -U semantic_user -d semantic_sql -c "SELECT 1;"
```

4. **Se il problema persiste, verificare i logs**:
```bash
docker-compose logs db
```

### Verifica Configurazione

Assicurati che nel `docker-compose.yml` siano impostate correttamente:
- `POSTGRES_USER: semantic_user`
- `POSTGRES_DB: semantic_sql`
- `DATABASE_URL: postgresql://semantic_user:semantic_pass@db:5432/semantic_sql`

### Re-inizializzazione Manuale

Se necessario, puoi creare manualmente il database:

```bash
# Entra nel container PostgreSQL
docker-compose exec db psql -U semantic_user -d postgres

# Crea il database se non esiste
CREATE DATABASE semantic_sql;

# Esci
\q

# Abilita l'estensione pgvector
docker-compose exec db psql -U semantic_user -d semantic_sql -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## Altri Problemi Comuni

### Container non si avvia

```bash
# Verifica i logs
docker-compose logs api
docker-compose logs db

# Riavvia i servizi
docker-compose restart
```

### Porta già in uso

Se la porta 5432 o 8000 è occupata:

```bash
# Trova il processo che usa la porta
lsof -i :5432
lsof -i :8000

# Modifica le porte nel docker-compose.yml
ports:
  - "5433:5432"  # Per PostgreSQL
  - "8001:8000"  # Per l'API
```

### Errore di connessione al database

Verifica che:
1. Il container del database sia in esecuzione: `docker-compose ps`
2. L'healthcheck sia passato: `docker-compose ps` (dovrebbe mostrare "healthy")
3. La DATABASE_URL sia corretta nel `.env` o `docker-compose.yml`
