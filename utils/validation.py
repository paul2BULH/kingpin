
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import os, re, xml.etree.ElementTree as ET

# ---------- Helpers ----------
def _norm(s: Optional[str]) -> str:
    return (s or "").strip()

def _eq(a: str, b: str) -> bool:
    return _norm(a).lower() == _norm(b).lower()

def _contains(a: str, b: str) -> bool:
    return _norm(b).lower() in _norm(a).lower()

# ---------- Tables Parser ----------

class PCSTables:
    """
    Parses icd10pcs_tables_2025.xml to provide:
      - header for axis 1..3 (Section, Body System, Operation) with code+text
      - all pcsRows with axis 4..7 (Body Part, Approach, Device, Qualifier) labels (code+text)
    """
    def __init__(self, root: ET.Element):
        self.root = root
        # Map '0XY' -> {
        #   "section": {"code": "0", "text": "Medical and Surgical"},
        #   "body_system": {"code": "F", "text": "Hepatobiliary System and Pancreas"},
        #   "operation": {"code": "T", "text": "Resection", "definition": "..."},
        #   "rows": [
        #       {"4":[{"code":"4","text":"Gallbladder"},...],
        #        "5":[{"code":"0","text":"Open"},...],
        #        "6":[{"code":"Z","text":"No Device"},...],
        #        "7":[{"code":"Z","text":"No Qualifier"},...]}
        #   ]
        # }
        self.tables: Dict[str, Dict[str, Any]] = {}
        self._parse()

    @classmethod
    def from_path(cls, path: str) -> "PCSTables":
        tree = ET.parse(path)
        return cls(tree.getroot())

    def _labels(self, axis_elem: ET.Element) -> List[Dict[str, str]]:
        out = []
        for lab in axis_elem.findall('label'):
            out.append({"code": lab.attrib.get('code', ''), "text": (lab.text or '').strip()})
        return out

    def _axis_info(self, table_elem: ET.Element) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        for ax in table_elem.findall('axis'):
            pos = ax.attrib.get('pos')
            labels = self._labels(ax)
            title = (ax.findtext('title') or '').strip()
            definition = (ax.findtext('definition') or '').strip()
            info[pos] = {"title": title, "definition": definition, "labels": labels}
        return info

    def _parse(self):
        for pt in self.root.findall('pcsTable'):
            header = self._axis_info(pt)
            # Expect single label for axis 1..3
            ax1 = header.get('1', {}); lab1 = (ax1.get('labels') or [{}])[0]
            ax2 = header.get('2', {}); lab2 = (ax2.get('labels') or [{}])[0]
            ax3 = header.get('3', {}); lab3 = (ax3.get('labels') or [{}])[0]
            sec = lab1.get('code','')
            bs = lab2.get('code','')
            op = lab3.get('code','')
            key = f"{sec}{bs}{op}" if sec and bs and op else None
            if not key:
                continue
            table_entry = {
                "section": {"code": sec, "text": lab1.get('text','')},
                "body_system": {"code": bs, "text": lab2.get('text','')},
                "operation": {"code": op, "text": lab3.get('text',''), "definition": header.get('3',{}).get('definition','')},
                "rows": []
            }
            # Rows (axis 4..7)
            for row in pt.findall('pcsRow'):
                row_dict = {}
                for ax in row.findall('axis'):
                    pos = ax.attrib.get('pos')
                    row_dict[pos] = self._labels(ax)
                # Only keep if at least body part axis present
                if row_dict:
                    table_entry["rows"].append(row_dict)
            self.tables[key] = table_entry

    # Lookup helpers
    def find_roots(self, section_code: str, body_system_name: Optional[str], operation_name: Optional[str]) -> List[str]:
        roots = []
        for k, t in self.tables.items():
            if t["section"]["code"] != section_code:
                continue
            bs_ok = True
            op_ok = True
            if body_system_name:
                bs_ok = _eq(t["body_system"]["text"], body_system_name)
            if operation_name:
                op_ok = _eq(t["operation"]["text"], operation_name)
            if bs_ok and op_ok:
                roots.append(k)
        return roots

    def best_match_row(self, root_key: str,
                       body_part_name: Optional[str],
                       approach_name: Optional[str],
                       device_name: Optional[str],
                       qualifier_name: Optional[str]) -> Tuple[Optional[str], Dict[str, Any], List[Dict[str, Any]]]:
        """
        Return (code, chosen_labels, alternates) where chosen_labels contains
        picked label objects for axis 4..7 and alternates contains other viable
        combinations with scores.
        """
        t = self.tables.get(root_key)
        if not t:
            return None, {}, []
        best = None
        best_score = -1
        best_choice = None

        alts: List[Dict[str, Any]] = []

        for row in t["rows"]:
            # axis positions 4..7 may each have several label options
            bparts = row.get('4', [])
            apprs = row.get('5', [])
            devs  = row.get('6', [])
            quals = row.get('7', [])

            # Scoring: prefer exact text match; fallback to any when None
            def pick(options, want_name: Optional[str]) -> Tuple[Optional[Dict[str,str]], int]:
                if not options:
                    return None, 0
                if not want_name:
                    # Default preference: if there is 'No Device' or 'No Qualifier', prefer that by convention
                    if any(_eq(o.get('text',''), 'No Device') for o in options):
                        for o in options:
                            if _eq(o.get('text',''), 'No Device'):
                                return o, 1
                    if any(_eq(o.get('text',''), 'No Qualifier') for o in options):
                        for o in options:
                            if _eq(o.get('text',''), 'No Qualifier'):
                                return o, 1
                    return options[0], 0
                # exact match
                for o in options:
                    if _eq(o.get('text',''), want_name):
                        return o, 3
                # substring match
                for o in options:
                    if _contains(o.get('text',''), want_name) or _contains(want_name, o.get('text','')):
                        return o, 2
                return options[0], 0

            pick4, s4 = pick(bparts, body_part_name)
            pick5, s5 = pick(apprs, approach_name)
            pick6, s6 = pick(devs, device_name)
            pick7, s7 = pick(quals, qualifier_name)
            score = s4 + s5 + s6 + s7
            choice = {"4": pick4, "5": pick5, "6": pick6, "7": pick7}
            if score > best_score:
                best_score = score
                best = (pick4, pick5, pick6, pick7)
                best_choice = choice

            # Record alt
            code = None
            if pick4 and pick5 and pick6 and pick7:
                code = f"{t['section']['code']}{t['body_system']['code']}{t['operation']['code']}{pick4['code']}{pick5['code']}{pick6['code']}{pick7['code']}"
            alts.append({
                "code": code,
                "score": score,
                "labels": choice
            })

        if best and best_choice:
            b4, b5, b6, b7 = best
            if b4 and b5 and b6 and b7:
                code = f"{t['section']['code']}{t['body_system']['code']}{t['operation']['code']}{b4['code']}{b5['code']}{b6['code']}{b7['code']}"
                return code, {"4": b4, "5": b5, "6": b6, "7": b7}, alts
        return None, {}, alts

