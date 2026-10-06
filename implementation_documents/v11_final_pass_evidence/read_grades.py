import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for name,count in [('v11-historical-objective',36),('v11-development',12)]:
    path=ROOT/'temp'/name/'inference.jsonl'
    for line in path.read_text(encoding='utf-8').splitlines()[count:]:
        r=json.loads(line)
        print(r['request']['messages'][-1]['content'].split('Provide detailed grading')[0])
        print(r['response']['choices'][0]['message']['content'])
