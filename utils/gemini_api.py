from __future__ import annotations
from typing import Any, Dict, Optional

def analyze_with_gemini(text: str, api_key: Optional[str]) -> Dict[str, Any]:
    """
    Calls Gemini 2.0 Flash (if library available and API key provided) to extract
    structured facts for PCS Section 0 coding.

    Returns a dict with keys:
      - ok: bool
      - facts: {...}  (objective, body_parts, approaches, devices, laterality, discontinued, converted_to_open, multi_sites, biopsy, qualifier_hints)
      - error: Optional[str]
    """
    if not api_key:
        return {"ok": False, "facts": {}, "error": "No API key provided"}

    # Prefer the new google-genai client; fallback to legacy if needed.
    client = None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        model_name = "gemini-2.0-flash"
        system_prompt = (
            "You are a surgical coding extraction assistant. "
            "Extract *only* structured JSON with the following keys: "
            "objective, body_systems, body_parts, approaches, devices, laterality, "
            "discontinued, converted_to_open, multi_sites, multi_objectives, biopsy, "
            "qualifier_hints, device_left_in_place. "
            "Use booleans for flags. Use lists where multiple values could exist. "
            "Do NOT add commentary."
        )
        user_text = text
        res = client.models.generate_content(model=model_name, contents=[{"role": "user", "parts": [system_prompt + "\n\n" + user_text]}])
        raw = res.text or ""
    except Exception as e_new:
        # Legacy client fallback
        try:
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=api_key)
            model = genai_legacy.GenerativeModel("gemini-2.0-flash")
            prompt = (
                "Extract strict JSON with keys: "
                "objective, body_systems, body_parts, approaches, devices, laterality, "
                "discontinued, converted_to_open, multi_sites, multi_objectives, biopsy, "
                "qualifier_hints, device_left_in_place. No commentary."
                "\n\nTEXT:\n" + text
            )
            res = model.generate_content(prompt)
            raw = res.text or ""
        except Exception as e_legacy:
            return {"ok": False, "facts": {}, "error": f"Gemini import/call failed: {e_new} / {e_legacy}"}

    # Try to locate a JSON block in the response
    import json, re
    m = re.search(r'\{[\s\S]*\}$', raw.strip())
    if not m:
        # Best effort: sometimes the model returns JSON already.
        try:
            facts = json.loads(raw)
            return {"ok": True, "facts": facts, "error": None}
        except Exception:
            return {"ok": False, "facts": {}, "error": "Gemini did not return JSON"}

    try:
        facts = json.loads(m.group(0))
        return {"ok": True, "facts": facts, "error": None}
    except Exception as e:
        return {"ok": False, "facts": {}, "error": f"JSON parse error: {e}"}
