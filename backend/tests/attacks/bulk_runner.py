"""Bulk attack runner utilities for evaluating all security modes."""

from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from .corpus import AttackCase, iter_attack_cases


VALID_DECISIONS = {"ALLOW", "SANITIZE", "BLOCK"}


@dataclass(frozen=True)
class AttackOutcome:
    """Single mode/case outcome."""

    mode: str
    case_id: str
    category: str
    decision: str
    risk_level: str
    reason: str


def run_attack_matrix(client, modes: Iterable[str], user_prefix: str = "attack_tester") -> Tuple[List[AttackOutcome], Dict[str, Dict[str, int]]]:
    """Execute all corpus cases against each security mode.

    Uses /admin/mode for global mode setting and /chat/ for contract-compliant requests.
    """

    outcomes: List[AttackOutcome] = []

    for mode in modes:
        mode_resp = client.post("/admin/mode", json={"mode": mode})
        assert mode_resp.status_code == 200, f"Failed to set mode={mode}: {mode_resp.text}"

        for case in iter_attack_cases():
            payload = case.to_chat_payload(user_id=f"{user_prefix}_{mode.lower()}")
            response = client.post("/chat/", json=payload)
            assert response.status_code == 200, f"Case {case.case_id} failed: {response.text}"

            body = response.json()
            decision = body["decision"]
            assert decision in VALID_DECISIONS, f"Invalid decision for {case.case_id}: {decision}"

            outcomes.append(
                AttackOutcome(
                    mode=mode,
                    case_id=case.case_id,
                    category=case.category,
                    decision=decision,
                    risk_level=body["risk_level"],
                    reason=body["reason"],
                )
            )

    summary = summarize_outcomes(outcomes)
    return outcomes, summary


def summarize_outcomes(outcomes: Iterable[AttackOutcome]) -> Dict[str, Dict[str, int]]:
    """Return per-mode and global decision counts."""

    per_mode: Dict[str, Counter] = {}
    global_counts: Counter = Counter()

    for outcome in outcomes:
        per_mode.setdefault(outcome.mode, Counter())
        per_mode[outcome.mode][outcome.decision] += 1
        global_counts[outcome.decision] += 1

    summary: Dict[str, Dict[str, int]] = {
        mode: {decision: counts.get(decision, 0) for decision in sorted(VALID_DECISIONS)}
        for mode, counts in per_mode.items()
    }
    summary["ALL"] = {decision: global_counts.get(decision, 0) for decision in sorted(VALID_DECISIONS)}
    return summary
