import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import gsheets  # Força o uso do nosso conector local para evitar o erro do Python 3.14

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Estoque Inteligente - Tecidos", layout="wide", initial_sidebar_state="expanded")

# Limite para o alerta visual de reposição
LIMITE_ALERTA = 2

# Conexão Manual e Direta com o Google Sheets através do arquivo local
conn = gsheets.GSheetsConnection(connection_name="gsheets")

def obtener_horario_brasilia():
    fuso_brasilia = timezone(timedelta(hours=-3))
    return datetime.now(fuso_brasilia).strftime("%d/%m/%Y %H:%M:%S")

# --- 2. CARREGAMENTO DE DADOS ---
def carregar_estoque():
    try:
        df = conn.read(worksheet="Cadastro_Estoque", ttl=0)
        df = df.dropna(subset=['ID'])
        df['ID'] = df['ID'].astype(str).str.strip()
        df['Nome do Tecido'] = df['Nome do Tecido'].fillna("").astype(str).str.strip()
        df['Quantidade de Peças'] = pd.to_numeric(df['Quantidade de Peças'], errors='coerce').fillna(0).astype(int)
        df['Metragem Total'] = pd.to_numeric(df['Metragem Total'], errors='coerce').fillna(0.0).astype(float)
        
        if 'Cor' not in df.columns:
            df['Cor'] = ""
        df['Cor'] = df['Cor'].fillna("").astype(str).str.strip()
        
        return df[['ID', 'Nome do Tecido', 'Cor', 'Quantidade de Peças', 'Metragem Total']]
    except Exception as e:
        st.error(f"Erro ao carregar estoque: {e}")
        return pd.DataFrame(columns=['ID', 'Nome do Tecido', 'Cor', 'Quantidade de Peças', 'Metragem Total'])

def carregar_historico():
    try:
        df = conn.read(worksheet="Historico_Movimentacao", ttl=0)
        if df.empty:
            return pd.DataFrame(columns=['Data/Hora', 'ID', 'Nome do Tecido', 'Cor', 'Tipo', 'Peças', 'Metragem', 'Motivo'])
        df['ID'] = df['ID'].astype(str).str.strip()
        if 'Cor' not in df.columns:
            df['Cor'] = ""
        df['Cor'] = df['Cor'].fillna("").astype(str).str.strip()
        return df[['Data/Hora', 'ID', 'Nome do Tecido', 'Cor', 'Tipo', 'Peças', 'Metragem', 'Motivo']]
    except Exception:
        return pd.DataFrame(columns=['Data/Hora', 'ID', 'Nome do Tecido', 'Cor', 'Tipo', 'Peças', 'Metragem', 'Motivo'])

if 'df_estoque' not in st.session_state:
    st.session_state.df_estoque = carregar_estoque()

if 'df_historico' not in st.session_state:
    st.session_state.df_historico = carregar_historico()

def salvar_dados(novo_estoque, novo_historico):
    try:
        conn.update(worksheet="Cadastro_Estoque", data=novo_estoque)
        conn.update(worksheet="Historico_Movimentacao", data=novo_historico)
        st.session_state.df_estoque = novo_estoque
        st.session_state.df_historico = novo_historico
        st.success("⚡ Estoque sincronizado instantaneamente!")
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao salvar na nuvem: {e}")

# --- 3. MENU LATERAL ---
menu = st.sidebar.radio("Navegação Direta", [
    "📊 Painel de Controle", 
    "🔄 Lançar Movimentação",
    "➕ Cadastrar Item", 
    "📜 Histórico Geral"
])

