"""Content-based triage heuristics for the Micro-Empathy AI prototype.

This module is decision support, not a clinical or emergency-detection system.
Officers must verify critical reports and use established dispatch procedures.
"""

from __future__ import annotations

from typing import Any


EMERGENCY_TERMS = (
    "life-threatening", "not breathing", "unconscious", "heart attack",
    "severe bleeding", "trapped", "collapsed", "electrocuted", "gas leak",
    " உயிருக்கு ஆபத்து", "மூச்சு விடவில்லை",
)
MEDICAL_TERMS = (
    "patient", "medical", "oxygen", "ventilator", "dialysis", "life support",
    "medical equipment", "bedridden", "மருத்துவ", "நோயாளி",
)
DEPENDENCY_TERMS = (
    "depend", "dependent", "relies on", "life support", "ventilator",
    "oxygen cylinder", "medical equipment", "machine",
)
FIRE_TERMS = ("fire", "smoke", "burning", "தீ", "புகை")
ACCIDENT_TERMS = ("accident", "crash", "collision", "road-la accident", "விபத்து")
DANGER_TERMS = (
    "danger", "dangerous", "exposed wire", "live wire", "electrocution",
    "gas leak", "trapped", "building collapse", "பாதுகாப்பற்ற",
)
VULNERABLE_TERMS = (
    "child", "children", "infant", "elderly", "senior citizen", "pregnant",
    "disabled", "wheelchair", "bedridden", "alone", "குழந்தை", "முதியவர்",
)
SERVICE_TERMS = (
    "power", "electricity", "current", "eb", "water", "road", "sewage",
    "drain", "gas", "மின்சாரம்", "தண்ணீர்",
)
DISRUPTION_TERMS = (
    "outage", "power cut", "current cut", "no power", "no electricity",
    "no water", "cut", "stopped", "not working", "poiduchu", "interrupted",
    "failure", "unavailable", "broken", "இல்லை",
)
URGENCY_TERMS = (
    "immediate", "immediately", "urgent", "urgently", "asap", "right now",
    "emergency", "help now", "விரைவாக", "உடனடியாக", "அவசரம்",
)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def analyze_complaint(complaint_text: str) -> dict[str, Any]:
    """Return a transparent priority estimate using the complaint's wording/context."""
    text = " ".join(complaint_text.casefold().split())
    medical = _contains_any(text, MEDICAL_TERMS)
    dependent_patient = medical and _contains_any(text, DEPENDENCY_TERMS)
    urgent_medical_power_need = (
        medical
        and _contains_any(text, URGENCY_TERMS)
        and _contains_any(text, ("power", "electricity", "current", "eb", "மின்சாரம்"))
    )
    service_disrupted = (
        _contains_any(text, SERVICE_TERMS)
        and (_contains_any(text, DISRUPTION_TERMS) or urgent_medical_power_need)
    )
    urgency = _contains_any(text, URGENCY_TERMS)
    fire = _contains_any(text, FIRE_TERMS)
    accident = _contains_any(text, ACCIDENT_TERMS)
    danger = _contains_any(text, DANGER_TERMS)
    life_threat = _contains_any(text, EMERGENCY_TERMS)
    vulnerable = _contains_any(text, VULNERABLE_TERMS)

    factors: list[dict[str, str]] = []
    score = 0

    def add_factor(key: str, label: str, points: int) -> None:
        nonlocal score
        factors.append({"key": key, "label": label})
        score += points

    if medical:
        add_factor("medical", "Medical situation", 25)
    if dependent_patient:
        add_factor("medical_dependency", "Dependence on medical equipment or support", 25)
    if service_disrupted:
        add_factor("service_disruption", "Essential service interruption", 10)
    if fire:
        add_factor("fire", "Fire or smoke reported", 45)
    if accident:
        add_factor("accident", "Road accident reported", 40)
    if danger:
        add_factor("danger", "Potential immediate danger", 45)
    if life_threat:
        add_factor("life_threat", "Possible life-threatening situation", 35)
    if vulnerable:
        add_factor("vulnerable_person", "Vulnerable person may be affected", 15)
    if urgency:
        add_factor("urgency", "Urgent assistance requested", 20)

    critical_medical_context = medical and service_disrupted and (urgency or dependent_patient)
    critical_danger_context = life_threat or (danger and (urgency or vulnerable))
    critical_incident_context = (fire or accident) and life_threat

    if critical_medical_context or critical_danger_context or critical_incident_context:
        priority = "CRITICAL"
        score = max(score, 90)
        explanation = (
            "The complaint combines signals that may involve immediate risk to life or "
            "essential medical support. This is an unverified assistive assessment."
        )
        action = "Verify immediately with the complainant and follow the appropriate emergency response protocol."
    elif fire or accident or danger or score >= 45:
        priority = "HIGH"
        score = max(score, 50)
        explanation = (
            "The complaint mentions a possible safety incident or multiple urgency signals "
            "that should be reviewed promptly."
        )
        action = "Review promptly and confirm the location, current risk, and assistance needed."
    elif score >= 20:
        priority = "MEDIUM"
        explanation = "Some urgency or impact signals are present; an officer should assess the details."
        action = "Review in the normal officer queue and contact the complainant if details are unclear."
    else:
        priority = "NORMAL"
        explanation = "No strong emergency signal was identified in the complaint text."
        action = "Add to the standard service queue and handle under local service timelines."

    return {
        "priority": priority,
        "score": min(score, 100),
        "detected_factors": factors,
        "explanation": explanation,
        "recommended_action": action,
    }
