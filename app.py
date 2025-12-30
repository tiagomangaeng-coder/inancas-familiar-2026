import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from st_supabase_connection import SupabaseConnection

# --- Configuração da Página ---
st.set_page_config(page_title="Finanças 2026", layout="wide", page_icon="💰")

# --- Conexão com Supabase ---
# O Streamlit gerencia a conexão e o cache automaticamente
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error("Erro ao conectar no Supabase. Verifique os Secrets.")
    st.stop()

# --- Funções de Banco de Dados (CRUD) ---
def get_data(table_name):
    return conn.query("*", table=table_name, ttl=0).execute().data

def add_financa(data, tipo, cat, desc, val, resp):
    try:
        conn.table("financas").insert({
            "data": data.strftime("%Y-%m-%d"),
            "tipo": tipo,
            "categoria": cat,
            "descricao": desc,
            "valor": val,
            "responsavel": resp
        }).execute()
        st.success("Registro adicionado!")
        st.cache_data.clear() # Limpa cache para atualizar tabela
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def delete_financa(ids_to_delete):
    for _id in ids_to_delete:
        conn.table("financas").delete().eq("id", _id).execute()
    st.success("Registros excluídos!")
    st.cache_data.clear()

def add_aux(table, nome):
    try:
        conn.table(table).insert({"nome": nome}).execute()
        st.success(f"{nome} adicionado!")
    except:
        st.warning("Item já existe ou erro na inserção.")

# --- Interface Principal ---
st.title("📊 Controle Familiar 2026")

# Abas substituindo o Notebook do Tkinter
tab_dados, tab_dash, tab_config = st.tabs(["📝 Registros", "📈 Dashboard", "⚙️ Configuração"])

# Carregar dados auxiliares
try:
    df_cats = pd.DataFrame(get_data("categorias"))
    lista_cats = df_cats['nome'].tolist() if not df_cats.empty else ["Geral"]
    
    df_resps = pd.DataFrame(get_data("responsaveis"))
    lista_resps = df_resps['nome'].tolist() if not df_resps.empty else ["Geral"]
except:
    lista_cats = ["Geral"]
    lista_resps = ["Geral"]

# ================= TAB 1: REGISTROS =================
with tab_dados:
    with st.expander("➕ Novo Lançamento", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            data_in = st.date_input("Data", datetime.today())
            tipo_in = st.selectbox("Tipo", ["Despesa", "Receita"])
        with col2:
            cat_in = st.selectbox("Categoria", lista_cats)
            valor_in = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        with col3:
            resp_in = st.selectbox("Responsável", lista_resps)
            desc_in = st.text_input("Descrição")

        if st.button("Salvar Lançamento", use_container_width=True):
            if not desc_in:
                st.warning("Preencha a descrição.")
            else:
                add_financa(data_in, tipo_in, cat_in, desc_in, valor_in, resp_in)
                st.rerun()

    st.divider()
    
    # Tabela Interativa (Substitui Treeview)
    st.subheader("Histórico")
    
    # Busca dados
    rows = get_data("financas")
    if rows:
        df = pd.DataFrame(rows)
        # Formatações para exibição
        df['data'] = pd.to_datetime(df['data'])
        
        # Filtro rápido na tabela
        col_f1, col_f2 = st.columns(2)
        filtro_mes = col_f1.selectbox("Filtrar Mês", ["Todos"] + list(range(1, 13)), index=0)
        
        df_show = df.copy()
        if filtro_mes != "Todos":
            df_show = df_show[df_show['data'].dt.month == int(filtro_mes)]

        df_show = df_show.sort_values(by='data', ascending=False)

        # Editor de dados (Permite apagar linhas selecionando)
        event = st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            selection_mode="multi-row",
            on_select="rerun",
            column_config={
                "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "id": None  # Ocultar ID
            }
        )
        
        # Lógica de exclusão baseada na seleção da tabela
        if len(event.selection.rows) > 0:
            ids_selecionados = df_show.iloc[event.selection.rows]['id'].tolist()
            st.error(f"Você selecionou {len(ids_selecionados)} itens.")
            if st.button("🗑️ Excluir Selecionados"):
                delete_financa(ids_selecionados)
                st.rerun()
    else:
        st.info("Nenhum dado lançado ainda.")

