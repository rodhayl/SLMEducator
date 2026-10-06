"""Audit only newly generated synthetic state and provisional open grading."""
import argparse
import json
from pathlib import Path
import time
import httpx

parser = argparse.ArgumentParser()
parser.add_argument('--state-dir', type=Path, required=True)
parser.add_argument('--base-url', required=True)
parser.add_argument('--label', required=True)
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[2]
destination = ROOT / 'implementation_documents/v11_final_pass_evidence' / (args.label + '-saved-audit.json')
if destination.exists():
    raise SystemExit('Audit already exists; never repeat grading')
fixture = json.loads((args.state_dir / 'fixture.json').read_text(encoding='utf-8'))
rows = [c for p in sorted(args.state_dir.glob('*-results.json')) for c in json.loads(p.read_text(encoding='utf-8'))['cases']]
audit = {'cases': [], 'grading': [], 'preparation': 'Synthetic automated workflow review/publication for grading checks; no human educational approval.'}
def count():
    path = args.state_dir / 'inference.jsonl'
    return len(path.read_text(encoding='utf-8').splitlines()) if path.exists() else 0
def save():
    destination.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
with httpx.Client(base_url=args.base_url, trust_env=False, timeout=310) as client:
    def login(username):
        account = next(c for c in fixture['credentials'] if c['username'] == username)
        response = client.post('/api/auth/login', data={'username': username, 'password': account['password']})
        response.raise_for_status()
        client.headers['Authorization'] = 'Bearer ' + response.json()['access_token']
    login('learner_a')
    learner_id = client.get('/api/auth/me').json()['id']
    login('teacher_a')
    for row in rows:
        login('teacher_a')
        record = {'id': row['id'], 'plan_id': row['plan_id'], 'saved_contents': []}
        audit['cases'].append(record)
        for url, key in [(f"/api/study-plans/{row['plan_id']}/tree", 'tree'), (f"/api/study-plans/{row['plan_id']}/source", 'source')]:
            response = client.get(url)
            record[key] = {'status': response.status_code, 'response': response.json()}
        for content_id in row['result'].get('saved_content_ids', []):
            response = client.get(f'/api/content/{content_id}')
            record['saved_contents'].append({'status': response.status_code, 'response': response.json()})
        if 'unreviewed_publication_status' not in row:
            response = client.post(f"/api/study-plans/{row['plan_id']}/workflow", json={'action': 'publish'})
            record['unreviewed_publication'] = {'request': {'action': 'publish'}, 'status': response.status_code, 'response': response.json()}
        save()
        if not row['result'].get('assessment'):
            continue
        assessment_id = next((i.get('assessment_id') for i in row['result']['items'] if i.get('assessment_id')), None)
        if not assessment_id:
            continue
        grading = {'id': row['id'], 'assessment_id': assessment_id, 'actions': [], 'inferences_before': count()}
        audit['grading'].append(grading)
        def action(method, url, payload=None):
            start = time.monotonic()
            response = client.request(method, url, json=payload) if payload is not None else client.request(method, url)
            grading['actions'].append({'method': method, 'url': url, 'request': payload, 'status': response.status_code, 'response': response.json(), 'seconds': time.monotonic()-start})
            save()
            response.raise_for_status()
            return response.json()
        try:
            definition = action('GET', f'/api/assessments/{assessment_id}')
            action('POST', f'/api/assessments/{assessment_id}/publish')
            action('POST', f"/api/study-plans/{row['plan_id']}/workflow", {'action': 'review'})
            action('POST', f"/api/study-plans/{row['plan_id']}/workflow", {'action': 'publish'})
            action('POST', f"/api/study-plans/{row['plan_id']}/assign", {'student_ids': [learner_id]})
            login('learner_a')
            attempt = action('POST', f'/api/assessments/{assessment_id}/start')
            payload = {'submission_id': attempt['submission_id'], 'answers': [{'question_id': q['id'], 'response_text': q.get('correct_answer') or 'The supplied evidence does not establish this fact.'} for q in definition['questions']]}
            initial = action('POST', f'/api/assessments/{assessment_id}/submit', payload)
            grading['inferences_after_initial'] = count()
            repeat = action('POST', f'/api/assessments/{assessment_id}/submit', payload)
            grading['inferences_after_repeat'] = count()
            grading['provisional'] = initial.get('score') is None and initial.get('needs_review') is True
            grading['repeat_same_attempt'] = repeat.get('submission_id') == initial.get('submission_id')
        except Exception as error:
            grading['error'] = str(error)
        save()
        print(row['id'], 'grading', grading.get('provisional'), grading.get('error', ''), flush=True)
audit['inferences_final'] = count()
save()
