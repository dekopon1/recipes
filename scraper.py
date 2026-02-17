from __future__ import annotations

import json
import requests
from bs4 import BeautifulSoup


def scrape_recipe(url: str) -> dict:
    """Fetch a URL, extract JSON-LD Recipe schema, and return structured data.

    Returns a dict with keys: title, ingredients, instructions, image, url.
    Raises ValueError if no Recipe schema is found.
    """
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    recipe_data = None
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue
        recipe_data = _find_recipe(data)
        if recipe_data:
            break

    if not recipe_data:
        raise ValueError(f"No Recipe JSON-LD schema found at {url}")

    instructions_raw = recipe_data.get("recipeInstructions", [])
    instructions = _parse_instructions(instructions_raw)

    image = recipe_data.get("image")
    if isinstance(image, list):
        image = image[0] if image else None
    elif isinstance(image, dict):
        image = image.get("url")

    return {
        "title": recipe_data.get("name", "Untitled"),
        "ingredients": recipe_data.get("recipeIngredient", []),
        "instructions": instructions,
        "image": image,
        "url": url,
    }


def _find_recipe(data) -> dict | None:
    """Recursively search JSON-LD data for a Recipe or object containing one."""
    if isinstance(data, dict):
        schema_type = data.get("@type", "")
        if isinstance(schema_type, list):
            schema_type = " ".join(schema_type)
        if "Recipe" in schema_type:
            return data
        # Check @graph arrays (common wrapper)
        if "@graph" in data:
            return _find_recipe(data["@graph"])
    elif isinstance(data, list):
        for item in data:
            result = _find_recipe(item)
            if result:
                return result
    return None


def _parse_instructions(raw) -> list[str]:
    """Normalise recipeInstructions into a flat list of step strings."""
    if isinstance(raw, str):
        return [raw]
    steps = []
    for item in raw:
        if isinstance(item, str):
            steps.append(item)
        elif isinstance(item, dict):
            if item.get("@type") == "HowToSection":
                steps.extend(_parse_instructions(item.get("itemListElement", [])))
            else:
                text = item.get("text", "")
                if text:
                    steps.append(text)
    return steps
