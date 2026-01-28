from langchain_core.prompts import ChatPromptTemplate
from generation.schemas import GeneratedSQL, ValidationResult

# --- GENERATOR PROMPT ---
GENERATOR_SYSTEM_PROMPT = """
You are a Senior SQL Developer (Dialect: PostgreSQL).
Your Job: Convert the provided **Technical Blueprint** into executable SQL.

**INPUTS:**
1. **Schema:** A cleaned JSON schema.
2. **Blueprint:** A set of logical steps and constraints.

**RULES:**
- **Strict Adherence:** Follow the `logical_steps` in the Blueprint exactly.
- **Trusted Context:** Use the `necessary_filters` and `enrichment_notes` as absolute truth. Do not hallucinate new filters.
- **Output:** Valid, optimized SQL code.
- **Naming:** Use the **Physical Names** for tables and columns (e.g. `stock_quantity`, NOT `wms_stock_quantity`). Only use slugs if they match the physical name.

**BLUEPRINT TO CODE MAPPING:**
- If Blueprint says "Use CTE", use `WITH ...`.
- If Blueprint mentions a specific JOIN path, write that specific ON condition.
"""

def build_generator_chain(llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", GENERATOR_SYSTEM_PROMPT),
        ("human", """
        BLUEPRINT:
        {blueprint_json}
        
        SCHEMA CONTEXT:
        {schema_context}
        
        (If this is a retry) PREVIOUS ERROR:
        {previous_error}
        """)
    ])
    chain = prompt | llm.with_structured_output(GeneratedSQL)
    return chain, prompt

# --- VALIDATOR PROMPT (The Linter) ---
# If you don't have a DB connected to do 'EXPLAIN', we use an LLM as a static Linter.
VALIDATOR_SYSTEM_PROMPT = """
You are a SQL Syntax Checker.
Analyze the provided SQL query against the Schema.

CHECK FOR:
1. **Syntax Errors:** Missing commas, wrong keywords.
2. **Hallucinations:** Using columns not present in the Schema provided.
3. **Logic Flaws:** GROUP BY mismatches.

If valid, return is_valid=True.
If invalid, provide the specific error message.
"""

def build_validator_chain(llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", VALIDATOR_SYSTEM_PROMPT),
        ("human", "SCHEMA:\n{schema_context}\n\nSQL TO CHECK:\n{sql_code}")
    ])
    chain = prompt | llm.with_structured_output(ValidationResult)
    return chain, prompt