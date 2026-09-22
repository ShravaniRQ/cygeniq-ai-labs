import asyncio
import json
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import markdown
from agent import init_agent

app = FastAPI()

# Mount the static directory to serve the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global reference to the agent
cygeniq_agent = None

@app.on_event("startup")
async def startup_event():
    global cygeniq_agent
    print("Initializing Cygeniq Agent backend...")
    cygeniq_agent = await init_agent()
    if cygeniq_agent is None:
        print("Failed to initialize agent. Check environment variables.")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/chat")
async def chat_endpoint(request: Request):
    if not cygeniq_agent:
        return JSONResponse(status_code=500, content={"error": "Agent not initialized"})

    body = await request.json()
    user_input = body.get("message")
    session_id = body.get("session_id", str(uuid.uuid4()))

    if not user_input:
        return JSONResponse(status_code=400, content={"error": "No message provided"})

    try:
        # We pass a thread_id via config to enable memory (checkpointing)
        config = {"configurable": {"thread_id": session_id}}
        
        # Invoke the LangGraph agent
        result = await cygeniq_agent.ainvoke({"messages": [("user", user_input)]}, config)
        
        # Extract the messages
        messages = result["messages"]
        final_message = messages[-1].content

        # Basic heuristic to determine source for the badge
        # LangGraph intermediate steps contain ToolMessages
        source_badge = None
        for msg in messages:
            if msg.type == "tool":
                if msg.name in ["query", "list_tables", "describe_table"]:
                    source_badge = {
                        "type": "db",
                        "label": "Postgres (Supabase)",
                        "drawerTitle": "Database query",
                        "drawerBody": f"<h4>Tool Used</h4><pre>{msg.name}</pre><h4>Result Snippet</h4><div class='excerpt'>{msg.content[:300]}...</div>"
                    }
                    break
                elif msg.name in ["read_file", "list_directory"]:
                    source_badge = {
                        "type": "file",
                        "label": "Filesystem (Policies)",
                        "drawerTitle": "Policy Document",
                        "drawerBody": f"<h4>Tool Used</h4><pre>{msg.name}</pre><h4>Result Snippet</h4><div class='excerpt'>{msg.content[:300]}...</div>"
                    }
                    break

        # Convert markdown text to HTML
        html_message = markdown.markdown(final_message)

        return {
            "blocks": [html_message],
            "source": source_badge
        }

    except Exception as e:
        print(f"Error processing chat: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
