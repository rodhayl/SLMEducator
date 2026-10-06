"""Display every visible generated field without duplicated provenance."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
for name in sys.argv[1:]:
    path = ROOT/'temp'/name
    rows = [r for p in sorted(path.glob('*-results.json')) for r in json.loads(p.read_text(encoding='utf-8'))['cases']]
    for row in rows[int(__import__('os').environ.get('V11_READ_SKIP', '0')):]:
        result = row['result']
        def prune(value):
            if isinstance(value, dict):
                return {k:prune(v) for k,v in value.items() if k not in {'generation','schema_version','objectives'}}
            if isinstance(value, list):
                return [prune(v) for v in value]
            return value
        print(json.dumps({'id':row['id'], 'status':row['http_status'], 'lesson':prune(result.get('lesson')), 'exercises':prune(result.get('exercises')), 'assessment':prune(result.get('assessment')), 'items':result.get('items'), 'error':result.get('errors')}, ensure_ascii=False))
