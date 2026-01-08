# API Documentation

Documentazione completa delle API REST Level 2 per il Semantic SQL Engine Management API.

## Base URL

```
http://localhost:8000
```

## Autenticazione

Attualmente non è implementata autenticazione. In produzione, aggiungere JWT o API keys.

## Domini API

### 1. Physical Ontology (Schema Management)

#### POST /api/v1/ontology/datasources

Crea un nuovo datasource. Richiesto prima di creare tabelle.

**Request Body:**
```json
{
  "name": "Sales DWH Prod",
  "engine": "postgres",
  "schema_scan_config": {
    "whitelist": ["public", "sales"],
    "blacklist": ["temp"]
  }
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Sales DWH Prod",
  "engine": "postgres",
  "schema_scan_config": {...},
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": null
}
```

**Errori:**
- `409 Conflict`: Nome datasource già esistente

---

#### POST /api/v1/ontology/tables

**Deep Create**: Crea una tabella e opzionalmente tutte le sue colonne in una singola transazione.

**Request Body:**
```json
{
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
      "semantic_name": "Importo Totale",
      "description": "Importo totale della transazione",
      "context_note": "Include IVA. Se null, transazione fallita."
    },
    {
      "name": "cust_id",
      "data_type": "INT",
      "is_primary_key": false,
      "description": "Foreign key verso tabella Clienti"
    }
  ]
}
```

**Response:** `201 Created`

**Logica Backend:**
1. Valida che `physical_name` sia univoco per quel Datasource
2. Salva Table
3. Salva le Columns linkandole alla Table
4. Genera embedding per `semantic_name + description` e salva il vettore

**Errori:**
- `404 Not Found`: Datasource non trovato
- `409 Conflict`: `physical_name` già esistente per questo datasource
- `422 Unprocessable Entity`: Validazione fallita (es. spazi in physical_name)

---

#### PATCH /api/v1/ontology/columns/{column_id}

Modifica fine di una colonna specifica.

**Request Body (tutti i campi sono opzionali):**
```json
{
  "semantic_name": "Importo Totale (Ivato)",
  "context_note": "ATTENZIONE: Usare solo per report finanziari, non per logistica.",
  "is_primary_key": true,
  "data_type": "DECIMAL(12,2)",
  "description": "Nuova descrizione"
}
```

**Response:** `200 OK`

**Note:**
- Campi omessi non vengono modificati
- Se vengono modificati `semantic_name`, `description` o `context_note`, l'embedding viene ricalcolato automaticamente

**Errori:**
- `404 Not Found`: Colonna non trovata

---

#### POST /api/v1/ontology/relationships

Definizione manuale dei JOIN. Fondamentale perché non facciamo reflection automatica.

**Request Body:**
```json
{
  "source_column_id": "550e8400-e29b-41d4-a716-446655440000",
  "target_column_id": "660e8400-e29b-41d4-a716-446655440001",
  "relationship_type": "ONE_TO_MANY",
  "is_inferred": false
}
```

**Response:** `201 Created`

**Tipi di relationship:**
- `ONE_TO_ONE`
- `ONE_TO_MANY`
- `MANY_TO_MANY`

**Comportamento Idempotente:**
- Se la relazione esiste già, restituisce quella esistente (stesso ID)

**Errori:**
- `400 Bad Request`: Source e target sono la stessa colonna
- `404 Not Found`: Una delle colonne non esiste

---

### 2. Business Semantics

#### POST /api/v1/semantics/metrics

Definizione di un calcolo riutilizzabile (metrica).

**Request Body:**
```json
{
  "name": "Average Basket Size",
  "description": "Valore medio del carrello per ordini completati",
  "sql_expression": "AVG(t_sales.amount_total)",
  "required_table_ids": ["550e8400-e29b-41d4-a716-446655440000"],
  "filter_condition": "t_sales.status = 'COMPLETED'"
}
```

**Response:** `201 Created`

**Validazione Enterprise:**
- Il backend valida la sintassi SQL usando `sqlglot` (dry run)
- Valida che tutte le tabelle in `required_table_ids` esistano

**Errori:**
- `400 Bad Request`: Sintassi SQL non valida
- `404 Not Found`: Una o più tabelle richieste non esistono
- `409 Conflict`: Nome metrica già esistente

---

#### POST /api/v1/semantics/synonyms/bulk

Inserimento massivo di sinonimi per migliorare il retrieval.

**Request Body:**
```json
{
  "target_id": "550e8400-e29b-41d4-a716-446655440000",
  "target_type": "TABLE",
  "terms": [
    "Anagrafica Clienti",
    "Acquirenti",
    "Subscriber List",
    "Utenza"
  ]
}
```

**Response:** `201 Created` (array di sinonimi creati)

**target_type possibili:**
- `TABLE`
- `COLUMN`
- `METRIC`
- `VALUE`

**Comportamento:**
- Crea un record separato in `Semantic_Synonym` per ogni termine
- Se un sinonimo esiste già (stesso term + target), viene restituito quello esistente (idempotente)
- Utile per popolare velocemente il dizionario

**Errori:**
- `422 Unprocessable Entity`: Validazione fallita (es. termini duplicati, lista vuota)

---

### 3. Context & Values

#### POST /api/v1/context/nominal-values

Mappatura Valore Reale <-> Etichetta Umana per colonne categoriche.

