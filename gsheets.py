import streamlit as st
from streamlit.connections import BaseConnection
import gspread
import pandas as pd

class GSheetsConnection(BaseConnection[gspread.client.Client]):
    def _connect(self, **kwargs) -> gspread.client.Client:
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            sec = st.secrets["connections"]["gsheets"]
            
            # Limpa qualquer formatação quebrada que a nuvem possa causar na chave
            pkey = sec.get("private_key", "")
            if "\\n" in pkey:
                pkey = pkey.replace("\\n", "\n")
            
            # Garante que os cabeçalhos da chave existam e estejam limpos
            if "-----BEGIN PRIVATE KEY-----" not in pkey:
                pkey = "-----BEGIN PRIVATE KEY-----\n" + pkey.strip() + "\n-----END PRIVATE KEY-----"
            
            creds = {
                "type": "service_account",
                "project_id": sec.get("project_id"),
                "private_key_id": sec.get("private_key_id"),
                "private_key": pkey,
                "client_email": sec.get("client_email"),
                "client_id": sec.get("client_id"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": sec.get("client_x509_cert_url")
            }
            return gspread.service_account_from_dict(creds)
        
        return gspread.service_account_from_dict(dict(st.secrets))

    def read(self, worksheet: str, ttl: int = 0, **kwargs) -> pd.DataFrame:
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