# --- TAB 1: PAINEL DE CONTROLE ---
if menu == "📊 Painel de Controle":
    df_exibir = st.session_state.df_estoque.copy()
    
    total_pecas = df_exibir['Quantidade de Peças'].sum()
    total_metros = df_exibir['Metragem Total'].sum()
    criticos = df_exibir[df_exibir['Quantidade de Peças'] <= LIMITE_ALERTA].shape[0] if not df_exibir.empty else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Peças Totais em Loja", f"{total_pecas} un")
    col2.metric("Metragem Global", f"{total_metros:.1f} m")
    col3.metric("Avisos de Reposição", f"{criticos} itens", delta=-criticos if criticos > 0 else 0, delta_color="inverse")
    
    st.divider()
    
    c_busca, c_filtro = st.columns([3, 1])
    busca = c_busca.text_input("⚡ Busca expressa (Digite qualquer termo, ID ou Cor):").strip().lower()
    apenas_criticos = c_filtro.checkbox("⚠️ Ver apenas o que está acabando", value=False)
    
    if df_exibir.empty:
        st.info("Nenhum tecido encontrado na base de dados.")
    else:
        if apenas_criticos:
            df_exibir = df_exibir[df_exibir['Quantidade de Peças'] <= LIMITE_ALERTA]
        if busca:
            df_exibir = df_exibir[
                df_exibir['Nome do Tecido'].str.lower().str.contains(busca) | 
                df_exibir['Cor'].str.lower().str.contains(busca) |
                df_exibir['ID'].str.lower().str.contains(busca)
            ]
            
        tecidos_unicos = df_exibir['Nome do Tecido'].unique()
        
        if len(tecidos_unicos) == 0:
            st.warning("Nenhum tecido corresponde aos filtros aplicados.")
            
        for tecido in tecidos_unicos:
            df_filtrado = df_exibir[df_exibir['Nome do Tecido'] == tecido]
            sub_p = df_filtrado['Quantidade de Peças'].sum()
            sub_m = df_filtrado['Metragem Total'].sum()
            
            titulo_aba = f"🧵 {tecido.upper()} ⸻ ({sub_p} Peças | {sub_m:.1f}m)"
            
            with st.expander(titulo_aba, expanded=True):
                df_tabela = df_filtrado[['ID', 'Cor', 'Quantidade de Peças', 'Metragem Total']].copy()
                df_tabela.columns = ['ID / Código', 'Cor do Tecido', 'Peças', 'Metragem (m)']
                
                def estilizar_linhas(row):
                    return ['background-color: rgba(255, 75, 75, 0.15); color: #ff4b4b; font-weight: bold;'] * len(row) if row['Peças'] <= LIMITE_ALERTA else [''] * len(row)
                
                st.dataframe(
                    df_tabela.style.apply(estilizar_linhas, axis=1),
                    use_container_width=True, 
                    hide_index=True
                )

# --- TAB 2: LANÇAR MOVIMENTAÇÃO ---
elif menu == "🔄 Lançar Movimentação":
    st.subheader("Registrar Entrada / Saída de Tecido")
    
    if st.session_state.df_estoque.empty:
        st.info("Cadastre um item primeiro na aba 'Cadastrar Item'.")
    else:
        lista_tecidos = sorted(list(st.session_state.df_estoque['Nome do Tecido'].unique()))
        tecido_sel = st.selectbox("1. Escolha o Tecido:", lista_tecidos)
        
        df_cores_disp = st.session_state.df_estoque[st.session_state.df_estoque['Nome do Tecido'] == tecido_sel]
        lista_cores = sorted(list(df_cores_disp['Cor'].unique()))
        cor_sel = st.selectbox("2. Escolha a Cor:", lista_cores)
        
        idx = st.session_state.df_estoque[(st.session_state.df_estoque['Nome do Tecido'] == tecido_sel) & (st.session_state.df_estoque['Cor'] == cor_sel)].index[0]
        dados_item = st.session_state.df_estoque.loc[idx]
        
        st.info(f"📊 Saldo Atual de **{tecido_sel} ({cor_sel})**: {dados_item['Quantidade de Peças']} peças | {dados_item['Metragem Total']} metros")
        
        with st.form("form_movimentacao_rapida"):
            tipo_mov = st.radio("Operação:", ["ENTRADA", "SAÍDA"], horizontal=True)
            
            c1, c2 = st.columns(2)
            pecas_mov = c1.number_input("Quantidade de Peças", min_value=0, value=0, step=1)
            metro_mov = c2.number_input("Metragem (m)", min_value=0.0, value=0.0, step=0.1)
            motivo_mov = st.text_input("Observação / Destino (Opcional)")
            
            enviar_mov = st.form_submit_button("Confirmar Lançamento", use_container_width=True)
            
            if enviar_mov:
                if pecas_mov == 0 and metro_mov == 0:
                    st.warning("Por favor, preencha valores válidos para Peças ou Metragem.")
                else:
                    df_est_copia = st.session_state.df_estoque.copy()
                    qtd_atual = dados_item['Quantidade de Peças']
                    metro_atual = dados_item['Metragem Total']
                    
                    valido = True
                    if tipo_mov == "ENTRADA":
                        novo_qtd = qtd_atual + pecas_mov
                        novo_metro = metro_atual + metro_mov
                    else:
                        if pecas_mov > qtd_atual or metro_mov > metro_atual:
                            st.error("Erro: Operação cancelada! Quantidade ou Metragem de SAÍDA é maior que o saldo em estoque.")
                            valido = False
                        else:
                            novo_qtd = qtd_atual - pecas_mov
                            novo_metro = metro_atual - metro_mov
                    
                    if valido:
                        df_est_copia.at[idx, 'Quantidade de Peças'] = int(novo_qtd)
                        df_est_copia.at[idx, 'Metragem Total'] = float(novo_metro)
                        
                        nova_mov = pd.DataFrame([{'Data/Hora': obtener_horario_brasilia(), 'ID': dados_item['ID'], 'Nome do Tecido': tecido_sel, 'Cor': cor_sel, 'Tipo': tipo_mov, 'Peças': int(pecas_mov), 'Metragem': float(metro_mov), 'Motivo': motivo_mov.strip() if motivo_mov.strip() else 'Movimentação rápida'}])
                        df_hist_copia = pd.concat([nova_mov, st.session_state.df_historico], ignore_index=True)
                        salvar_dados(df_est_copia, df_hist_copia)

