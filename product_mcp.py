import os
import json
import logging
from typing import Optional, List, Dict, Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from mcp.server.mcpserver import MCPServer as FastMCP

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product-mcp")

mcp = FastMCP("Cygeniq Product Intelligence MCP")

# -------------------------------------------------------------------------
# Cygeniq Product Knowledge Base
# -------------------------------------------------------------------------
PRODUCT_CATALOG: Dict[str, Dict[str, Any]] = {
    "HexaShield AI": {
        "tagline": "AI Security, Red Teaming, Runtime Assurance & Guardrails",
        "description": "Enterprise-grade AI security platform for LLM applications, RAG pipelines, Agentic AI, and AI inference APIs. Validates and safeguards systems against adversarial attacks, jailbreaks, data leakage, and excessive agency.",
        "supported_architectures": ["LLMs", "RAG Pipelines", "Autonomous Agents (MCP/ReAct)", "AI APIs & Endpoints"],
        "deployment_options": ["On-Premise", "Private Cloud (VPC)", "SaaS", "Air-Gapped Hybrid"],
        "modules": [
            {
                "name": "AI Red Teaming & Adversarial Testing",
                "capabilities": [
                    "Direct and indirect prompt injection attack simulation",
                    "Safety jailbreak and policy bypass validation",
                    "RAG data exfiltration and sensitive PII leakage testing",
                    "Adversarial perturbation testing on vision and multimodal inputs",
                    "Automated vulnerability scoring aligned with OWASP Top 10 for LLM Applications"
                ]
            },
            {
                "name": "Agentic AI & MCP Assurance",
                "capabilities": [
                    "Model Context Protocol (MCP) tool-call verification and sandboxing",
                    "Excessive agency prevention and least-privilege tool boundary enforcement",
                    "Tool abuse detection (e.g. unauthorized OS commands or database exfiltration)",
                    "Persistent memory poisoning detection in conversational and vector memory",
                    "Malicious embedding and vector injection defenses"
                ]
            },
            {
                "name": "Runtime Guardrails & Security Gateway",
                "capabilities": [
                    "Ultra-low latency real-time prompt and response sanitization (<15ms)",
                    "Dynamic PII masking, tokenization, and GDPR/DPDP redacting",
                    "Hallucination and toxic content filtering",
                    "Adaptive rate limiting and API abuse prevention"
                ]
            },
            {
                "name": "AI Risk Scoring & Findings Reporting",
                "capabilities": [
                    "Executive compliance dashboards and technical finding scorecards",
                    "Automated remediation playbooks for model fine-tuning and system prompt hardening",
                    "Evidence export for external auditors and enterprise risk committees"
                ]
            }
        ]
    },
    "GRCortex": {
        "tagline": "AI & Cybersecurity Governance, Risk, and Compliance Automation",
        "description": "Comprehensive governance and regulatory compliance automation platform tailored for highly regulated sectors (Banking, Financial Services, Insurance, Healthcare). Translates complex regulations into actionable controls, assessments, and continuous evidence verification.",
        "supported_architectures": ["Enterprise IT", "AI Systems", "Cloud Platforms", "Third-Party Vendor Ecosystems"],
        "deployment_options": ["SaaS (Enterprise)", "Private Cloud", "On-Premises for Regulated Banks"],
        "modules": [
            {
                "name": "Regulatory & Standard Framework Management",
                "capabilities": [
                    "Pre-configured regulatory frameworks: RBI Cyber Security Guidelines, SEBI Cyber Resilience Framework, IRDAI, CERT-In",
                    "Global AI governance standards: NIST AI RMF 1.0, ISO/IEC 42001 (AIMS), EU AI Act, Singapore Model AI Governance",
                    "Data protection compliance: DPDP Act 2023, GDPR, CCPA",
                    "Cross-regulatory requirement harmonisation and overlap reduction"
                ]
            },
            {
                "name": "Assessment & Vendor Risk Automation",
                "capabilities": [
                    "Automated compliance questionnaire dispatch and scoring",
                    "Third-party AI and software vendor risk assessments",
                    "Evidence-based requirement verification (Policy -> Requirement -> Control -> Evidence)",
                    "Audit trail logging with immutable verification timestamps"
                ]
            },
            {
                "name": "Gap Analysis & Remediation Orchestration",
                "capabilities": [
                    "Real-time gap detection against regulatory deadlines",
                    "Remediation task assignment, SLA tracking, and escalation paths",
                    "Automated board-level and regulator-ready compliance report generation"
                ]
            }
        ]
    },
    "CyberTix AI": {
        "tagline": "Autonomous AI-Powered Security Operations & Threat Investigation",
        "description": "AI-native SOC co-pilot and automated investigation platform that accelerates threat triage, correlates multi-source telemetry, performs MITRE ATT&CK mapping, and executes rapid containment workflows.",
        "supported_architectures": ["SIEM / EDR Integrations", "Cloud Security Telemetry", "Network PCAP / Flow Logs", "Identity & Access Logs"],
        "deployment_options": ["Cloud Managed", "Hybrid SIEM Connector", "On-Premises SOC Enclave"],
        "modules": [
            {
                "name": "Automated Alert Triage & Correlation",
                "capabilities": [
                    "Multi-signal alert deduplication and false-positive reduction (>85% alert reduction)",
                    "Dynamic attack timeline reconstruction across endpoints, identity, and cloud",
                    "Behavioral anomaly detection across unusual employee access patterns"
                ]
            },
            {
                "name": "Threat Intelligence & IOC Telemetry",
                "capabilities": [
                    "Automated IP, file hash, domain, and URL reputation analysis",
                    "Deep MITRE ATT&CK technique, tactic, and sub-technique classification",
                    "PCAP packet and payload inspection with protocol anomaly detection"
                ]
            },
            {
                "name": "Investigation Playbooks & Containment Workflows",
                "capabilities": [
                    "Automated root cause analysis and forensic reporting",
                    "One-click containment playbooks (host isolation, credential rotation, firewall blocking)",
                    "Integration with Microsoft Defender, CrowdStrike, Splunk, Sentinel, and Palo Alto Networks"
                ]
            }
        ]
    }
}


