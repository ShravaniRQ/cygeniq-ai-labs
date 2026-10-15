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
logger = logging.getLogger("grc-mcp")

mcp = FastMCP("Cygeniq GRC & Regulatory Intelligence MCP")

# -------------------------------------------------------------------------
# Comprehensive Regulatory Frameworks & Controls Database
# -------------------------------------------------------------------------
REGULATORY_FRAMEWORKS: Dict[str, Dict[str, Any]] = {
    "RBI_CSF": {
        "name": "RBI Cyber Security Framework & IT Governance Guidelines",
        "authority": "Reserve Bank of India (RBI)",
        "applicable_sectors": ["Commercial Banks", "NBFCs", "Payment Service Operators", "Co-operative Banks"],
        "summary": "Mandates strict cybersecurity governance, access management, network isolation, 24x7 SOC continuous monitoring, incident response within 2 to 6 hours, and rigorous vendor risk management.",
        "domains": [
            {
                "domain": "Governance & Oversight",
                "controls": [
                    {
                        "control_id": "RBI-GOV-01",
                        "title": "Board-Level Cyber Security Committee & CISO Independence",
                        "requirement": "Banks must establish a dedicated Cyber Security Committee and appoint a CISO with direct reporting to the Board Risk Committee.",
                        "cygeniq_mapping": {
                            "product": "GRCortex",
                            "module": "Assessment & Vendor Risk Automation",
                            "evidence": "CISO charter, board quarterly audit log, and GRCortex compliance dashboard."
                        }
                    },
                    {
                        "control_id": "RBI-GOV-02",
                        "title": "Cyber Crisis Management Plan (CCMP)",
                        "requirement": "Annual simulation of cyber crisis management plan covering ransomware, insider sabotage, and cloud disruption.",
                        "cygeniq_mapping": {
                            "product": "HexaShield AI",
                            "module": "AI Red Teaming & Adversarial Testing",
                            "evidence": "Red teaming simulation report and table-top exercise findings."
                        }
                    }
                ]
            },
            {
                "domain": "Access Control & Data Protection",
                "controls": [
                    {
                        "control_id": "RBI-ACS-01",
                        "title": "Mandatory Multi-Factor Authentication (MFA) & Privileged Access",
                        "requirement": "MFA for all remote administrative access, customer transaction channels, and strict PAM credential rotation.",
                        "cygeniq_mapping": {
                            "product": "GRCortex",
                            "module": "Control-to-Evidence Mapping",
                            "evidence": "PAM audit trails, active MFA session logs, and access review sign-offs."
                        }
                    },
                    {
                        "control_id": "RBI-DTA-01",
                        "title": "Data-at-Rest and Data-in-Transit Encryption",
                        "requirement": "Use of AES-256 for data at rest and TLS 1.3 for data in transit; cryptographic key management adhering to FIPS 140-2.",
                        "cygeniq_mapping": {
                            "product": "HexaShield AI",
                            "module": "Runtime Guardrails & Security Gateway",
                            "evidence": "TLS enforcement certificates, hardware security module (HSM) attestation, and data tokenization logs."
                        }
                    }
                ]
            },
            {
                "domain": "SOC Monitoring & Incident Response",
                "controls": [
                    {
                        "control_id": "RBI-SOC-01",
                        "title": "Continuous 24x7 SOC Monitoring & Threat Telemetry",
                        "requirement": "Real-time log ingestion from endpoints, network perimeters, databases, and core banking applications into SIEM.",
                        "cygeniq_mapping": {
                            "product": "CyberTix AI",
                            "module": "Automated Alert Triage & Correlation",
                            "evidence": "Continuous SIEM telemetry ingestion logs, MTTR/MTTD metrics, and behavioral anomaly alerts."
                        }
                    },
                    {
                        "control_id": "RBI-INC-01",
                        "title": "Mandatory Cyber Incident Reporting within 6 Hours",
                        "requirement": "All critical security breaches, unauthorized access, and ransomware outbreaks must be notified to RBI within 6 hours.",
                        "cygeniq_mapping": {
                            "product": "CyberTix AI",
                            "module": "Investigation Playbooks & Containment Workflows",
                            "evidence": "Automated incident timeline generation, forensic breach report, and CERT-In/RBI notification template."
                        }
                    }
                ]
            }
        ]
    },
    "SEBI_CSCRF": {
        "name": "SEBI Cybersecurity & Cyber Resilience Framework (CSCRF)",
        "authority": "Securities and Exchange Board of India (SEBI)",
        "applicable_sectors": ["Stock Exchanges", "Depositories", "Clearing Corporations", "Brokers", "Mutual Funds"],
        "summary": "Focuses on high resilience, business continuity, automated SOC alerting, API security, and supply-chain auditing for capital market participants.",
        "domains": [
            {
                "domain": "Anticipate & Identify",
                "controls": [
                    {
                        "control_id": "SEBI-ID-01",
                        "title": "Comprehensive Asset Inventory & Shadow IT Discovery",
                        "requirement": "Automated discovery of all hardware, cloud endpoints, microservices, and AI APIs handling market transactions.",
                        "cygeniq_mapping": {
                            "product": "GRCortex",
                            "module": "Assessment & Vendor Risk Automation",
                            "evidence": "Automated asset discovery catalog and API vulnerability matrix."
                        }
                    }
                ]
            },
            {
                "domain": "Protect & Detect",
                "controls": [
                    {
                        "control_id": "SEBI-PR-01",
                        "title": "API Gateway Security & Excessive Data Exposure Prevention",
                        "requirement": "Enforce strict rate-limiting, schema validation, and sensitive data masking on all trading and market data APIs.",
                        "cygeniq_mapping": {
                            "product": "HexaShield AI",
                            "module": "Runtime Guardrails & Security Gateway",
                            "evidence": "Gateway request validation logs, PII redaction audit trails, and tokenized API outputs."
                        }
                    },
                    {
                        "control_id": "SEBI-DT-01",
                        "title": "Automated MITRE ATT&CK Aligned Threat Detection",
                        "requirement": "Correlate telemetry against known adversary techniques with automated containment capabilities.",
                        "cygeniq_mapping": {
                            "product": "CyberTix AI",
                            "module": "Threat Intelligence & IOC Telemetry",
                            "evidence": "MITRE ATT&CK tactical heatmap, IOC correlation records, and playbook execution history."
                        }
                    }
                ]
            }
        ]
    },
    "NIST_AI_RMF": {
        "name": "NIST AI Risk Management Framework (AI RMF 1.0)",
        "authority": "National Institute of Standards and Technology (NIST)",
        "applicable_sectors": ["Enterprises deploying LLMs, Generative AI, and Autonomous Agents"],
        "summary": "Provides actionable guidance to govern, map, measure, and manage risks from AI systems, emphasizing trustworthiness, explainability, fairness, and safety.",
        "domains": [
            {
                "domain": "GOVERN",
                "controls": [
                    {
                        "control_id": "NIST-GOVERN-1.1",
                        "title": "Organizational AI Risk Policies & Accountability",
                        "requirement": "Policies and procedures defining acceptable AI use, risk tolerances, and executive accountability across the AI lifecycle.",
                        "cygeniq_mapping": {
                            "product": "GRCortex",
                            "module": "Regulatory & Standard Framework Management",
                            "evidence": "AI Ethics & Governance Charter, role-based approval logs, and risk threshold definitions."
                        }
                    }
                ]
            },
            {
                "domain": "MAP & MEASURE",
                "controls": [
                    {
                        "control_id": "NIST-MEASURE-2.3",
                        "title": "Adversarial Robustness & Safety Validation",
                        "requirement": "Systematic testing of AI models against prompt injections, adversarial perturbations, hallucination, and data extraction.",
                        "cygeniq_mapping": {
                            "product": "HexaShield AI",
                            "module": "AI Red Teaming & Adversarial Testing",
                            "evidence": "OWASP LLM benchmark scorecard, automated jailbreak test suites, and model robustness metrics."
                        }
                    }
                ]
            },
            {
                "domain": "MANAGE",
                "controls": [
                    {
                        "control_id": "NIST-MANAGE-1.3",
                        "title": "Runtime Guardrails & De-risking Mechanisms",
                        "requirement": "Active controls to intercept and mitigate harmful, toxic, or privacy-violating model outputs in production.",
                        "cygeniq_mapping": {
                            "product": "HexaShield AI",
                            "module": "Runtime Guardrails & Security Gateway",
                            "evidence": "Low-latency guardrail telemetry, blocked prompt alerts, and output sanitization metrics."
                        }
                    }
                ]
            }
        ]
    },
    "ISO_42001": {
        "name": "ISO/IEC 42001:2023 - Artificial Intelligence Management System (AIMS)",
        "authority": "International Organization for Standardization (ISO / IEC)",
        "applicable_sectors": ["Organizations developing, providing, or deploying AI-enabled systems"],
        "summary": "First global certifiable management system standard for AI. Covers AI policy, risk assessment, impact analysis, lifecycle management, third-party AI risk, and continuous improvement.",
        "domains": [
            {
                "domain": "Clause 6 & 8: AI Risk Management & Assessment",
                "controls": [
                    {
                        "control_id": "ISO-42001-A.6",
                        "title": "AI Risk & Consequence Assessment",
                        "requirement": "Formal methodology to identify risks of unintended behavior, bias, security vulnerabilities, and societal harm throughout AI lifecycle.",
                        "cygeniq_mapping": {
                            "product": "GRCortex",
                            "module": "Assessment & Vendor Risk Automation",
                            "evidence": "AI System Risk Register, Impact Assessment (AIA) reports, and risk treatment plans."
                        }
                    },
                    {
                        "control_id": "ISO-42001-A.8",
                        "title": "Data Governance & Traceability for AI",
                        "requirement": "Ensuring data provenance, quality validation, bias mitigation, and auditability of training/fine-tuning datasets.",
                        "cygeniq_mapping": {
                            "product": "GRCortex",
                            "module": "Control-to-Evidence Mapping",
                            "evidence": "Dataset lineage logs, data quality scorecards, and consent records."
                        }
                    }
                ]
            },
            {
                "domain": "Clause 9: AI System Verification, Validation & Auditing",
                "controls": [
                    {
                        "control_id": "ISO-42001-A.9",
                        "title": "Continuous Independent AI Verification & Red Teaming",
                        "requirement": "Regular technical verification and stress testing of AI systems against abuse cases and operational drift.",
                        "cygeniq_mapping": {
                            "product": "HexaShield AI",
                            "module": "AI Red Teaming & Adversarial Testing",
                            "evidence": "Third-party red teaming reports, model calibration logs, and annual ISO 42001 internal audit records."
                        }
                    }
                ]
            }
        ]
    },
    "DPDP_ACT": {
        "name": "Digital Personal Data Protection (DPDP) Act 2023",
        "authority": "Data Protection Board of India / Ministry of Electronics & IT",
        "applicable_sectors": ["All entities processing digital personal data of Indian citizens"],
        "summary": "Mandates clear notice, verifiable consent, purpose limitation, data minimization, right to erasure, and strict breach reporting with penalties up to ₹250 Crores.",
        "domains": [
            {
                "domain": "Consent & Data Principal Rights",
                "controls": [
                    {
                        "control_id": "DPDP-CON-01",
                        "title": "Notice and Verifiable Consent Management",
                        "requirement": "Data Fiduciaries must provide transparent notice in 22 scheduled languages with granular consent capture.",
                        "cygeniq_mapping": {
                            "product": "GRCortex",
                            "module": "Regulatory & Standard Framework Management",
                            "evidence": "Consent log repository, multi-lingual notice templates, and consent withdrawal audit trail."
                        }
                    },
                    {
                        "control_id": "DPDP-ERS-01",
                        "title": "Right to Correction and Erasure (Data Destruction)",
                        "requirement": "Personal data must be securely wiped upon withdrawal of consent or once the specified processing purpose is fulfilled.",
                        "cygeniq_mapping": {
                            "product": "GRCortex",
                            "module": "Control-to-Evidence Mapping",
                            "evidence": "Automated database deletion logs, retention schedule certificates, and shredding manifests."
                        }
                    }
                ]
            },
            {
                "domain": "Security Safeguards & Breach Mitigation",
                "controls": [
                    {
                        "control_id": "DPDP-SEC-01",
                        "title": "Reasonable Security Safeguards & Prompt Injection Defense",
                        "requirement": "Preventing personal data breaches resulting from prompt extraction, model inversion, or unauthorized AI agent actions.",
                        "cygeniq_mapping": {
                            "product": "HexaShield AI",
                            "module": "Agentic AI & MCP Assurance",
                            "evidence": "PII redaction gateway logs, model memory leakage tests, and boundary enforcement reports."
                        }
                    }
                ]
            }
        ]
    }
}


