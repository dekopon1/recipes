import streamlit as st


def recipe_card(
    recipe: dict,
    on_add_to_plan: callable | None = None,
    on_archive: callable | None = None,
    on_delete: callable | None = None,
    on_unarchive: callable | None = None,
) -> None:
    """Render a single recipe as a clean, minimalist card.

    Expected recipe keys:
        title, image (or image_url), ingredients, instructions,
        and optionally url (or source_url).
    """
    title = recipe.get("title", "Untitled")
    image = recipe.get("image") or recipe.get("image_url")
    ingredients = recipe.get("ingredients", [])
    instructions = recipe.get("instructions", [])
    source = recipe.get("url") or recipe.get("source_url")
    is_archived = recipe.get("archived", False)
    recipe_id = recipe.get("id", title)

    with st.container(border=True):
        # -- Header -----------------------------------------------------------
        if is_archived:
            st.subheader(f"~~{title}~~ 📦")
        else:
            st.subheader(title)

        # -- Image ------------------------------------------------------------
        if image:
            st.image(image, use_container_width=True)

        # -- Ingredients ------------------------------------------------------
        with st.expander("Ingredients", expanded=True):
            for item in ingredients:
                st.markdown(f"- {item}")

        # -- Instructions -----------------------------------------------------
        with st.expander("Steps", expanded=False):
            for i, step in enumerate(instructions, 1):
                st.markdown(f"**{i}.** {step}")

        # -- Footer -----------------------------------------------------------
        if source:
            st.markdown(f"[View source ↗]({source})")

        btn_cols = st.columns(3)
        with btn_cols[0]:
            if on_add_to_plan and not is_archived:
                if st.button("➕ Meal Plan", key=f"add_{recipe_id}"):
                    on_add_to_plan(recipe)
        with btn_cols[1]:
            if is_archived and on_unarchive:
                if st.button("♻️ Restore", key=f"unarch_{recipe_id}"):
                    on_unarchive(recipe)
            elif on_archive:
                if st.button("📦 Archive", key=f"arch_{recipe_id}"):
                    on_archive(recipe)
        with btn_cols[2]:
            if on_delete:
                if st.button("🗑️ Delete", key=f"del_{recipe_id}"):
                    on_delete(recipe)
