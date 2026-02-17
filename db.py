import json
import os
from uuid import uuid4

import httpx
from dotenv import load_dotenv

load_dotenv()


class RecipeDB:
    """Thin wrapper around Supabase REST API for the recipes table."""

    TABLE = "recipes"

    def __init__(self, url: str | None = None, key: str | None = None):
        self.url = (url or os.environ["SUPABASE_URL"]).rstrip("/")
        self.key = key or os.environ["SUPABASE_KEY"]
        self.rest_url = f"{self.url}/rest/v1"
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # -- writes ---------------------------------------------------------------

    def save_recipe(self, recipe: dict) -> dict:
        """Insert a recipe and return the created row.

        Expects a dict with: title, ingredients, instructions,
        image_url, source_url, and optionally tags.
        A UUID is generated automatically if 'id' is not provided.
        """
        row = {
            "id": recipe.get("id", str(uuid4())),
            "title": recipe["title"],
            "ingredients": recipe["ingredients"],
            "instructions": recipe["instructions"],
            "image_url": recipe.get("image_url") or recipe.get("image"),
            "source_url": recipe.get("source_url") or recipe.get("url"),
            "tags": recipe.get("tags", []),
        }
        resp = httpx.post(
            f"{self.rest_url}/{self.TABLE}",
            headers=self.headers,
            content=json.dumps(row),
        )
        resp.raise_for_status()
        return resp.json()[0]

    # -- reads ----------------------------------------------------------------

    def list_recipes(
        self, limit: int = 50, offset: int = 0, include_archived: bool = False,
    ) -> list[dict]:
        """Return a paginated list of recipes ordered by title."""
        params: dict = {"order": "title.asc", "select": "*"}
        if not include_archived:
            params["archived"] = "eq.false"
        resp = httpx.get(
            f"{self.rest_url}/{self.TABLE}",
            headers={**self.headers, "Range": f"{offset}-{offset + limit - 1}"},
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    def get_recipe(self, recipe_id: str) -> dict | None:
        """Fetch a single recipe by its UUID. Returns None if not found."""
        resp = httpx.get(
            f"{self.rest_url}/{self.TABLE}",
            headers={**self.headers, "Accept": "application/vnd.pgrst.object+json"},
            params={"id": f"eq.{recipe_id}", "select": "*"},
        )
        if resp.status_code == 406:  # Not found (no rows)
            return None
        resp.raise_for_status()
        return resp.json()

    def search_recipes(self, query: str, include_archived: bool = False) -> list[dict]:
        """Search recipes by title (case-insensitive partial match)."""
        params = {
            "title": f"ilike.*{query}*",
            "order": "title.asc",
            "select": "*",
        }
        if not include_archived:
            params["archived"] = "eq.false"
        resp = httpx.get(
            f"{self.rest_url}/{self.TABLE}",
            headers=self.headers,
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    # -- updates / deletes ----------------------------------------------------

    def archive_recipe(self, recipe_id: str) -> dict:
        """Soft-delete: set archived = true."""
        resp = httpx.patch(
            f"{self.rest_url}/{self.TABLE}",
            headers=self.headers,
            params={"id": f"eq.{recipe_id}"},
            content=json.dumps({"archived": True}),
        )
        resp.raise_for_status()
        return resp.json()[0]

    def unarchive_recipe(self, recipe_id: str) -> dict:
        """Restore an archived recipe."""
        resp = httpx.patch(
            f"{self.rest_url}/{self.TABLE}",
            headers=self.headers,
            params={"id": f"eq.{recipe_id}"},
            content=json.dumps({"archived": False}),
        )
        resp.raise_for_status()
        return resp.json()[0]

    def delete_recipe(self, recipe_id: str) -> None:
        """Permanently delete a recipe."""
        resp = httpx.delete(
            f"{self.rest_url}/{self.TABLE}",
            headers=self.headers,
            params={"id": f"eq.{recipe_id}"},
        )
        resp.raise_for_status()
