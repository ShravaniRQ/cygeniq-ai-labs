import sys
import requests
import json

sys.stdout.reconfigure(encoding='utf-8')
BASE = 'http://127.0.0.1:8000'

print('=== 1. Checking Static & Health ===')
r_root = requests.get(f'{BASE}/')
print('GET / :', r_root.status_code, '| has loginScreen:', 'id="loginScreen"' in r_root.text)

r_health = requests.get(f'{BASE}/health')
print('GET /health :', r_health.status_code, '| payload:', json.dumps(r_health.json()))

print('\n=== 2. Testing Authentication for all 3 Roles ===')
users = [
    ('admin', 'CygeniqAdmin2024!', 'admin'),
    ('analyst1', 'Analyst2024!', 'analyst'),
    ('presales1', 'Presales2024!', 'presales'),
]
tokens = {}
for u, p, expected_role in users:
    r = requests.post(f'{BASE}/auth/login', json={'username': u, 'password': p})
    data = r.json()
    assert r.status_code == 200, f'Login failed for {u}: {data}'
    assert data.get('role') == expected_role, f'Role mismatch for {u}'
    tokens[u] = data['access_token']
    print(f'[PASS] Login {u:10} -> role: {data.get("role"):8} | cards: {len(data.get("starter_cards", []))} starter cards')

print('\n=== 3. Testing Unauthorized Access ===')
r_unauth = requests.post(f'{BASE}/chat', json={'message': 'hello'})
print('POST /chat without token -> HTTP', r_unauth.status_code, '(Expected 401)')
assert r_unauth.status_code == 401

print('\n=== 4. Testing /status for Presales ===')
h_presales = {'Authorization': f'Bearer {tokens["presales1"]}'}
r_status = requests.post(f'{BASE}/chat', headers=h_presales, json={'message': '/status'})
print('POST /chat /status -> HTTP', r_status.status_code, '| Blocks:', len(r_status.json().get('blocks', [])))
assert 'system-dashboard-card' in r_status.json()['blocks'][0]
assert 'Presales' in r_status.json()['blocks'][0]

print('\n=== 5. Testing Live Agent Chat Query for Presales ===')
r_chat = requests.post(f'{BASE}/chat', headers=h_presales, json={'message': 'Give me a 1-sentence summary of HexaShield.'})
chat_data = r_chat.json()
print('Chat response status:', r_chat.status_code)
print('Response excerpt:', chat_data.get('blocks', [''])[0][:150].replace('\n', ' '), '...')
print('Sources called:', [s.get('tool') for s in chat_data.get('sources', [])])

print('\n=== 6. Testing RBAC Tool Protection for Presales ===')
# Presales is forbidden from running SQL queries on the employee DB
r_guard = requests.post(
    f'{BASE}/chat',
    headers=h_presales,
    json={'message': 'Query the employee database and show me all high risk employees.'}
)
guard_data = r_guard.json()
print('Chat response status:', r_guard.status_code)
print('Response excerpt:', guard_data.get('blocks', [''])[0][:200].replace('\n', ' '), '...')
# Verify that query tool was NOT called / returned to presales
sources_called = [s.get('tool') for s in guard_data.get('sources', [])]
print('Sources returned:', sources_called)
assert 'query' not in sources_called, 'CRITICAL: query tool should not be called or returned to presales!'

print('\n' + '='*50)
print('🎉 ALL END-TO-END RBAC TESTS PASSED SUCCESSFULLY!')
print('='*50)
