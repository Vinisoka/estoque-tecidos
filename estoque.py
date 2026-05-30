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

# Constantes globais com o nome exato das abas na planilha
ABA_ESTOQUE = "Estoque"
ABA_HISTORICO = "Historico"
ABA_LINHAS = "Linhas"   

# 1. SISTEMA DE AUTENTICAÇÃO (LOGIN)
def check_password():
    """Retorna True se o usuário inseriu a senha correta."""
    def password_entered():
        user = st.session_state["username"].strip()
        pwd = st.session_state["password"].strip()
        
        # Puxa os usuários e senhas do arquivo de segredos
        usuarios_validos = st.secrets["passwords"]
        
        if user in usuarios_validos and usuarios_validos[user] == pwd:
            st.session_state["password_correct"] = True
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

# Se não estiver logado, para a execução do código exatamente aqui
if not check_password():
    st.stop()

# --- A PARTIR DAQUI O USUÁRIO ESTÁ LOGADO COM TOTAL SEGURANÇA ---

# Inicializa conexão com o Google Sheets
try:
    conn = gsheets.GSheetsConnection(connection_name="gsheets")
except Exception as e:
    st.error(f"Erro na conexão com o Google Sheets: {e}")
    st.stop()

# Carrega os dados da Planilha
@st.cache_data(ttl=5)
def carregar_dados():
    try:
        df_est = conn.read(worksheet=ABA_ESTOQUE)
        df_hist = conn.read(worksheet=ABA_HISTORICO)
        
        # Lê a aba de linhas também de forma global
        dados_lin = conn.read(worksheet=ABA_LINHAS)
        df_lin = pd.DataFrame(dados_lin)
        
        return pd.DataFrame(df_est), pd.DataFrame(df_hist), df_lin
    except Exception as e:
        st.error(f"Erro ao ler tabelas: {e}. Verifique se os nomes das abas na planilha estão corretos.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Recebe as 3 tabelas atualizadas do Sheets
df_estoque, df_historico, df_linhas = carregar_dados()

# Garantir colunas obrigatórias e tipos corretos para tecidos
for col in ["ID / Código", "Tipo do Tecido", "Cor do Tecido", "Peças", "Metragem (m)"]:
    if df_estoque.empty or col not in df_estoque.columns:
        df_estoque[col] = ""

df_estoque["Peças"] = pd.to_numeric(df_estoque["Peças"], errors="coerce").fillna(0).astype(int)
df_estoque["Metragem (m)"] = pd.to_numeric(df_estoque["Metragem (m)"], errors="coerce").fillna(0.0)

# 2. INTERFACE E NAVEGAÇÃO COMPACTA (OTIMIZADA PARA CELULAR)
st.sidebar.markdown(f"👤 **Logado como:** `Painel`")
menu = st.sidebar.radio(
    "Navegação Direta",
    ["📊 Painel de Controle", "🧵 Estoque de Linhas", "➕ Lançar Movimentação", "📝 Cadastrar Item", "📋 Histórico Geral", "⚙️ Gerenciar Estoque"]
)

# Botão de Logout na barra lateral
if st.sidebar.button("🚪 Sair do Sistema"):
    del st.session_state["password_correct"]
    if "user_logado" in st.session_state:
        del st.session_state["user_logado"]
    st.rerun()


# --- ABA: ESTOQUE DE LINHAS ---
if menu == "🧵 Estoque de Linhas":
    st.title("🧵 Controle de Estoque - Linhas")
    
    # Valida e limpa os dados da memória para exibição do Saldo (Trata linhas fantasmas da planilha)
    if df_linhas is None or df_linhas.empty:
        df_linhas_exibir = pd.DataFrame(columns=["Cor/Código", "Marca", "Quantidade de Cones"])
    else:
        df_linhas_exibir = df_linhas.dropna(subset=["Cor/Código"]).copy()
        df_linhas_exibir = df_linhas_exibir[df_linhas_exibir["Cor/Código"].astype(str).str.strip() != ""]

    # Abas internas organizadas para economizar espaço em telas mobile
    tab_saldo, tab_cadastro, tab_movimentacao = st.tabs(["📋 Saldo Atual", "📝 Cadastrar Linha", "🔄 Lançar Cones"])

    # 1. TABELA DE SALDO
    with tab_saldo:
        st.subheader("Saldo Atual de Cones")
        if df_linhas_exibir.empty:
            st.info("Nenhuma linha cadastrada ainda.")
        else:
            st.dataframe(df_linhas_exibir, use_container_width=True, hide_index=True)

    # 2. FORMULÁRIO DE CADASTRO
    with tab_cadastro:
        st.subheader("Cadastrar Nova Linha/Cor")
        with st.form("form_cadastro_linha", clear_on_submit=True):
            cor_codigo = st.text_input("Cor / Código da Linha (ex: Preto - Ricamare 2024)")
            marca_linha = st.text_input("Marca (ex: Ricamare, Setta)")
            cones_iniciais = st.number_input("Quantidade de Cones Inicial", min_value=0, step=1, value=0)
            
            btn_salvar_linha = st.form_submit_button("Salvar Linha", use_container_width=True)
            
            if btn_salvar_linha:
                texto_cor = str(cor_codigo).strip()
                texto_marca = str(marca_linha).strip()
    
                if not texto_cor or not texto_marca:
                    st.error("Por favor, preencha todos os campos obrigatórios (Cor/Código e Marca)!")
                else:
                    nova_linha_df = pd.DataFrame([{
                        "Cor/Código": texto_cor,
                        "Marca": texto_marca,
                        "Quantidade de Cones": int(cones_iniciais)
                    }])
        
                    # Lê em tempo real direto da nuvem (ttl=0 evita sobreposição de dados)
                    try:
                        dados_reais_sheets = conn.read(worksheet=ABA_LINHAS, ttl=0)
                        df_linhas_atualizado = pd.DataFrame(dados_reais_sheets)
                    except:
                        df_linhas_atualizado = pd.DataFrame(columns=["Cor/Código", "Marca", "Quantidade de Cones"])
        
                    if not df_linhas_atualizado.empty:
                        df_linhas_atualizado = df_linhas_atualizado.dropna(subset=["Cor/Código"])
                        df_linhas_atualizado = df_linhas_atualizado[df_linhas_atualizado["Cor/Código"].astype(str).str.strip() != ""]
            
                    if df_linhas_atualizado.empty:
                        df_linhas_novas = nova_linha_df
                    else:
                        df_linhas_novas = pd.concat([df_linhas_atualizado, nova_linha_df], ignore_index=True)
            
                    try:
                        conn.update(worksheet=ABA_LINHAS, data=df_linhas_novas)
                        st.success(f"🧵 Linha '{texto_cor}' cadastrada com sucesso!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as f:
                        st.error(f"Erro ao salvar na planilha: {f}")

    # 3. FORMULÁRIO DE MOVIMENTAÇÃO (ENTRADA/SAÍDA DE CONES)
    with tab_movimentacao:
        st.subheader("Registrar Entrada ou Saída de Cones")
        if df_linhas_exibir.empty:
            st.info("Cadastre pelo menos uma linha antes de lançar movimentações.")
        else:
            with st.form("form_movimentacao_linha", clear_on_submit=True):
                lista_opcoes = df_linhas_exibir.apply(lambda r: f"{r['Cor/Código']} ({r['Marca']})", axis=1).tolist()
                linha_selecionada = st.selectbox("Selecione a Linha/Cor", options=lista_opcoes)
                
                tipo_mov = st.radio("Tipo de Movimentação", ["📥 Entrada (+)", "📤 Saída (-)"], horizontal=True)
                qtd_mov = st.number_input("Quantidade de Cones", min_value=1, step=1, value=1)
                
                btn_mov_linha = st.form_submit_button("Confirmar Movimentação de Linhas", use_container_width=True)
                
                if btn_mov_linha:
                    idx_selecionado = lista_opcoes.index(linha_selecionada)
                    cor_original = df_linhas_exibir.iloc[idx_selecionado]["Cor/Código"]
                    marca_original = df_linhas_exibir.iloc[idx_selecionado]["Marca"]
                    
                    try:
                        df_linhas_reais = pd.DataFrame(conn.read(worksheet=ABA_LINHAS, ttl=0))
                    except:
                        df_linhas_reais = df_linhas_exibir.copy()
                    
                    filtro = (df_linhas_reais["Cor/Código"].astype(str).str.strip() == str(cor_original).strip()) & \
                             (df_linhas_reais["Marca"].astype(str).str.strip() == str(marca_original).strip())
                    
                    if not df_linhas_reais[filtro].empty:
                        idx_planilha = df_linhas_reais[filtro].index[0]
                        qtd_atual = int(df_linhas_reais.at[idx_planilha, "Quantidade de Cones"])
                        
                        if "Entrada" in tipo_mov:
                            novo_saldo = qtd_atual + int(qtd_mov)
                        else:
                            novo_saldo = max(0, qtd_atual - int(qtd_mov))
                        
                        df_linhas_reais.at[idx_planilha, "Quantidade de Cones"] = novo_saldo
                        
                        try:
                            conn.update(worksheet=ABA_LINHAS, data=df_linhas_reais)
                            st.success(f"🔄 Estoque atualizado! Novo saldo de '{cor_original}': {novo_saldo} cones.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao atualizar planilha: {e}")
                    else:
                        st.error("Erro ao localizar o item na planilha. Atualize a página.")


# --- ABA: PAINEL DE CONTROLE ---
elif menu == "📊 Painel de Controle":
    st.title("📊 Painel de Controle")
    
    if df_estoque.empty:
        st.info("O estoque está vazio ou os dados não foram carregados corretamente.")
    else:
        pecas_totais = int(df_estoque["Peças"].sum())
        metragem_total = float(df_estoque["Metragem (m)"].sum())
        itens_alerta = df_estoque[(df_estoque["Metragem (m)"] < 20) | (df_estoque["Peças"] == 0)].shape[0]
        
        c1, c2, c3 = st.columns([1, 1, 1])
        c1.metric("Peças Totais em Loja", f"{pecas_totais} un")
        c2.metric("Metragem Global", f"{metragem_total:.1f} m")
        c3.metric("Avisos de Reposição", f"{itens_alerta} itens", delta="- Alerta" if itens_alerta > 0 else "OK")
        
        st.markdown("---")
        
    st.subheader("📦 Saldo Atual do Estoque")
    st.markdown("Use a tabela abaixo para pesquisar, ordenar ou filtrar os rolos disponíveis.")
    
    busca = st.text_input("🔍 Busca rápida (Tecido, Cor ou ID):", "").strip().lower()
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
        
    if not df_filtrado.empty:
        st.dataframe(
            df_filtrado[["ID / Código", "Tipo do Tecido", "Cor do Tecido", "Peças", "Metragem (m)"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhum tecido encontrado para os filtros aplicados.")


# --- ABA: LANÇAR MOVIMENTAÇÃO (TECIDOS) ---
elif menu == "➕ Lançar Movimentação":
    st.title("➕ Lançar Movimentação")
    
    if df_estoque.empty or df_estoque["ID / Código"].astype(str).str.strip().eq("").all():
        st.warning("Cadastre um tecido válido primeiro.")
    else:
        df_estoque["label"] = df_estoque["Tipo do Tecido"].astype(str) + " - " + df_estoque["Cor do Tecido"].astype(str) + " (" + df_estoque["ID / Código"].astype(str) + ")"
        
        with st.form("form_movimentacao"):
            item_selecionado = st.selectbox("Escolha o Tecido:", df_estoque["label"].dropna().unique())
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
                        "Usuário": "Painel",
                        "Observação": obs
                    }])
                    
                    df_historico_novo = pd.concat([df_historico, nova_mov], ignore_index=True)
                    
                    if "label" in df_estoque.columns:
                        df_estoque.drop(columns=["label"], inplace=True)
                        
                    conn.update(worksheet=ABA_ESTOQUE, data=df_estoque)
                    conn.update(worksheet=ABA_HISTORICO, data=df_historico_novo)
                    
                    st.success("Estoque sincronizado e updated com sucesso!")
                    st.cache_data.clear()
                    st.rerun()


# --- ABA: CADASTRAR NOVO ITEM (TECIDOS) ---
elif menu == "📝 Cadastrar Item":
    st.title("📝 Cadastrar Novo Tecido por Cor")
    st.markdown("Insira o tipo e a respectiva cor do rolo. O sistema gerará o ID único automaticamente.")
    
    with st.form("form_cadastro"):
        novo_tipo = st.text_input("Nome/Tipo do Tecido (Ex: Oxford, Suplex):").strip()
        nova_cor = st.text_input("Cor do Tecido (Ex: Vermelho, Azul Bic):").strip()
        
        c1, c2 = st.columns(2)
        with c1:
            pecas_ini = st.number_input("Peças Iniciais (Rolos):", min_value=0, step=1, value=0)
        with c2:
            metro_ini = st.number_input("Metragem Inicial Total (m):", min_value=0.0, step=0.1, value=0.0)
            
        bt_cadastrar = st.form_submit_button("Cadastrar no Sistema", use_container_width=True)
        
        if bt_cadastrar:
            if not novo_tipo or not nova_cor:
                st.error("Por favor, preencha o Tipo do Tecido e a Cor.")
            else:
                duplicado = df_estoque[
                    (df_estoque["Tipo do Tecido"].astype(str).str.strip().str.lower() == novo_tipo.lower()) & 
                    (df_estoque["Cor do Tecido"].astype(str).str.strip().str.lower() == nova_cor.lower())
                ]
                
                if not duplicado.empty:
                    st.error(f"⚠️ O item '{novo_tipo} - {nova_cor}' já está cadastrado no sistema!")
                else:
                    try:
                        ids_numericos = pd.to_numeric(df_estoque["ID / Código"], errors="coerce").dropna()
                        proximo_id = int(ids_numericos.max() + 1) if not ids_numericos.empty else 1
                    except:
                        proximo_id = len(df_estoque) + 1
                    
                    novo_item = pd.DataFrame([{
                        "ID / Código": proximo_id,
                        "Tipo do Tecido": novo_tipo,
                        "Cor do Tecido": nova_cor,
                        "Peças": int(pecas_ini),
                        "Metragem (m)": float(metro_ini)
                    }])
                    
                    if df_estoque.empty or df_estoque["ID / Código"].astype(str).str.strip().eq("").all():
                        df_estoque_novo = novo_item
                    else:
                        df_estoque_novo = pd.concat([df_estoque, novo_item], ignore_index=True)
                    
                    if "label" in df_estoque_novo.columns:
                        df_estoque_novo.drop(columns=["label"], inplace=True)
                        
                    conn.update(worksheet=ABA_ESTOQUE, data=df_estoque_novo)
                    st.success(f"🎉 '{novo_tipo} - {nova_cor}' cadastrado com sucesso! ID Gerado: {proximo_id}")
                    st.cache_data.clear()
                    st.rerun()


# --- ABA: HISTÓRICO GERAL ---
elif menu == "📋 Histórico Geral":
    st.title("📜 Histórico de Movimentações")
    st.markdown("Lista detalhada de quem realizou entradas ou saídas no estoque.")
    
    if not df_historico.empty:
        st.dataframe(df_historico.iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma movimentação registrada até o momento.")


# --- ABA: GERENCIAR ESTOQUE ---
elif menu == "⚙️ Gerenciar Estoque":
    st.title("⚙️ Gerenciar Itens do Estoque")
    st.markdown("Use esta tela para corrigir nomes e cores ou remover itens do sistema diretamente na planilha.")

    if not df_estoque.empty:
        df_estoque["Identificador"] = df_estoque["Tipo do Tecido"].astype(str) + " - " + df_estoque["Cor do Tecido"].astype(str)
        
        item_selecionado = st.selectbox(
            "🔍 Selecione o item que deseja gerenciar:", 
            df_estoque["Identificador"].dropna().unique()
        )
        
        dados_tecido = df_estoque[df_estoque["Identificador"] == item_selecionado].iloc[0]
        
        st.divider()
        col_editar, col_excluir = st.columns(2)
        
        with col_editar:
            st.subheader("📝 Editar Dados")
            novo_tipo = st.text_input("Tipo do Tecido:", value=dados_tecido["Tipo do Tecido"])
            nova_cor = st.text_input("Cor do Tecido:", value=dados_tecido["Cor do Tecido"])
            
            if st.button("💾 Salvar Alterações", use_container_width=True):
                if novo_tipo.strip() == "" or nova_cor.strip() == "":
                    st.error("O tipo e a cor não podem ficar em branco.")
                else:
                    with st.spinner("Atualizando na planilha..."):
                        idx = df_estoque[df_estoque["Identificador"] == item_selecionado].index[0]
                        df_estoque.loc[idx, "Tipo do Tecido"] = novo_tipo.strip()
                        df_estoque.loc[idx, "Cor do Tecido"] = nova_cor.strip()
                        
                        df_salvar = df_estoque.copy()
                        if "Identificador" in df_salvar.columns:
                            df_salvar.drop(columns=["Identificador"], inplace=True)
                        if "label" in df_salvar.columns:
                            df_salvar.drop(columns=["label"], inplace=True)
                            
                        conn.update(worksheet=ABA_ESTOQUE, data=df_salvar)
                        st.success(f"🎉 Alterações salvas com sucesso!")
                        st.cache_data.clear()
                        st.rerun()

        with col_excluir:
            st.subheader("🚨 Excluir Item")
            st.warning("Atenção: A exclusão removerá este rolo/cor permanentemente do saldo.")
            
            confirmar = st.checkbox(f"Confirmo que desejo excluir permanentemente o item {item_selecionado}")
            
            if st.button("🗑️ Excluir Item", type="primary", use_container_width=True, disabled=not confirmar):
                with st.spinner("Removendo da planilha..."):
                    df_estoque_novo = df_estoque[df_estoque["Identificador"] != item_selecionado].copy()
                    
                    if "Identificador" in df_estoque_novo.columns:
                        df_estoque_novo.drop(columns=["Identificador"], inplace=True)
                    if "label" in df_estoque_novo.columns:
                        df_estoque_novo.drop(columns=["label"], inplace=True)
                        
                    conn.update(worksheet=ABA_ESTOQUE, data=df_estoque_novo)
                    st.success(f"🗑️ '{item_selecionado}' foi removido do estoque.")
                    st.cache_data.clear()
                    st.rerun()
    else:
        st.info("Nenhum tecido encontrado para gerenciar.")