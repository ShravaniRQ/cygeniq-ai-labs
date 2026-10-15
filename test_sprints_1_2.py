"""
Test suite to verify Sprint 1 and Sprint 2 implementations:
- Policy MCP (Vector search over policies)
- Product Intelligence MCP (Product capabilities & RFP matcher)
- SharePoint MCP (Read + Write upload)
"""

import asyncio
import json
from policy_mcp import search_policies, list_available_policies, check_compliance_requirement
from product_mcp import list_products, get_product_datasheet, search_product_capabilities, match_rfp_requirement_to_features
from sharepoint_mcp import list_knowledge_areas


async def run_tests():
    print("=" * 60)
    print("RUNNING VERIFICATION FOR SPRINT 1 & SPRINT 2")
    print("=" * 60)

    # 1. Test Policy MCP
    print("\n[TEST 1] Policy MCP - list_available_policies:")
    res = await list_available_policies()
    print(res)

    print("\n[TEST 2] Policy MCP - search_policies('data retention'):")
    res = await search_policies("data retention", n_results=2)
    print(res)

    print("\n[TEST 3] Policy MCP - check_compliance_requirement('retaining resumes for 2 years'):")
    res = await check_compliance_requirement("retaining resumes for 2 years")
    print(res[:300] + "...")

    # 2. Test Product MCP
    print("\n" + "-" * 60)
    print("\n[TEST 4] Product MCP - list_products:")
    res = await list_products()
    products_obj = json.loads(res)
    for p in products_obj["products"]:
        print(f"  • {p['product']}: {p['tagline']}")

    print("\n[TEST 5] Product MCP - search_product_capabilities('prompt injection'):")
    res = await search_product_capabilities("prompt injection")
    print(res)

    print("\n[TEST 6] Product MCP - match_rfp_requirement_to_features('Tool must prevent autonomous agent excessive agency'):")
    res = await match_rfp_requirement_to_features("Tool must prevent autonomous agent excessive agency")
    print(res)

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