# -------------------------------------------------------------------------
# MCP Tools
# -------------------------------------------------------------------------

@mcp.tool()
async def list_regulatory_frameworks() -> str:
    """
    List all regulatory frameworks, authorities, applicable sectors, and covered governance domains.
    """
    summary = []
    for code, f in REGULATORY_FRAMEWORKS.items():
        summary.append({
            "framework_code": code,
            "name": f["name"],
            "authority": f["authority"],
            "applicable_sectors": f["applicable_sectors"],
            "summary": f["summary"],
            "domains": [d["domain"] for d in f["domains"]]
        })
    return json.dumps({"frameworks": summary, "total_frameworks": len(summary)}, indent=2)


@mcp.tool()
async def get_framework_controls(framework_code: str, domain_filter: Optional[str] = None) -> str:
    """
    Retrieve specific controls, requirements, and compliance evidence criteria for a framework.

    Args:
        framework_code: Framework identifier (e.g. 'RBI_CSF', 'SEBI_CSCRF', 'NIST_AI_RMF', 'ISO_42001', 'DPDP_ACT').
        domain_filter: Optional keyword to filter specific domains (e.g. 'Access', 'SOC', 'Governance', 'Consent').
    """
    logger.info(f"Retrieving controls for framework: '{framework_code}' (filter: {domain_filter})")
    matched_key = next((k for k in REGULATORY_FRAMEWORKS if k.lower() == framework_code.strip().lower()), None)
    
    if not matched_key:
        return f"Error: Framework '{framework_code}' not found. Available framework codes: {list(REGULATORY_FRAMEWORKS.keys())}"

    fw = REGULATORY_FRAMEWORKS[matched_key]
    matched_domains = []

    for d in fw["domains"]:
        if domain_filter and domain_filter.lower() not in d["domain"].lower():
            # Check if domain filter matches any control inside
            filtered_controls = [c for c in d["controls"] if domain_filter.lower() in c["title"].lower() or domain_filter.lower() in c["requirement"].lower()]
            if filtered_controls:
                matched_domains.append({"domain": d["domain"], "controls": filtered_controls})
        else:
            matched_domains.append(d)

    return json.dumps({
        "framework": fw["name"],
        "authority": fw["authority"],
        "matched_domains": matched_domains
    }, indent=2)


