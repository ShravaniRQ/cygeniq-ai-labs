import os
from dotenv import load_dotenv
load_dotenv()  # Load .env file automatically
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
import logging

# Suppress debug logs for cleaner terminal output
logging.getLogger("httpx").setLevel(logging.WARNING)

async def init_agent():
    print("Connecting to official MCP servers via npx...")
    
    # Check for required API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY environment variable is not set.")
        return None
        print("Please configure your .env file.")
        return

    # Use a mock DB URL if none provided so the agent doesn't crash on boot,
    # though the Postgres MCP will throw connection errors if it tries to query it.
    db_url = os.getenv("SUPABASE_URL", "postgresql://localhost:5432/postgres")

    # Connect to Official MCPs
    try:
        client = MultiServerMCPClient({
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
                "transport": "stdio"
            },
            "postgres": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-postgres", db_url],
                "transport": "stdio"
            },
            "memory": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-memory"],
                "transport": "stdio"
            }
        })
        tools = await client.get_tools()
        print(f"Successfully connected! Loaded {len(tools)} tools.")
    except Exception as e:
        print(f"Failed to connect to MCP servers. Ensure Node.js is installed. Error: {e}")
        return

    print("\nInitializing Grok model (x-ai/grok-4.3)...")
    model = ChatOpenAI(
        model="x-ai/grok-4.3",
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        max_tokens=4096,
    )

    system_message = SystemMessage(content="""You are a helpful internal assistant for Cygeniq AI Labs.
You have access to the following tools — ALWAYS use them to answer questions:

1. **Postgres/Database tools**: Employee records are stored in a Postgres database. The table is called 'employees' with lowercase columns: name, role, risk_level. To query it, use SQL like: SELECT * FROM employees WHERE risk_level = 'High'. ALWAYS query the database for employee questions. Never use filesystem tools for employee data.
2. **Filesystem tools**: Policy documents are stored in the 'policies' folder. To read HR or security policies, list files in the 'policies' directory first, then read the relevant file (e.g. read_file with path 'policies/hr_policy.md').
3. **Memory tools**: Store and retrieve long-term facts across conversations.

IMPORTANT: Employee/risk data = Postgres tools. Policy documents = Filesystem tools (in the 'policies' folder). Always try the correct tool before saying data is unavailable.""")

    agent = create_react_agent(model, tools, prompt=system_message)
    return agent
