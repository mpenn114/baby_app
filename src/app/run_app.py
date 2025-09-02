import streamlit as st
from src.app.ui import display_bowels, display_drinking, display_sleeping


def run_app():
    """
    Run the Streamlit app
    """
    st.set_page_config(page_title="Archie App", layout="wide")
    st.markdown(
        "<h1 style='text-align: center; color: #FF80AB;'>My First App</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h4 style='text-align: center;'>Archie Penn: 2025</h4>", unsafe_allow_html=True
    )
    st.markdown("_____________")
    pages = {"Bowels": "💩", "Sleeping": "😴", "Drinking": "🍼"}
    selected_page = st.sidebar.selectbox(
        "Choose Page", pages.keys(), format_func=lambda x: f"{pages.get(x)} {x}"
    )

    if selected_page == "Bowels":
        display_bowels()
    elif selected_page == "Sleeping":
        display_sleeping()
    else:
        display_drinking()
