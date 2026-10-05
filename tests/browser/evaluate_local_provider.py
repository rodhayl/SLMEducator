"""Execute the frozen synthetic rubric once through actual application HTTP.

Start local_provider_server.py first. Only its new synthetic fixture is read.
No response or provider is mocked, and semantic scores are recorded separately.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import time

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8097")
    parser.add_argument("--split", choices=["development", "reserved"], required=True)
    parser.add_argument("--max-tokens", type=int, default=2000)
    parser.add_argument("--cases-file", type=Path)
    parser.add_argument("--reasoning-effort", choices=["none"])
    args = parser.parse_args()
    fixture = json.loads((args.state_dir / "fixture.json").read_text(encoding="utf-8"))
    cases_file = args.cases_file or Path(__file__).resolve().parents[1] / "fixtures/local_semantic_cases.json"
    cases = json.loads(cases_file.read_text(encoding="utf-8"))
    destination = args.state_dir / (args.split + "-results.json")
    if destination.exists():
        raise SystemExit("Results already exist; preserve them instead of cherry-picking another run")
    results = {"rubric_sha256": sha256(cases_file.read_bytes()).hexdigest(), "cases": []}
    with httpx.Client(base_url=args.base_url, trust_env=False, timeout=310) as client:
        teacher = next(row for row in fixture["credentials"] if row["username"] == "teacher_a")
        def authenticate():
            auth = client.post("/api/auth/login", data={"username": teacher["username"], "password": teacher["password"]})
            auth.raise_for_status()
            client.headers["Authorization"] = "Bearer " + auth.json()["access_token"]

        authenticate()
        config = {"provider": "lm_studio", "model": "slm-production-evaluation",
                  "endpoint": "http://127.0.0.1:1234", "temperature": 0, "max_tokens": args.max_tokens}
        if args.reasoning_effort:
            config["reasoning_effort"] = args.reasoning_effort
        client.post("/api/settings/ai", json=config).raise_for_status()
        results["configuration"] = client.get("/api/settings/ai").json()
        for case in cases["cases"]:
            if case["split"] != args.split:
                continue
            authenticate()
            course = client.post("/api/study-plans/", json={"title": case["id"], "phases": [{"name": "Review", "content_ids": []}]})
            course.raise_for_status()
            plan_id = course.json()["id"]
            source = case["source"] + ("\n[appendix]\nUnrelated synthetic inventory entry. " * case.get("padding_repeat", 0))
            payload = {"subject": case["topic"], "topic_name": case["topic"], "grade_level": case["level"],
                       "learning_objectives": [case["objective"]], "source_material": source,
                       "include_lesson": case["kind"] == "lesson", "include_exercises": case["kind"] == "exercise",
                       "num_exercises": 1, "include_assessment": case["kind"] == "open", "num_assessment_questions": 1,
                       "study_plan_id": plan_id, "auto_save": True, "phase_index": 0}
            if case["kind"] == "open":
                payload["assessment_question_types"] = ["short_answer"]
            start = time.monotonic()
            response = client.post("/api/generate/full-topic-package", json=payload)
            record = {"id": case["id"], "plan_id": plan_id, "seconds": time.monotonic() - start,
                      "http_status": response.status_code, "result": response.json()}
            # A repetition must reuse saved IDs and only retry failed items.
            if response.status_code == 200:
                authenticate()
                repeat = client.post("/api/generate/full-topic-package", json=payload)
                record["repeat"] = {"http_status": repeat.status_code, "result": repeat.json()}
                authenticate()
                denied = client.post(f"/api/study-plans/{plan_id}/workflow", json={"action": "publish"})
                record["unreviewed_publication_status"] = denied.status_code
            results["cases"].append(record)
            destination.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(case["id"], response.status_code, round(record["seconds"], 2), flush=True)


if __name__ == "__main__":
    main()
