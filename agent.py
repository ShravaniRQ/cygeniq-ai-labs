import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import asyncio

async def main():
    # 1. Initialize the MultiServerMCPClient with Person A's initial servers
    # We are starting with Policy and Database MCPs
    client = MultiServerMCPClient({
        # The database MCP is an external script (we assume it's available or will be run similarly)
        "database": {
            "command": "python", 
            "args": ["mcp/postgres_mcp_server.py"], 
            "transport": "stdio"
        },
        # Running Policy MCP via stdio for local development
        "policy": {
            "command": "python",
            "args": ["mcp/policy_server.py"],
            "transport": "stdio"
        }
    })

    print("Connecting to MCP servers...")
    tools = await client.get_tools()
    print(f"Loaded {len(tools)} tools from MCPs.")

    # 2. Initialize the LLM
    print("Initializing Grok model (x-ai/grok-4-fast:free)...")
    model = ChatOpenAI(
        model="x-ai/grok-4-fast:free",
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY", "dummy"), 
    )

    # 3. Create the React Agent
    agent = create_react_agent(model, tools)

    # 4. Run a test query
    test_query = "What's our data retention policy for HR records?"
    print(f"\nUser: {test_query}")
    
    try:
        response = await agent.ainvoke({
            "messages": [{"role": "user", "content": test_query}]
        })
        print(f"\nAgent: {response['messages'][-1].content}")
    except Exception as e:
        print(f"\nAgent loop failed. Ensure API keys are set and MCPs are running. Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
