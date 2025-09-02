from google.oauth2 import service_account
from google.cloud.bigquery import Client
import streamlit as st


@st.cache_resource()
def bq_client() -> Client:
    """
    Get the GBQ client, authenticated via a service account
    """
    sa_info = st.secrets["google_service_account"]
    credentials = service_account.Credentials.from_service_account_info(sa_info)
    client = Client(credentials=credentials, project=credentials.project_id)

    return client