@mcp.tool()
async def map_control_to_product_evidence(control_id: str) -> str:
    """
    Map a specific regulatory control ID (e.g. 'RBI-ACS-01', 'RBI-SOC-01', 'NIST-MEASURE-2.3', 'DPDP-SEC-01')
    to Cygeniq product capabilities and audit evidence.

    Args:
        control_id: The exact or partial control identifier.
    """
    logger.info(f"Mapping control to evidence: '{control_id}'")
    clean_id = control_id.strip().upper()
    found = []

    for f_code, fw in REGULATORY_FRAMEWORKS.items():
        for d in fw["domains"]:
            for c in d["controls"]:
                if clean_id in c["control_id"].upper() or clean_id in c["title"].upper():
                    found.append({
                        "framework": fw["name"],
                        "domain": d["domain"],
                        "control_id": c["control_id"],
                        "title": c["title"],
                        "requirement": c["requirement"],
                        "solution_mapping": c["cygeniq_mapping"]
                    })

    if not found:
        return f"Error: No control found matching identifier '{control_id}'. Example control IDs: RBI-ACS-01, RBI-SOC-01, NIST-MEASURE-2.3, ISO-42001-A.6, DPDP-SEC-01."

    return json.dumps({"query_control_id": control_id, "matches": found}, indent=2)