**Request Body:**
```json
{
  "column_id": "550e8400-e29b-41d4-a716-446655440000",
  "values": [
    {
      "raw": "LOM",
      "label": "Lombardia"
    },
    {
      "raw": "LAZ",
      "label": "Lazio"
    },
    {
      "raw": "CAM",
      "label": "Campania"
    }
  ]
}
```

**Response:** `201 Created` (array di valori creati/aggiornati)

**Comportamento:**
- Vettorializza ogni `label`
- Quando l'agente cercherà "utenti laziali", troverà il record e saprà di dover usare `WHERE col = 'LAZ'`
- Se un valore raw esiste già per quella colonna, viene aggiornato con la nuova label (idempotente)

**Errori:**
- `404 Not Found`: Colonna non trovata
- `422 Unprocessable Entity`: Valori raw duplicati nella richiesta

---

#### POST /api/v1/context/rules

Regole di business testuali applicate a una colonna.

**Request Body:**
```json
{
  "column_id": "550e8400-e29b-41d4-a716-446655440000",
  "rule_text": "Se la data di consegna è nel futuro, l'ordine è considerato 'In Transito'. Se è NULL, l'ordine è 'In Preparazione'."
}
```

**Response:** `201 Created`

**Comportamento:**
- Genera embedding per `rule_text`
- Permette di recuperare la regola quando la query tocca l'argomento pertinente

**Errori:**
- `404 Not Found`: Colonna non trovata
- `422 Unprocessable Entity`: `rule_text` vuoto o solo spazi

---

### 4. Learning (Few-Shot)

#### POST /api/v1/learning/golden-sql

Inserimento esempi corretti per few-shot learning.

**Request Body:**
```json
{
  "datasource_id": "550e8400-e29b-41d4-a716-446655440000",
  "prompt_text": "Quanti clienti abbiamo in Lombardia?",
  "sql_query": "SELECT count(*) FROM customers WHERE region = 'LOM'",
  "complexity": 1,
  "verified": true
}
```

**Response:** `201 Created`

**Validazione:**
- Valida la sintassi SQL rispetto al dialetto del Datasource
- L'embedding viene calcolato su `prompt_text` (cruciale per il retrieval)

**complexity:** Intero da 1 a 5 (usato per selezionare esempi di difficoltà analoga)

**Errori:**
- `400 Bad Request`: Sintassi SQL non valida
- `404 Not Found`: Datasource non trovato
- `422 Unprocessable Entity`: Validazione fallita (es. complexity fuori range, prompt vuoto)

---

## Errori Standard

Tutti gli endpoint restituiscono errori nel formato:

```json
{
  "error": "Error message",
  "detail": "Detailed error information",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**Status Codes:**
- `200 OK`: Successo
- `201 Created`: Risorsa creata con successo
- `400 Bad Request`: Richiesta non valida (es. validazione SQL fallita)
- `404 Not Found`: Risorsa non trovata
- `409 Conflict`: Conflitto (es. nome già esistente)
- `422 Unprocessable Entity`: Validazione input fallita
- `500 Internal Server Error`: Errore server

---

## Principi di Design Implementati

✅ **Atomic & Bulk**: Supportiamo inserimenti singoli per precisione e bulk per velocità  
✅ **Deep Writes**: Creazione tabella + colonne in singola transazione  
✅ **Idempotenza**: Gestione duplicati senza errori (upsert dove appropriato)  
✅ **Validazione Rigorosa**: DTO con Pydantic, validazione SQL con sqlglot  
✅ **Vettorializzazione Automatica**: Embedding generati automaticamente con OpenAI  

---

## Esempi Completi

### Workflow Completo: Creare un Datasource e Popolarlo

```bash
# 1. Creare datasource
curl -X POST http://localhost:8000/api/v1/ontology/datasources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E-commerce DWH",
    "engine": "postgres"
  }'

# 2. Creare tabella con colonne
curl -X POST http://localhost:8000/api/v1/ontology/tables \
  -H "Content-Type: application/json" \
  -d '{
    "datasource_id": "<datasource_id_from_step_1>",
    "physical_name": "orders",
    "semantic_name": "Orders",
    "description": "Tabella ordini",
    "columns": [
      {"name": "id", "data_type": "INT", "is_primary_key": true},
      {"name": "customer_id", "data_type": "INT", "is_primary_key": false},
      {"name": "total_amount", "data_type": "DECIMAL(10,2)", "is_primary_key": false}
    ]
  }'

# 3. Creare sinonimi
curl -X POST http://localhost:8000/api/v1/semantics/synonyms/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "target_id": "<table_id_from_step_2>",
    "target_type": "TABLE",
    "terms": ["Ordini", "Acquisti", "Transazioni"]
  }'

# 4. Aggiungere valori nominali
curl -X POST http://localhost:8000/api/v1/context/nominal-values \
  -H "Content-Type: application/json" \
  -d '{
    "column_id": "<column_id>",
    "values": [
      {"raw": "PENDING", "label": "In Attesa"},
      {"raw": "COMPLETED", "label": "Completato"}
    ]
  }'

# 5. Aggiungere golden SQL example
curl -X POST http://localhost:8000/api/v1/learning/golden-sql \
  -H "Content-Type: application/json" \
  -d '{
    "datasource_id": "<datasource_id>",
    "prompt_text": "Mostra tutti gli ordini completati",
    "sql_query": "SELECT * FROM orders WHERE status = '\''COMPLETED'\''",
    "complexity": 1,
    "verified": true
  }'
```
