import re
from fractions import Fraction

import streamlit as st

# -- Unit normalisation -------------------------------------------------------

UNIT_ALIASES: dict[str, str] = {
    "tablespoon": "tbsp", "tablespoons": "tbsp", "tbsps": "tbsp", "tbs": "tbsp", "T": "tbsp",
    "teaspoon": "tsp", "teaspoons": "tsp", "tsps": "tsp", "t": "tsp",
    "cup": "cup", "cups": "cup", "c": "cup",
    "ounce": "oz", "ounces": "oz",
    "pound": "lb", "pounds": "lb", "lbs": "lb",
    "gram": "g", "grams": "g",
    "kilogram": "kg", "kilograms": "kg",
    "milliliter": "ml", "milliliters": "ml", "millilitres": "ml",
    "liter": "l", "liters": "l", "litres": "l", "litre": "l",
    "pinch": "pinch", "pinches": "pinch",
    "clove": "clove", "cloves": "clove",
    "can": "can", "cans": "can",
    "bunch": "bunch", "bunches": "bunch",
    "slice": "slice", "slices": "slice",
    "piece": "piece", "pieces": "piece",
}

CONVERTIBLE: dict[tuple[str, str], float] = {
    ("tsp", "tbsp"): 3.0,   # 3 tsp = 1 tbsp
    ("tbsp", "cup"): 16.0,  # 16 tbsp = 1 cup
    ("g", "kg"): 1000.0,
    ("ml", "l"): 1000.0,
    ("oz", "lb"): 16.0,
}

# Vulgar-fraction map for ingredient strings like "½ cup"
_VULGAR_MAP = {
    "½": "1/2", "⅓": "1/3", "⅔": "2/3",
    "¼": "1/4", "¾": "3/4",
    "⅕": "1/5", "⅖": "2/5", "⅗": "3/5", "⅘": "4/5",
    "⅙": "1/6", "⅚": "5/6",
    "⅛": "1/8", "⅜": "3/8", "⅝": "5/8", "⅞": "7/8",
}

_QTY_RE = re.compile(
    r"^\s*([\d\s/½⅓⅔¼¾⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞.]+)\s*"  # quantity (numbers, fractions, vulgar)
    r"([a-zA-Z.]+)?\s*"                          # optional unit
    r"(.*)",                                      # remainder = item name
    re.UNICODE,
)


def _parse_quantity(text: str) -> tuple[float, str, str]:
    """Parse an ingredient string into (quantity, unit, name).

    Returns (0, '', full_text) when parsing fails.
    """
    m = _QTY_RE.match(text.strip())
    if not m:
        return 0.0, "", text.strip()

    raw_qty, raw_unit, name = m.group(1).strip(), (m.group(2) or "").strip().rstrip("."), m.group(3).strip()

    # Replace vulgar fractions
    for vf, frac in _VULGAR_MAP.items():
        raw_qty = raw_qty.replace(vf, frac)

    # Evaluate quantity — handles "1 1/2", "1/2", "2" etc.
    try:
        parts = raw_qty.split()
        qty = float(sum(Fraction(p) for p in parts))
    except (ValueError, ZeroDivisionError):
        return 0.0, "", text.strip()

    unit = UNIT_ALIASES.get(raw_unit, UNIT_ALIASES.get(raw_unit.lower(), raw_unit.lower()))
    name = name.strip(" ,.-\t")
    if not name and raw_unit:
        name = raw_unit
        unit = ""

    return qty, unit, name


def _try_convert(qty: float, from_unit: str, to_unit: str) -> float | None:
    """Attempt to convert qty from one unit to another. Returns None on failure."""
    if from_unit == to_unit:
        return qty
    key = (from_unit, to_unit)
    if key in CONVERTIBLE:
        return qty / CONVERTIBLE[key]
    key_rev = (to_unit, from_unit)
    if key_rev in CONVERTIBLE:
        return qty * CONVERTIBLE[key_rev]
    return None


