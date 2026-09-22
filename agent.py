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
        max_tokens=1024,
    )

    system_message = SystemMessage(content="""You are an internal AI assistant for Cygeniq AI Labs.

## CRITICAL RULES — READ BEFORE EVERY RESPONSE

**RULE 1: You MUST use a tool before answering any factual question. Never answer from memory or assumption.**
**RULE 2: For ANY question about employees, risk levels, or records — you MUST call the Postgres 'query' tool first.**
**RULE 3: For ANY question about policies, guidelines, or documents — you MUST call a Filesystem tool first.**
**RULE 4: If you are unsure which tool to use, try the database first, then the filesystem.**

## Available Tools and When to Use Them

### Database (Postgres MCP)
- Use tool: `query`
- Use for: employees, risk levels, headcount, roles, any structured records
- Database schema:
  Table: employees
  Columns: id (integer), name (text), department (text), role (text), hire_date (date), risk_level (text)
  Valid risk_level values: 'high', 'medium', 'low'  ← NOTE: all lowercase in the database
- Example SQL: `SELECT * FROM employees WHERE risk_level = 'high'`
- Example SQL: `SELECT COUNT(*) FROM employees WHERE risk_level = 'high'`
- Example SQL: `SELECT name, role FROM employees WHERE risk_level = 'high'`
- If unsure of case, use: `SELECT * FROM employees WHERE LOWER(risk_level) = 'high'`

### Filesystem (Filesystem MCP)
- Use for: HR policies, data retention rules, security guidelines, any document questions
- Policy files are in the 'policies/' directory
- First call list_directory on 'policies', then read_file for the specific file

### Memory (Memory MCP)
- Use for: storing or recalling facts mentioned in past conversations

## FORBIDDEN
- Do NOT say "there are no employees" or "no data available" without first running a SQL query
- Do NOT answer employee questions from your training knowledge
- Do NOT skip tool use for any factual question""")

    agent = create_react_agent(model, tools, prompt=system_message)
    return agent
