import streamlit as st
import json, os
from utils.parser import extract_section0_facts
from utils.pcs_builder import summarize_candidates, map_to_pcs_code
from utils.rules_engine import load_rules, apply_rules, build_code_skeleton
from utils.gemini_api import analyze_with_gemini
from utils.validation import TablesContext, resolve_code

st.set_page_config(page_title="PCS Section 0 – MVP", layout="wide")

st.title("ICD-10-PCS – Section '0' (Medical & Surgical) MVP")
st.caption("Scaffold for Section 0 only • Facts extraction + Character Builder • Plug tables later for authoritative codes")

with st.sidebar:
    st.header("Scope")
    honor_b61b = st.checkbox("Honor PCS B6.1b (suppress routine wound drains)", value=True)

    use_gemini = st.checkbox("Use Gemini AI for extraction", value=False, help="Requires GEMINI_API_KEY in st.secrets or below.")
    api_key = st.text_input("GEMINI_API_KEY (optional)", type="password", value=st.secrets.get('GEMINI_API_KEY', '') if 'GEMINI_API_KEY' in st.secrets else "")
    st.markdown("**Section:** 0 (Medical & Surgical) — fixed for this MVP.")
    st.info("Future work: attach official tables in `assets/` and enable real mapping/validation.")

rules_path = os.path.join('assets', 'pcs_guidelines_rules_2025.json')
RULES = load_rules(rules_path) if os.path.exists(rules_path) else None
TABLES_CTX = TablesContext(assets_dir='assets')

st.subheader("1) Paste Procedure Text")
sample_1 = "Laparoscopic cholecystectomy performed. Critical view achieved. Gallbladder removed. A JP drain was placed."
sample_2 = "Incision and drainage of right forearm abscess under local anesthesia; wound irrigated and packed."
sample_3 = "Open reduction and internal fixation (ORIF) of distal radius fracture with plate and screws."

c1, c2, c3 = st.columns(3)
if c1.button("Try: Laparoscopic cholecystectomy"):
    st.session_state["proc_text"] = sample_1
if c2.button("Try: I&D forearm abscess"):
    st.session_state["proc_text"] = sample_2
if c3.button("Try: ORIF distal radius"):
    st.session_state["proc_text"] = sample_3

proc_text = st.text_area("Procedure note / Operative note", value=st.session_state.get("proc_text", ""), height=220, placeholder="Paste operative text here...")

