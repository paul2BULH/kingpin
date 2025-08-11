# Section "0" – Medical & Surgical keyword hints (names only, not letters)
# These are intentionally conservative and **not exhaustive**.
# You will plug official tables later to map names → characters.
from __future__ import annotations
from typing import Dict, List, Tuple

# Root operation names (subset): keep names; do not assume the letter yet
ROOT_OPERATION_HINTS: Dict[str, List[str]] = {
    "Excision": ["excision", "partial removal", "wedge resection", "biopsy", "shave"],
    "Resection": ["resection", "total removal", "lobectomy", "nephrectomy", "cholecystectomy"],
    "Drainage": ["drainage", "i&d", "incision and drainage", "aspiration", "tap", "paracentesis", "thoracentesis"],
    "Insertion": ["insertion", "place", "implant"],
    "Replacement": ["replacement", "arthroplasty", "prosthesis placement"],
    "Repair": ["repair", "suture", "closure", "herniorrhaphy"],
    "Bypass": ["bypass", "anastomosis", "graft",
               "bypass graft"],
    "Dilation": ["dilation", "angioplasty", "balloon"],
    "Supplement": ["augmentation", "reinforcement", "mesh placement"],
    "Fusion": ["fusion", "arthrodesis"],
    "Drainage Control": ["control of bleeding", "hemostasis", "control hemorrhage"]
}

# Body system name hints (subset)
BODY_SYSTEM_HINTS: Dict[str, List[str]] = {
    "Skin and Subcutaneous Tissue": ["skin", "dermis", "subcutaneous", "fascia"],
    "Musculoskeletal System": ["muscle", "tendon", "bone", "joint", "vertebra", "disc"],
    "Respiratory System": ["lung", "bronchus", "trachea", "pleura"],
    "Gastrointestinal System": ["stomach", "duodenum", "jejunum", "ileum", "colon", "rectum", "anus", "liver", "gallbladder"],
    "Hepatobiliary System and Pancreas": ["liver", "bile", "hepatic", "pancreas", "gallbladder"],
    "Urinary System": ["kidney", "ureter", "bladder", "urethra"],
    "Female Reproductive System": ["uterus", "ovary", "fallopian", "cervix", "vagina"],
    "Male Reproductive System": ["prostate", "testis", "penis", "vas deferens"],
    "Cardiovascular System": ["heart", "coronary", "aorta", "artery", "vein"],
    "Lymphatic and Hemic Systems": ["spleen", "lymph", "lymph node"],
    "Nervous System": ["brain", "spinal", "nerve", "cranial"],
    "Endocrine System": ["thyroid", "adrenal", "pituitary"]
}

# Approach hints (names only)
APPROACH_HINTS: Dict[str, List[str]] = {
    "Open": ["open", "laparotomy", "thoracotomy"],
    "Percutaneous": ["percutaneous", "needle", "puncture"],
    "Percutaneous Endoscopic": ["laparoscopic", "thoracoscopic", "arthroscopic", "endoscopic"],
    "Natural or Artificial Opening": ["transnasal", "transoral", "vaginal approach"],
    "Natural or Artificial Opening Endoscopic": ["endoscopic via mouth", "colonoscopy", "gastroscopy"],
    "Via Natural or Artificial Opening with Percutaneous Endoscopic Assistance": ["hybrid endoscopic with percutaneous assistance"],
    "External": ["external fixation", "manual reduction"]
}

# Device presence hints (names only)
DEVICE_HINTS: List[Tuple[str, List[str]]] = [
    ("Drainage Device", ["drain", "jp drain", "chest tube", "pigtail"]),
    ("Stent", ["stent"]),
    ("Catheter", ["catheter", "foley"]),
    ("Synthetic Substitute", ["mesh", "graft", "patch"]),
    ("Intraluminal Device", ["prosthesis", "valve", "pacemaker", "lead"]),
]
