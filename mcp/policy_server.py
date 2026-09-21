import os
from fastmcp import FastMCP
import chromadb
from chromadb.utils import embedding_functions

# Initialize MCP Server
mcp = FastMCP("PolicyServer")

# Initialize ChromaDB client (mocking local persistent client for the 'policies' collection)
# In production, this would point to the directory where ingestion pipeline saved the DB
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./chroma_db")
try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    # Using the default sentence-transformers embedding function
    sentence_transformer_ef = embedding_functions.DefaultEmbeddingFunction()
    collection = chroma_client.get_or_create_collection(
        name="policies",
        embedding_function=sentence_transformer_ef
    )
except Exception as e:
    # Fallback/mock if DB isn't initialized yet
    collection = None

@mcp.tool()
def search_policies(query: str, n_results: int = 3) -> list[dict]:
    """
    Search the internal policy documents for a given query.
    
    Args:
        query: The search string (e.g., 'What is the data retention policy?')
        n_results: The number of relevant document chunks to return.
    """
    print(f"[LOG] search_policies called with query: '{query}'") # Per-call logging rule
    
    if not collection:
        return [{"error": "Vector database not initialized or accessible."}]
        
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Format results for the LLM
        formatted_results = []
        if results and 'documents' in results and results['documents']:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i] if 'metadatas' in results and results['metadatas'] else {}
                })
        return formatted_results
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]

if __name__ == "__main__":
    mcp.run()
