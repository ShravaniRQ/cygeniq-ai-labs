import os
import re
import math
import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from mcp.server.mcpserver import MCPServer as FastMCP

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("policy-mcp")

mcp = FastMCP("Cygeniq Policy MCP")

POLICIES_DIR = Path(__file__).parent / "knowledge" / "policies"


# -------------------------------------------------------------------------
# Semantic / BM25 Vector Index Engine (Zero heavy dependencies)
# -------------------------------------------------------------------------
class PolicySearchEngine:
    def __init__(self, directory: Path):
        self.directory = directory
        self.chunks: List[Dict[str, Any]] = []
        self.doc_freq: Dict[str, int] = {}
        self.avg_doc_len: float = 0.0
        self.total_docs: int = 0
        self.index()

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"\b[A-Za-z0-9_]{2,}\b", text)]

    def index(self):
        """Parse and chunk all markdown policy files."""
        self.chunks = []
        if not self.directory.exists():
            logger.warning(f"Policies directory does not exist: {self.directory}")
            return

        for file_path in self.directory.glob("*.md"):
            try:
                content = file_path.read_text(encoding="utf-8")
                policy_name = file_path.name
                
                # Split content into logical sections by headers (#, ##, ###)
                sections = re.split(r"\n(?=#{1,3}\s+)", content)
                for sec in sections:
                    lines = sec.strip().splitlines()
                    if not lines:
                        continue
                    header = lines[0].lstrip("#").strip()
                    tokens = self._tokenize(sec)
                    
                    self.chunks.append({
                        "policy": policy_name,
                        "title": header,
                        "content": sec.strip(),
                        "tokens": tokens,
                        "length": len(tokens),
                        "file_path": str(file_path)
                    })
            except Exception as e:
                logger.error(f"Error indexing {file_path}: {e}")

        self.total_docs = len(self.chunks)
        if self.total_docs == 0:
            return

        # Calculate document frequencies
        self.doc_freq = {}
        total_len = 0
        for chunk in self.chunks:
            total_len += chunk["length"]
            unique_terms = set(chunk["tokens"])
            for t in unique_terms:
                self.doc_freq[t] = self.doc_freq.get(t, 0) + 1

        self.avg_doc_len = total_len / self.total_docs if self.total_docs > 0 else 1.0

    def search(self, query: str, n_results: int = 3, policy_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.chunks:
            self.index()

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # BM25 parameters
        k1 = 1.5
        b = 0.75
        scores = []

        for chunk in self.chunks:
            if policy_filter and policy_filter.lower() not in chunk["policy"].lower():
                continue

            score = 0.0
            doc_len = chunk["length"]
            chunk_tokens = chunk["tokens"]
            term_counts = {}
            for t in chunk_tokens:
                term_counts[t] = term_counts.get(t, 0) + 1

            for q in query_tokens:
                if q in term_counts:
                    freq = term_counts[q]
                    df = self.doc_freq.get(q, 1)
                    idf = math.log(1.0 + (self.total_docs - df + 0.5) / (df + 0.5))
                    numerator = freq * (k1 + 1.0)
                    denominator = freq + k1 * (1.0 - b + b * (doc_len / (self.avg_doc_len or 1.0)))
                    score += idf * (numerator / denominator)

            if score > 0:
                scores.append({
                    "policy": chunk["policy"],
                    "title": chunk["title"],
                    "content": chunk["content"],
                    "relevance_score": round(score, 3)
                })

        scores.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scores[:n_results]


engine = PolicySearchEngine(POLICIES_DIR)


# -------------------------------------------------------------------------
# MCP Tools
# -------------------------------------------------------------------------

@mcp.tool()
async def search_policies(query: str, n_results: int = 3, policy_filter: Optional[str] = None) -> str:
    """
    Search company policy and compliance guidelines using vector semantic search.

    Args:
        query: The natural language search question or keyword (e.g. 'data retention period' or 'password requirements').
        n_results: Maximum number of relevant policy clauses to retrieve (default: 3).
        policy_filter: Optional filter to search within a specific policy (e.g. 'hr_policy' or 'security_guidelines').
    """
    logger.info(f"Searching policies for: '{query}' (filter: {policy_filter})")
    results = engine.search(query, n_results=n_results, policy_filter=policy_filter)
    if not results:
        return json.dumps({
            "query": query,
            "message": "No matching policy sections found.",
            "results": []
        }, indent=2)

    return json.dumps({
        "query": query,
        "count": len(results),
        "results": results
    }, indent=2)


@mcp.tool()
async def get_policy_details(policy_name: str) -> str:
    """
    Retrieve the full raw markdown text of a specific policy.

    Args:
        policy_name: The name or part of the policy file (e.g. 'hr_policy.md' or 'security_guidelines.md').
    """
    logger.info(f"Retrieving policy details: '{policy_name}'")
    clean_name = policy_name.strip().lower()
    if not clean_name.endswith(".md"):
        clean_name += ".md"

    for file_path in POLICIES_DIR.glob("*.md"):
        if clean_name in file_path.name.lower():
            return f"--- Policy: {file_path.name} ---\n\n" + file_path.read_text(encoding="utf-8")

    available = [f.name for f in POLICIES_DIR.glob("*.md")]
    return f"Error: Policy '{policy_name}' not found. Available policies: {available}"


@mcp.tool()
async def list_available_policies() -> str:
    """
    List all corporate policies currently loaded and indexed in the knowledge base.
    """
    policies = []
    for file_path in POLICIES_DIR.glob("*.md"):
        content = file_path.read_text(encoding="utf-8")
        first_line = content.splitlines()[0] if content.splitlines() else file_path.name
        title = first_line.lstrip("#").strip()
        policies.append({
            "file": file_path.name,
            "title": title,
            "size_bytes": file_path.stat().st_size
        })

    return json.dumps({"indexed_policies": policies, "total": len(policies)}, indent=2)


@mcp.tool()
async def check_compliance_requirement(topic: str) -> str:
    """
    Perform a compliance check against all indexed policies for a specific operational practice or topic.

    Args:
        topic: The practice to evaluate (e.g., 'storing customer resumes for 12 months', 'using 8-character passwords').
    """
    logger.info(f"Checking compliance for topic: '{topic}'")
    matches = engine.search(topic, n_results=2)
    if not matches:
        return f"No direct policy mandate found regarding '{topic}'."

    evidence = "\n\n".join([f"[{m['policy']} - {m['title']}]:\n{m['content']}" for m in matches])
    return (
        f"--- Policy Compliance Evidence for '{topic}' ---\n"
        f"Relevant Clauses:\n{evidence}\n"
    )


if __name__ == "__main__":
    mcp.run()
