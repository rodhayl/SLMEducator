"""Print synthetic output and frozen criteria for manual technical review."""
import json
from pathlib import Path
import sys

def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k != 'generation' and not (k == 'content' and 'sections' in value)}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value

ROOT = Path(__file__).resolve().parents[1]
fixtures = {c['id']: c for p in (ROOT / 'tests/fixtures').glob('local_semantic*.json') for c in json.loads(p.read_text(encoding='utf-8')).get('cases', [])}
data = json.loads((ROOT / sys.argv[1]).read_text(encoding='utf-8'))
for c in data['cases'][int(sys.argv[2]) if len(sys.argv) > 2 else 0:]:
    print(c['id'], 'ORACLE:', fixtures[c['id']]['oracle'])
    print(json.dumps(clean({k:c['result'].get(k) for k in ['lesson','exercises','assessment']}), ensure_ascii=True))
