"""Native current-snapshot check for the Khaos Brain model-system parent."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from model import CHILD_MODEL_ID, CHILD_MODEL_PATH, REQUIRED_QUESTION_IDS, observed_child_contract


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    child = root / CHILD_MODEL_PATH
    completed = subprocess.run(
        [sys.executable, str(child)],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    problems: list[str] = []
    payload: dict[str, object] = {}
    if completed.returncode != 0:
        problems.append(f"child exited with {completed.returncode}")
    try:
        loaded = json.loads(completed.stdout)
        if isinstance(loaded, dict):
            payload = loaded
        else:
            problems.append("child result is not an object")
    except json.JSONDecodeError as exc:
        problems.append(f"child result is not JSON: {exc}")
    if payload.get("model") != CHILD_MODEL_ID:
        problems.append("child model identity mismatch")
    questions = payload.get("question_results", {})
    if not isinstance(questions, dict):
        questions = {}
        problems.append("child question_results is not an object")
    for question_id in REQUIRED_QUESTION_IDS:
        if questions.get(question_id) is not True:
            problems.append(f"required question is not terminal true: {question_id}")
    result = {
        "model": observed_child_contract(),
        "child_exit_code": completed.returncode,
        "required_question_results": {
            question_id: questions.get(question_id) for question_id in REQUIRED_QUESTION_IDS
        },
        "problems": problems,
        "ok": not problems,
    }
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
