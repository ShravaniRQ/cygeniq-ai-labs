"""Quick test script to verify Microsoft Graph API auth and SharePoint connectivity."""
import os
from dotenv import load_dotenv
load_dotenv()

import msal
import requests

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

def get_token():
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    app = msal.ConfidentialClientApplication(CLIENT_ID, authority=authority, client_credential=CLIENT_SECRET)
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        print("[OK] Access token acquired successfully!")
        return result["access_token"]
    else:
        print(f"[ERROR] Auth failed: {result.get('error_description')}")
        return None

def find_site(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{GRAPH_BASE}/sites?search=Cygeniq", headers=headers)
    data = resp.json()
    sites = data.get("value", [])
    if sites:
        print(f"[OK] Found {len(sites)} site(s):")
        for s in sites:
            print(f"     - {s.get('displayName')} (ID: {s.get('id')})")
        site_id = sites[0]["id"]
        
        # Test Drives
        drives_resp = requests.get(f"{GRAPH_BASE}/sites/{site_id}/drives", headers=headers)
        if drives_resp.status_code == 200:
            drives = drives_resp.json().get("value", [])
            print(f"[OK] Found {len(drives)} drive(s):")
            for d in drives:
                print(f"     * Drive: '{d.get('name')}' (ID: {d.get('id')})")
                items_resp = requests.get(f"{GRAPH_BASE}/drives/{d['id']}/root/children", headers=headers)
                if items_resp.status_code == 200:
                    items = items_resp.json().get("value", [])
                    print(f"       Items ({len(items)}): {[it.get('name') for it in items]}")
                else:
                    print(f"       [WARN] Failed to list items in drive {d.get('name')}: {items_resp.status_code}")
        else:
            print(f"[WARN] Failed to list drives: {drives_resp.status_code} {drives_resp.text}")

        # Test Per-drive Search
        for d in drives:
            d_id = d["id"]
            d_name = d["name"]
            d_search = requests.get(f"{GRAPH_BASE}/drives/{d_id}/root/search(q='AI')", headers=headers)
            if d_search.status_code == 200:
                hits = d_search.json().get("value", [])
                if hits:
                    print(f"[OK] Drive '{d_name}' found {len(hits)} hit(s):")
                    for h in hits:
                        print(f"       * {h.get('name')} (id: {h.get('id')})")
            else:
                print(f"       Drive '{d_name}' search returned status: {d_search.status_code}")

        # Test Reading a document from a drive
        ai_prod = next((d for d in drives if d['name'] == 'AI Products'), None)
        if ai_prod:
            item_resp = requests.get(f"{GRAPH_BASE}/drives/{ai_prod['id']}/root:/HexaShield_Overview.docx", headers=headers)
            print(f"[OK] Fetched item metadata: {item_resp.status_code}")
            if item_resp.status_code == 200:
                item_data = item_resp.json()
                dl_url = item_data.get("@microsoft.graph.downloadUrl")
                if dl_url:
                    content_resp = requests.get(dl_url)
                    import io
                    from docx import Document
                    doc = Document(io.BytesIO(content_resp.content))
                    paras = [p.text for p in doc.paragraphs if p.text.strip()]
                    print(f"[OK] Successfully read HexaShield_Overview.docx ({len(paras)} paragraphs)!")
                    print(f"     Preview: {paras[0] if paras else 'empty'}")
    else:
        print(f"[WARN] No sites found. Response: {data}")

token = get_token()
if token:
    find_site(token)

import asyncio
from sharepoint_mcp import list_knowledge_areas, search_sharepoint, read_sharepoint_document

async def test_mcp_functions():
    print("\n" + "="*50)
    print("Testing SharePoint MCP Tools directly:")
    print("="*50)
    
    print("\n[TEST 1] list_knowledge_areas():")
    areas = await list_knowledge_areas()
    print(areas)

    print("\n[TEST 2] search_sharepoint('CyberTix'):")
    search_res = await search_sharepoint('CyberTix')
    print(search_res)

    print("\n[TEST 3] read_sharepoint_document('/AI Products/CyberTix_Overview.docx'):")
    doc_res = await read_sharepoint_document('/AI Products/CyberTix_Overview.docx')
    print(doc_res[:300] + ("..." if len(doc_res) > 300 else ""))

asyncio.run(test_mcp_functions())