# ================= TAB 2: DASHBOARD =================
with tab_dash:
    rows = get_data("financas")
    if rows:
        df = pd.DataFrame(rows)
        df['data'] = pd.to_datetime(df['data'])
        
        # Filtros do Dashboard
        c1, c2, c3 = st.columns(3)
        ano_sel = c1.selectbox("Ano", [2024, 2025, 2026], index=2)
        mes_sel = c2.selectbox("Mês", ["Todos"] + list(range(1, 13)))
        resp_sel = c3.selectbox("Filtrar Responsável", ["Todos"] + lista_resps)
        
        # Aplicar Filtros
        df_filtered = df[df['data'].dt.year == ano_sel]
        if mes_sel != "Todos":
            df_filtered = df_filtered[df_filtered['data'].dt.month == int(mes_sel)]
        if resp_sel != "Todos":
            df_filtered = df_filtered[df_filtered['responsavel'] == resp_sel]
            
        # Métricas (Cards)
        receita = df_filtered[df_filtered['tipo'] == 'Receita']['valor'].sum()
        despesa = df_filtered[df_filtered['tipo'] == 'Despesa']['valor'].sum()
        saldo = receita - despesa
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Receitas", f"R$ {receita:,.2f}")
        m2.metric("Despesas", f"R$ {despesa:,.2f}", delta_color="inverse")
        m3.metric("Saldo", f"R$ {saldo:,.2f}", delta=f"{saldo:,.2f}")
        
        st.divider()
        
        # Gráficos (Usando Plotly, melhor para Mobile que Matplotlib)
        g1, g2 = st.columns(2)
        
        # Gráfico de Pizza (Categorias)
        df_desp = df_filtered[df_filtered['tipo'] == 'Despesa']
        if not df_desp.empty:
            fig_pie = px.pie(df_desp, values='valor', names='categoria', title='Despesas por Categoria')
            g1.plotly_chart(fig_pie, use_container_width=True)
            
            # Gráfico de Barra (Responsáveis)
            df_resp_group = df_desp.groupby('responsavel')['valor'].sum().reset_index()
            fig_bar = px.bar(df_resp_group, x='responsavel', y='valor', title='Gastos por Responsável', color='responsavel')
            g2.plotly_chart(fig_bar, use_container_width=True)
            
            # Gráfico de Linha (Evolução) - Mostra ano todo se mês for "Todos"
            st.subheader("Evolução no Tempo")
            df_evol = df[df['tipo'] == 'Despesa'].groupby('data')['valor'].sum().reset_index()
            fig_line = px.line(df_evol, x='data', y='valor', title='Evolução de Despesas Diárias')
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Sem despesas no período selecionado.")