analyze = st.button("Analyze (Section 0 heuristics)")
if analyze and proc_text.strip():
    facts = extract_section0_facts(proc_text)

    # Optionally call Gemini for structured facts
    ai_facts_resp = None
    if use_gemini:
        key = api_key or None
        ai_facts_resp = analyze_with_gemini(proc_text, key)
        if ai_facts_resp.get("ok"):
            ai_facts = ai_facts_resp.get("facts") or {}
            # Normalize AI keys to match downstream
            facts.update({
                "objective": ai_facts.get("objective"),
                "body_parts": ai_facts.get("body_parts"),
                "approaches": ai_facts.get("approaches"),
                "devices": ai_facts.get("devices"),
                "laterality": ai_facts.get("laterality"),
                "discontinued": ai_facts.get("discontinued"),
                "converted_to_open": ai_facts.get("converted_to_open"),
                "multi_sites": ai_facts.get("multi_sites"),
                "multi_objectives": ai_facts.get("multi_objectives"),
                "biopsy": ai_facts.get("biopsy"),
                "qualifier_hints": ai_facts.get("qualifier_hints"),
                "device_left_in_place": ai_facts.get("device_left_in_place"),
            })
        else:
            st.warning(f"Gemini extraction failed: {ai_facts_resp.get('error')}")

    summary = summarize_candidates(facts)
    st.subheader("2) Extracted Facts")
    st.json({"heuristics": summary, "ai": (ai_facts_resp or {})})

    # Apply rules if available
    rules_out = None
    if RULES:
        rules_out = apply_rules(proc_text, facts, RULES)
        st.subheader("3) Rules Evaluation (from pcs_guidelines_rules_2025.json)")
        st.json(rules_out)
    else:
        st.info("Rules file not found in assets/.")

    st.subheader("4) Character Builder (Names; not letters yet)")
    col1, col2 = st.columns(2)
    with col1:
        root_op = st.selectbox(
            "Root Operation (name)",
            options=["—"] + [x["name"] for x in summary["root_operations"]],
            index=0
        )
        body_sys = st.selectbox(
            "Body System (name)",
            options=["—"] + [x["name"] for x in summary["body_systems"]],
            index=0
        )
        approach = st.selectbox(
            "Approach (name)",
            options=["—"] + [x["name"] for x in summary["approaches"]],
            index=0
        )
    with col2:
        body_part = st.text_input("Body Part (normalized name)", value="", placeholder="e.g., Gallbladder, Liver, Skin, Distal radius")
        device = st.selectbox(
            "Device (name)",
            options=["—"] + [x["name"] for x in summary["devices"]],
            index=0
        )
        qualifier = st.text_input("Qualifier (name)", value="", placeholder="e.g., Diagnostic, Via natural opening, etc.")

    if st.button("Build Draft (no letters yet)"):
        result = map_to_pcs_code(
            section_name="0 (Medical & Surgical)",
            body_system_name=body_sys if body_sys != "—" else None,
            root_operation_name=root_op if root_op != "—" else None,
            body_part_name=body_part or None,
            approach_name=approach if approach != "—" else None,
            device_name=device if device != "—" else None,
            qualifier_name=qualifier or None,
            tables_context=None
        )
        # Build a 7-char skeleton: '0??????' (letters resolved once tables are integrated)
        skeleton = build_code_skeleton(
            section_char="0",
            body_system_char="?",
            root_operation_char="?",
            body_part_char="?",
            approach_char="?",
            device_char="?",
            qualifier_char="?"
        )
        st.success("Draft built (names only). Attach tables later to resolve actual 7 characters.")
        st.json({"draft": result, "skeleton": skeleton})

    st.markdown("### 5) Auto-Pick (Tables-driven) — Section 0")
    autopick = st.button("Auto-Pick Code from Tables")
    if autopick:
        # Re-evaluate rules to include overrides in the final mapping
        eff_rules = apply_rules(proc_text, facts, RULES) if RULES else None
        if not TABLES_CTX.is_ready():
            st.error("Official Tables not loaded. Place icd10pcs_tables_2025.xml in assets/.")
        else:
            # Apply rule-derived overrides/hints
            if eff_rules and eff_rules.get("updates"):
                u = eff_rules["updates"]
                # Body system bias: choose first if user didn't set one
                if (body_sys == "—" or not body_sys) and u.get("body_system_bias"):
                    body_sys = u["body_system_bias"][0]
                # Root operation hint
                if (root_op == "—" or not root_op) and u.get("root_operation_hint"):
                    root_op = (u["root_operation_hint"][0].split("|")[0])
                # Approach override
                if u.get("approach_override") and (approach == "—" or not approach):
                    # If multiple in value like 'Open|Percutaneous Endoscopic', pick first
                    approach = u["approach_override"].split("|")[0]
                # Device override if not selected by user
                if u.get("device_override") and (device == "—" or not device):
                    device = u["device_override"]
                # Qualifier hints
                if u.get("qualifier_hints") and not qualifier:
                    qualifier = u["qualifier_hints"][0]

            # B6.1b suppression: if rules mark routine wound drain integral and user selected Insertion + Drainage Device, block autopick.
            if honor_b61b and eff_rules and eff_rules.get("updates", {}).get("integral_wound_drain"):
                if (root_op == "Insertion" and (device == "Drainage Device" or (device and "Drainage Device" in str(device)))):
                    st.warning("PCS B6.1b: Routine wound/JP/Hemovac drain is integral to the main procedure — no separate insertion code.")
                    st.stop()
            res = resolve_code(
                context=TABLES_CTX,
                section_name="0 (Medical & Surgical)",
                body_system_name=body_sys if body_sys != "—" else None,
                root_operation_name=root_op if root_op != "—" else None,
                body_part_name=(body_part or None),
                approach_name=approach if approach != "—" else None,
                device_name=device if device != "—" else None,
                qualifier_name=(qualifier or None),
                note_text=proc_text
            )
            if res.get("ok") and res.get("candidates"):
                st.success("Tables-driven candidates:")
                cands = res["candidates"]
                topn = cands[:3]
                for i, c in enumerate(topn, 1):
                    st.markdown(f"**#{i} — {c['pcs_code']}**")
                    st.write({
                        "labels": c.get("labels"),
                        "components": c.get("components"),
                        "score": c.get("score"),
                        "root_key": c.get("root_key")
                    })
                with st.expander("See raw resolver output"):
                    st.json(res)
            else:
                st.warning(res.get("error") or "No candidates matched the current selections.")
else:
    st.info("Paste a procedure and click **Analyze**.")

st.divider()
st.caption("MVP notes: This build intentionally avoids mapping names → letters until official tables are integrated in `utils/validation.py`.")
