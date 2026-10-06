"""Verify and document only the completed single synthetic pass."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'implementation_documents/v11_final_pass_evidence'
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
checks = read(OUT/'checks.json')
scores = read(OUT/'scores.json')
preflight = read(OUT/'preflight.json')
assert preflight['model_sha256']=='90fd44e29e0d7cffeb0fd00dc73cfdab9ed0b0e95306ecf7821ea634c940c370'
assert preflight['lm_studio_product_version']=='0.4.25.0'
assert 'nvidia-cuda12-avx2-2.51.0' in preflight['runtime_path']
loaded = preflight['loaded_instances']
if isinstance(loaded,dict) and 'value' in loaded: loaded=loaded['value']
if isinstance(loaded,dict): loaded=[loaded]
active = next(m for m in loaded if m['identifier']=='slm-production-evaluation')
assert active['contextLength']==8192 and active['parallel']==1
assert active['path']=='unsloth/gemma-4-12B-it-qat-GGUF/gemma-4-12B-it-qat-UD-Q4_K_XL.gguf'
prior = read(ROOT/'implementation_documents/v10_single_pass_evidence/scores.json')
v9_path = ROOT/'implementation_documents/v10_single_pass_evidence/historical-v9-scores.json'
v9 = read(v9_path)
assert git('rev-parse','HEAD') == 'a9d3760e541ae8a60b572b372d47f3e90b2e8894'
assert git('diff','--','src','tests/fixtures','tests/browser') == ''
assert prior['historical_accepted']==35 and prior['development_accepted']==8
assert v9['accepted']==37
assert len(scores['cases'])==len(checks['cases'])==56
assert len(checks['grading'])==5
old = {c['id']:c for c in prior['cases']}
old9 = {c['id']:c for c in v9['cases']}
assert set(old)=={c['id'] for c in scores['cases']}
shutil.copyfile(v9_path,OUT/'historical-v9-scores.json')
shutil.copyfile(ROOT/'implementation_documents/v10_single_pass_evidence/scores.json',OUT/'historical-v10-scores.json')
violations=[]
for c in checks['cases']:
    for key in ['all_ready','replay_same_saved_ids','replay_same_item_identity','persisted_ids_match','no_duplicate_ids_or_positions','publication_409','lesson_roles_separate','lesson_task_fields_literal']:
        if not c[key]: violations.append([c['id'], key])
    for saved in c['saved_items']:
        for key in ['expected_version','draft_unverified','fragment_hash_matches','document_hash_matches','literal_ranges_match','character_counts_match','budget_at_most_6000','fragment_in_request']:
            if not saved[key]: violations.append([c['id'],key])
    p=c['parameters']
    if p['model']!='slm-production-evaluation' or p['temperature']!=0 or p['reasoning_effort']!='none' or p['max_tokens'] not in [2000,4000]:
        violations.append([c['id'],'parameters'])
for grade in checks['grading']:
    for key in ['provisional','repeat_same_attempt']:
        if not grade[key]: violations.append([grade['id'],key])
    if grade['initial_inferences']!=1 or grade['repeat_inferences']!=0 or grade['error']:
        violations.append([grade['id'],'grading_accounting'])
records=[]
boundaries=[]
for label,count in [('historical-objective',36),('historical-source-review',8),('development',12)]:
    records_here=[json.loads(line) for line in (OUT/(label+'-inference.jsonl')).read_text(encoding='utf-8').splitlines()]
    records.extend(records_here)
    boundaries.append([records_here[0]['response']['created'],records_here[count-1]['response']['created']])
    if len(records_here)!=count+len([g for g in checks['grading'] if any(c['id']==g['id'] and c['battery']==label for c in checks['cases'])]):
        violations.append([label,'one_generation_per_case'])
assert boundaries[0][1]<=boundaries[1][0] and boundaries[1][1]<=boundaries[2][0]
assert checks['totals']['all_inferences']==61
tokens={k:sum(r['response'].get('usage',{}).get(k,0) for r in records) for k in ['prompt_tokens','completion_tokens','total_tokens']}
reasoning=sum(r['response'].get('usage',{}).get('completion_tokens_details',{}).get('reasoning_tokens',0) for r in records)
assert reasoning==0
cleanup=read(OUT/'cleanup.json')
assert cleanup['evaluation_servers_listening']==0 and not cleanup['native_stream_process_exists']
after=cleanup['loaded_model_after']
if isinstance(after,dict) and 'value' in after: after=after['value']
if isinstance(after,dict): after=[after]
retained=next(m for m in after if m['identifier']=='slm-production-evaluation')
assert retained['path']==active['path'] and retained['contextLength']==8192 and retained['parallel']==1 and retained['status']=='idle'
assert len({r['response']['id'] for r in records})==61
capture_start=read(OUT/'capture_start.json')
assert datetime.fromisoformat(capture_start['recorded_stream_start_utc'].replace('Z','+00:00')).timestamp() < boundaries[0][0]
grading_scores=read(OUT/'grading_visible_scores.json')
assert {c['id'] for c in grading_scores['cases']}=={c['id'] for c in checks['grading']}
native=[json.loads(line) for line in (OUT/'native_inputs.jsonl').read_text(encoding='utf-8').splitlines()]
coverage=[]
for index,r in enumerate(records):
    matches=[n for n in native if all(m['content'].strip() in n['data']['input'] for m in r['request']['messages'])]
    coverage.append({'transport_index':index,'response_id':r['response'].get('id'),'native_exact_matches':len(matches),'request_sha256':hashlib.sha256(json.dumps(r['request'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()})
(OUT/'native_coverage.json').write_text(json.dumps(coverage,indent=2),encoding='utf-8')
verification={'candidate_sha':git('rev-parse','HEAD'),'source_tree':git('rev-parse','HEAD^{tree}'),'application_tree':git('rev-parse','HEAD:src'),'application_prompts_fixtures_harness_unchanged':True,'historical_v9':'37/44','historical_v10':'35/44 + 8/12','historical_cases':44,'development_cases':12,'new_characterization_pairs_scored':0,'first_responses_preserved':56,'generation_inferences':56,'grading_inferences':5,'probe_inferences':0,'total_inferences':61,'reasoning_tokens':reasoning,'tokens':tokens,'generation_order_created_boundaries':boundaries,'native_events':len(native),'native_exact_generation_coverage':checks['totals']['native_inputs_with_exact_request_match'],'native_exact_all_inference_coverage':sum(c['native_exact_matches']>0 for c in coverage),'contract_violations':violations,'scoring':'Manual technical assessment of every visible field, including summary and questions; no LLM judge or human pedagogical acceptance.'}
(OUT/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
parts=['# Pasada final única: consistencia de afirmaciones de lecciones', '', f"Candidato `{verification['candidate_sha']}`; árbol `{verification['source_tree']}`. Aplicación, prompts, fixtures, oráculos y harness intactos. Worktree nuevo y tres estados sintéticos nuevos; evidencia anterior conservada.", '', f"Resultado v11: **{scores['historical_accepted']}/44 históricos** y, por separado, **{scores['development_accepted']}/12 desarrollo**. Históricos preservados: v9 **37/44**, v10 **35/44 + 8/12**. No se puntúan las nuevas parejas de caracterización.", '', 'Cinco dimensiones originales, 0/1/2; PASS exige cinco 2. A=accuracy, F=source_fidelity, U=usefulness, L=readability, I=missing_information. Juicio técnico manual del agente, sin juez LLM ni aprobación pedagógica humana. Se inspeccionan título, cuerpo, resumen, vocabulario, preguntas, source_review, respuestas y pistas. El caso dev-explanation mantiene el oráculo congelado que exige dos tazas aunque el objetivo pide pétalos; no se cambia ninguna nota histórica.', '', '## Identidad y configuración', '', 'Gemma SHA256 `90fd44e29e0d7cffeb0fd00dc73cfdab9ed0b0e95306ecf7821ea634c940c370`; LM Studio **0.4.25.0**; runtime CUDA **2.51.0**. Alias `slm-production-evaluation`, contexto 8192, paralelo 1, temperatura 0 y reasoning_effort=none. Límites existentes: lecciones/evaluaciones 4000, ejercicios 2000, correcciones abiertas 1000. No se descarga, recarga ni sustituye modelo. No se interrumpe Trading.', '', '## Contabilidad y contratos', '', f"56 generaciones (44 históricos, después 12 de desarrollo), cinco correcciones abiertas y cero probes: **61 inferencias**. Replays únicamente ready, sin inferencias adicionales. Tokens: {tokens}; reasoning_tokens=0. Primeras respuestas completas y contabilidad HTTP se conservan. Cobertura nativa exacta: **{verification['native_exact_generation_coverage']}/56 generaciones**, **{verification['native_exact_all_inference_coverage']}/61 inferencias**. No se repiten casos para rellenar trazas.", '', f"Incumplimientos técnicos detectados: {json.dumps(violations,ensure_ascii=False)}. Verificación individual en checks.json: recibos literales/rangos y hashes, lecciones v11, ejercicios/evaluaciones v10, draft/unverified, publicación sin revisión 409, identidades y posiciones sin duplicados, cinco notas abiertas provisionales y replay sin nueva corrección.", '', 'La captura se inició antes del primer caso. Solo se guardan entradas nativas con fuente sintética congelada exacta o pregunta abierta generada en este estado; los demás eventos se descartan en memoria. La evidencia nativa demuestra texto renderizado, no interpretación de tokens especiales. No se investiga tokenización ni otra arquitectura.', '']
for title,development in [('Comparación histórica por caso',False),('Desarrollo por caso (separado)',True)]:
    parts += ['## '+title,'','| Caso | v9 | v10 | v11 A/F/U/L/I | v11 | Evaluación de todos los campos |','|---|---|---|---|---|---|']
    for c in scores['cases']:
        if (c['battery']=='development')!=development: continue
        result='PASS' if c['accepted'] else 'FAIL'
        previous='/'.join(str(old[c['id']]['scores'][d]) for d in scores['dimensions'])+' '+('PASS' if old[c['id']]['accepted'] else 'FAIL')
        earlier=('/'.join(str(old9[c['id']]['scores'][d]) for d in scores['dimensions'])+' '+('PASS' if old9[c['id']]['accepted'] else 'FAIL')) if c['id'] in old9 else '—'
        values='/'.join(str(c['scores'][d]) for d in scores['dimensions'])
        parts.append(f"| {c['id']} | {earlier} | {previous} | {values} | {result} | {c['reason'].replace('|','/')} |")
    parts.append('')
parts += ['## Cinco correcciones abiertas: todos los campos visibles','', 'Estas son las cinco correcciones ya contabilizadas, sin casos ni inferencias nuevos. Sus notas de feedback se muestran aparte de las 56 salidas de generación y no alteran históricos. Las cinco sugerencias fueron 5/5, pero score sigue null y needs_review=true; no son notas finales.', '', '| Caso | A/F/U/L/I | Feedback, explicación, improvements, misconceptions y strengths |','|---|---|---|']
for grade in grading_scores['cases']:
    parts.append('| '+grade['id']+' | '+'/'.join(map(str,grade['scores']))+' | '+grade['reason']+' |')
parts += ['', '## Fallos conservados','']
parts += [f"- **{c['id']}**: {c['reason']}" for c in scores['cases'] if not c['accepted']]
parts += ['', '## Evidencias y parada', '', '[Verificación](v11_final_pass_evidence/verification.json), [contratos y contabilidad](v11_final_pass_evidence/checks.json), [notas](v11_final_pass_evidence/scores.json), [configuración e identidad](v11_final_pass_evidence/preflight.json), [cobertura nativa](v11_final_pass_evidence/native_coverage.json), [entradas nativas](v11_final_pass_evidence/native_inputs.jsonl), [manifiesto SHA256](v11_final_pass_evidence/manifest.json). Los archivos por batería conservan primeras respuestas, replays, auditoría persistida y cada solicitud/respuesta HTTP de inferencia. No se incluyen bases de datos, claves, credenciales ni configuración privada.', '', 'Esta pasada termina aquí, incluidos sus fallos. Sin reparaciones, nuevas evaluaciones, Actions, main, EXE, piloto, despliegue o datos reales. Los procesos de evaluación propios se detienen; Gemma permanece cargado; no se ha intervenido Trading. La entrega permite decidir cierre o una limitación concreta, sin iniciar otra ronda automática.','']
report=ROOT/'implementation_documents/lesson_claim_consistency_20261006_final_pass_report.md'
report.write_text('\n'.join(parts),encoding='utf-8')
for source in (ROOT/'temp/v11-tools').glob('*.py'):
    shutil.copyfile(source,OUT/source.name)
shutil.copyfile(ROOT/'tests/browser/evaluate_local_provider.py', OUT/'executed_harness.py')
def inspect(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if k.lower() in {'password','access_token','authorization','jwt_secret','slm_encryption_key','recovery_key','api_key','credentials'}:
                assert v in (None,''),k
            inspect(v)
    elif isinstance(value,list):
        for v in value: inspect(v)
for p in OUT.iterdir():
    assert p.suffix not in {'.db','.key','.log'} and p.name!='fixture.json'
    if p.suffix=='.json': inspect(read(p))
    if p.suffix=='.jsonl':
        for line in p.read_text(encoding='utf-8').splitlines(): inspect(json.loads(line))
manifest={'source_commit':verification['candidate_sha'],'written_at_utc':datetime.now(timezone.utc).isoformat(),'files':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted([p for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json']+[report])]}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(verification,ensure_ascii=False,indent=2))