# ================= TAB 3: CONFIGURAÇÃO =================
with tab_config:
    st.header("⚙️ Configurações e Importação")
    
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.subheader("Categorias")
        nova_cat = st.text_input("Nova Categoria")
        if st.button("Adicionar Categoria"):
            if nova_cat:
                add_aux("categorias", nova_cat)
                st.rerun()
            
    with col_r:
        st.subheader("Responsáveis")
        novo_resp = st.text_input("Novo Responsável")
        if st.button("Adicionar Responsável"):
            if novo_resp:
                add_aux("responsaveis", novo_resp)
                st.rerun()
            
    st.divider()
    
    st.subheader("📂 Importação de Dados (Excel)")
    st.info("Suporta arquivos com colunas mensais (JANEIRO, FEVEREIRO...) ou lista simples.")
    
    uploaded_file = st.file_uploader("Arraste sua planilha aqui", type=['xlsx', 'xls'])
    tipo_import = st.radio("Esses dados são:", ["Despesa", "Receita"], horizontal=True)
    
    if uploaded_file:
        if st.button("Processar e Importar"):
            try:
                df = pd.read_excel(uploaded_file)
                
                # --- LÓGICA DE LIMPEZA E IMPORTAÇÃO ---
                count = 0
                rows_to_insert = []
                
                # Detectar se é planilha de meses (Pivot) ou Lista Simples
                cols_upper = [str(c).upper() for c in df.columns]
                meses_pt = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", 
                           "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
                tem_meses = len([m for m in meses_pt if m in cols_upper]) >= 3
                
                status_text = st.empty()
                status_text.text("Lendo arquivo...")

                if tem_meses:
                    # === MODO PIVOT (Colunas de Meses) ===
                    # Tenta adivinhar responsável pelo nome do arquivo
                    filename = uploaded_file.name.upper()
                    resp_padrao = "Geral"
                    if "TIAGO" in filename and "BYANCA" not in filename: resp_padrao = "Tiago"
                    elif "BYANCA" in filename: resp_padrao = "Byanca"
                    elif "CASAL" in filename: resp_padrao = "Casal"
                    
                    year = 2026 # Padrão, ou você pode colocar um input para escolher o ano
                    
                    for index, row in df.iterrows():
                        # Tenta achar descrição e categoria
                        desc = str(row.iloc[0]) if len(row) > 0 else "Importado"
                        cat = str(row.iloc[2]) if len(row) > 2 else "Geral"
                        
                        # Limpeza básica
                        if pd.isna(desc) or desc == 'nan': continue
                        
                        # Varrer colunas de meses
                        for col_name in df.columns:
                            col_upper = str(col_name).upper().strip()
                            mes_idx = -1
                            for i, m_name in enumerate(meses_pt):
                                if m_name in col_upper:
                                    mes_idx = i + 1
                                    break
                            
                            if mes_idx > 0:
                                val_raw = row[col_name]
                                if pd.isna(val_raw): continue
                                
                                try:
                                    # Limpa R$ e converte vírgula
                                    val_str = str(val_raw).replace("R$", "").replace(" ", "")
                                    if "," in val_str and "." in val_str: val_str = val_str.replace(".", "").replace(",", ".")
                                    elif "," in val_str: val_str = val_str.replace(",", ".")
                                    
                                    valor = float(val_str)
                                    if valor > 0:
                                        data_iso = f"{year}-{mes_idx:02d}-01" # Sempre dia 01
                                        rows_to_insert.append({
                                            "data": data_iso,
                                            "tipo": tipo_import,
                                            "categoria": cat,
                                            "descricao": desc,
                                            "valor": valor,
                                            "responsavel": resp_padrao
                                        })
                                        count += 1
                                except:
                                    continue

                else:
                    # === MODO LISTA PADRÃO ===
                    for index, row in df.iterrows():
                        try:
                            # Ajuste conforme suas colunas: 0=Data, 1=Tipo, 2=Cat, 3=Desc, 4=Valor, 5=Resp
                            raw_date = row.iloc[0]
                            # Tenta converter data excel ou string
                            if isinstance(raw_date, str):
                                dt_obj = datetime.strptime(raw_date, "%d/%m/%Y")
                            else:
                                dt_obj = raw_date
                            
                            data_iso = dt_obj.strftime("%Y-%m-%d")
                            
                            val_raw = row.iloc[4]
                            val_str = str(val_raw).replace("R$", "").replace(" ", "").replace(",", ".")
                            valor = float(val_str)
                            
                            rows_to_insert.append({
                                "data": data_iso,
                                "tipo": row.iloc[1] if len(row)>1 else tipo_import,
                                "categoria": row.iloc[2] if len(row)>2 else "Geral",
                                "descricao": row.iloc[3] if len(row)>3 else "Importado",
                                "valor": valor,
                                "responsavel": row.iloc[5] if len(row)>5 else "Geral"
                            })
                            count += 1
                        except Exception as e:
                            print(f"Erro linha {index}: {e}")
                            continue

                # Inserção no Banco (em lotes para ser rápido)
                if rows_to_insert:
                    status_text.text(f"Inserindo {count} registros no banco...")
                    # Supabase permite insert de lista
                    conn.table("financas").insert(rows_to_insert).execute()
                    st.success(f"Sucesso! {count} registros importados.")
                    st.cache_data.clear()
                    # Aguarda 2s e recarrega
                    import time
                    time.sleep(2)
                    st.rerun()
                else:
                    st.warning("Nenhum dado válido encontrado para importar.")

            except Exception as e:
                st.error(f"Erro ao processar arquivo: {e}")
    
    if uploaded_file:
        st.info("Funcionalidade de importação pronta para receber a lógica Pandas do seu código original.")
        # Aqui entra a lógica do seu 'import_from_file' adaptada para ler do buffer 'uploaded_file'
        # Se quiser que eu adapte a lógica complexa de importação do seu código original, me avise!
