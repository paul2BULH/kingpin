from __future__ import annotations
from typing import Dict, Any, List, Optional

# This module assembles suggestions and exposes an integration point for
# mapping names → official characters via the PCS Tables.
# We keep **names** here to avoid wrong letter mappings before tables are loaded.

def summarize_candidates(facts: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "section": "0 (Medical & Surgical)",
        "root_operations": [ {"name": n, "score": s} for n, s in facts.get("root_operation_candidates", []) ],
        "body_systems": [ {"name": n, "score": s} for n, s in facts.get("body_system_candidates", []) ],
        "approaches": [ {"name": n, "score": s} for n, s in facts.get("approach_candidates", []) ],
        "devices": [ {"name": n, "score": s} for n, s in facts.get("device_hints", []) ],
        "flags": facts.get("raw_text_flags", [])
    }

def map_to_pcs_code(section_name: str,
                    body_system_name: Optional[str],
                    root_operation_name: Optional[str],
                    body_part_name: Optional[str],
                    approach_name: Optional[str],
                    device_name: Optional[str],
                    qualifier_name: Optional[str],
                    tables_context: Any = None) -> Dict[str, Any]:
    """Placeholder mapper. Returns a structured response explaining next steps.
    Replace with real table-driven mapping that yields the 7-character code.
    """
    result = {
        "section": section_name or "0 (Medical & Surgical)",
        "body_system": body_system_name,
        "root_operation": root_operation_name,
        "body_part": body_part_name,
        "approach": approach_name,
        "device": device_name,
        "qualifier": qualifier_name,
        "pcs_code": None,
        "valid": False,
        "explanation": "Tables not loaded: map names → characters with official 2025 PCS tables, then validate combination.",
    }
    return result
