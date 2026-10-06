"""Read-only native provider identity and template evidence; no inference."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / '.v9-evaluation-worktree' / '.evaluation-tools'))
import lmstudio

destination = ROOT / 'implementation_documents' / 'v10_single_pass_evidence'
destination.mkdir(exist_ok=True)
model = lmstudio.llm('slm-production-evaluation')
chat = lmstudio.Chat('APPLICATION_RULE_SYNTHETIC')
chat.add_user_message('SOURCE_DATA_SYNTHETIC')
rendered = model.apply_prompt_template(chat)
(destination / 'rendered_preflight.txt').write_text(rendered, encoding='utf-8')
config = model.get_load_config()
(destination / 'load_config.json').write_text(json.dumps(config, default=str, indent=2), encoding='utf-8')
template = Path(r'C:\Users\dhays\.lmstudio\.internal\temp\lmstudio-chat-template-ooiZCQ\chat-template.jinja')
(destination / 'active_template.jinja').write_bytes(template.read_bytes())
weights = Path(r'C:\Users\dhays\.lmstudio\models\unsloth\gemma-4-12B-it-qat-GGUF\gemma-4-12B-it-qat-UD-Q4_K_XL.gguf')
with weights.open('rb') as source:
    digest = hashlib.file_digest(source, 'sha256').hexdigest()
evidence = {'model_filename': weights.name, 'model_bytes': weights.stat().st_size,
            'model_sha256': digest, 'template_sha256': hashlib.sha256(template.read_bytes()).hexdigest(),
            'alias': model.identifier, 'inferences': 0,
            'system_separate': '<|turn>system\nAPPLICATION_RULE_SYNTHETIC<turn|>' in rendered,
            'user_separate': '<|turn>user\nSOURCE_DATA_SYNTHETIC<turn|>' in rendered}
(destination / 'preflight.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
print(json.dumps(evidence))
print(rendered)
