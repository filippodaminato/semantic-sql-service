# src/main.py
import asyncio
import argparse
import uuid
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Internal Imports
from core.state import AgentState
from core.logger import setup_logger
from core.graph import build_main_graph # Assuming main graph is here

# Load env
load_dotenv()

def parse_args():
    parser = argparse.ArgumentParser(description="AI SQL Agent CLI")
    parser.add_argument("query", type=str, nargs='?', help="The question to ask the database")
    parser.add_argument("--model", type=str, default="gpt-4o", help="LLM model to use")
    parser.add_argument("--verbose", action="store_true", help="Print everything to console")
    return parser.parse_args()

async def main():
    # 1. Parsing Input
    args = parse_args()
    
    # Interactive mode if no query
    query = args.query
    if not query:
        print("🤖 Enter your query:")
        query = input("> ")

    # 2. Setup Deep Observability
    run_id = str(uuid.uuid4())[:8] # ID corto
    logger = setup_logger(run_id)
    
    logger.info(f"🚀 STARTING RUN: {run_id}")
    logger.info(f"❓ Query: {query}")
    logger.info(f"📂 Full logs will be saved to: logs/run_{run_id}.jsonl")

    # 3. Setup Agent
    try:
        llm = ChatOpenAI(model=args.model, temperature=0)
        app = build_main_graph(llm) # Your graph constructor
    except Exception as e:
        logger.critical("Failed to build graph", exc_info=True)
        sys.exit(1)

    # 4. Initial State
    initial_state = {
        "run_id": run_id,
        "question": query,
        "global_logs": [],
        "raw_datasource": None,
        "refined_datasource": None,
        "final_sql": None
    }
    
    # Track state locally for logging
    final_state = initial_state.copy()

    # 5. Execution Stream
    print(f"\n{'='*40}\nProcessing... (Run ID: {run_id})\n{'='*40}")
    
    try:
        async for event in app.astream(initial_state):
            for node_name, state_update in event.items():
                # Minimal visual feedback in console
                print(f"✅ [{node_name}] completed.")
                
                # Update local state tracking
                final_state.update(state_update)
                
                # If critical error in state, stop
                if state_update.get("error"):
                    logger.error(f"Stopped due to error: {state_update['error']}")
                    break
                    
    except Exception as e:
        logger.critical(f"🔥 Critical failure in execution loop: {e}", exc_info=True)
        print("\n❌ Error occurred. Check logs for stack trace.")

    # 6. Log Final State
    logger.info("🏁 Final Agent State", extra={"final_state": final_state})

    print(f"\n{'='*40}\nDone. Check logs/run_{run_id}.jsonl for full trace.\n{'='*40}")

if __name__ == "__main__":
    asyncio.run(main())