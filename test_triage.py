import httpx, json
payload = {'message': 'Our API response times have spiked to 5s and we are seeing 503 errors'}
r = httpx.post('http://127.0.0.1:8090/triage', json=payload, timeout=120)
print('Status:', r.status_code)
data = r.json()
for result in data.get('results', []):
    print(f"Agent: {result['agent']}, Tools: {result['tools_used']}")
    print(result['content'][:200])
    print('---')