# --- TAB 3: CADASTRAR ITEM ---
elif menu == "➕ Cadastrar Item":
    st.subheader("Cadastrar Novo Tecido ou Adicionar Cor")
    
    ids_existentes = sorted(list(st.session_state.df_estoque['ID'].unique()))
    opcoes_id = ["[ + Criar Novo ID ]"] + ids_existentes
    selecao_id = st.selectbox("Selecione um ID ou crie um do zero:", opcoes_id)
    
    with st.form("form_novo_cadastro"):
        if selecao_id == "[ + Criar Novo ID ]":
            novo_id = st.text_input("Código / ID Único:")
            novo_nome = st.text_input("Nome do Tecido (Ex: Oxford):")
        else:
            novo_id = selecao_id
            nome_descoberto = st.session_state.df_estoque[st.session_state.df_estoque['ID'] == novo_id]['Nome do Tecido'].iloc[0]
            st.warning(f"Vinculando ao Tecido: {nome_descoberto} (ID: {novo_id})")
            novo_nome = nome_descoberto
            
        nova_cor = st.text_input("Cor do Tecido:")
        qtd_inicial = st.number_input("Estoque Inicial (Peças)", min_value=0, value=0, step=1)
        metro_inicial = st.number_input("Estoque Inicial (Metragem)", min_value=0.0, value=0.0, step=0.1)
        
        salvar_item = st.form_submit_button("Concluir Cadastro", use_container_width=True)
        
        if salvar_item:
            novo_id = novo_id.strip()
            novo_nome = novo_nome.strip()
            nova_cor = nova_cor.strip()
            
            if not novo_id or not novo_nome or not nova_cor:
                st.error("Todos os campos de texto (ID, Nome e Cor) precisam ser preenchidos!")
            else:
                df_check = st.session_state.df_estoque
                existe_duplicado = ((df_check['ID'] == novo_id) & (df_check['Cor'].fillna("").astype(str).str.lower() == nova_cor.lower())).any()
                
                if existe_duplicado:
                    st.error(f"Essa cor '{nova_cor}' já existe para o ID {novo_id}!")
                else:
                    nova_linha = pd.DataFrame([{'ID': novo_id, 'Nome do Tecido': novo_nome, 'Cor': nova_cor, 'Quantidade de Peças': int(qtd_inicial), 'Metragem Total': float(metro_inicial)}])
                    df_atualizado = pd.concat([st.session_state.df_estoque, nova_linha], ignore_index=True)
                    
                    df_hist_atualizado = st.session_state.df_historico.copy()
                    if qtd_inicial > 0 or metro_inicial > 0:
                        nova_mov = pd.DataFrame([{'Data/Hora': obtener_horario_brasilia(), 'ID': novo_id, 'Nome do Tecido': novo_nome, 'Cor': nova_cor, 'Tipo': 'ENTRADA', 'Peças': int(qtd_inicial), 'Metragem': float(metro_inicial), 'Motivo': 'Saldo Inicial de Cadastro'}])
                        df_hist_atualizado = pd.concat([nova_mov, df_hist_atualizado], ignore_index=True)
                    
                    salvar_dados(df_atualizado, df_hist_atualizado)

# --- TAB 4: HISTÓRICO GERAL ---
elif menu == "📜 Histórico Geral":
    st.subheader("Auditoria de Movimentações Recentes")
    if st.session_state.df_historico.empty:
        st.info("Nenhuma movimentação registrada.")
    else:
        st.dataframe(st.session_state.df_historico, use_container_width=True, hide_index=True)

# Sincronização manual
with st.sidebar:
    st.divider()
    if st.button("🔄 Forçar Sincronização Google"):
        st.session_state.df_estoque = carregar_estoque()
        st.session_state.df_historico = carregar_historico()
        st.rerun()