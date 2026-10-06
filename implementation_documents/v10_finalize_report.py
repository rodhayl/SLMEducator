"""Validate the completed evaluation and inventory its sanitized artifacts."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'implementation_documents/v10_single_pass_evidence'
report = ROOT / 'implementation_documents/source_trust_20261006_single_pass_report.md'
scores = json.loads((OUT / 'scores.json').read_text(encoding='utf-8'))
checks = json.loads((OUT / 'checks.json').read_text(encoding='utf-8'))
assert len(scores['cases']) == len(checks['cases']) == 56
assert scores['historical_accepted'] == 35 and scores['development_accepted'] == 8
for c in checks['cases']:
    for key in ['all_ready', 'replay_same_saved_ids', 'replay_same_item_identity', 'persisted_ids_match', 'no_duplicate_ids_or_positions', 'publication_409', 'lesson_roles_separate', 'lesson_task_fields_literal']:
        assert c[key], (c['id'],key)
    assert c['initial_status']==c['replay_status']==200
    assert c['parameters']['temperature']==0 and c['parameters']['reasoning_effort']=='none'
    assert c['parameters']['model']=='slm-production-evaluation'
    assert c['parameters']['max_tokens'] in [2000,4000]
    assert c['usage']['completion_tokens_details']['reasoning_tokens']==0
    for item in c['saved_items']:
        for key in ['v10','draft_unverified','fragment_hash_matches','document_hash_matches','literal_ranges_match','character_counts_match','budget_at_most_6000','fragment_in_request']:
            assert item[key], (c['id'],key)
for grade in checks['grading']:
    assert grade['provisional'] and grade['repeat_same_attempt'] and grade['initial_inferences']==1 and grade['repeat_inferences']==0 and grade['error'] is None
assert len(checks['grading'])==5 and checks['totals']['all_inferences']==62
baseline = json.loads((OUT/'historical-v9-scores.json').read_text(encoding='utf-8'))
assert baseline['accepted']==37 and len([c for c in baseline['cases'] if not c['accepted']])==7
assert (OUT/'historical-v9-scores.json').read_bytes()==(ROOT/'docs/reports/windows-v9-semantic-gui-20261006/evidence/final-scores.json').read_bytes()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='7a60df5e5b3d76af48996c2e052f283eee66b2b8'
assert subprocess.check_output(['git','diff','--','src','tests/fixtures'],cwd=ROOT)==b''
first_and_last = []
for label,count in [('historical-objective',36),('historical-source-review',8),('development',12)]:
    records = [json.loads(line) for line in (OUT/(label+'-inference.jsonl')).read_text(encoding='utf-8').splitlines()][:count]
    first_and_last.append((records[0]['response']['created'],records[-1]['response']['created']))
assert first_and_last[0][1] <= first_and_last[1][0]
assert first_and_last[1][1] <= first_and_last[2][0]
def inspect_secrets(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key.lower() in {'password','access_token','authorization','jwt_secret','slm_encryption_key','recovery_key','api_key','credentials'}:
                assert item in (None,''), key
            inspect_secrets(item)
    elif isinstance(value,list):
        for item in value:
            inspect_secrets(item)
for path in OUT.iterdir():
    assert path.suffix not in {'.db','.key','.log'} and path.name!='fixture.json'
    if path.suffix=='.json':
        inspect_secrets(json.loads(path.read_text(encoding='utf-8-sig')))
    elif path.suffix=='.jsonl':
        for line in path.read_text(encoding='utf-8').splitlines():
            inspect_secrets(json.loads(line))
body = report.read_text(encoding='utf-8').split('\n### Regresión histórica 44 casos')[0].rstrip()
parts = []
for title,development in [('Regresión histórica 44 casos',False),('Desarrollo independiente 12 casos',True)]:
    parts.extend(['\n### '+title+'\n','| Caso | A | F | U | L | I | Resultado |','|---|---:|---:|---:|---:|---:|---|'])
    for case in scores['cases']:
        if (case['battery']=='development') != development:
            continue
        values = ' | '.join(str(case['scores'][d]) for d in scores['dimensions'])
        parts.append('| '+case['id']+' | '+values+' | '+('PASS' if case['accepted'] else 'FAIL')+' |')
report.write_text(body+'\n'+'\n'.join(parts)+'\n',encoding='utf-8')
commands = [
    {'command':'python -m pytest tests/test_local_provider_server_isolation.py tests/trust/test_ai_generation_boundaries.py -q --basetemp=.evaluation-state/focused-validation -p no:cacheprovider','result':'70 passed in 11.30s'},
    {'command':'python -m pytest tests/test_v10_evaluation_replay_guard.py -q -p no:cacheprovider --basetemp=.evaluation-state/replay-guard-tests','result':'5 passed in 0.72s'},
    {'command':'python -m flake8 tests/browser/evaluate_local_provider.py --select E9,F63,F7,F82 --jobs 1','result':'exit 0'},
    {'command':'python -m mypy tests/browser/evaluate_local_provider.py --follow-imports=silent --cache-dir=.evaluation-state/mypy','result':'exit 1, line 65: Sequence[str] has no attribute append'},
    {'command':'python -m mypy implementation_documents/v10_single_pass_evidence/baseline_evaluator.py --follow-imports=silent --cache-dir=.evaluation-state/mypy-baseline','result':'exit 1, original pinned bytes line 73: same Sequence[str] append error'},
]
for state,port,cases,splits in [('v10-historical-objective',8111,'local_semantic_objective_20261005.json',['development','reserved']),('v10-historical-source-review',8112,'local_semantic_source_review_20261005.json',['reserved']),('v10-development',8113,'local_semantic_source_trust_development_20261006.json',['development'])]:
    commands.append({'command':f'python tests/browser/local_provider_server.py --state-dir .evaluation-state/{state} --port {port}','result':'NEW synthetic state created'})
    for split in splits:
        commands.append({'command':f'python tests/browser/evaluate_local_provider.py --state-dir .evaluation-state/{state} --base-url http://127.0.0.1:{port} --cases-file tests/fixtures/{cases} --split {split} --max-tokens 4000 --reasoning-effort none','result':'exit 0; see preserved first responses and replays'})
verification={'python':r'..\.production-worktree\venv\Scripts\python.exe','commands':commands,'preparation_errors':['Initial pytest named a nonexistent tests/test_source_prompt_boundaries.py; zero tests ran.','Initial inline report-table helper had SyntaxError; no report write or inference occurred.'],
    'requirements_audit':{'pinned_source':True,'new_synthetic_states':3,'frozen_fixture_blobs_unchanged':True,'application_and_prompts_diff_empty':True,'historical_cases_once':44,'development_cases_once_after_historical':12,'explicit_five_dimensional_scores':56,'historical_v9_preserved':True,'ready_only_replay_guard_verified':True,'first_response_durable_verified':True,'per_content_v10_receipts_verified':56,'lesson_role_and_task_fields_verified':40,'publication_409':56,'provisional_open_grades':5,'real_inference_accounting_verified':62,'native_render_coverage':52},
    'limitation':'Four generation calls lack a matching native rendered-input trace; all HTTP provider requests/responses are preserved. No repeat to fill missing traces.'}
(OUT/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
files = [p for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json']
files += [report, ROOT/'.gitattributes', ROOT/'tests/browser/evaluate_local_provider.py',ROOT/'tests/test_v10_evaluation_replay_guard.py']
files += list((ROOT/'implementation_documents').glob('v10_*.py'))
manifest={'source_commit':'7a60df5e5b3d76af48996c2e052f283eee66b2b8','source_tree':'475ed46e2b8b66431bae2162243007b82b606d20','written_at_utc':datetime.now(timezone.utc).isoformat(),
          'hash_scope':'Observed working-file bytes. evaluated_harness.py preserves the executed harness bytes; Git may normalize the tracked harness line endings.',
          'files':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
for link in re.findall(r'\]\(([^)]+)\)',report.read_text(encoding='utf-8')):
    if not link.startswith('https://'):
        assert (report.parent/link).exists(), link
print('Verified 56 scores, 56 receipts, 56 replays, 56 publication guards, 5 provisional grades, 62 inferences.')
print('Report links exist; manifest files:',len(manifest['files']))
