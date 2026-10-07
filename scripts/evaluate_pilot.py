"""Summarize explicitly recorded pilot observations; never run providers or invent results."""

import argparse
import json
import math
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
CRITICAL = ("lost_work", "false_save", "unauthorized_exposure", "invalid_final_grade")


def summarize(record: dict) -> dict:
    """Compute bounded counts and a conservative evidence gate, not efficacy."""
    cases = json.loads((ROOT / "docs/pilot/evaluation_cases.json").read_text())["cases"]
    required = {case["id"] for case in cases}
    ratings = record.get("case_ratings", [])
    ids = [row["case_id"] for row in ratings]
    if len(ids) != len(set(ids)) or any(value not in required for value in ids):
        raise ValueError("Each known evaluation case may be rated once")
    if any(type(row.get("acceptable")) is not bool for row in ratings):
        raise ValueError("Every recorded rating needs an explicit acceptable boolean")
    tasks = record.get("tasks", [])
    if any(type(row.get("completed_without_rescue")) is not bool for row in tasks):
        raise ValueError("Every task needs an explicit completion result")
    incidents = record.get("incidents", {})
    if any(type(value) is not int or value < 0 for value in incidents.values()):
        raise ValueError("Incident counts must be nonnegative integers")
    durations = [
        row[field]
        for row in tasks
        for field in ("authoring_minutes", "correction_minutes", "baseline_minutes")
        if field in row
    ]
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        for value in durations
    ):
        raise ValueError("Measured durations must be nonnegative numbers")
    measured = [
        row["authoring_minutes"] + row.get("correction_minutes", 0)
        for row in tasks
        if "authoring_minutes" in row
    ]
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        for value in measured
    ):
        raise ValueError("Measured durations must be nonnegative numbers")
    acceptable = sum(row["acceptable"] for row in ratings)
    critical = sum(incidents.get(key, 0) for key in CRITICAL)
    complete = set(ids) == required
    reviewed = record.get("teacher_reviewed") is True
    live = record.get("evidence_mode") == "observed_human_pilot"
    if critical:
        decision = "stop_and_repair"
    elif (
        not complete
        or not reviewed
        or not live
        or not tasks
        or not all(key in incidents for key in CRITICAL)
    ):
        decision = "awaiting_human_evidence"
    elif acceptable / len(ratings) < 0.9:
        decision = "adjust_and_repeat"
    else:
        decision = "eligible_for_teacher_decision"
    return {
        "decision": decision,
        "rated_cases": len(ratings),
        "required_cases": len(required),
        "acceptable_cases": acceptable,
        "acceptable_fraction": acceptable / len(ratings) if ratings else None,
        "tasks_observed": len(tasks),
        "tasks_without_rescue": sum(row["completed_without_rescue"] for row in tasks),
        "critical_incidents": critical,
        "median_authoring_including_correction_minutes": (
            median(measured) if measured else None
        ),
        "evidence_mode": record.get("evidence_mode", "not_recorded"),
        "limitation": "This small task evaluation does not establish educational efficacy, child suitability, accessibility conformance, or legal acceptance.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observations", type=Path)
    args = parser.parse_args()
    try:
        print(
            json.dumps(summarize(json.loads(args.observations.read_text())), indent=2)
        )
        return 0
    except (ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
