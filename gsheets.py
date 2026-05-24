import streamlit as st
from streamlit.connections import BaseConnection
import gspread
import pandas as pd

class GSheetsConnection(BaseConnection[gspread.client.Client]):
    def _connect(self, **kwargs) -> gspread.client.Client:
        # 1. Tenta ler o formato padrão de conexões do Streamlit (Mais seguro na nuvem)
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            sec = st.secrets["connections"]["gsheets"]
            creds = {
                "type": sec.get("type", "service_account"),
                "project_id": sec.get("project_id"),
                "private_key_id": sec.get("private_key_id"),
                "private_key": sec.get("private_key", "").replace("\\n", "\n"),
                "client_email": sec.get("client_email"),
                "client_id": sec.get("client_id"),
                "auth_uri": sec.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": sec.get("token_uri", "https://oauth2.googleapis.com/token"),
                "auth_provider_x509_cert_url": sec.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
                "client_x509_cert_url": sec.get("client_x509_cert_url")
            }
            return gspread.service_account_from_dict(creds)
        
        # 2. Se houver um bloco isolado [gconnections]
        if "gconnections" in st.secrets:
            return gspread.service_account_from_dict(st.secrets["gconnections"])
            
        # 3. Fallback para ambiente local
        return gspread.service_account_from_dict(dict(st.secrets))

    def read(self, worksheet: str, ttl: int = 0, **kwargs) -> pd.DataFrame:
        # Busca a URL da planilha de forma flexível
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        else:
            url = st.secrets.get("spreadsheet")
            
        client = self._connect()
        sh = client.open_by_url(url)
        wks = sh.worksheet(worksheet)
        data = wks.get_all_records()
        return pd.DataFrame(data)

    def update(self, worksheet: str, data: pd.DataFrame, **kwargs):
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        else:
            url = st.secrets.get("spreadsheet")
            
        client = self._connect()
        sh = client.open_by_url(url)
        wks = sh.worksheet(worksheet)
        wks.clear()
        wks.update([data.columns.values.tolist()] + data.fillna("").values.tolist())
        st.cache_data.clear()