"""
Item Name Parser
================
Central, reusable service for extracting structured data from CNCLeaders item names.

Naming convention:  <Material>-<ToolFamily><Size>-<Dim>-<Length>-<Flutes>...
Example:            C-SEM6-D6-50-2F
                    ↑  ↑↑↑
                    │  │└── trailing digits stripped → Tool Family = SEM
                    │  └─── second segment
                    └─────── first segment = Material = C

Extend this file to extract additional fields (Diameter, Flutes, etc.) later.
Adding a new Material: add an entry to MATERIAL_LABELS.
Adding a new Tool Family: no config needed — the parser strips trailing digits automatically.
"""

import re

# ---------------------------------------------------------------------------
# Configuration — update these mappings as the product line grows
# ---------------------------------------------------------------------------

MATERIAL_LABELS = {
    "C":   {"en": "Carbide",                              "ar": "كربيد"},
    "HSS": {"en": "HSS",                                  "ar": "صلب عالي السرعات"},
    "TCT": {"en": "TCT",                                  "ar": "عود كربيد ملحوم في جسم صلب"},
    "CW":  {"en": "CW",                                   "ar": "شفرات كربيد ملحومة فى جسم صلب"},
    "CM":  {"en": "CM",                                   "ar": "كربيد يستخدم فى المعادن"},
    "M&G": {"en": "M&G",                                  "ar": "رخام و زجاج"},
}

# Optional canonical aliases — map any known variant to the standard key.
# e.g. {"CARBIDE": "C"} would let "CARBIDE-SEM6-..." parse as material "C".
MATERIAL_ALIASES: dict = {}

# ---------------------------------------------------------------------------
# Static canonical lists — the single place to add new families / materials
# ---------------------------------------------------------------------------

# All known tool families in display order.
# Extend this list when new families are introduced.
ALL_TOOL_FAMILIES: list[str] = [
    "ALEM", "ALV", "BB", "BEM", "BD", "BN", "DT", "DR", "EM",
    "FBN", "FEM", "FINE", "HB", "HV", "RBN", "RE", "REM", "RSEM",
    "SBN", "SEM", "SEMT", "TBN", "TEM", "TFEM", "TREM", "V", "REAMER",
]

# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

_TRAILING_DIGITS = re.compile(r"\d+$")


def parse_item_name(item_name: str) -> dict | None:
    """
    Parse a CNCLeaders item name and return its structured components.

    Returns a dict with at minimum:
        material    (str)  — e.g. "C", "HSS"
        tool_family (str | None) — e.g. "SEM", "FEM", or None if unparseable

    Returns None if the item name is empty or has no recognisable structure
    (fewer than two dash-separated segments).

    This function is the single source of truth for item name parsing.
    Extend the returned dict here when new fields are needed.
    """
    if not item_name or not isinstance(item_name, str):
        return None

    parts = item_name.strip().split("-", 2)
    if len(parts) < 2:
        return None

    raw_material = parts[0].strip().upper()
    material = MATERIAL_ALIASES.get(raw_material, raw_material)

    raw_tf = parts[1].strip().upper()
    tool_family = _TRAILING_DIGITS.sub("", raw_tf) or None

    return {
        "material": material,
        "tool_family": tool_family,
    }


def get_material_label(material_code: str, lang: str = "en") -> str:
    """
    Return the human-readable label for a material code.
    Falls back to the code itself when no label is configured.
    """
    entry = MATERIAL_LABELS.get(material_code)
    if not entry:
        return material_code
    return entry.get(lang) or entry.get("en") or material_code


def build_tool_family_like_pattern(tool_family: str) -> str:
    """
    Build the SQL LIKE pattern that matches all items belonging to a Tool Family.

    Example: "SEM" → "%-SEM%"

    The leading '%-' ensures the tool family appears after the material segment.
    """
    return f"%-{tool_family}%"


def build_material_like_pattern(material: str) -> str:
    """
    Build the SQL LIKE pattern that matches all items with a given Material.

    Example: "C" → "C-%"
    """
    return f"{material}-%"