@mcp.tool()
async def evaluate_compliance_gap(policy_or_system_description: str, framework_code: str) -> str:
    """
    Analyze an enterprise operational description or policy excerpt against a regulatory framework,
    detecting compliance gaps and recommending remediation actions.

    Args:
        policy_or_system_description: Description of current enterprise security or AI implementation.
        framework_code: Regulatory code to evaluate against (e.g. 'RBI_CSF', 'SEBI_CSCRF', 'NIST_AI_RMF', 'ISO_42001', 'DPDP_ACT').
    """
    logger.info(f"Evaluating compliance gap for framework: '{framework_code}'")
    matched_key = next((k for k in REGULATORY_FRAMEWORKS if k.lower() == framework_code.strip().lower()), None)
    if not matched_key:
        return f"Error: Framework '{framework_code}' not found. Available codes: {list(REGULATORY_FRAMEWORKS.keys())}"

    fw = REGULATORY_FRAMEWORKS[matched_key]
    text_lower = policy_or_system_description.lower()
    
    gaps = []
    satisfied = []

    for d in fw["domains"]:
        for c in d["controls"]:
            # Evaluate presence of key control concepts
            keywords = [w.lower() for w in c["title"].split() if len(w) > 4]
            hits = sum(1 for kw in keywords if kw in text_lower)
            if hits > 0 or any(t.lower() in text_lower for t in [c["control_id"].lower(), c["title"][:15].lower()]):
                satisfied.append({
                    "control_id": c["control_id"],
                    "title": c["title"],
                    "status": "Likely Addressed"
                })
            else:
                gaps.append({
                    "control_id": c["control_id"],
                    "title": c["title"],
                    "requirement": c["requirement"],
                    "recommended_remediation": f"Implement {c['cygeniq_mapping']['product']} ({c['cygeniq_mapping']['module']}) to produce {c['cygeniq_mapping']['evidence']}."
                })

    compliance_score = int((len(satisfied) / (len(satisfied) + len(gaps))) * 100) if (satisfied or gaps) else 0

    return json.dumps({
        "evaluated_framework": fw["name"],
        "compliance_score_percentage": f"{compliance_score}%",
        "satisfied_controls_count": len(satisfied),
        "gap_count": len(gaps),
        "identified_gaps": gaps,
        "satisfied_controls": satisfied,
        "summary_recommendation": f"To achieve full compliance with {fw['name']}, prioritize remediating the {len(gaps)} identified gaps using Cygeniq's automated GRCortex & HexaShield evidence pipelines."
    }, indent=2)


