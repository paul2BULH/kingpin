from __future__ import annotations
import re
from typing import Dict, Any, List, Tuple
from .keywords_section0 import ROOT_OPERATION_HINTS, BODY_SYSTEM_HINTS, APPROACH_HINTS, DEVICE_HINTS

def _norm(text: str) -> str:
    return (text or "").lower()

def _score_hits(text: str, keywords: List[str]) -> int:
    return sum(1 for k in keywords if re.search(r"\b" + re.escape(k) + r"\b", text))

def extract_section0_facts(raw_text: str) -> Dict[str, Any]:
    t = _norm(raw_text)
    facts: Dict[str, Any] = {
        "root_operation_candidates": [],
        "body_system_candidates": [],
        "approach_candidates": [],
        "device_hints": [],
        "raw_text_flags": []
    }

    # Root operations
    ro_scores = []
    for name, kws in ROOT_OPERATION_HINTS.items():
        score = _score_hits(t, kws)
        if score:
            ro_scores.append((name, score))
    ro_scores.sort(key=lambda x: x[1], reverse=True)
    facts["root_operation_candidates"] = ro_scores[:5]

    # Body system
    bs_scores = []
    for name, kws in BODY_SYSTEM_HINTS.items():
        score = _score_hits(t, kws)
        if score:
            bs_scores.append((name, score))
    bs_scores.sort(key=lambda x: x[1], reverse=True)
    facts["body_system_candidates"] = bs_scores[:5]

    # Approach
    ap_scores = []
    for name, kws in APPROACH_HINTS.items():
        score = _score_hits(t, kws)
        if score:
            ap_scores.append((name, score))
    ap_scores.sort(key=lambda x: x[1], reverse=True)
    facts["approach_candidates"] = ap_scores[:5]

    # Device
    device_hits = []
    for name, kws in DEVICE_HINTS:
        score = _score_hits(t, kws)
        if score:
            device_hits.append((name, score))
    device_hits.sort(key=lambda x: x[1], reverse=True)
    facts["device_hints"] = device_hits[:5]

    # Simple flags
    for flag in ["biopsy", "excisional", "laparoscopic", "open", "percutaneous", "thoracoscopic", "endoscopic"]:
        if re.search(r"\b" + flag + r"\b", t):
            facts["raw_text_flags"].append(flag)


    # Additional domain flags from recent notes
    if re.search(r"\bunicondyl|\bunicomp|\buka\b", t):
        facts.setdefault("qualifier_hints", []).append("Unicondylar")
        facts["raw_text_flags"].append("unicondylar")
    if re.search(r"\bcement(ed)?\b|\bpmma\b", t):
        facts.setdefault("device_hints", []).append(("Synthetic Substitute, Cemented", 1))
        facts["raw_text_flags"].append("cemented")
    if re.search(r"hemovac|\bjp drain\b|drain left in place", t):
        facts.setdefault("device_hints", []).append(("Drainage Device", 1))
        facts["raw_text_flags"].append("drain_placed")
    if re.search(r"down to fascia|into fascia", t):
        facts.setdefault("body_system_candidates", []).insert(0, ("Subcutaneous Tissue and Fascia", 5))

    return facts
