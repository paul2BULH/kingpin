from __future__ import annotations
from typing import Any, Dict, List, Tuple
import json, os, re

def load_rules(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def detect_flags(raw_text: str) -> Dict[str, bool]:
    t = (raw_text or "").lower()
    def has(*words):
        return any(re.search(r"" + re.escape(w.lower()) + r"", t) for w in words)
    return {
        "biopsy": has("biopsy"),
        "aborted": has("aborted", "abandon", "terminated"),
        "discontinued": has("discontinued", "aborted"),
        "converted_to_open": has("converted to open", "conversion to open"),
        "drain_placed": has("drain placed", "jp drain", "drain left in place", "chest tube", "hemovac"),
        "no_device_left": has("removed at end", "no device left"),
        "hemostasis": has("hemostasis", "control of bleeding", "control hemorrhage"),
        "bilateral": has("bilateral", "both sides"),
        "embolization": has("embolization", "occlude", "narrow"),
        "unicondylar": has("unicondylar", "unicompartmental", "uka"),
        "cemented": has("cement", "cemented", "pmma"),
        "down_to_fascia": has("down to fascia", "into fascia")
    }


def apply_rules(raw_text: str, facts: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
    flags = detect_flags(raw_text)
    # Start with pass-through
    result: Dict[str, Any] = {
        "updates": {},
        "queries": [],
        "notes": [],
    }
    # Procedure patterns
    patterns_path = os.path.join("assets", "procedure_patterns.json")
    ptns = _load_patterns(patterns_path)
    p_updates = _apply_procedure_patterns(raw_text, ptns)
    for k,v in p_updates.items():
        if k == "notes":
            continue
        if isinstance(v, list):
            if k in result["updates"] and isinstance(result["updates"].get(k), list):
                result["updates"][k] += v
            else:
                result["updates"][k] = v
        else:
            result["updates"][k] = v
    if p_updates.get("outside_section_matches"):
        result["notes"].append("Outside Section 0 detected: " + "; ".join(p_updates["outside_section_matches"]))
    # PCS B6.1b – routine post-op wound drains are integral to the primary procedure
    t = (raw_text or "").lower()
    try:
        distinct = _distinct_drainage_procedure(t)
    except Exception:
        distinct = False
    if flags.get("drain_placed") and not distinct:
        result["updates"]["integral_wound_drain"] = True
        result["notes"].append("Routine wound/JP/Hemovac drain considered integral to the main procedure (PCS B6.1b) – suppress separate Insertion/Device code.")

    # Example rule: B3.4 Biopsy -> Diagnostic qualifier
    if flags.get("biopsy"):
        result["updates"].setdefault("qualifier_hints", []).append("Diagnostic")
        result["notes"].append("Biopsy detected -> consider 'Diagnostic' qualifier (B3.4).")

    # Example rule: B6.1 Device remains -> Only code device if left in place
    if flags.get("no_device_left"):
        result["updates"]["device_override"] = "No Device"
        result["notes"].append("Device removed at end -> code 'No Device' (B6.1).")
    elif flags.get("drain_placed"):
        result["updates"]["device_override"] = "Drainage Device"
        result["notes"].append("Drain left in place -> code Drainage Device when applicable (B6.2).")

    # Knee UKA keywords -> Unicondylar qualifier
    if flags.get("unicondylar"):
        result["updates"].setdefault("qualifier_hints", []).append("Unicondylar")
        result["notes"].append("Unicondylar arthroplasty -> consider 'Unicondylar' qualifier.")
    # Cemented prosthesis hints -> prefer cemented device value
    if flags.get("cemented"):
        result["updates"]["device_override"] = "Synthetic Substitute, Cemented"
        result["notes"].append("Cemented prosthesis -> device value 'Synthetic Substitute, Cemented'.")
    # Debridement down to fascia -> bias body system to Subcutaneous Tissue and Fascia and approach Open
    if flags.get("down_to_fascia"):
        result["updates"].setdefault("body_system_bias", []).append("Subcutaneous Tissue and Fascia")
        result["updates"]["approach_override"] = "Open"
        result["notes"].append("Debridement to fascia -> body system 'Subcutaneous Tissue and Fascia', approach 'Open'.")
    # Example rule: B5.2 Approach hierarchy
    if flags.get("converted_to_open"):
        result["updates"]["approach_override"] = "Open"
        result["notes"].append("Converted to open -> approach is Open (B5.2).")

    # Insufficient documentation -> emit query (A8)
    missing_items = []
    for k in ["objective", "body_parts", "approaches"]:
        if not facts.get(k):
            missing_items.append(k)
    if missing_items:
        result["queries"].append({
            "reason": "Documentation insufficient for required characters (A8)",
            "ask": [f"Clarify {', '.join(missing_items)} with precise terms."]
        })

    return result

def build_code_skeleton(section_char: str = "0",
                        body_system_char: str = "?",
                        root_operation_char: str = "?",
                        body_part_char: str = "?",
                        approach_char: str = "?",
                        device_char: str = "?",
                        qualifier_char: str = "?") -> str:
    return f"{section_char}{body_system_char}{root_operation_char}{body_part_char}{approach_char}{device_char}{qualifier_char}"


import json, os, re

def _load_patterns(path: str):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"procedures": []}

def _apply_procedure_patterns(raw_text: str, patterns: dict) -> dict:
    t = (raw_text or "").lower()
    updates = {"notes": []}
    matches = []
    for p in (patterns.get("procedures") or []):
        for rx in p.get("triggers", []):
            try:
                if re.search(rx, t):
                    matches.append(p)
                    break
            except re.error:
                continue
    if not matches:
        return updates

    # Merge matched hints
    for p in matches:
        if p.get("root_operation_hint"):
            updates.setdefault("root_operation_hint", set()).add(p["root_operation_hint"])
        # Handle qualifiers
        for q in p.get("qualifier_hints", []) or []:
            if isinstance(q, dict):
                if re.search(q.get("if", "."), t):
                    updates.setdefault("qualifier_hints", set()).add(q.get("qualifier"))
            else:
                updates.setdefault("qualifier_hints", set()).add(q)
        # Body system/approach
        for bh in p.get("body_system_hints", []) or []:
            cond = bh.get("if", ".")
            if re.search(cond, t):
                updates.setdefault("body_system_bias", set()).update( (bh.get("body_system") or "").split("|") )
                if bh.get("approach"):
                    updates["approach_override"] = bh["approach"]
        # Devices
        for dh in p.get("device_hints", []) or []:
            if re.search(dh.get("if", "."), t):
                updates["device_override"] = dh.get("device")
        # Multi-code recipe
        if p.get("multi_code_recipe"):
            updates.setdefault("multi_code_recipe", set()).update(p["multi_code_recipe"])
        # Outside section marker
        if p.get("section") and p["section"] != "0":
            updates.setdefault("outside_section_matches", set()).add(f"{p['name']} -> Section {p['section']}")
    # Normalize sets to lists
    for k,v in list(updates.items()):
        if isinstance(v, set):
            updates[k] = sorted([x for x in v if x])

    return updates


def _distinct_drainage_procedure(t: str) -> bool:
    '''
    Return True when the note documents a separate drainage procedure
    (e.g., tube thoracostomy, IR abscess catheter, nephrostomy), not a routine wound drain.
    '''
    t = (t or "").lower()
    triggers = [
        r"\bir\b", r"interventional radiology", r"ct[-\s]?guided", r"ultrasound[-\s]?guided",
        r"tube thoracostomy", r"\bthoracostomy\b", r"pigtail", r"nephrostomy",
        r"cholecystostomy", r"percutaneous drain", r"image[-\s]?guided drain", r"guided catheter",
        r"paracentesis", r"thoracentesis"
    ]
    return any(re.search(rx, t) for rx in triggers)