# ---------- Index Parser (lightweight leads) ----------

class PCSIndex:
    """
    Parses icd10pcs_index_2025.xml to provide term → code leads like '0FT4'.
    """
    def __init__(self, root: ET.Element):
        self.root = root

    @classmethod
    def from_path(cls, path: str) -> "PCSIndex":
        tree = ET.parse(path)
        return cls(tree.getroot())

    def find_leads_in_text(self, text: str, limit: int = 10) -> List[str]:
        """
        Naive scan of mainTerm titles and their 'see' entries; collects codes text (usually 3-4 chars like 0FT4).
        """
        t = (text or "").lower()
        leads: List[str] = []
        for mt in self.root.iterfind('.//mainTerm'):
            title = (mt.findtext('title') or '').strip()
            if not title:
                continue
            if title.lower() in t:
                # collect codes from children 'codes'
                for codes in mt.iterfind('.//codes'):
                    c = (codes.text or '').strip()
                    if c and c not in leads:
                        leads.append(c)
                        if len(leads) >= limit:
                            return leads
        return leads

# ---------- Public Context + Resolver ----------

# ---------- Synonym & Aggregation Keys ----------

def _load_json_if_exists(path: str):
    if os.path.exists(path):
        import json
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

class BodyPartKey:
    def __init__(self, data: dict):
        # expects {"data": {"synonym": ["Preferred Name", ...], ...}}
        self.map = {}
        raw = (data or {}).get("data") or {}
        for syn, prefs in raw.items():
            self.map[syn.strip().lower()] = [p.strip() for p in prefs]

    def lookup(self, name: Optional[str]) -> List[str]:
        if not name:
            return []
        n = name.strip().lower()
        return self.map.get(n, [name])

