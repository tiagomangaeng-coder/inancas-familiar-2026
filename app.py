import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
from st_supabase_connection import SupabaseConnection

# --- Configuração da Página ---
st.set_page_config(page_title="Finanças 2026", layout="wide", page_icon="💰")

# --- Conexão com Supabase ---
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error("Erro ao conectar no Supabase. Verifique os Secrets.")
    st.stop()

# --- Funções de Banco de Dados (CRUD) ---
def get_data(table_name):
    """Busca todos os dados de uma tabela."""
    try:
        # CORREÇÃO APLICADA: Usando .select("*") em vez de .query()
        response = conn.table(table_name).select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Erro ao buscar dados de {table_name}: {e}")
        return []

def add_financa(data, tipo, cat, desc, val, resp):
    """Adiciona um novo registro."""
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
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def delete_financa(ids_to_delete):
    """Deleta registros por ID."""
    try:
        for _id in ids_to_delete:
            conn.table("financas").delete().eq("id", _id).execute()
        st.success("Registros excluídos!")
        st.cache_data.clear()
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")

def add_aux(table, nome):
    """Adiciona categoria ou responsável."""
    try:
        conn.table(table).insert({"nome": nome}).execute()
        st.success(f"{nome} adicionado!")
        st.cache_data.clear()
    except:
        st.warning("Item já existe ou erro na inserção.")

# --- Interface Principal ---
st.title("📊 Controle Familiar 2026")

tab_dados, tab_dash, tab_config = st.tabs(["📝 Registros", "📈 Dashboard", "⚙️ Configuração"])

# Carregar listas auxiliares
try:
    data_cats = get_data("categorias")
    lista_cats = [item['nome'] for item in data_cats] if data_cats else ["Geral"]
    
    data_resps = get_data("responsaveis")
    lista_resps = [item['nome'] for item in data_resps] if data_resps else ["Geral"]
except:
    lista_cats = ["Geral"]
    lista_resps = ["Geral"]

# ================= TAB 1: REGISTROS =================
with tab_dados:
    # --- Formulário de Inserção ---
    with st.expander("➕ Novo Lançamento", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            data_in = st.date_input("Data", datetime.today())
            tipo_in = st.selectbox("Tipo", ["Despesa", "Receita"])
        with c2:
            cat_in = st.selectbox("Categoria", lista_cats)
            valor_in = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        with c3:
            resp_in = st.selectbox("Responsável", lista_resps)
            desc_in = st.text_input("Descrição")

        if st.button("Salvar Lançamento", use_container_width=True):
            if not desc_in:
                st.warning("Preencha a descrição.")
            else:
                add_financa(data_in, tipo_in, cat_in, desc_in, valor_in, resp_in)
                st.rerun()

    st.divider()
    
    # --- Tabela de Dados ---
    st.subheader("Histórico de Lançamentos")
    
    rows = get_data("financas")
    if rows:
        df = pd.DataFrame(rows)
        
        # Converter data
        df['data'] = pd.to_datetime(df['data'])
        
        # Filtros Rápidos
        col_f1, col_f2, col_f3 = st.columns(3)
        filtro_mes = col_f1.selectbox("Mês", ["Todos"] + list(range(1, 13)), index=0)
        filtro_ano = col_f2.selectbox("Ano", [2025, 2026], index=1)
        filtro_resp = col_f3.selectbox("Resp.", ["Todos"] + lista_resps)
        
        # Aplicar Filtros
        df_show = df.copy()
        if filtro_mes != "Todos":
            df_show = df_show[df_show['data'].dt.month == int(filtro_mes)]
        
        df_show = df_show[df_show['data'].dt.year == int(filtro_ano)]
        
        if filtro_resp != "Todos":
            df_show = df_show[df_show['responsavel'] == filtro_resp]

        df_show = df_show.sort_values(by='data', ascending=False)

        # Exibição da Tabela com Seleção
        event = st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            selection_mode="multi-row",
            on_select="rerun",
            column_config={
                "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "id": None, # Oculta ID visualmente mas mantém nos dados
                "created_at": None
            }
        )
        
        # Botão de Exclusão
        if len(event.selection.rows) > 0:
            # Pega o ID das linhas selecionadas no DataFrame filtrado
            ids_selecionados = df_show.iloc[event.selection.rows]['id'].tolist()
            st.warning(f"{len(ids_selecionados)} itens selecionados.")
            
            if st.button("🗑️ Excluir Itens Selecionados", type="primary"):
                delete_financa(ids_selecionados)
    else:
        st.info("Nenhum dado encontrado no banco.")

