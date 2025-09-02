import streamlit as st
from src.clients.bigquery_client import bq_client


def display_bowels():
    """
    Display the bowels page
    """
    st.markdown("<h1 style='text-align: center;'>Bowels 💩</h1>", unsafe_allow_html=True)
    st.write(get_nappies_data())


def get_nappies_data():
    """
    Get the nappies data from GBQ
    """
    client = bq_client()
    return client.query("SELECT * FROM archie-baby-app.baby_app.nappies").to_dataframe()