class DeviceKey:
    def __init__(self, data: dict):
        # expects {"data": {"synonym or brand": ["PCS Device Value", ...], ...}}
        self.map = {}
        raw = (data or {}).get("data") or {}
        for syn, vals in raw.items():
            self.map[syn.strip().lower()] = [v.strip() for v in vals]

    def lookup(self, name: Optional[str]) -> List[str]:
        if not name:
            return []
        return self.map.get(name.strip().lower(), [name])

class DeviceAggregation:
    def __init__(self, data: dict):
        # expects {"records": [{"specific_device": "...", "general_device": "...", ...}, ...]}
        self.to_general = {}
        recs = (data or {}).get("records") or []
        for r in recs:
            spec = (r.get("specific_device") or "").strip()
            gen = (r.get("general_device") or "").strip()
            if spec and gen:
                self.to_general.setdefault(spec, set()).add(gen)

    def generalize(self, name: Optional[str]) -> List[str]:
        if not name:
            return []
        return list(self.to_general.get(name, []))

# ---------- Extend TablesContext to load keys ----------

class TablesContext:
    def __init__(self, assets_dir: str):
        self.assets_dir = assets_dir
        self.tables: Optional[PCSTables] = None
        self.index: Optional[PCSIndex] = None
        self.body_key: Optional[BodyPartKey] = None
        self.device_key: Optional[DeviceKey] = None
        self.device_agg: Optional[DeviceAggregation] = None
        self.loaded: bool = False
        self.load()

    def load(self):
        tables_path = os.path.join(self.assets_dir, "icd10pcs_tables_2025.xml")
        index_path = os.path.join(self.assets_dir, "icd10pcs_index_2025.xml")
        if os.path.exists(tables_path):
            self.tables = PCSTables.from_path(tables_path)
        if os.path.exists(index_path):
            self.index = PCSIndex.from_path(index_path)
        # Keys
        bp_json = _load_json_if_exists(os.path.join(self.assets_dir, "body_part_key.json"))
        if bp_json: self.body_key = BodyPartKey(bp_json)
        dev_json = _load_json_if_exists(os.path.join(self.assets_dir, "device_key.json"))
        if dev_json: self.device_key = DeviceKey(dev_json)
        agg_json = _load_json_if_exists(os.path.join(self.assets_dir, "device_aggregation.json"))
        if agg_json: self.device_agg = DeviceAggregation(agg_json)
        self.loaded = self.tables is not None

    def is_ready(self) -> bool:
        return self.loaded

# ---------- Normalization helpers ----------

def _norm_body_part(context: TablesContext, name: Optional[str]) -> List[str]:
    """Return a list of preferred names for matching axis-4 labels."""
    if not name:
        return []
    # use body part key; else return the given name
    if context and context.body_key:
        return context.body_key.lookup(name) or [name]
    return [name]