@mcp.tool()
async def generate_compliance_checklist(framework_code: str, industry: str) -> str:
    """
    Generate an audit checklist for enterprise compliance assessment tailored to a target industry.

    Args:
        framework_code: Regulatory code ('RBI_CSF', 'SEBI_CSCRF', 'NIST_AI_RMF', 'ISO_42001', 'DPDP_ACT').
        industry: Target industry sector (e.g. 'Banking', 'FinTech', 'Healthcare', 'Enterprise SaaS').
    """
    matched_key = next((k for k in REGULATORY_FRAMEWORKS if k.lower() == framework_code.strip().lower()), None)
    if not matched_key:
        return f"Error: Framework '{framework_code}' not found."

    fw = REGULATORY_FRAMEWORKS[matched_key]
    checklist = []

    for d in fw["domains"]:
        for c in d["controls"]:
            checklist.append({
                "item_id": c["control_id"],
                "domain": d["domain"],
                "control_name": c["title"],
                "audit_question": f"Does the {industry} organization have verified technical evidence for '{c['requirement']}'?",
                "mandatory_evidence": c["cygeniq_mapping"]["evidence"],
                "verifying_solution": c["cygeniq_mapping"]["product"]
            })

    return json.dumps({
        "framework": fw["name"],
        "target_industry": industry,
        "total_checklist_items": len(checklist),
        "checklist": checklist
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