def _format_qty(qty: float) -> str:
    """Render a quantity as a clean string (whole or simple fraction)."""
    if qty == 0:
        return ""
    if qty == int(qty):
        return str(int(qty))
    # Try to express as a nice fraction
    try:
        f = Fraction(qty).limit_denominator(16)
        if f.numerator > f.denominator:
            whole = f.numerator // f.denominator
            rem = f - whole
            return f"{whole} {rem}" if rem else str(whole)
        return str(f)
    except (ValueError, OverflowError):
        return f"{qty:.2f}".rstrip("0").rstrip(".")


# -- Core logic ---------------------------------------------------------------

def combine_ingredients(recipes: list[dict]) -> list[dict]:
    """Merge ingredients from multiple recipes.

    Each recipe dict should contain an 'ingredients' key (list[str]).
    Returns a sorted list of dicts: {name, qty, unit, raw_sources}.
    """
    merged: dict[str, dict] = {}  # key = lowercase name

    for recipe in recipes:
        for line in recipe.get("ingredients", []):
            qty, unit, name = _parse_quantity(line)
            key = name.lower().strip()
            if not key:
                continue

            if key in merged:
                existing = merged[key]
                if unit and existing["unit"]:
                    converted = _try_convert(qty, unit, existing["unit"])
                    if converted is not None:
                        existing["qty"] += converted
                    else:
                        # Can't convert — try the other direction
                        converted_rev = _try_convert(existing["qty"], existing["unit"], unit)
                        if converted_rev is not None:
                            existing["qty"] = converted_rev + qty
                            existing["unit"] = unit
                        else:
                            existing["qty"] += qty
                            if unit != existing["unit"]:
                                existing["unit"] = f'{existing["unit"]}+{unit}'
                else:
                    existing["qty"] += qty
                    existing["unit"] = existing["unit"] or unit
                existing["raw_sources"].append(line)
            else:
                merged[key] = {
                    "name": name,
                    "qty": qty,
                    "unit": unit,
                    "raw_sources": [line],
                }

    return sorted(merged.values(), key=lambda x: x["name"].lower())


# -- Streamlit UI -------------------------------------------------------------

_CHECKBOX_CSS = """
<style>
div[data-testid="stCheckbox"] label span {
    font-size: 1.15rem;
}
div[data-testid="stCheckbox"] label span[data-testid="stCheckboxLabel"] {
    padding-left: 0.4rem;
}
</style>
"""


def grocery_list_ui(recipes: list[dict] | None = None):
    """Render the grocery list page.

    If *recipes* is None, uses meal-plan recipes from session state.
    """
    # Inject larger-checkbox CSS once
    st.markdown(_CHECKBOX_CSS, unsafe_allow_html=True)

    # Resolve recipe list
    if recipes is None:
        meal_plan: dict[str, list] = st.session_state.get("meal_plan", {})
        recipes = [r for day_recipes in meal_plan.values() for r in day_recipes]

    if not recipes:
        st.info("No recipes in your meal plan yet. Add some from the Recipes page!")
        return

    items = combine_ingredients(recipes)

    if "grocery_checked" not in st.session_state:
        st.session_state.grocery_checked = {}

    # -- Toolbar --------------------------------------------------------------
    cols = st.columns([1, 1, 6])
    with cols[0]:
        if st.button("Select All"):
            for item in items:
                st.session_state.grocery_checked[item["name"].lower()] = True
            st.rerun()
    with cols[1]:
        if st.button("Clear All"):
            st.session_state.grocery_checked = {}
            st.rerun()

    st.markdown("---")

    # -- List -----------------------------------------------------------------
    for item in items:
        key = item["name"].lower()
        qty_str = _format_qty(item["qty"])
        unit = f" {item['unit']}" if item["unit"] else ""
        label = f"**{qty_str}{unit}** {item['name']}" if qty_str else item["name"]

        checked = st.session_state.grocery_checked.get(key, False)
        if checked:
            label = f"~~{label}~~"

        new_val = st.checkbox(
            label,
            value=checked,
            key=f"groc_{key}",
        )
        if new_val != checked:
            st.session_state.grocery_checked[key] = new_val
            st.rerun()

    # -- Summary --------------------------------------------------------------
    total = len(items)
    done = sum(1 for item in items if st.session_state.grocery_checked.get(item["name"].lower(), False))
    st.markdown("---")
    st.caption(f"{done} / {total} items checked off")
