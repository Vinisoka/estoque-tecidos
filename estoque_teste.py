import streamlit as st
import pandas as pd
import gsheets

st.set_page_config(page_title="Controle Estoque", layout="wide")

def check_password():
    if "perfil" not in st.session_state:
        with st.form("login_form"):
            user = st.text_input("Usuário").strip()
            pwd = st.text_input("Senha", type="password").strip()
            if st.form_submit_button("Entrar"):
                users = {"Vinicius": {"p": "011089", "r": "ADMIN"}, "Breno": {"p": "ang2767", "r": "OPERADOR"}, "Batata": {"p": "batata", "r": "OPERADOR"}}
                if user in users and users[user]["p"] == pwd:
                    st.session_state["perfil"] = users[user]["r"]
                    st.session_state["user"] = user
                    st.rerun()
                else: st.error("Acesso negado")
        return False
    return True

if not check_password(): st.stop()
conn = gsheets.GSheetsConnection(connection_name="gsheets")
df = conn.read(worksheet="Estoque")
df_hist = conn.read(worksheet="Historico")

# Removi os emojis dos textos para evitar o erro de sintaxe
menu = st.sidebar.radio("Navegação", ["Painel", "Movimentacao", "Cadastrar", "Editar Item", "Historico"])
if st.sidebar.button("Sair"): del st.session_state["perfil"]; st.rerun()

if menu == "Painel":
    st.title("Estoque")
    exibir = df.copy()
    if st.session_state["perfil"] != "ADMIN":
        exibir = exibir.drop(columns=["Preço Custo", "Preço Venda"], errors="ignore")
    st.dataframe(exibir, use_container_width=True)

elif menu == "Movimentacao":
    st.title("Lançar Movimentação")
    idx = st.selectbox("Tecido", df.index, format_func=lambda x: f"{df.loc[x, 'Tipo do Tecido']} - {df.loc[x, 'Cor do Tecido']}")
    tipo = st.radio("Operação", ["ENTRADA", "SAÍDA"])
    p = st.number_input("Peças", 0); m = st.number_input("Metros", 0.0)
    if st.button("Confirmar"):
        f = 1 if tipo == "ENTRADA" else -1
        df.loc[idx, "Peças"] += (p * f); df.loc[idx, "Metragem (m)"] += (m * f)
        conn.update(worksheet="Estoque", data=df)
        st.success("Movimentação registrada!")

elif menu == "Cadastrar":
    st.title("Novo Item")
    with st.form("cad"):
        i = st.text_input("ID"); t = st.text_input("Tipo"); c = st.text_input("Cor")
        p = st.number_input("Peças", 0); m = st.number_input("Metros", 0.0)
        pc = st.number_input("Custo", 0.0); pv = st.number_input("Venda", 0.0)
        if st.form_submit_button("Salvar"):
            novo = pd.DataFrame([{"ID": i, "Tipo do Tecido": t, "Cor do Tecido": c, "Peças": p, "Metragem (m)": m, "Preço Custo": pc, "Preço Venda": pv}])
            conn.update(worksheet="Estoque", data=pd.concat([df, novo], ignore_index=True))
            st.success("Item criado!")

elif menu == "Editar Item":
    st.title("Edição")
    if st.session_state["perfil"] != "ADMIN": st.error("Acesso restrito.")
    else:
        idx = st.selectbox("Selecione", df.index, format_func=lambda x: f"{df.loc[x, 'ID']} - {df.loc[x, 'Tipo do Tecido']}")
        with st.form("edit"):
            t = st.text_input("Tipo", df.loc[idx, "Tipo do Tecido"]); c = st.text_input("Cor", df.loc[idx, "Cor do Tecido"])
            p = st.number_input("Peças", value=int(df.loc[idx, "Peças"])); m = st.number_input("Metros", value=float(df.loc[idx, "Metragem (m)"]))
            pc = st.number_input("Preço Custo", value=float(df.loc[idx, "Preço Custo"])); pv = st.number_input("Preço Venda", value=float(df.loc[idx, "Preço Venda"]))
            if st.form_submit_button("Atualizar"):
                df.loc[idx] = [df.loc[idx, "ID"], t, c, p, m, pc, pv]
                conn.update(worksheet="Estoque", data=df); st.success("Atualizado!")

elif menu == "Historico":
    st.title("Histórico")
    st.dataframe(df_hist.iloc[::-1], use_container_width=True)