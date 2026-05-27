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

# 1. SISTEMA DE AUTENTICAÇÃO (LOGIN)
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
@st.cache_data(ttl=0)
def carregar_dados():
    try:
        df_est = conn.read(worksheet=ABA_ESTOQUE)
        df_hist = conn.read(worksheet=ABA_HISTORICO)
        return df_est, df_hist
    except Exception as e:
        st.error(f"Erro ao ler tabelas: {e}. Verifique se os nomes das abas na planilha estão corretos (Estoque e Historico).")
        return pd.DataFrame(), pd.DataFrame()

df_estoque, df_historico = carregar_dados()

# Garantir colunas obrigatórias e tipos corretos
for col in ["ID / Código", "Tipo do Tecido", "Cor do Tecido", "Peças", "Metragem (m)"]:
    if df_estoque.empty or col not in df_estoque.columns:
        df_estoque[col] = ""

df_estoque["Peças"] = pd.to_numeric(df_estoque["Peças"], errors="coerce").fillna(0).astype(int)
df_estoque["Metragem (m)"] = pd.to_numeric(df_estoque["Metragem (m)"], errors="coerce").fillna(0.0)

# 2. INTERFACE E NAVEGAÇÃO COMPACTA (OTIMIZADA PARA CELULAR)
st.sidebar.markdown(f"👤 **Logado como:** `{st.session_state.get('user_logado', 'Usuário')}`")
menu = st.sidebar.radio(
    "Navegação Direta",
    ["📊 Painel de Controle", "➕ Lançar Movimentação", "📝 Cadastrar Item", "📜 Histórico Geral", "⚙️ Gerenciar Estoque"]
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
        
       # 2. Filtros e Tabela Interativa Global
    st.subheader("📦 Saldo Atual do Estoque")
    st.markdown("Use a tabela abaixo para pesquisar, ordenar ou filtrar os rolos disponíveis.")
    
    # Seus filtros originais mantidos e integrados
    busca = st.text_input("🔍 Busca rápida (Tecido, Cor ou ID):", "").strip().lower()
    ver_alerta = st.checkbox("⚠️ Ver apenas o que está acabando")
    
    df_filtrado = df_estoque.copy()
    
    # Aplica a busca por Tipo, Cor ou ID
    if busca:
        df_filtrado = df_filtrado[
            df_filtrado["Tipo do Tecido"].astype(str).str.lower().str.contains(busca) | 
            df_filtrado["Cor do Tecido"].astype(str).str.lower().str.contains(busca) | 
            df_filtrado["ID / Código"].astype(str).str.lower().str.contains(busca)
        ]
        
    # Aplica o filtro de alerta
    if ver_alerta:
        df_filtrado = df_filtrado[(df_filtrado["Metragem (m)"] < 20) | (df_filtrado["Peças"] == 0)]
        
    # Exibe os dados de forma rica e interativa
    if not df_filtrado.empty:
        st.dataframe(
            df_filtrado[["ID / Código", "Tipo do Tecido", "Cor do Tecido", "Peças", "Metragem (m)"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhum tecido encontrado para os filtros aplicados.")

# --- ABA 2: LANÇAR MOVIMENTAÇÃO (ENTRADAS E SAÍDAS) ---
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

# --- ABA 3: CADASTRAR NOVO ITEM (COM ID AUTOMÁTICO POR COR) ---
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
                # 1. Validação inteligente contra duplicados (evita cadastrar o mesmo tipo com a mesma cor)
                duplicado = df_estoque[
                    (df_estoque["Tipo do Tecido"].astype(str).str.strip().str.lower() == novo_tipo.lower()) & 
                    (df_estoque["Cor do Tecido"].astype(str).str.strip().str.lower() == nova_cor.lower())
                ]
                
                if not duplicado.empty:
                    st.error(f"⚠️ O item '{novo_tipo} - {nova_cor}' já está cadastrado no sistema! Acesse 'Lançar Movimentação' para adicionar mais rolos/metragem a ele.")
                else:
                    # 2. Geração automática do próximo ID sequencial
                    try:
                        # Extrai os números de ID atuais limpando valores inválidos
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
                    
                    # Se a planilha estava vazia, cria um dataframe novo direto
                    if df_estoque.empty or df_estoque["ID / Código"].astype(str).str.strip().eq("").all():
                        df_estoque_novo = novo_item
                    else:
                        df_estoque_novo = pd.concat([df_estoque, novo_item], ignore_index=True)
                    
                    if "label" in df_estoque_novo.columns:
                        df_estoque_novo.drop(columns=["label"], inplace=True)
                        
                    # Envia para o banco de dados
                    conn.update(worksheet=ABA_ESTOQUE, data=df_estoque_novo)
                    st.success(f"🎉 '{novo_tipo} - {nova_cor}' cadastrado com sucesso! ID Gerado: {proximo_id}")
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
 # --- ABA 5: GERENCIAR ESTOQUE (EDITAR / EXCLUIR) ---
elif menu == "⚙️ Gerenciar Estoque":
    st.title("⚙️ Gerenciar Itens do Estoque")
    st.markdown("Use esta tela para corrigir nomes e cores ou remover itens do sistema diretamente na planilha.")

    if not df_estoque.empty:
        # Cria uma combinação de Tipo + Cor para o usuário identificar o item exato
        df_estoque["Identificador"] = df_estoque["Tipo do Tecido"] + " - " + df_estoque["Cor do Tecido"]
        
        # Seleção do item que será alterado
        item_selecionado = st.selectbox(
            "🔍 Selecione o item que deseja gerenciar:", 
            df_estoque["Identificador"].unique()
        )
        
        # Puxa os dados atuais do item selecionado
        dados_tecido = df_estoque[df_estoque["Identificador"] == item_selecionado].iloc[0]
        
        st.divider()
        
        # Cria duas colunas na tela: uma para editar, outra para excluir
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
                        # Localiza a linha combinando o Tipo antigo e a Cor antiga
                        # Buscamos pelas colunas B (Tipo) e C (Cor) na planilha
                        try:
                            # Procura a linha onde o Tipo e a Cor batem perfeitamente
                            todas_linhas = sheet_estoque.get_all_records()
                            linha_index = None
                            for i, linha_dados in enumerate(todas_linhas, start=2):
                                if (str(linha_dados.get("Tipo do Tecido")) == str(dados_tecido["Tipo do Tecido"]) and 
                                    str(linha_dados.get("Cor do Tecido")) == str(dados_tecido["Cor do Tecido"])):
                                    linha_index = i
                                    break
                            
                            if linha_index:
                                # Atualiza o Tipo na Coluna B (2) e a Cor na Coluna C (3)
                                sheet_estoque.update_cell(linha_index, 2, novo_tipo.strip())
                                sheet_estoque.update_cell(linha_index, 3, nova_cor.strip())
                                
                                st.success(f"🎉 '{item_selecionado}' atualizado com sucesso!")
                                st.cache_data.clear() # Limpa o cache para recarregar a planilha
                                st.rerun()
                            else:
                                st.error("Erro ao localizar a linha exata deste item na planilha.")
                        except Exception as e:
                            st.error(f"Erro na conexão com a planilha: {e}")

        with col_excluir:
            st.subheader("🚨 Excluir Item")
            st.warning("Atenção: A exclusão removerá este rolo/cor permanentemente do saldo.")
            
            # Caixa de confirmação para evitar cliques por acidente
            confirmar = st.checkbox(f"Confirmo que desejo excluir permanentemente o item {item_selecionado}")
            
            if st.button("🗑️ Excluir Item", type="primary", use_container_width=True, disabled=not confirmar):
                with st.spinner("Removendo da planilha..."):
                    try:
                        todas_linhas = sheet_estoque.get_all_records()
                        linha_index = None
                        for i, linha_dados in enumerate(todas_linhas, start=2):
                            if (str(linha_dados.get("Tipo do Tecido")) == str(dados_tecido["Tipo do Tecido"]) and 
                                str(linha_dados.get("Cor do Tecido")) == str(dados_tecido["Cor do Tecido"])):
                                linha_index = i
                                break
                        
                        if linha_index:
                            sheet_estoque.delete_rows(linha_index) # Deleta a linha inteira na planilha
                            
                            st.success(f"🗑️ '{item_selecionado}' foi removido do estoque.")
                            st.cache_data.clear() # Limpa o cache para atualizar as telas
                            st.rerun()
                        else:
                            st.error("Erro ao localizar o item para exclusão.")
                    except Exception as e:
                        st.error(f"Erro ao deletar na planilha: {e}")
    else:
        st.info("Nenhum tecido encontrado para gerenciar.")