def _norm_device(context: TablesContext, name: Optional[str]) -> List[str]:
    """Return a list of candidate device names (specific + generalized)."""
    if not name:
        return []
    candidates = [name]
    if context and context.device_key:
        candidates = context.device_key.lookup(name) or [name]
    # generalize
    more = []
    if context and context.device_agg:
        for c in list(candidates):
            more += context.device_agg.generalize(c)
    # de-dup
    out = []
    for v in candidates + more:
        if v and v not in out:
            out.append(v)
    return out



def resolve_code(context: TablesContext,
                 section_name: str,
                 body_system_name: Optional[str],
                 root_operation_name: Optional[str],
                 body_part_name: Optional[str],
                 approach_name: Optional[str],
                 device_name: Optional[str],
                 qualifier_name: Optional[str],
                 note_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Deterministic resolver using official tables.
    Strategy:
      1) Find roots for Section 0 that match body_system_name + root_operation_name.
      2) If none, try index leads from note_text (first 3 chars define root).
      3) For each candidate root, pick best row by matching body part/approach/device/qualifier names.
      4) Rank by score; return top + alternates.
    """
    if not context or not context.tables:
        return {"ok": False, "error": "Tables not loaded.", "candidates": []}

    # 1) Exact header match
    roots = context.tables.find_roots(section_code="0",
                                      body_system_name=body_system_name,
                                      operation_name=root_operation_name)

    # 2) Index leads (fallback)
    if not roots and note_text and context.index:
        leads = context.index.find_leads_in_text(note_text)
        # normalize leads to 3-char roots (first three chars)
        roots = []
        for lead in leads:
            rt = lead[:3]
            if rt.startswith('0') and rt not in roots and rt in context.tables.tables:
                roots.append(rt)

    candidates: List[Dict[str, Any]] = []
    for rt in roots:
        bp_list = _norm_body_part(context, body_part_name)
        dev_list = _norm_device(context, device_name)
        # Try each combination of normalized names; keep best
        trial_best = None
        trial_best_choice = None
        trial_best_alts = None
        trial_best_score = -1
        for bp in (bp_list or [None]):
            for dv in (dev_list or [None]):
                code, chosen, alts = context.tables.best_match_row(
                    root_key=rt,
                    body_part_name=bp,
                    approach_name=approach_name,
                    device_name=dv,
                    qualifier_name=qualifier_name
                )
                if code:
                    score = sum(1 for k,v in chosen.items() if v)
                    if score > trial_best_score:
                        trial_best_score = score
                        trial_best = code
                        trial_best_choice = chosen
                        trial_best_alts = alts
        code, chosen, alts = trial_best, trial_best_choice, (trial_best_alts or [])
        if code:
            t = context.tables.tables[rt]
            candidates.append({
                "pcs_code": code,
                "components": {
                    "section": t["section"]["code"],
                    "body_system": t["body_system"]["code"],
                    "root_operation": t["operation"]["code"],
                    "body_part": chosen.get("4",{}).get("code") if chosen.get("4") else None,
                    "approach": chosen.get("5",{}).get("code") if chosen.get("5") else None,
                    "device": chosen.get("6",{}).get("code") if chosen.get("6") else None,
                    "qualifier": chosen.get("7",{}).get("code") if chosen.get("7") else None,
                },
                "labels": {
                    "section": t["section"]["text"],
                    "body_system": t["body_system"]["text"],
                    "root_operation": t["operation"]["text"],
                    "body_part": chosen.get("4",{}).get("text") if chosen.get("4") else None,
                    "approach": chosen.get("5",{}).get("text") if chosen.get("5") else None,
                    "device": chosen.get("6",{}).get("text") if chosen.get("6") else None,
                    "qualifier": chosen.get("7",{}).get("text") if chosen.get("7") else None,
                },
                "score": sum(1 for k,v in chosen.items() if v),
                "root_key": rt
            })
    # Rank by score desc (tie-breaker by code)
    candidates.sort(key=lambda x: (x["score"], x["pcs_code"]), reverse=True)

    return {"ok": True, "error": None, "candidates": candidates[:5]}
