# Fix: OpenAI SDK Compatibility Issue

## Problema

Errore all'avvio del servizio:
```
TypeError: Client.__init__() got an unexpected keyword argument 'proxies'
```

## Causa

Incompatibilità tra le versioni di `openai` SDK (1.3.0) e `httpx`. La versione vecchia di OpenAI SDK tentava di passare il parametro `proxies` a `httpx.Client` che non lo supportava nella versione installata.

## Soluzione Applicata

1. **Aggiornato `openai`**: da `^1.3.0` a `^1.12.0` in `pyproject.toml`
2. **Aggiunto `httpx` esplicito**: `httpx>=0.25.1` come dipendenza runtime
3. **Aggiornato Dockerfile**: installa `openai>=1.12.0` e `httpx>=0.25.1`

## File Modificati

- `pyproject.toml`: Aggiornata versione openai e aggiunto httpx
- `Dockerfile`: Aggiornate versioni nelle installazioni pip
- `src/services/embedding_service.py`: Nessuna modifica necessaria, solo versione SDK

## Come Applicare

```bash
# Fermare i container
docker-compose down

# Ricostruire l'immagine
docker-compose build --no-cache api

# Riavviare i servizi
docker-compose up -d
```

## Verifica

Dopo il riavvio, verificare che il servizio parta correttamente:

```bash
docker-compose logs api
curl http://localhost:8000/health
```

## Note

- Assicurarsi che `OPENAI_API_KEY` sia impostata nel file `.env`
- Le nuove versioni sono retrocompatibili, nessuna modifica al codice necessario