# -------------------------------------------------------------------------
# MCP Tools
# -------------------------------------------------------------------------

@mcp.tool()
async def list_products() -> str:
    """
    List all Cygeniq products, their taglines, core descriptions, and primary modules.
    """
    summary = []
    for name, p in PRODUCT_CATALOG.items():
        summary.append({
            "product": name,
            "tagline": p["tagline"],
            "description": p["description"],
            "modules": [m["name"] for m in p["modules"]],
            "deployment_options": p["deployment_options"]
        })
    return json.dumps({"products": summary, "total_products": len(summary)}, indent=2)


@mcp.tool()
async def get_product_datasheet(product_name: str) -> str:
    """
    Get the complete specification, modules, capabilities, and architectures for a Cygeniq product.

    Args:
        product_name: Name of the product (e.g. 'HexaShield', 'GRCortex', or 'CyberTix').
    """
    target = None
    for name, data in PRODUCT_CATALOG.items():
        if product_name.strip().lower() in name.lower():
            target = (name, data)
            break

    if not target:
        return f"Error: Product '{product_name}' not found. Available products: {list(PRODUCT_CATALOG.keys())}"

    name, data = target
    return json.dumps({name: data}, indent=2)


@mcp.tool()
async def search_product_capabilities(query: str, product_filter: Optional[str] = None) -> str:
    """
    Search across capabilities, features, and use cases across all Cygeniq products.

    Args:
        query: Feature, threat, regulation, or capability keyword (e.g. 'prompt injection', 'NIST', 'SOC triage', 'MCP security').
        product_filter: Optional product name to restrict search (e.g. 'HexaShield', 'GRCortex', 'CyberTix').
    """
    logger.info(f"Searching product capabilities for: '{query}' (filter: {product_filter})")
    tokens = [t.lower() for t in query.split() if len(t) > 2]
    matches = []

    for prod_name, prod_data in PRODUCT_CATALOG.items():
        if product_filter and product_filter.lower() not in prod_name.lower():
            continue

        for mod in prod_data["modules"]:
            mod_name = mod["name"]
            for cap in mod["capabilities"]:
                # Simple keyword matching score
                cap_lower = cap.lower()
                matched_tokens = [t for t in tokens if t in cap_lower or t in mod_name.lower() or t in prod_name.lower()]
                if matched_tokens or query.lower() in cap_lower:
                    matches.append({
                        "product": prod_name,
                        "module": mod_name,
                        "capability": cap,
                        "relevance": len(matched_tokens)
                    })

    matches.sort(key=lambda x: x["relevance"], reverse=True)
    if not matches:
        return f"No direct capabilities found matching '{query}'. Try searching for broader terms (e.g. 'injection', 'compliance', 'investigation', 'agent')."

    return json.dumps({
        "query": query,
        "match_count": len(matches),
        "results": matches[:10]
    }, indent=2)


@mcp.tool()
async def match_rfp_requirement_to_features(requirement_text: str) -> str:
    """
    Analyze an RFP clause or client security requirement and map it to Cygeniq product capabilities,
    specifying compliance status (Supported / Configurable) and evidence.

    Args:
        requirement_text: The client RFP requirement or RFP question.
    """
    logger.info(f"Matching RFP requirement: '{requirement_text[:80]}...'")
    req_lower = requirement_text.lower()
    matches = []

    for prod_name, prod_data in PRODUCT_CATALOG.items():
        for mod in prod_data["modules"]:
            for cap in mod["capabilities"]:
                words = [w for w in cap.lower().split() if len(w) > 3]
                hits = sum(1 for w in words if w in req_lower)
                if hits >= 2 or any(k in req_lower for k in ["prompt injection", "jailbreak", "rbi", "sebi", "soc", "mcp", "mitre", "excessive agency"]):
                    # Check if relevant
                    if hits > 0 or any(k in cap.lower() for k in ["prompt injection", "jailbreak", "rbi", "sebi", "mcp", "mitre"] if k in req_lower):
                        matches.append({
                            "product": prod_name,
                            "module": mod["name"],
                            "feature": cap,
                            "confidence_score": min(1.0, 0.4 + hits * 0.15)
                        })

    matches.sort(key=lambda x: x["confidence_score"], reverse=True)
    best_matches = matches[:5]
    
    status = "Fully Supported" if best_matches else "Under Evaluation"
    response = {
        "requirement": requirement_text,
        "compliance_status": status,
        "primary_solution": best_matches[0]["product"] if best_matches else "Consult Cygeniq Architecture Team",
        "matching_capabilities": best_matches,
        "standard_proposal_response": (
            f"Cygeniq addresses this requirement through our {best_matches[0]['product'] if best_matches else 'Platform'} "
            f"suite, offering {best_matches[0]['feature'] if best_matches else 'custom integration'}. "
            f"Deployment supports enterprise air-gapped, on-premise, and private cloud configurations with full auditability."
        )
    }

    return json.dumps(response, indent=2)


if __name__ == "__main__":
    mcp.run()
