# Discovery API - Guida per Agenti AI

Questa documentazione descrive come utilizzare la Discovery API per agenti AI che implementano text-to-sql. L'API fornisce ricerca semantica ibrida (vector + full-text) su tutto il knowledge graph.

## Indice

1. [Overview](#overview)
2. [Architettura](#architettura)
3. [Endpoint Discovery API](#endpoint-discovery-api)
4. [Workflow Tipici](#workflow-tipici)
5. [Best Practices](#best-practices)
6. [Verifica Sistema](#verifica-sistema)
7. [Esempi di Codice](#esempi-di-codice)

---

## Overview

### Scopo

La Discovery API è progettata specificamente per agenti AI che devono:
- Cercare tabelle, colonne, relazioni rilevanti per una query in linguaggio naturale
- Trovare metriche semantiche predefinite
- Recuperare esempi golden SQL simili (few-shot learning)
- Costruire contesto per generazione SQL

### Caratteristiche Principali

- **Ricerca Semantica Ibrida**: Combina vector search (embeddings) e full-text search (PostgreSQL FTS)
- **Supporto Multilingua**: Funziona con italiano, inglese, e altre lingue
- **Filtri Flessibili**: Filtra per datasource, table, column per scope preciso
- **Score di Rilevanza**: Ogni risultato include uno score per ranking
- **Performance Ottimizzate**: Indici HNSW, indici compositi, N+1 queries risolte

### Base URL

```
http://localhost:8000/api/v1/discovery
```

---

## Architettura

### Pattern di Ricerca

L'API usa **Reciprocal Rank Fusion (RRF)** per combinare:
1. **Vector Search**: Similarità semantica usando embeddings (OpenAI text-embedding-3-small)
2. **Full-Text Search**: Matching esatto di keywords usando PostgreSQL TSVECTOR

I risultati vengono fusi usando RRF, dando priorità a risultati che appaiono in entrambe le ricerche.

### Struttura Dati

```
Datasource
  ├── Tables
  │     ├── Columns
  │     │     ├── Context Rules
  │     │     └── Low Cardinality Values
  │     └── Edges (Relationships)
  ├── Metrics (Semantic)
  ├── Synonyms
  └── Golden SQL Examples
```

---

## Endpoint Discovery API

### 1. POST /datasources

Cerca datasources per dominio o descrizione.

**Request**:
```json
{
  "query": "e-commerce sales",
  "limit": 10
}
```

**Response**:
```json
[
  {
    "id": "uuid",
    "slug": "ecommerce_ds",
    "name": "E-Commerce Database",
    "description": "Main e-commerce database",
    "engine": "postgres",
    "context_signature": "sales, orders, products",
    "created_at": "2026-01-13T10:00:00Z",
    "updated_at": null
  }
]
```

**Use Case**: Trovare il datasource corretto per una query.

---

### 2. POST /tables

Cerca tabelle con filtro opzionale per datasource.

**Request**:
```json
{
  "query": "ordini prodotti",
  "datasource_slug": "ecommerce_ds",
  "limit": 10
}
```

**Response**:
```json
[
  {
    "id": "uuid",
    "datasource_id": "uuid",
    "slug": "ordini_table",
    "physical_name": "t_ordini",
    "semantic_name": "Ordini",
    "description": "Tabella principale degli ordini",
    "ddl_context": "CREATE TABLE t_ordini (...)",
    "created_at": "2026-01-13T10:00:00Z",
    "updated_at": null
  }
]
```

**Use Case**: Trovare tabelle rilevanti per costruire la query SQL.

**Filtri**:
- `datasource_slug` (opzionale): Limita ricerca a un datasource specifico

---

### 3. POST /columns

Cerca colonne con filtri multipli (datasource, table).

**Request**:
```json
{
  "query": "importo totale",
  "datasource_slug": "ecommerce_ds",
  "table_slug": "ordini_table",
  "limit": 10
}
```

**Response**:
```json
[
  {
    "id": "uuid",
    "table_id": "uuid",
    "table_slug": "ordini_table",
    "slug": "importo_totale_col",
    "name": "importo_totale",
    "semantic_name": "Importo Totale",
    "data_type": "DECIMAL(10,2)",
    "is_primary_key": false,
    "description": "Importo totale incluso IVA",
    "context_note": "NULL significa ordine cancellato",
    "created_at": "2026-01-13T10:00:00Z",
    "updated_at": null
  }
]
```

**Use Case**: Trovare colonne specifiche per SELECT, WHERE, GROUP BY.

**Filtri**:
- `datasource_slug` (opzionale): Limita a datasource
- `table_slug` (opzionale): Limita a tabella specifica
- Entrambi possono essere usati insieme

---

### 4. POST /edges

Cerca relazioni/edges tra tabelle per costruire JOIN.

**Request**:
```json
{
  "query": "ordine cliente",
  "datasource_slug": "ecommerce_ds",
  "table_slug": "ordini_table",
  "limit": 10
}
```

**Response**:
```json
[
  {
    "id": "uuid",
    "source_column_id": "uuid",
    "target_column_id": "uuid",
    "source": "ordini_table.cliente_id_col",
    "target": "clienti_table.cliente_id_pk_col",
    "relationship_type": "MANY_TO_ONE",
    "is_inferred": false,
    "description": "Ordine appartiene a Cliente",
    "context_note": null,
    "created_at": "2026-01-13T10:00:00Z"
  }
]
```

**Use Case**: Trovare come fare JOIN tra tabelle.

**Filtri**:
- `datasource_slug` (opzionale): Limita a datasource
- `table_slug` (opzionale): Trova edges che coinvolgono questa tabella (source o target)

---

### 5. POST /metrics

Cerca metriche semantiche predefinite.

**Request**:
```json
{
  "query": "ricavi totali",
  "datasource_slug": "ecommerce_ds",
  "limit": 10
}
```

**Response**:
```json
[
  {
    "id": "uuid",
    "datasource_id": "uuid",
    "slug": "ricavi_totali_metric",
    "name": "Ricavi Totali",
    "description": "Somma di tutti gli importi degli ordini completati",
    "calculation_sql": "SELECT SUM(importo_totale) FROM t_ordini WHERE stato = 'COMPLETATO'",
    "required_tables": ["t_ordini"],
    "filter_condition": "stato = 'COMPLETATO'",
    "created_at": "2026-01-13T10:00:00Z",
    "updated_at": null
  }
]
```

**Use Case**: Usare metriche predefinite invece di costruire SQL da zero.

**Filtri**:
- `datasource_slug` (opzionale): Limita a datasource

---

### 6. POST /synonyms

Cerca sinonimi che mappano termini a entità.

**Request**:
```json
{
  "query": "clients",
  "datasource_slug": "ecommerce_ds",
  "limit": 10
}
```

**Response**:
```json
[
  {
    "id": "uuid",
    "term": "clients",
    "target_id": "uuid",
    "target_type": "TABLE",
    "maps_to_slug": "clienti_table",
    "created_at": "2026-01-13T10:00:00Z"
  }
]
```

**Use Case**: Risolvere sinonimi e varianti terminologiche.

**Filtri**:
- `datasource_slug` (opzionale): Limita a datasource

---

### 7. POST /golden_sql

Cerca esempi golden SQL simili per few-shot learning.

**Request**:
```json
{
  "query": "Prodotti quasi finiti",
  "datasource_slug": "ecommerce_ds",
  "limit": 3
}
```

**Response**:
```json
[
  {
    "id": "uuid",
    "datasource_id": "uuid",
    "prompt": "Prodotti quasi finiti",
    "sql": "SELECT * FROM t_prodotti WHERE stato = 'SEMI_FINITO'",
    "complexity": 2,
    "verified": true,
    "score": 0.85,
    "created_at": "2026-01-13T10:00:00Z",
    "updated_at": null
  }
]
```

**Use Case**: Few-shot learning - usare esempi simili per guidare la generazione SQL.

**Filtri**:
- `datasource_slug` (opzionale): Limita a datasource

**Note**: 
- `score` indica rilevanza semantica (più alto = più rilevante)
- `complexity` (1-5) può essere usato per filtrare esempi di difficoltà simile

---

### 8. POST /context_rules

Cerca regole di contesto per colonne.

**Request**:
```json
{
  "query": "IVA importo",
  "datasource_slug": "ecommerce_ds",
  "table_slug": "ordini_table",
  "limit": 10
}
```

**Response**:
```json
[
  {
    "id": "uuid",
    "column_id": "uuid",
    "slug": "rule_importo_iva",
    "rule_text": "L'importo include sempre l'IVA al 22%",
    "created_at": "2026-01-13T10:00:00Z",
    "updated_at": null
  }
]
```

**Use Case**: Ottenere contesto business per interpretare correttamente i dati.

**Filtri**:
- `datasource_slug` (opzionale): Limita a datasource
- `table_slug` (opzionale): Limita a tabella

---

### 9. POST /low_cardinality_values

Cerca valori nominali (categorical values) per colonne.

**Request**:
```json
{
  "query": "finito",
  "datasource_slug": "ecommerce_ds",
  "table_slug": "prodotti_table",
  "column_slug": "stato_prodotto_col",
  "limit": 10
}
```

**Response**:
```json
[
  {
    "id": "uuid",
    "column_id": "uuid",
    "column_slug": "stato_prodotto_col",
    "table_slug": "prodotti_table",
    "value_raw": "FINITO",
    "value_label": "Prodotto Finito",
    "created_at": "2026-01-13T10:00:00Z",
    "updated_at": null
  }
]
```

**Use Case**: Trovare valori validi per colonne categoriche (es. stati, tipi).

**Filtri**:
- `datasource_slug` (opzionale)
- `table_slug` (opzionale)
- `column_slug` (opzionale): Limita a colonna specifica

---

## Workflow Tipici

### Workflow 1: Ricerca Semplice Tabella

**Scenario**: Agente cerca "ordini" per trovare la tabella rilevante.

```python
# Step 1: Cerca datasource
datasources = api.post("/discovery/datasources", json={"query": "e-commerce"})
ds_slug = datasources[0]["slug"]

# Step 2: Cerca tabelle
tables = api.post("/discovery/tables", json={
    "query": "ordini",
    "datasource_slug": ds_slug
})
ordini_table = tables[0]
```

---

### Workflow 2: Costruzione Query Complessa con JOIN

**Scenario**: Agente deve costruire query "Mostra ordini con nome cliente".

```python
# Step 1: Trova tabella ordini
tables = api.post("/discovery/tables", json={
    "query": "ordini",
    "datasource_slug": ds_slug
})
ordini_table = tables[0]

# Step 2: Trova colonne ordini
columns = api.post("/discovery/columns", json={
    "query": "cliente",
    "datasource_slug": ds_slug,
    "table_slug": ordini_table["slug"]
})
cliente_id_col = next(c for c in columns if "cliente" in c["slug"])

# Step 3: Trova relazioni per JOIN
edges = api.post("/discovery/edges", json={
    "query": "",
    "datasource_slug": ds_slug,
    "table_slug": ordini_table["slug"]
})
# Trova edge che collega ordini a clienti
ordine_cliente_edge = next(
    e for e in edges 
    if "cliente" in e["target"] and ordini_table["slug"] in e["source"]
)

# Step 4: Costruisci SQL
# JOIN usando source e target dall'edge
sql = f"""
SELECT o.*, c.nome 
FROM {ordini_table["physical_name"]} o
JOIN {ordine_cliente_edge["target"].split(".")[0]} c 
  ON o.{cliente_id_col["name"]} = c.{ordine_cliente_edge["target"].split(".")[1]}
"""
```

---

### Workflow 3: Ricerca Metriche Semantiche

**Scenario**: Agente cerca "ricavi" e usa metrica predefinita.

```python
# Cerca metriche
metrics = api.post("/discovery/metrics", json={
    "query": "ricavi totali",
    "datasource_slug": ds_slug
})

if metrics:
    # Usa SQL predefinito invece di costruirlo
    metric = metrics[0]
    sql = metric["calculation_sql"]
    # SQL già validato e ottimizzato!
else:
    # Fallback: costruisci SQL manualmente
    ...
```

---

### Workflow 4: Few-Shot Learning con Golden SQL

**Scenario**: Agente usa esempi simili per generare SQL.

```python
# Cerca esempi simili
golden_sqls = api.post("/discovery/golden_sql", json={
    "query": "Prodotti quasi finiti",
    "datasource_slug": ds_slug,
    "limit": 3
})

# Usa i top 3 esempi come few-shot context per LLM
few_shot_examples = [
    {
        "prompt": g["prompt"],
        "sql": g["sql"]
    }
    for g in golden_sqls[:3]
]

# Invia a LLM con few-shot examples
llm_prompt = f"""
Ecco esempi simili:
{format_examples(few_shot_examples)}

Genera SQL per: "Prodotti quasi finiti"
"""
```

---

## Best Practices

### 1. Strutturare Query per Migliori Risultati

**Buone Pratiche**:
- Usa termini specifici del dominio: "ordini e-commerce" invece di "tabelle"
- Includi contesto: "importo totale ordini" invece di "importo"
- Usa sinonimi comuni: "clienti" o "clients" funzionano entrambi

**Esempi**:
```python
# ✅ Buono: Specifico e contestualizzato
api.post("/discovery/tables", json={"query": "ordini e-commerce con importi"})

# ❌ Evitare: Troppo generico
api.post("/discovery/tables", json={"query": "tabelle"})
```

### 2. Quando Usare Filtri vs Ricerca Globale

**Usa Filtri Quando**:
- Conosci già il datasource (sempre consigliato se possibile)
- Stai cercando colonne di una tabella specifica
- Vuoi risultati più precisi e veloci

**Ricerca Globale Quando**:
- Non conosci il datasource
- Stai esplorando il knowledge graph
- Vuoi vedere tutti i risultati possibili

**Esempio**:
```python
# ✅ Con filtro: Più preciso
columns = api.post("/discovery/columns", json={
    "query": "importo",
    "datasource_slug": ds_slug,
    "table_slug": "ordini_table"
})

# ⚠️ Senza filtro: Più lento, più risultati
columns = api.post("/discovery/columns", json={"query": "importo"})
```

### 3. Interpretare Score di Rilevanza

Lo `score` nei risultati indica rilevanza semantica:
- **Score > 0.05**: Molto rilevante (appare in entrambe le ricerche)
- **Score 0.01-0.05**: Rilevante (appare in una ricerca)
- **Score < 0.01**: Poco rilevante (considera filtrare)

**Esempio**:
```python
results = api.post("/discovery/golden_sql", json={"query": "..."})
# Filtra per score minimo
relevant = [r for r in results if r["score"] > 0.02]
```

### 4. Gestione Errori e Edge Cases

**Query Vuote**:
- `golden_sql` ritorna lista vuota se query è vuota
- Altri endpoint possono ritornare risultati anche con query vuota (se non filtrati)

**Filtri Non Esistenti**:
- Se `datasource_slug` non esiste, ritorna lista vuota
- Comportamento coerente: nessun errore, solo risultati vuoti

**Nessun Risultato**:
- Tutti gli endpoint ritornano `[]` se nessun risultato
- Controlla sempre `len(results) > 0` prima di usare risultati

---

## Verifica Sistema

### Checklist Verifica

#### ✅ Endpoint Funzionanti

Tutti gli endpoint discovery sono operativi:
- [x] `POST /datasources` - Funziona
- [x] `POST /tables` - Funziona
- [x] `POST /columns` - Funziona
- [x] `POST /edges` - Funziona
- [x] `POST /metrics` - Funziona
- [x] `POST /synonyms` - Funziona
- [x] `POST /golden_sql` - Funziona
- [x] `POST /context_rules` - Funziona
- [x] `POST /low_cardinality_values` - Funziona

#### ✅ Performance

- [x] **N+1 Queries Risolte**: `search_columns` e `search_synonyms` usano batch loading
- [x] **Indici Utilizzati**: Indici compositi e foreign keys creati
- [x] **Vector Search**: Indici HNSW creati su tutte le colonne embedding
- [x] **Tempi di Risposta**: < 200ms per query tipiche

#### ✅ Supporto Multilingua

- [x] **Ricerca Italiana**: Funziona con `search_vector` in 'simple'
- [x] **Query Italiane**: "Prodotti quasi finiti" trova risultati rilevanti
- [x] **Descrizioni Multilingua**: Supportate correttamente

#### ✅ Integrità Dati

- [x] **Constraint Unici**: Prevengono duplicati
- [x] **NOT NULL**: `semantic_metrics.datasource_id` è NOT NULL
- [x] **Relazioni**: Foreign keys hanno indici

#### ✅ Materialized View

- [x] **View Creata**: `mv_schema_edges_expanded` esiste
- [x] **Funzione Refresh**: `refresh_schema_edges_view()` disponibile
- [x] **Indici View**: Indici creati per query veloci

### Test di Verifica

Eseguire i test per verificare tutto:

```bash
# Test migration
pytest tests/test_migration.py -v

# Test agentic completi
pytest tests/test_agentic.py -v

# Test discovery esistenti
pytest tests/test_retrieval_discovery.py -v
```

Tutti i test dovrebbero passare.

---

## Esempi di Codice

### Client API Python

```python
import requests
from typing import List, Dict, Optional

class DiscoveryAPIClient:
    """Client per Discovery API per agenti AI"""
    
    def __init__(self, base_url: str = "http://localhost:8000/api/v1/discovery"):
        self.base_url = base_url
    
    def search_datasources(self, query: str, limit: int = 10) -> List[Dict]:
        """Cerca datasources"""
        response = requests.post(
            f"{self.base_url}/datasources",
            json={"query": query, "limit": limit}
        )
        response.raise_for_status()
        return response.json()
    
    def search_tables(self, query: str, datasource_slug: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Cerca tabelle"""
        payload = {"query": query, "limit": limit}
        if datasource_slug:
            payload["datasource_slug"] = datasource_slug
        
        response = requests.post(f"{self.base_url}/tables", json=payload)
        response.raise_for_status()
        return response.json()
    
    def search_columns(self, query: str, datasource_slug: Optional[str] = None, 
                      table_slug: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Cerca colonne"""
        payload = {"query": query, "limit": limit}
        if datasource_slug:
            payload["datasource_slug"] = datasource_slug
        if table_slug:
            payload["table_slug"] = table_slug
        
        response = requests.post(f"{self.base_url}/columns", json=payload)
        response.raise_for_status()
        return response.json()
    
    def search_golden_sql(self, query: str, datasource_slug: Optional[str] = None, limit: int = 3) -> List[Dict]:
        """Cerca golden SQL examples per few-shot learning"""
        payload = {"query": query, "limit": limit}
        if datasource_slug:
            payload["datasource_slug"] = datasource_slug
        
        response = requests.post(f"{self.base_url}/golden_sql", json=payload)
        response.raise_for_status()
        return response.json()
    
    def search_edges(self, query: str, datasource_slug: Optional[str] = None, 
                    table_slug: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Cerca relazioni/edges"""
        payload = {"query": query, "limit": limit}
        if datasource_slug:
            payload["datasource_slug"] = datasource_slug
        if table_slug:
            payload["table_slug"] = table_slug
        
        response = requests.post(f"{self.base_url}/edges", json=payload)
        response.raise_for_status()
        return response.json()


# Esempio di utilizzo
client = DiscoveryAPIClient()

# Workflow completo
datasources = client.search_datasources("e-commerce")
ds_slug = datasources[0]["slug"]

tables = client.search_tables("ordini", datasource_slug=ds_slug)
columns = client.search_columns("importo", datasource_slug=ds_slug, table_slug=tables[0]["slug"])
edges = client.search_edges("", datasource_slug=ds_slug, table_slug=tables[0]["slug"])
golden_sqls = client.search_golden_sql("ricavi mese", datasource_slug=ds_slug)
```

### Pattern di Ricerca

```python
def build_sql_context(user_query: str, datasource_slug: str) -> Dict:
    """
    Costruisce contesto completo per generazione SQL.
    
    Returns:
        Dict con tutte le informazioni necessarie per LLM
    """
    client = DiscoveryAPIClient()
    
    # 1. Trova tabelle rilevanti
    tables = client.search_tables(user_query, datasource_slug=datasource_slug, limit=5)
    
    # 2. Per ogni tabella, trova colonne
    all_columns = []
    for table in tables:
        cols = client.search_columns(user_query, datasource_slug=datasource_slug, 
                                     table_slug=table["slug"], limit=10)
        all_columns.extend(cols)
    
    # 3. Trova relazioni tra tabelle
    edges = []
    for table in tables:
        table_edges = client.search_edges("", datasource_slug=datasource_slug, 
                                          table_slug=table["slug"], limit=10)
        edges.extend(table_edges)
    
    # 4. Trova metriche semantiche
    metrics = client.search_metrics(user_query, datasource_slug=datasource_slug, limit=3)
    
    # 5. Trova golden SQL examples
    golden_sqls = client.search_golden_sql(user_query, datasource_slug=datasource_slug, limit=3)
    
    return {
        "tables": tables,
        "columns": all_columns,
        "edges": edges,
        "metrics": metrics,
        "golden_sql_examples": golden_sqls,
        "user_query": user_query
    }
```

### Costruzione Contesto per LLM

```python
def format_context_for_llm(context: Dict) -> str:
    """Formatta contesto per prompt LLM"""
    
    prompt = f"Query utente: {context['user_query']}\n\n"
    
    # Tabelle
    prompt += "## Tabelle Disponibili\n"
    for table in context["tables"]:
        prompt += f"- {table['semantic_name']} ({table['physical_name']}): {table.get('description', '')}\n"
    
    # Colonne
    prompt += "\n## Colonne Rilevanti\n"
    for col in context["columns"][:20]:  # Limita a top 20
        prompt += f"- {col['semantic_name']} ({col['name']}): {col.get('description', '')}\n"
    
    # Relazioni
    prompt += "\n## Relazioni\n"
    for edge in context["edges"][:10]:
        prompt += f"- {edge['source']} -> {edge['target']} ({edge['relationship_type']})\n"
    
    # Metriche
    if context["metrics"]:
        prompt += "\n## Metriche Semantiche Disponibili\n"
        for metric in context["metrics"]:
            prompt += f"- {metric['name']}: {metric['description']}\n"
            prompt += f"  SQL: {metric['calculation_sql']}\n"
    
    # Golden SQL Examples
    if context["golden_sql_examples"]:
        prompt += "\n## Esempi Simili\n"
        for ex in context["golden_sql_examples"]:
            prompt += f"Q: {ex['prompt']}\n"
            prompt += f"A: {ex['sql']}\n\n"
    
    prompt += "\nGenera SQL per la query utente."
    return prompt
```

---

## Note Finali

### Limitazioni Conosciute

1. **Materialized View**: `mv_schema_edges_expanded` richiede refresh manuale quando cambiano i dati
2. **Indici Vectoriali**: Creazione può richiedere tempo su dataset molto grandi
3. **Score RRF**: I score sono relativi, non assoluti (usare per ranking, non threshold assoluti)

### Roadmap Futura

- [ ] Auto-refresh materialized view via trigger
- [ ] Caching risultati ricerca frequenti
- [ ] Supporto per più lingue specifiche (francese, tedesco, spagnolo)
- [ ] API streaming per risultati grandi
- [ ] Filtri avanzati (date range, complexity range, etc.)

### Supporto

Per problemi o domande:
- Verifica i test in `tests/test_agentic.py`
- Controlla i log dell'API per errori
- Verifica che la migration sia applicata: `alembic current`

---

**Ultimo Aggiornamento**: 2026-01-13
**Versione API**: 0.1.0