# ================= TAB 2: DASHBOARD =================
with tab_dash:
    rows = get_data("financas")
    if rows:
        df = pd.DataFrame(rows)
        df['data'] = pd.to_datetime(df['data'])
        
        # Filtros do Dashboard
        st.caption("Filtros do Dashboard")
        c1, c2, c3 = st.columns(3)
        ano_dash = c1.selectbox("Ano Ref.", [2025, 2026], index=1, key="dash_ano")
        mes_dash = c2.selectbox("Mês Ref.", ["Todos"] + list(range(1, 13)), key="dash_mes")
        resp_dash = c3.selectbox("Resp. Ref.", ["Todos"] + lista_resps, key="dash_resp")
        
        # Filtragem
        df_d = df[df['data'].dt.year == ano_dash]
        if mes_dash != "Todos":
            df_d = df_d[df_d['data'].dt.month == int(mes_dash)]
        if resp_dash != "Todos":
            df_d = df_d[df_d['responsavel'] == resp_dash]
            
        # Cards
        receita = df_d[df_d['tipo'] == 'Receita']['valor'].sum()
        despesa = df_d[df_d['tipo'] == 'Despesa']['valor'].sum()
        saldo = receita - despesa
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Receitas", f"R$ {receita:,.2f}")
        k2.metric("Despesas", f"R$ {despesa:,.2f}", delta_color="inverse")
        k3.metric("Saldo", f"R$ {saldo:,.2f}", delta=f"{saldo:,.2f}")
        
        st.divider()
        
        # Gráficos
        col_g1, col_g2 = st.columns(2)
        
        df_desp = df_d[df_d['tipo'] == 'Despesa']
        
        # 1. Pizza Categorias
        if not df_desp.empty:
            fig_pie = px.pie(df_desp, values='valor', names='categoria', title='Despesas por Categoria', hole=0.4)
            col_g1.plotly_chart(fig_pie, use_container_width=True)
            
            # 2. Barra Responsáveis
            df_resp_group = df_desp.groupby('responsavel')['valor'].sum().reset_index()
            fig_bar = px.bar(df_resp_group, x='responsavel', y='valor', title='Quem gastou mais?', text_auto='.2s', color='responsavel')
            col_g2.plotly_chart(fig_bar, use_container_width=True)
            
            # 3. Linha Evolução
            st.subheader("Evolução Mensal (Receitas vs Despesas)")
            # Agrupar por mês e tipo
            df_evol = df_d.groupby([df_d['data'].dt.to_period("M").astype(str), 'tipo'])['valor'].sum().reset_index()
            df_evol.columns = ['Mes', 'Tipo', 'Valor']
            
            fig_line = px.line(df_evol, x='Mes', y='Valor', color='Tipo', markers=True, 
                               color_discrete_map={'Receita': 'green', 'Despesa': 'red'})
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Sem despesas registradas para gerar gráficos.")

# ================= TAB 3: CONFIGURAÇÃO & IMPORTAÇÃO =================
with tab_config:
    st.header("⚙️ Configurações e Importação")
    
    # --- Gestão de Categorias e Responsáveis ---
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
    
    # --- IMPORTAÇÃO AVANÇADA (Sua Lógica) ---
    st.subheader("📂 Importação de Dados (Excel)")
    st.info("O sistema detecta automaticamente se a planilha é Mensal (Colunas Janeiro, Fevereiro...) ou Lista Simples.")
    
    uploaded_file = st.file_uploader("Arraste sua planilha aqui", type=['xlsx', 'xls'])
    tipo_import = st.radio("Esses dados são principalmente:", ["Despesa", "Receita"], horizontal=True)
    
    if uploaded_file:
        if st.button("Processar e Importar"):
            try:
                df = pd.read_excel(uploaded_file)
                
                count = 0
                rows_to_insert = []
                
                # Detectar Pivot (Colunas com nomes de meses)
                cols_upper = [str(c).upper() for c in df.columns]
                meses_pt = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", 
                           "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
                tem_meses = len([m for m in meses_pt if m in cols_upper]) >= 3
                
                status_text = st.empty()
                status_text.text("Lendo arquivo e convertendo dados...")

                if tem_meses:
                    # === MODO PIVOT (Colunas de Meses) ===
                    filename = uploaded_file.name.upper()
                    resp_padrao = "Geral"
                    if "TIAGO" in filename and "BYANCA" not in filename: resp_padrao = "Tiago"
                    elif "BYANCA" in filename: resp_padrao = "Byanca"
                    elif "CASAL" in filename: resp_padrao = "Casal"
                    
                    year = 2026 
                    
                    for index, row in df.iterrows():
                        desc = str(row.iloc[0]) if len(row) > 0 else "Importado"
                        cat = str(row.iloc[2]) if len(row) > 2 else "Geral"
                        
                        if pd.isna(desc) or desc == 'nan': continue
                        
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
                                    val_str = str(val_raw).replace("R$", "").replace(" ", "")
                                    if "," in val_str and "." in val_str: val_str = val_str.replace(".", "").replace(",", ".")
                                    elif "," in val_str: val_str = val_str.replace(",", ".")
                                    
                                    valor = float(val_str)
                                    if valor > 0:
                                        data_iso = f"{year}-{mes_idx:02d}-01"
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
                            # Ajuste de colunas: 0=Data, 1=Tipo, 2=Cat, 3=Desc, 4=Valor, 5=Resp
                            raw_date = row.iloc[0]
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

                # Inserção em Lote no Supabase
                if rows_to_insert:
                    status_text.text(f"Enviando {count} registros para o Supabase...")
                    
                    # Dividir em lotes menores para não travar a API se for muito grande
                    batch_size = 100
                    for i in range(0, len(rows_to_insert), batch_size):
                        batch = rows_to_insert[i:i + batch_size]
                        conn.table("financas").insert(batch).execute()
                    
                    st.success(f"Sucesso! {count} registros importados.")
                    st.cache_data.clear()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.warning("Nenhum dado válido encontrado para importar.")

            except Exception as e:
                st.error(f"Erro ao processar arquivo: {e}")
