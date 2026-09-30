"""
Deterministic lead scoring for the Z&T AI Ops Agent.

The AI (LLM) only *enriches* a lead (summary, reply text). It does NOT decide the
score. The business decision — HOT / WARM / NURTURE — is made here by plain, fixed
rules so it is transparent, testable, and never changes based on a model's mood.

Usage (n8n Code node or Python):
    from score_lead import score_lead
    result = score_lead(lead_dict)
    # -> {"score": 82, "qualification": "HOT", "score_reasons": [...]}
"""

from typing import Optional

# The four services Z&T actually offers (must match the knowledge base).
CORE_SERVICES = {
    "waterproofing",
    "swimming_pools",
    "landscape_design",
    "building_works",
}

# Cities close enough to still be worth a site visit.
NEARBY = {"wah", "taxila", "murree", "attock", "gujar khan", "kahuta", "fateh jang"}


def _score_budget(budget: Optional[float]) -> int:
    if budget is None:
        return 0
    if budget >= 500_000:
        return 25
    if budget >= 200_000:
        return 18
    if budget >= 50_000:
        return 10
    return 4  # below our PKR 50k minimum, but still a real number


def _score_timeline(days: Optional[int]) -> int:
    if days is None:
        return 0
    if days <= 14:
        return 20
    if days <= 30:
        return 14
    if days <= 90:
        return 8
    return 3


def _score_service(service: Optional[str]) -> int:
    if not service:
        return 0
    if service in CORE_SERVICES:
        return 20
    if service == "other":
        return 5
    return 0


def _score_location(location: Optional[str]) -> int:
    if not location:
        return 0
    loc = location.strip().lower()
    if "islamabad" in loc or "rawalpindi" in loc or "pindi" in loc or "isb" in loc:
        return 15
    if any(city in loc for city in NEARBY):
        return 8
    return 3  # some location given, but far


def _score_authority(authority: Optional[str]) -> int:
    mapping = {"yes": 10, "unknown": 4, "no": 0}
    return mapping.get((authority or "unknown").strip().lower(), 4)


def _score_completeness(lead: dict) -> int:
    """+2 for each key detail the lead actually provided (max 10)."""
    points = 0
    for field in ("from_name", "from_email", "phone", "budget_pkr", "timeline_days"):
        value = lead.get(field)
        if value not in (None, "", []):
            points += 2
    return min(points, 10)


def score_lead(lead: dict) -> dict:
    """
    Score a normalized inquiry and classify it.

    Expected keys on `lead`:
        from_name, from_email, phone,
        service_requested, location,
        budget_pkr, timeline_days, decision_authority

    Returns dict: { "score": int, "qualification": str, "score_reasons": list[str] }
    """
    parts = {
        "budget": _score_budget(lead.get("budget_pkr")),
        "timeline": _score_timeline(lead.get("timeline_days")),
        "service_match": _score_service(lead.get("service_requested")),
        "location": _score_location(lead.get("location")),
        "authority": _score_authority(lead.get("decision_authority")),
        "completeness": _score_completeness(lead),
    }

    total = sum(parts.values())

    if total >= 70:
        qualification = "HOT"
    elif total >= 45:
        qualification = "WARM"
    else:
        qualification = "NURTURE"

    reasons = [f"{name}: {pts} pts" for name, pts in parts.items()]

    return {
        "score": total,
        "qualification": qualification,
        "score_reasons": reasons,
    }


if __name__ == "__main__":
    # Quick manual check
    demo = {
        "from_name": "Ali Raza",
        "from_email": "ali@example.com",
        "phone": "03001234567",
        "service_requested": "swimming_pools",
        "location": "Bahria Town, Rawalpindi",
        "budget_pkr": 1_800_000,
        "timeline_days": 20,
        "decision_authority": "yes",
    }
    print(score_lead(demo))
