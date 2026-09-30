"""
Tests for the deterministic lead scorer.

Run from the project root:
    pip install pytest
    pytest -q
"""

import os
import sys

# Make src/ importable without any install step.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from score_lead import score_lead  # noqa: E402


def test_hot_lead():
    lead = {
        "from_name": "Ali Raza",
        "from_email": "ali@example.com",
        "phone": "03001234567",
        "service_requested": "swimming_pools",
        "location": "Bahria Town, Rawalpindi",
        "budget_pkr": 1_800_000,
        "timeline_days": 20,        # 14 pts
        "decision_authority": "yes",
    }
    result = score_lead(lead)
    # 25 + 14 + 20 + 15 + 10 + 10 = 94
    assert result["score"] == 94
    assert result["qualification"] == "HOT"


def test_warm_lead():
    lead = {
        "from_name": "Sara",
        "from_email": "sara@example.com",
        "phone": None,
        "service_requested": "landscape_design",
        "location": "Wah Cantt",
        "budget_pkr": 120_000,       # 10
        "timeline_days": 60,         # 8
        "decision_authority": "unknown",  # 4
    }
    result = score_lead(lead)
    # 10 + 8 + 20 + 8(nearby) + 4 + completeness(name,email,budget,timeline=8) = 58
    assert result["score"] == 58
    assert result["qualification"] == "WARM"


def test_nurture_lead():
    lead = {
        "from_name": None,
        "from_email": "someone@example.com",
        "phone": None,
        "service_requested": "other",   # 5
        "location": "Lahore",           # far -> 3
        "budget_pkr": 20_000,           # 4
        "timeline_days": 200,           # 3
        "decision_authority": "no",     # 0
    }
    result = score_lead(lead)
    # 4 + 3 + 5 + 3 + 0 + completeness(email,budget,timeline=6) = 21
    assert result["score"] == 21
    assert result["qualification"] == "NURTURE"


def test_empty_lead_is_nurture():
    result = score_lead({})
    # Empty lead still gets 4 pts: missing authority defaults to "unknown" (4).
    assert result["score"] == 4
    assert result["qualification"] == "NURTURE"
    assert len(result["score_reasons"]) == 6
