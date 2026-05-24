import streamlit as st
import pandas as pd
from datetime import datetime
import gsheets

# Configuração da página - DEVE SER A PRIMEIRA LINHA DO STREAMLIT
st.set_page_config(
    page_title="Controle de Estoque - Tecidos",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed" # Esconde o menu lateral por padrão para poupar espaço no celular
)

# 1. SISTEMA DE AUTENTICAÇÃO (LOGIN)
def check_password():
    """Retorna True se o usuário inseriu a senha correta."""
    def password_entered():
        user = st.session_state["username"].strip()
        pwd = st.session_state["password"].strip()
        
        # Base de usuários cadastrados
        usuarios_validos = {
            "Vinicius": "011089",
            "Breno": "ang2767",
            "Batata": "batata"
        }
        
        if user in usuarios_validos and usuarios_validos[user] == pwd:
            st.session_state["password_correct"] = True
            st.session_state["user_logado"] = user
            del st.session_state["password"]  # Remove a senha da memória por segurança
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        # Tela inicial de Login
        st.markdown("<h2 style='text-align: center;'>🔒 Controle de Estoque</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Insira suas credenciais para acessar o sistema</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                st.text_input("Usuário", key="username")
                st.text_input("Senha", type="password", key="password")
                st.form_submit_button("Entrar", on_click=password_entered)
            
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("❌ Usuário ou senha incorretos.")
        return False
    return True

# Se não estiver logado, para a execução do código exatamente aqui e não lê mais nada abaixo
if not check_password():
    st.stop()

# --- A PARTIR DAQUI O USUÁRIO ESTÁ LOGADO COM TOTAL SEGURANÇA ---

# Inicializa conexão com o Google Sheets
try:
    conn = gsheets.GSheetsConnection(connection_name="gsheets")
except Exception as e:
    st.error(f"Erro na conexão com o Google Sheets: {e}")
    st.stop()

# Nome das abas da planilha
ABA_ESTOQUE = "Estoque"
ABA_HISTORICO = "Historico"

# Carrega os dados da Planilha
@st.cache_data(ttl=0)
def carregar_dados():
    try:
        df_est = conn.read(worksheet=ABA_ESTOQUE)
        df_hist = conn.read(worksheet=ABA_HISTORICO)
        return df_est, df_hist
    except Exception as e:
        st.error(f"Erro ao ler tabelas: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_estoque, df_historico = carregar_dados()

# Garantir colunas obrigatórias e tipos corretos
for col in ["ID / Código", "Tipo do Tecido", "Cor do Tecido", "Peças", "Metragem (m)"]:
    if col not in df_estoque.columns:
        df_estoque[col] = ""

df_estoque["Peças"] = pd.to_numeric(df_estoque["Peças"], errors="coerce").fillna(0).astype(int)
df_estoque["Metragem (m)"] = pd.to_numeric(df_estoque["Metragem (m)"], errors="coerce").fillna(0.0)

# 2. INTERFACE E NAVEGAÇÃO COMPACTA (OTIMIZADA PARA CELULAR)
st.sidebar.markdown(f"👤 **Logado como:** `{st.session_state.get('user_logado', 'Usuário')}`")
menu = st.sidebar.radio(
    "Navegação Direta",
    ["📊 Painel de Controle", "➕ Lançar Movimentação", "📝 Cadastrar Item", "📜 Histórico Geral"]
)

# Botão de Logout na barra lateral
if st.sidebar.button("🚪 Sair do Sistema"):
    del st.session_state["password_correct"]
    if "user_logado" in st.session_state:
        del st.session_state["user_logado"]
    st.rerun()

# --- ABA 1: PAINEL DE CONTROLE ---
if menu == "📊 Painel de Controle":
    st.title("📊 Painel de Controle")
    
    # Cards de resumo empilháveis/responsivos
    pecas_totais = int(df_estoque["Peças"].sum())
    metragem_total = float(df_estoque["Metragem (m)"].sum())
    
    # Alerta de estoque baixo (menos de 20m ou 0 peças)
    itens_alerta = df_estoque[(df_estoque["Metragem (m)"] < 20) | (df_estoque["Peças"] == 0)].shape[0]
    
    c1, c2, c3 = st.columns([1, 1, 1])
    c1.metric("Peças Totais em Loja", f"{pecas_totais} un")
    c2.metric("Metragem Global", f"{metragem_total:.1f} m")
    c3.metric("Avisos de Reposição", f"{itens_alerta} itens", delta="- Alerta" if itens_alerta > 0 else "OK")
    
    st.markdown("---")
    
    # Busca expressa simplificada para celular
    busca = st.text_input("🔍 Busca rápida (Tecido, Cor ou ID):").strip().lower()
    
    ver_alerta = st.checkbox("⚠️ Ver apenas o que está acabando")
    
    df_filtrado = df_estoque.copy()
    if busca:
        df_filtrado = df_filtrado[
            df_filtrado["Tipo do Tecido"].astype(str).str.lower().str.contains(busca) |
            df_filtrado["Cor do Tecido"].astype(str).str.lower().str.contains(busca) |
            df_filtrado["ID / Código"].astype(str).str.lower().str.contains(busca)
        ]
        
    if ver_alerta:
        df_filtrado = df_filtrado[(df_filtrado["Metragem (m)"] < 20) | (df_filtrado["Peças"] == 0)]
        
    # Exibição do Estoque por Grupos (Sanfonas facilitam no celular)
    if not df_filtrado.empty:
        tecidos_unicos = df_filtrado["Tipo do Tecido"].unique()
        for tecido in tecidos_unicos:
            df_grupo = df_filtrado[df_filtrado["Tipo do Tecido"] == tecido]
            p_grupo = df_grupo["Peças"].sum()
            m_grupo = df_grupo["Metragem (m)"].sum()
            
            with st.expander(f"📦 {tecido.upper()} — ({p_grupo} Peças | {m_grupo:.1f}m)"):
                st.dataframe(
                    df_grupo[["ID / Código", "Cor do Tecido", "Peças", "Metragem (m)"]], 
                    use_container_width=True, 
                    hide_index=True
                )
    else:
        st.info("Nenhum tecido encontrado para os filtros aplicados.")

# --- ABA 2: LANÇAR MOVIMENTAÇÃO (ENTRADAS E SAÍDAS) ---
elif menu == "➕ Lançar Movimentação":
    st.title("➕ Lançar Movimentação")
    
    if df_estoque.empty:
        st.warning("Cadastre um tecido primeiro.")
    else:
        df_estoque["label"] = df_estoque["Tipo do Tecido"] + " - " + df_estoque["Cor do Tecido"] + " (" + df_estoque["ID / Código"].astype(str) + ")"
        
        with st.form("form_movimentacao"):
            item_selecionado = st.selectbox("Escolha o Tecido:", df_estoque["label"].unique())
            tipo_mov = st.radio("Tipo de Operação:", ["SAÍDA (Venda/Uso)", "ENTRADA (Reposição)"])
            
            cx, cy = st.columns(2)
            with cx:
                qnt_pecas = st.number_input("Quantidade de Peças:", min_value=0, step=1, value=0)
            with cy:
                qnt_metro = st.number_input("Metragem em Metros (m):", min_value=0.0, step=0.1, value=0.0)
                
            obs = st.text_input("Observação / Destino:")
            bt_Gravar = st.form_submit_button("Confirmar Lançamento")
            
            if bt_Gravar:
                if qnt_pecas == 0 and qnt_metro == 0.0:
                    st.error("Informe uma quantidade de peças ou metragem válida.")
                else:
                    linha_idx = df_estoque[df_estoque["label"] == item_selecionado].index[0]
                    id_codigo = df_estoque.loc[linha_idx, "ID / Código"]
                    tecido_nome = df_estoque.loc[linha_idx, "Tipo do Tecido"]
                    cor_nome = df_estoque.loc[linha_idx, "Cor do Tecido"]
                    
                    pecas_atuais = df_estoque.loc[linha_idx, "Peças"]
                    metro_atual = df_estoque.loc[linha_idx, "Metragem (m)"]
                    
                    if "SAÍDA" in tipo_mov:
                        if qnt_pecas > pecas_atuais or qnt_metro > metro_atual:
                            st.warning("Atenção: A saída é maior do que a quantidade disponível em estoque!")
                        df_estoque.loc[linha_idx, "Peças"] = max(0, pecas_atuais - qnt_pecas)
                        df_estoque.loc[linha_idx, "Metragem (m)"] = max(0.0, metro_atual - qnt_metro)
                        fator_p, fator_m = -qnt_pecas, -qnt_metro
                    else:
                        df_estoque.loc[linha_idx, "Peças"] = pecas_atuais + qnt_pecas
                        df_estoque.loc[linha_idx, "Metragem (m)"] = metro_atual + qnt_metro
                        fator_p, fator_m = qnt_pecas, qnt_metro
                    
                    nova_mov = pd.DataFrame([{
                        "Data/Hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "ID / Código": id_codigo,
                        "Tipo do Tecido": tecido_nome,
                        "Cor do Tecido": cor_nome,
                        "Tipo Movimentação": tipo_mov.split(" ")[0],
                        "Peças Movimentadas": fator_p,
                        "Metragem Movimentada (m)": fator_m,
                        "Usuário": st.session_state["user_logado"],
                        "Observação": obs
                    }])
                    
                    df_historico_novo = pd.concat([df_historico, nova_mov], ignore_index=True)
                    
                    if "label" in df_estoque.columns:
                        df_estoque.drop(columns=["label"], inplace=True)
                        
                    conn.update(worksheet=ABA_ESTOQUE, data=df_estoque)
                    conn.update(worksheet=ABA_HISTORICO, data=df_historico_novo)
                    
                    st.success("Estoque sincronizado e atualizado com sucesso!")
                    st.cache_data.clear()
                    st.rerun()

# --- ABA 3: CADASTRAR NOVO ITEM ---
elif menu == "📝 Cadastrar Item":
    st.title("📝 Cadastrar Novo Tecido")
    
    with st.form("form_cadastro"):
        novo_id = st.text_input("ID / Código Único do Tecido:").strip()
        novo_tipo = st.text_input("Nome/Tipo do Tecido (Ex: Suplex):").strip()
        nova_cor = st.text_input("Cor do Tecido:").strip()
        
        c1, c2 = st.columns(2)
        with c1:
            pecas_ini = st.number_input("Peças Iniciais:", min_value=0, step=1, value=0)
        with c2:
            metro_ini = st.number_input("Metragem Inicial (m):", min_value=0.0, step=0.1, value=0.0)
            
        bt_cadastrar = st.form_submit_button("Cadastrar no Sistema")
        
        if bt_cadastrar:
            if not novo_id or not novo_tipo or not nova_cor:
                st.error("Por favor, preencha todos os campos obrigatórios (ID, Tipo e Cor).")
            elif novo_id in df_estoque["ID / Código"].astype(str).values:
                st.error("Esse ID / Código já existe no seu estoque. Use outro identificador.")
            else:
                novo_item = pd.DataFrame([{
                    "ID / Código": novo_id,
                    "Tipo do Tecido": novo_tipo,
                    "Cor do Tecido": nova_cor,
                    "Peças": int(pecas_ini),
                    "Metragem (m)": float(metro_ini)
                }])
                
                df_estoque_novo = pd.concat([df_estoque, novo_item], ignore_index=True)
                
                if "label" in df_estoque_novo.columns:
                    df_estoque_novo.drop(columns=["label"], inplace=True)
                    
                conn.update(worksheet=ABA_ESTOQUE, data=df_estoque_novo)
                st.success(f"Tecido {novo_tipo} ({nova_cor}) adicionado com sucesso!")
                st.cache_data.clear()
                st.rerun()

# --- ABA 4: HISTÓRICO GERAL ---
elif menu == "📜 Histórico Geral":
    st.title("📜 Histórico de Movimentações")
    st.markdown("Lista detalhada de quem realizou entradas ou saídas no estoque.")
    
    if not df_historico.empty:
        st.dataframe(df_historico.iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma movimentação registrada até o momento.")