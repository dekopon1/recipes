import streamlit as st

from components.meal_planner import meal_planner_ui, add_to_meal_plan
from components.grocery_list import grocery_list_ui
from components.recipe_card import recipe_card
from scraper import scrape_recipe
from db import RecipeDB

st.set_page_config(page_title="Recipes", page_icon="🍽️", layout="wide")

with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- Sidebar Navigation ---
st.sidebar.title("🍽️ Recipes")
page = st.sidebar.radio("Navigate", ["Recipes", "Meal Planner", "Grocery List"])

st.sidebar.markdown("---")
st.sidebar.caption("© 2026 Recipes App")

# --- Database (cached so it persists across reruns) ---
@st.cache_resource
def get_db():
    return RecipeDB()

db = get_db()

# --- Pages ---
if page == "Recipes":
    st.header("Recipes")

    # -- Import a recipe from URL --
    with st.container(border=True):
        st.subheader("Import a Recipe")
        url = st.text_input("Paste a recipe URL", placeholder="https://www.example.com/recipe/...")
        if st.button("Import", disabled=not url):
            with st.spinner("Scraping recipe..."):
                try:
                    recipe = scrape_recipe(url)
                    saved = db.save_recipe(recipe)
                    st.success(f"Saved **{saved['title']}**!")
                    st.cache_data.clear()
                except ValueError as e:
                    st.error(f"Could not find a recipe on that page: {e}")
                except Exception as e:
                    st.error(f"Something went wrong: {e}")

    st.markdown("---")

    # -- Search & filter bar --
    filter_cols = st.columns([3, 1])
    with filter_cols[0]:
        search_query = st.text_input(
            "🔍 Search recipes", placeholder="Type to search by title...",
            label_visibility="collapsed",
        )
    with filter_cols[1]:
        show_archived = st.checkbox("Show archived")

    # -- Load recipes --
    @st.cache_data(ttl=10)
    def load_recipes(_query: str, _include_archived: bool):
        if _query:
            return db.search_recipes(_query, include_archived=_include_archived)
        return db.list_recipes(include_archived=_include_archived)

    recipes = load_recipes(search_query, show_archived)

    # -- Callbacks --
    def _archive(r):
        db.archive_recipe(r["id"])
        st.cache_data.clear()
        st.toast(f"Archived **{r['title']}**")
        st.rerun()

    def _unarchive(r):
        db.unarchive_recipe(r["id"])
        st.cache_data.clear()
        st.toast(f"Restored **{r['title']}**")
        st.rerun()

    def _delete(r):
        db.delete_recipe(r["id"])
        st.cache_data.clear()
        st.toast(f"Deleted **{r['title']}**")
        st.rerun()

    # -- Display recipes --
    if recipes:
        cols = st.columns(2)
        for i, r in enumerate(recipes):
            with cols[i % 2]:
                recipe_card(
                    r,
                    on_add_to_plan=lambda r=r: add_to_meal_plan(r),
                    on_archive=_archive,
                    on_unarchive=_unarchive,
                    on_delete=_delete,
                )
    else:
        st.info("No recipes found." if search_query else "No recipes yet. Import one above!")

elif page == "Meal Planner":
    st.header("Meal Planner")
    meal_planner_ui()

elif page == "Grocery List":
    st.header("Grocery List")
    grocery_list_ui()
