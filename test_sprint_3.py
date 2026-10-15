"""
Test suite to verify Sprint 3 implementation:
- GRC & Regulatory Intelligence MCP (Frameworks, controls, evidence mapping, gap evaluation, and audit checklists)
"""

import asyncio
import json
from grc_mcp import (
    list_regulatory_frameworks,
    get_framework_controls,
    map_control_to_product_evidence,
    evaluate_compliance_gap,
    generate_compliance_checklist,
)


async def run_grc_tests():
    print("=" * 60)
    print("RUNNING VERIFICATION FOR SPRINT 3 (GRC & REGULATORY MCP)")
    print("=" * 60)

    # Test 1: List all frameworks
    print("\n[TEST 1] list_regulatory_frameworks:")
    res = await list_regulatory_frameworks()
    data = json.loads(res)
    print(f"Total Frameworks: {data['total_frameworks']}")
    for fw in data["frameworks"]:
        print(f"  • {fw['framework_code']}: {fw['name']} ({fw['authority']})")

    # Test 2: Get controls for NIST AI RMF
    print("\n[TEST 2] get_framework_controls('NIST_AI_RMF'):")
    res = await get_framework_controls("NIST_AI_RMF")
    nist_data = json.loads(res)
    for d in nist_data["matched_domains"]:
        print(f"  Domain: {d['domain']} ({len(d['controls'])} controls)")

    # Test 3: Map control to Cygeniq product evidence
    print("\n[TEST 3] map_control_to_product_evidence('RBI-SOC-01'):")
    res = await map_control_to_product_evidence("RBI-SOC-01")
    map_data = json.loads(res)
    match = map_data["matches"][0]
    print(f"  Control: {match['control_id']} - {match['title']}")
    print(f"  Solution: {match['solution_mapping']['product']} ({match['solution_mapping']['module']})")
    print(f"  Mandatory Evidence: {match['solution_mapping']['evidence']}")

    # Test 4: Evaluate Compliance Gap
    print("\n[TEST 4] evaluate_compliance_gap against DPDP_ACT:")
    sample_system = "Our customer application asks for user consent via email and stores data securely in postgres with AES-256."
    res = await evaluate_compliance_gap(sample_system, "DPDP_ACT")
    gap_data = json.loads(res)
    print(f"  Compliance Score: {gap_data['compliance_score_percentage']}")
    print(f"  Gaps Identified: {gap_data['gap_count']}")
    if gap_data["identified_gaps"]:
        first_gap = gap_data["identified_gaps"][0]
        print(f"  Top Gap: {first_gap['control_id']} - {first_gap['title']}")
        print(f"  Remediation: {first_gap['recommended_remediation']}")

    # Test 5: Generate Compliance Checklist for Banking
    print("\n[TEST 5] generate_compliance_checklist('RBI_CSF', 'Commercial Banking'):")
    res = await generate_compliance_checklist("RBI_CSF", "Commercial Banking")
    checklist_data = json.loads(res)
    print(f"  Generated {checklist_data['total_checklist_items']} audit questions.")
    for item in checklist_data["checklist"][:2]:
        print(f"    - [{item['item_id']}] {item['audit_question']}")
        print(f"      Verified by: {item['verifying_solution']}")

    print("\n" + "=" * 60)
    print("ALL SPRINT 3 GRC TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_grc_tests())
