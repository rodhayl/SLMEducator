"""Retain only native input containing exact frozen synthetic source text."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sources = []
for name in ['local_semantic_objective_20261005.json', 'local_semantic_source_review_20261005.json', 'local_semantic_source_trust_development_20261006.json']:
    for case in json.loads((ROOT / 'tests/fixtures' / name).read_text(encoding='utf-8'))['cases']:
        sources.extend(line[:80] for line in case['source'].splitlines() if len(line) >= 30 and not line.startswith('['))
destination = ROOT / 'implementation_documents/v10_single_pass_evidence/native_inputs.jsonl'
process = subprocess.Popen([r'C:\Users\dhays\.lmstudio\bin\lms.exe', 'log', 'stream', '--source', 'model', '--filter', 'input', '--json'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8')
try:
    for line in process.stdout:
        try:
            data = json.loads(line)['data']
        except (ValueError, KeyError):
            continue
        native = data.get('input', '')
        if data.get('modelIdentifier') == 'slm-production-evaluation' and any(source in native for source in sources):
            with destination.open('a', encoding='utf-8') as output:
                output.write(line)
            print('Captured synthetic native input', flush=True)
finally:
    process.terminate()
    process.wait(timeout=10)
