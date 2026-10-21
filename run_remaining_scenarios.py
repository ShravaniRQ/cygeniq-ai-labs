import sys
import time
import requests

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://127.0.0.1:8000"

# Login as admin
r_login = requests.post(f"{BASE}/auth/login", json={"username": "admin", "password": "CygeniqAdmin2024!"})
assert r_login.status_code == 200, f"Login failed: {r_login.text}"
token = r_login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

SCENARIOS = [
    {
        "id": "4. Product Association",
        "question": "Which products are associated with Cygeniq?",
        "check": lambda ans: "hexashield" in ans.lower() and "grcortex" in ans.lower() and "cybertix" in ans.lower()
    },
    {
        "id": "5. Application vs Product",
        "question": "Does Cygeniq AI Labs develop HexaShield AI, GRCortex, and CyberTix AI?",
        "check": lambda ans: any(w in ans.lower() for w in ["internal application", "cygeniq owns", "does not develop", "application used by", "not the developer", "parent organization"])
    },
    {
        "id": "6. Shared Product Improvement",
        "question": "How can the AI Practice Team contribute to product improvement?",
        "check": lambda ans: any(w in ans.lower() for w in ["poc", "research", "requirement", "feedback", "testing", "evaluation"])
    },
    {
        "id": "7. Autonomous Claims (CyberTix)",
        "question": "Does CyberTix AI automatically resolve all Tier-1 incidents without human verification?",
        "check": lambda ans: any(w in ans.lower() for w in ["no", "does not", "human", "operator", "assist", "verification", "triage"])
    },
    {
        "id": "8. Guaranteed Compliance (GRCortex)",
        "question": "Does GRCortex guarantee complete compliance out of the box with every framework?",
        "check": lambda ans: any(w in ans.lower() for w in ["no", "does not guarantee", "audit", "evidence", "specific", "verification"])
    }
]

print("=== Running Acceptance Scenarios 4 through 8 ===")
for sc in SCENARIOS:
    print(f"\n[SCENARIO] {sc['id']}")
    print(f"Q: {sc['question']}")
    session_id = f"test-session-{abs(hash(sc['id']))}"
    try:
        res = requests.post(
            f"{BASE}/chat",
            headers=headers,
            json={"message": sc["question"], "session_id": session_id},
            timeout=120
        )
        if res.status_code != 200:
            print(f"❌ HTTP {res.status_code}: {res.text}")
            continue
        data = res.json()
        reply = data.get("blocks", [""])[0]
        sources = [s["tool"] for s in data.get("sources", [])]
        passed = sc["check"](reply)
        print(f"Status: {'✅ PASSED' if passed else '⚠️ REVIEW'}")
        print(f"Tools Used: {sources}")
        snippet = reply.replace("\n", " ")[:260]
        print(f"Response: {snippet}...")
    except Exception as e:
        print(f"❌ Exception: {e}")
    time.sleep(3)

print("\n=== Acceptance Scenarios Run Complete ===")
