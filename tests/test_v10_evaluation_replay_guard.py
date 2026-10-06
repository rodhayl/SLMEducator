"""Replay safety checks for the one-pass evaluation harness only."""
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest


@pytest.mark.parametrize('items,replay', [([], False), ([{'status': 'failed'}], False),
    ([{'status': 'ready'}, {'status': 'failed'}], False), ([{'status': 'running'}], False),
    ([{'status': 'ready'}], True)])
def test_replay_requires_every_item_ready(tmp_path, items, replay):
    path = Path(__file__).parent / 'browser/evaluate_local_provider.py'
    spec = importlib.util.spec_from_file_location('evaluation_guard', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / 'fixture.json').write_text(json.dumps({'credentials': [{'username': 'teacher_a', 'password': 'synthetic-only'}]}))
    cases = tmp_path / 'cases.json'
    cases.write_text(json.dumps({'cases': [{'id': 'synthetic-guard', 'split': 'development', 'source': 'synthetic', 'topic': 'synthetic', 'level': 'adult', 'objective': 'synthetic', 'kind': 'lesson'}]}))
    generated = []
    class Response:
        status_code = 200
        def __init__(self, data):
            self.data = data
        def json(self):
            return self.data
        def raise_for_status(self):
            pass
    class Client:
        headers = {}
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get(self, url):
            return Response({})
        def post(self, url, **kwargs):
            if url.endswith('/login'):
                return Response({'access_token': 'synthetic'})
            if url == '/api/study-plans/':
                return Response({'id': 1})
            if url == '/api/generate/full-topic-package':
                generated.append(url)
                if len(generated) > 1:
                    # First response must already be durable before replay.
                    saved = json.loads((tmp_path / 'development-results.json').read_text())
                    assert saved['cases'][0]['result']['items'] == items
                    raise RuntimeError('synthetic replay interruption')
                return Response({'items': items})
            return Response({})
    args = ['evaluate', '--state-dir', str(tmp_path), '--split', 'development', '--cases-file', str(cases)]
    with patch.object(sys, 'argv', args), patch.object(module.httpx, 'Client', Client):
        if replay:
            with pytest.raises(RuntimeError, match='synthetic replay interruption'):
                module.main()
        else:
            module.main()
    assert len(generated) == (2 if replay else 1)
    saved = json.loads((tmp_path / 'development-results.json').read_text())
    assert saved['cases'][0]['result']['items'] == items
