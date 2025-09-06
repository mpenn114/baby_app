import streamlit as st
from src.app.ui import display_bowels, display_drinking, display_sleeping
import matplotlib.pyplot as plt
from src.cfg.colour_config import ColourConfig
from matplotlib import font_manager

COLOURS = ColourConfig()


def run_app():
    """
    Run the Streamlit app
    """
    # Set up the app
    verify_user()

    # Add configs
    st.set_page_config(page_title="Archie App", layout="wide")
    get_font()
    plt.rcParams.update(
        {
            "legend.facecolor": COLOURS.YELLOW_HEX,
            "legend.edgecolor": COLOURS.BROWN_HEX,
            "legend.labelcolor": COLOURS.BROWN_HEX,
            "axes.facecolor": COLOURS.BLUE_HEX,
            "figure.facecolor": COLOURS.YELLOW_HEX,
        }
    )

    # Create title and subtitle
    st.markdown(
        "<h1 style='text-align: center;'>My First App</h1>",
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


def verify_user():
    """
    Verify a user of the app using the query params
    """
    # Allow for local running
    if st.secrets.get('environment',None) == 'dev':
        return
    
    if (
        "password" in st.query_params
        and st.query_params["password"] == st.secrets["password"]
    ):
        return

    st.error("Unauthorised user!")
    st.stop()

def get_font():
    """
    Get the font
    """
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playpen+Sans&display=swap');

    html, body, [class*="css"] {
        font-family: 'Playpen Sans', cursive !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
    # Add a TTF file to matplotlib’s font manager
    font_path = "src/cfg/fonts/playpen_sans.ttf"
    font_manager.fontManager.addfont(font_path)
