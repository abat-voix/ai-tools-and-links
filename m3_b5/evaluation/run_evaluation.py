"""Offline release gate for saved synthetic support runs."""

import argparse
import hashlib
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    """Load records and reject duplicate IDs."""
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    ids = [record["id"] for record in records]
    if not records or len(ids) != len(set(ids)):
        raise ValueError("Нужен непустой набор с уникальными id")
    return records


def evaluate(dataset: list[dict], saved_run: list[dict], minimum_pass_rate: float) -> dict:
    """Check access, actions and answer evidence before applying a score gate."""
    if not 0 <= minimum_pass_rate <= 1:
        raise ValueError("Порог должен находиться между 0 и 1")
    actual = {row["id"]: row for row in saved_run}
    if len(actual) != len(saved_run) or set(actual) != {row["id"] for row in dataset}:
        raise ValueError("Каждому id набора нужна ровно одна запись прогона")
    versions = {row["prompt_version"] for row in saved_run}
    if len(versions) != 1:
        raise ValueError("В одном прогоне должна быть одна версия промпта")
    results = []
    for case in dataset:
        row = actual[case["id"]]
        access_ok = row["access"] == case["expected_access"]
        action_ok = row["action"] == case["expected_action"]
        if "assertion" in case:
            assertion = case["assertion"]
            text = row["answer"].casefold()
            answer_ok = (all(term.casefold() in text for term in assertion["contains"])
                         and not any(term.casefold() in text for term in assertion["forbids"]))
            verdict = "pass" if answer_ok else "fail"
            evidence = "Проверка обязательных и запрещённых фрагментов"
        else:
            judge = row.get("judge", {})
            verdict = judge.get("verdict", "error")
            if verdict not in {"pass", "fail", "review", "error"}:
                raise ValueError("Неизвестный вердикт судьи")
            evidence = judge.get("evidence", "")
            if not all(judge.get(key) for key in ("model", "rubric_version", "evidence")):
                verdict = "error"
        passed = access_ok and action_ok and verdict == "pass"
        results.append({"id": case["id"], "category": case["category"],
                        "passed": passed, "access_ok": access_ok, "action_ok": action_ok,
                        "verdict": verdict, "evidence": evidence,
                        "critical_failure": case["critical"] and not passed})
    rate = sum(row["passed"] for row in results) / len(results)
    reasons = []
    if any(not row["access_ok"] for row in results):
        reasons.append("access_violation")
    if any(row["critical_failure"] for row in results):
        reasons.append("critical_failure")
    if any(row["verdict"] in {"review", "error"} for row in results):
        reasons.append("unresolved_evaluation")
    if rate < minimum_pass_rate:
        reasons.append("pass_rate_below_threshold")
    return {"dataset_version": "support-gate-v1", "prompt_version": versions.pop(),
            "fixture_kind": "synthetic", "passed": sum(row["passed"] for row in results),
            "total": len(results), "pass_rate": rate, "minimum_pass_rate": minimum_pass_rate,
            "release": "blocked" if reasons else "allowed", "reasons": reasons, "results": results}


def main() -> None:
    """Evaluate a saved run and exit nonzero when the release is blocked."""
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=base / "dataset.jsonl")
    parser.add_argument("--run", type=Path, default=base / "runs/synthetic-good.jsonl")
    parser.add_argument("--minimum-pass-rate", type=float, default=0.8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(read_jsonl(args.dataset), read_jsonl(args.run), args.minimum_pass_rate)
    report["dataset_sha256"] = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as target:
            target.write(rendered)
    print(rendered, end="")
    raise SystemExit(0 if report["release"] == "allowed" else 1)


if __name__ == "__main__":
    main()
