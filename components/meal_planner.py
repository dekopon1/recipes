from datetime import date, timedelta

import streamlit as st

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAYS_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _init_state():
    """Ensure session-state keys exist."""
    if "meal_plan" not in st.session_state:
        st.session_state.meal_plan = {}  # date_str -> list[dict]
    if "planner_week_offset" not in st.session_state:
        st.session_state.planner_week_offset = 0


def _two_week_dates(offset: int = 0) -> list[date]:
    """Return 14 dates (Mon–Sun × 2) starting from the given week offset."""
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [monday + timedelta(days=i) for i in range(14)]


def _date_key(d: date) -> str:
    return d.isoformat()


def _get_meals(d: date) -> list[dict]:
    return st.session_state.meal_plan.get(_date_key(d), [])


def _set_meals(d: date, meals: list[dict]):
    st.session_state.meal_plan[_date_key(d)] = meals


def add_to_meal_plan(recipe: dict, target_date: date | None = None):
    """Add a recipe to a specific date (defaults to today)."""
    _init_state()
    if target_date is None:
        target_date = date.today()
    key = _date_key(target_date)
    st.session_state.meal_plan.setdefault(key, []).append(recipe)


def meal_planner_ui():
    """Render the two-week meal planner grid with move controls."""
    _init_state()

    week_offset = st.session_state.planner_week_offset
    dates = _two_week_dates(week_offset)
    today = date.today()

    # -- Toolbar --------------------------------------------------------------
    toolbar = st.columns([1, 1, 1, 3])
    with toolbar[0]:
        if st.button("← Prev"):
            st.session_state.planner_week_offset -= 1
            st.rerun()
    with toolbar[1]:
        if st.button("Today"):
            st.session_state.planner_week_offset = 0
            st.rerun()
    with toolbar[2]:
        if st.button("Next →"):
            st.session_state.planner_week_offset += 1
            st.rerun()
    with toolbar[3]:
        st.markdown(
            f"**{dates[0].strftime('%b %d')} – {dates[13].strftime('%b %d, %Y')}**"
        )

    # -- Render two rows of 7 columns ----------------------------------------
    for week in range(2):
        week_dates = dates[week * 7 : (week + 1) * 7]
        st.markdown("---")
        cols = st.columns(7)
        for i, d in enumerate(week_dates):
            with cols[i]:
                is_today = d == today
                header = f"**{DAYS[i]}**  \n{d.strftime('%b %d')}"
                if is_today:
                    header = f"📍 {header}"
                st.markdown(header)

                meals = _get_meals(d)
                if meals:
                    for idx, r in enumerate(meals):
                        with st.container(border=True):
                            st.caption(r.get("title", "Untitled"))

                            btn_cols = st.columns(2)
                            # -- Move to another day --
                            with btn_cols[0]:
                                new_date = st.date_input(
                                    "Move to",
                                    value=d,
                                    label_visibility="collapsed",
                                    key=f"mv_{_date_key(d)}_{idx}",
                                )
                                if new_date != d:
                                    # Remove from current day
                                    current = _get_meals(d)
                                    moved = current.pop(idx)
                                    _set_meals(d, current)
                                    # Add to target day
                                    add_to_meal_plan(moved, new_date)
                                    st.rerun()
                            # -- Remove --
                            with btn_cols[1]:
                                if st.button("✕", key=f"rm_{_date_key(d)}_{idx}"):
                                    current = _get_meals(d)
                                    current.pop(idx)
                                    _set_meals(d, current)
                                    st.rerun()
                else:
                    st.caption("No meals")

    # -- Clear fortnight ------------------------------------------------------
    st.markdown("---")
    if st.button("🗑️ Clear these two weeks"):
        for d in dates:
            st.session_state.meal_plan.pop(_date_key(d), None)
        st.rerun()
