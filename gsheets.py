import streamlit as st
from streamlit.connections import BaseConnection
import gspread
import pandas as pd

class GSheetsConnection(BaseConnection[gspread.client.Client]):
    def _connect(self, **kwargs) -> gspread.client.Client:
        # Se você configurou como [gconnections] ou usar as chaves diretas
        if "gconnections" in st.secrets:
            return gspread.service_account_from_dict(st.secrets["gconnections"])
        elif "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            # Tenta pegar as credenciais de dentro da estrutura padrão do Streamlit
            sec = st.secrets["connections"]["gsheets"]
            creds = {
                "type": sec.get("type", "service_account"),
                "project_id": sec.get("project_id"),
                "private_key_id": sec.get("private_key_id"),
                "private_key": sec.get("private_key"),
                "client_email": sec.get("client_email"),
                "client_id": sec.get("client_id"),
                "auth_uri": sec.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": sec.get("token_uri", "https://oauth2.googleapis.com/token"),
                "auth_provider_x509_cert_url": sec.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
                "client_x509_cert_url": sec.get("client_x509_cert_url")
            }
            return gspread.service_account_from_dict(creds)
        
        # Caso não ache os blocos acima, tenta carregar o dicionário completo do secrets
        return gspread.service_account_from_dict(dict(st.secrets))

    def read(self, worksheet: str, ttl: int = 0, **kwargs) -> pd.DataFrame:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        client = self._connect()
        sh = client.open_by_url(url)
        wks = sh.worksheet(worksheet)
        data = wks.get_all_records()
        return pd.DataFrame(data)

    def update(self, worksheet: str, data: pd.DataFrame, **kwargs):
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        client = self._connect()
        sh = client.open_by_url(url)
        wks = sh.worksheet(worksheet)
        wks.clear()
        wks.update([data.columns.values.tolist()] + data.fillna("").values.tolist())
        st.cache_data.clear()