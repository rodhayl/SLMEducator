"""Capture only the uniquely marked synthetic control inference."""
import json
from pathlib import Path
import subprocess
import threading
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]
directory = ROOT / 'implementation_documents/v10_single_pass_evidence'
marker = 'SLM_V10_PREFLIGHT_20261006_SINGLE_PASS'
records = []
process = subprocess.Popen([r'C:\Users\dhays\.lmstudio\bin\lms.exe', 'log', 'stream', '--source', 'model', '--filter', 'input', '--json'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8')
def collect():
    for line in process.stdout:
        if marker in line:
            records.append(line)
threading.Thread(target=collect, daemon=True).start()
time.sleep(3)
request = {'model': 'slm-production-evaluation', 'messages': [
    {'role': 'system', 'content': marker + ' system rule: respond OK.'},
    {'role': 'user', 'content': marker + ' synthetic user data.'}],
    'temperature': 0, 'max_tokens': 4, 'reasoning_effort': 'none'}
start = time.monotonic()
with httpx.Client(trust_env=False, timeout=60) as client:
    response = client.post('http://127.0.0.1:1234/v1/chat/completions', json=request)
time.sleep(2)
process.terminate()
process.wait(timeout=10)
(directory / 'effective_probe.json').write_text(json.dumps({'request': request, 'response': response.json(), 'status': response.status_code, 'seconds': time.monotonic()-start, 'inferences': 1}, indent=2), encoding='utf-8')
(directory / 'effective_probe_native.jsonl').write_text(''.join(records), encoding='utf-8')
print('http_status', response.status_code, 'native_records', len(records))
for record in records:
    print(record)
