"""Bulk corpus tests across all security modes."""

import os
import sys

from fastapi.testclient import TestClient

# Add repository root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.app.main import app
from backend.tests.attacks.bulk_runner import run_attack_matrix
from backend.tests.attacks.corpus import iter_attack_cases


def test_attack_corpus_bulk_runner(chat_headers):
    """Run attack corpus in every mode and emit per-case + summary outcomes."""

    client = TestClient(app)
    modes = ["Off", "Weak", "Normal", "Strong"]

    outcomes, summary = run_attack_matrix(client=client, modes=modes, chat_headers=chat_headers)

    expected_count = len(modes) * len(iter_attack_cases())
    assert len(outcomes) == expected_count

    # Strong mode should never be more permissive than Off mode for this attack corpus.
    off_allow = summary["Off"]["ALLOW"]
    strong_allow = summary["Strong"]["ALLOW"]
    assert strong_allow <= off_allow

    # Emit per-case outcomes (for test logs) and summary stats.
    for outcome in outcomes:
        print(
            f"[ATTACK] mode={outcome.mode:<6} case={outcome.case_id:<28} "
            f"category={outcome.category:<32} decision={outcome.decision:<8} risk={outcome.risk_level}"
        )

    print("[SUMMARY] decision_counts_per_mode")
    for mode in modes + ["ALL"]:
        counts = summary[mode]
        print(
            f"[SUMMARY] mode={mode:<6} "
            f"ALLOW={counts['ALLOW']:<2} SANITIZE={counts['SANITIZE']:<2} BLOCK={counts['BLOCK']:<2}"
        )
