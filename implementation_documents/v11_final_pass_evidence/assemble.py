"""Assemble immutable synthetic responses and explicit manual rubric decisions."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'implementation_documents/v11_final_pass_evidence'
DIMS = ['accuracy', 'source_fidelity', 'usefulness', 'readability', 'missing_information']
# These are manual judgments after reading all claims, summaries and questions.
# No model judge, inferred pass from HTTP status, or historical score copying.
DECISIONS = json.loads((OUT / 'decisions.json').read_text(encoding='utf-8'))

specs = [('historical-objective','v11-historical-objective',['development','reserved'],'local_semantic_objective_20261005.json'),
         ('historical-source-review','v11-historical-source-review',['reserved'],'local_semantic_source_review_20261005.json'),
         ('development','v11-development',['development'],'local_semantic_source_trust_development_20261006.json')]
native = [json.loads(line) for line in (OUT / 'native_inputs.jsonl').read_text(encoding='utf-8').splitlines()]
scores = {'scope': 'Evaluación técnica manual del agente, sin juez LLM ni aceptación humana educativa; una sola pasada.', 'dimensions': DIMS, 'acceptance': 'Exactly five 2 scores', 'cases': []}
checks = {'cases': [], 'batteries': [], 'grading': []}
all_generation_inferences = 0
all_inferences = 0
for label, state_name, splits, fixture_name in specs:
    state = ROOT / 'temp' / state_name
    fixture_path = ROOT / 'tests/fixtures' / fixture_name
    fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
    frozen = {c['id']: c for c in fixture['cases']}
    transport = [json.loads(line) for line in (state / 'inference.jsonl').read_text(encoding='utf-8').splitlines()]
    shutil.copyfile(state / 'inference.jsonl', OUT / (label + '-inference.jsonl'))
    audit = json.loads((OUT / (label + '-saved-audit.json')).read_text(encoding='utf-8'))
    saved = {c['id']: c for c in audit['cases']}
    rows = []
    for split in splits:
        path = state / (split + '-results.json')
        shutil.copyfile(path, OUT / (label + '-' + split + '-results.json'))
        rows.extend(json.loads(path.read_text(encoding='utf-8'))['cases'])
    assert len(rows) == len(frozen)
    generation = transport[:len(rows)]
    assert len(generation) == len(rows)
    assert len(transport) == len(rows) + sum(g.get('inferences_after_repeat',0)-g['inferences_before'] for g in audit['grading'])
    for row, inference in zip(rows, generation):
        case = frozen[row['id']]
        values, reason = DECISIONS[row['id']]
        assert len(values) == 5 and all(v in [0,1,2] for v in values)
        scores['cases'].append({'id': row['id'], 'battery': label, 'fixture': fixture_name, 'split': case['split'], 'oracle': case['oracle'], 'scores': dict(zip(DIMS,values)), 'accepted': values == [2]*5, 'reason': reason})
        saved_row = saved[row['id']]
        source = saved_row['source']['response']['source']['extracted_text']
        tree = saved_row['tree']['response']['contents']
        ids = row['result']['saved_content_ids']
        item_checks = []
        for content in saved_row['saved_contents']:
            data = content['response']['content_data']
            gen = data['generation']
            usage = gen['source_usage']
            literal = '\n\n'.join('['+p['reference']+']\n'+source[p['start']:p['end']] for p in usage['ranges'])
            item_checks.append({'content_id': content['response']['id'], 'version': gen['prompt_version'],
                'expected_version': gen['prompt_version'] == ('teacher-reviewed-v11-consistent-lesson-claims' if case['kind']=='lesson' else 'teacher-reviewed-v10-separated-lesson-request'),
                'draft_unverified': gen['review_status']=='draft' and gen['source_support']=='unverified',
                'fragment_hash_matches': hashlib.sha256(usage['fragment'].encode()).hexdigest()==usage['fragment_hash'],
                'document_hash_matches': hashlib.sha256(source.encode()).hexdigest()==usage['source_document_id'],
                'literal_ranges_match': literal==usage['fragment'],
                'character_counts_match': len(usage['fragment'])==usage['included_characters'] and len(source)==usage['source_characters'],
                'budget_at_most_6000': len(usage['fragment'])<=6000,
                'fragment_in_request': usage['fragment'] in inference['request']['messages'][-1]['content'],
                'use_coverage': usage['use_coverage'], 'extraction_coverage': gen['extraction_coverage']})
        matches = [n for n in native if all(m['content'].strip() in n['data']['input'] for m in inference['request']['messages'])]
        repeat = row.get('repeat',{})
        task_matches = True
        if case['kind'] == 'lesson':
            task = json.loads(inference['request']['messages'][-1]['content'].split('\n\n')[0].split('\n',1)[1])
            task_matches = task['topic']==case['topic'] and task['grade_level']==case['level'] and task['learning_objectives']==[case['objective']]
        checks['cases'].append({'id':row['id'], 'battery':label, 'initial_status':row['http_status'],
            'all_ready': bool(row['result']['items']) and all(i['status']=='ready' for i in row['result']['items']),
            'replay_same_result': repeat.get('result')==row['result'], 'replay_status':repeat.get('http_status'),
            'replay_same_saved_ids':repeat.get('result',{}).get('saved_content_ids')==ids,
            'replay_same_item_identity':repeat.get('result',{}).get('items')==row['result']['items'],
            'persisted_ids_match': sorted(i['id'] for i in tree)==sorted(ids),
            'no_duplicate_ids_or_positions':len(tree)==len(ids)==len(set(ids))==len({(i['phase_index'],i['order_index']) for i in tree}),
            'publication_409':row.get('unreviewed_publication_status', saved_row.get('unreviewed_publication',{}).get('status'))==409,
            'roles': [m['role'] for m in inference['request']['messages']], 'lesson_roles_separate':case['kind']!='lesson' or [m['role'] for m in inference['request']['messages']]==['system','user'],
            'lesson_task_fields_literal':task_matches,
            'parameters':{k:inference['request'].get(k) for k in ['model','temperature','max_tokens','reasoning_effort']},
            'usage':inference['response'].get('usage'), 'native_input_matches':len(matches),
            'native_input_reasoning_disabled': all('<|think|>' not in n['data']['input'] for n in matches) if matches else None,
            'saved_items':item_checks})
    for grade in audit['grading']:
        checks['grading'].append({'id':grade['id'],'provisional':grade.get('provisional'), 'repeat_same_attempt':grade.get('repeat_same_attempt'),
            'initial_inferences':grade.get('inferences_after_initial',0)-grade['inferences_before'],
            'repeat_inferences':grade.get('inferences_after_repeat',0)-grade.get('inferences_after_initial',0), 'error':grade.get('error')})
    checks['batteries'].append({'label':label,'cases':len(rows),'accepted':sum(scores['cases'][-len(rows)+i]['accepted'] for i in range(len(rows))),
        'generation_inferences':len(generation),'grading_inferences':len(transport)-len(generation),'total_inferences':len(transport), 'generation_seconds':sum(r['seconds'] for r in rows),
        'fixture_sha256':hashlib.sha256(fixture_path.read_bytes()).hexdigest(), 'fixture_git_blob':subprocess.check_output(['git','hash-object',str(fixture_path)],cwd=ROOT,text=True).strip()})
    all_generation_inferences += len(generation)
    all_inferences += len(transport)
checks['totals']={'generation_inferences':all_generation_inferences,'grading_inferences':all_inferences-all_generation_inferences,'probe_inferences':0,'all_inferences':all_inferences,
    'application_generation_requests':sum(1+('repeat' in c) for _,state,splits,_ in specs for split in splits for c in json.loads((ROOT/'temp'/state/(split+'-results.json')).read_text(encoding='utf-8'))['cases']),
    'native_inputs_with_exact_request_match':sum(c['native_input_matches']>0 for c in checks['cases'])}
scores['historical_accepted']=sum(c['accepted'] for c in scores['cases'] if c['battery']!='development')
scores['historical_total']=44
scores['development_accepted']=sum(c['accepted'] for c in scores['cases'] if c['battery']=='development')
scores['development_total']=12
for name,data in [('scores.json',scores),('checks.json',checks)]:
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
assert len(scores['cases'])==56 and len(DECISIONS)==56
print(json.dumps({'batteries':checks['batteries'],'totals':checks['totals'],'failed':[c['id'] for c in scores['cases'] if not c['accepted']]},indent=2))
