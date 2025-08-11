# ICD-10-PCS Section "0" (Medical & Surgical) – Streamlit MVP

This is a **scaffold** focused **only on Section "0"**. It gives you a working Streamlit UI, a lightweight NLP heuristic layer to extract procedure facts, and a **clean integration point** to plug in the official PCS **Tables/Index/Definitions** later.

> ⚠️ Important: This MVP **does not** return authoritative 7‑character codes yet. It extracts facts (candidate body system, root operation, approach, device signals) and shows a **Character Builder** where you can select axes. Final code letters must be validated and mapped via the official 2025 PCS tables (to be integrated next).

## What’s included

- `streamlit_app.py` – Streamlit UI with:
  - Text input (procedure note or op note)
  - Fact extraction (Section 0 heuristics)
  - Character Builder (names only, not letters yet)
  - Placeholder validator hooks

- `utils/` – Minimal logic split:
  - `keywords_section0.py` – curated keywords for body systems, root operations, approaches, device hints
  - `parser.py` – simple NLP extraction for Section 0 (regex/keyword scoring)
  - `pcs_builder.py` – assembles suggestions and exposes a future `map_to_pcs_code(...)` integration point
  - `validation.py` – placeholder for table-based validation/mapping

- `assets/` – drop your reference files here later:
  - `body_part_key.json` – body part synonyms → normalized PCS body part names
  - `device_key.json` – device synonyms → normalized device categories
  - `README.md` – guidance on where to place official tables/index/definitions

## Next steps (when you’re ready)
1. Place the official 2025 PCS **tables/index/definitions** in `assets/` (XML or JSON).
2. Implement `utils/validation.py` to load tables and perform **body part / device / qualifier** mapping + **code validity** checks.
3. Implement `utils/pcs_builder.map_to_pcs_code(...)` to turn the selected **axis names** into **official characters** using those tables.

## Run locally
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```



---

## AI + Rules Roadmap (Foundation)

- **AI extraction (Gemini 2.0 Flash)**: `utils/gemini_api.py` parses operative text into structured facts (objective, approaches, devices, etc.).
- **Guidelines rules**: Place `pcs_guidelines_rules_2025.json` in `assets/` (already done). The app loads it and applies a small engine in `utils/rules_engine.py` to set qualifier/device/approach overrides and emit documentation queries (e.g., A8).
- **Table-driven mapping (next)**: Implement `utils/validation.py` to consume the official 2025 PCS tables and translate **names → characters** with row validity checks.
- **Deterministic + AI hybrid**: Use AI for fact extraction only; **mapping/validation stays deterministic** via tables/rules for auditability.

### Configure Gemini API
- Preferred: add to Streamlit secrets: `GEMINI_API_KEY = "YOUR_KEY"`
- Or paste in the sidebar field.

