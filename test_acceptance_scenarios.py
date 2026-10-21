import sys
import requests
import json

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://127.0.0.1:8000"

# 1. Login as admin
print("--- Logging in ---")
r_login = requests.post(f"{BASE}/auth/login", json={"username": "admin", "password": "CygeniqAdmin2024!"})
assert r_login.status_code == 200, f"Login failed: {r_login.text}"
token = r_login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("Login successful.\n")

SCENARIOS = [
    {
        "id": "1. Organizational Identity",
        "question": "What is Cygeniq?",
        "check": lambda ans: any(w in ans.lower() for w in ["organization", "overall organization", "company"])
    },
    {
        "id": "2. Application Identity",
        "question": "What is Cygeniq AI Labs?",
        "check": lambda ans: any(w in ans.lower() for w in ["application", "internal application", "ai practice team"])
    },
    {
        "id": "3. Team Collaboration",
        "question": "How are the AI Practice Team and developing team related?",
        "check": lambda ans: any(w in ans.lower() for w in ["collaborat", "same organization", "responsibilities"])
    },
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

results = []
for sc in SCENARIOS:
    print(f"Testing Scenario: {sc['id']}")
    print(f"Q: {sc['question']}")
    session_id = f"test-sc-{abs(hash(sc['id']))}"
    res = requests.post(
        f"{BASE}/chat",
        headers=headers,
        json={"message": sc["question"], "session_id": session_id},
        timeout=60
    )
    if res.status_code != 200:
        print(f"  ❌ Error HTTP {res.status_code}: {res.text}")
        results.append((sc['id'], False, f"HTTP {res.status_code}"))
        continue

    data = res.json()
    blocks = data.get("blocks", [""])
    reply = blocks[0] if blocks else ""
    passed = sc["check"](reply)
    clean_snippet = reply.replace("\n", " ")[:220]
    print(f"  Status: {'✅ PASSED' if passed else '⚠️ NEEDS REVIEW'}")
    print(f"  Snippet: {clean_snippet}...")
    results.append((sc['id'], passed, clean_snippet))
    print()

print("="*60)
print("ACCEPTANCE TEST SUITE SUMMARY:")
print("="*60)
all_pass = True
for sc_id, passed, snippet in results:
    status_icon = "✅ PASS" if passed else "❌ FAIL"
    if not passed: all_pass = False
    print(f"{status_icon} | {sc_id}")

print("="*60)
print(f"FINAL RESULT: {'ALL SCENARIOS PASSED' if all_pass else 'SOME SCENARIOS FAILED'}")
