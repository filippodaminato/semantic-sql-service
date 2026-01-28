# Semantic SQL Engine - Management API

Enterprise microservice for managing semantic knowledge to generate SQL queries.

## 🏗️ Architecture

The system implements an architecture with 4 main domains:

1. **Physical Ontology**: Physical schema management (tables, columns, relations)
2. **Business Semantics**: Semantic abstraction (metrics, synonyms)
3. **Context & Values**: Contextual intelligence (nominal values, rules)
4. **Learning**: Few-shot learning (golden SQL examples)

## 🚀 Quick Start

Follow these steps to start the entire stack, load data, and test the system.

### 1. Environment Setup

Copy the configuration file and set your `OPENAI_API_KEY`:

```bash
cp .env.example .env
nano .env # Insert your OpenAI API Key
```

### 2. Start Services

Start the database and backend API with Docker Compose:

```bash
docker-compose up -d
```

Wait a few seconds for the database to be ready.

### 3. Load Data (Seeding)

Run the seed script to populate the database with the example schema (WMS):

```bash
# Run DB migrations and populate with data
docker-compose exec api alembic upgrade head
docker-compose exec api python scripts/seed_wms_metadata.py
```

### 4. Start Frontend (Playground)

To use the API visually, start the frontend application:

```bash
cd tools/semantic-sql-frontend
npm start
```

Now open your browser at: [http://localhost:4200](http://localhost:4200)

### 5. Test Text-to-SQL (Agent Workflow)

To test Text-to-SQL generation via the Python Agent CLI:

1. Navigate to the workflow folder:
   ```bash
   cd tools/agents-research/workflow-v1
   ```

2. Ensure dependencies are installed (recommended in a virtualenv):
   ```bash
   # Dependencies are managed in the main project (see root pyproject.toml)
   # Ensure you have the virtual environment active with installed dependencies
   # Ensure OPENAI_API_KEY is set in your environment or in the .env in this folder
   ```

3. Run the agent:
   ```bash
   python main.py "How many orders were shipped yesterday?"
   ```

   Or in interactive mode:
   ```bash
   python main.py
   ```

4. **Debug Logs**:
   To visualize execution logs, open `tools/agents-research/workflow-v1/debugger-ui/index.html` in your browser.
   Then select the JSONL log file generated in `tools/agents-research/workflow-v1/logs/`.

## 🏗️ Useful Resources

- **Database Admin (PgAdmin)**: http://localhost:5050 (Login: `admin@admin.com` / `admin`)

## 📦 Main Folder Structure

- `src/`: Backend API source code
- `scripts/`: Seeding and maintenance scripts (e.g. `seed_wms_metadata.py`)
- `tools/agents-research/workflow-v1/`: Text-to-SQL Agent code and Debugger UI
- `tools/semantic-sql-frontend/`: Frontend Angular Application
