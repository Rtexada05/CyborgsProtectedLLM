"""CLI script to run the full attack corpus against all security modes."""

import json
import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.app.main import app
from backend.tests.attacks.bulk_runner import run_attack_matrix


if __name__ == "__main__":
    client = TestClient(app)
    modes = ["Off", "Weak", "Normal", "Strong"]
    client_api_key = os.getenv("CLIENT_API_KEY")
    chat_headers = {"X-API-Key": client_api_key} if client_api_key else None

    outcomes, summary = run_attack_matrix(
        client=client,
        modes=modes,
        user_prefix="attack_script",
        chat_headers=chat_headers,
    )

    print("Per-case outcomes:")
    for outcome in outcomes:
        print(
            f"- mode={outcome.mode:<6} case={outcome.case_id:<28} "
            f"category={outcome.category:<32} decision={outcome.decision:<8} risk={outcome.risk_level}"
        )

    print("\nSummary stats:")
    print(json.dumps(summary, indent=2))
