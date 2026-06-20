from dotenv import load_dotenv
load_dotenv()
import requests, json, traceback

try:
    r = requests.post(
        'http://127.0.0.1:8000/api/chat',
        json={'message': 'summarize the document', 'session_id': 'test-session-debug-456', 'document_ids': None},
        stream=True,
        timeout=30
    )
    print('Status:', r.status_code)
    for line in r.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            print(decoded[:300])
except Exception as e:
    traceback.print_exc()
