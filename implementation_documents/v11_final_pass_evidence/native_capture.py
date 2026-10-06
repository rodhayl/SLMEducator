"""Filter native events in memory to only this pass's exact synthetic requests."""
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'implementation_documents/v11_final_pass_evidence'
specs = ['local_semantic_objective_20261005.json', 'local_semantic_source_review_20261005.json', 'local_semantic_source_trust_development_20261006.json']
sources = [c['source'] for name in specs for c in json.loads((ROOT/'tests/fixtures'/name).read_text(encoding='utf-8'))['cases']]
started_ms = int(time.time()*1000)
process = subprocess.Popen([r'C:\Users\dhays\.lmstudio\bin\lms.exe', 'log', 'stream', '--source', 'model', '--filter', 'input', '--json'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8')
(OUT/'capture_start.json').write_text(json.dumps({'pid': process.pid, 'inferences': 0, 'filter': 'Exact frozen synthetic source or exact grading question from this pass; other events discarded in memory.'}), encoding='utf-8')
print('Native stream started', flush=True)
try:
    for line in process.stdout:
        try:
            event = json.loads(line)
            data = event['data']
        except (ValueError, KeyError):
            continue
        native = data.get('input', '')
        if event.get('timestamp', 0) < started_ms:
            continue
        if data.get('modelIdentifier') != 'slm-production-evaluation':
            continue
        matched = any(source in native for source in sources)
        if not matched and 'Grade this student' in native:
            for path in (ROOT/'temp').glob('v11-*/**/*-results.json'):
                try:
                    rows = json.loads(path.read_text(encoding='utf-8'))['cases']
                    for row in rows:
                        assessment = row['result'].get('assessment') or {}
                        for question in assessment.get('questions', []):
                            text = question.get('question') or question.get('question_text')
                            if text and 'Question: '+text+'\n' in native:
                                matched = True
                except (ValueError, KeyError):
                    continue
        if matched:
            with (OUT/'native_inputs.jsonl').open('a', encoding='utf-8') as output:
                output.write(line)
            print('Captured synthetic native input', flush=True)
finally:
    process.terminate()
    process.wait(timeout=10)
