import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
from st_supabase_connection import SupabaseConnection

# --- Configuração da Página ---
st.set_page_config(page_title="Finanças 2026", layout="wide", page_icon="💰")

# ================= TELA DE ABERTURA (SPLASH SCREEN) =================
if "splash_shown" not in st.session_state:
    st.session_state.splash_shown = False

if not st.session_state.splash_shown:
    splash = st.empty()
    splash_html = """
    <style>
        .splash-container { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: #ffffff; z-index: 999999; display: flex; flex-direction: column; justify-content: center; align-items: center; font-family: sans-serif; }
        .splash-title { font-size: 3rem; font-weight: bold; color: #2E7D32; margin-bottom: 10px; animation: fadeIn 1.5s ease-in-out; }
        .splash-subtitle { font-size: 1.5rem; color: #555; animation: fadeIn 2s ease-in-out; }
        .splash-footer { position: absolute; bottom: 40px; font-size: 0.9rem; color: #888; animation: slideUp 1s ease-out; }
        @keyframes fadeIn { 0% { opacity: 0; } 100% { opacity: 1; } }
        @keyframes slideUp { 0% { transform: translateY(20px); opacity: 0; } 100% { transform: translateY(0); opacity: 1; } }
    </style>
    <div class="splash-container">
        <div class="splash-title">Controle Financeiro</div>
        <div class="splash-subtitle">Tiago e Byanca</div>
        <div class="splash-footer">Desenvolvido por tmanga - 2026</div>
    </div>
    """
    splash.markdown(splash_html, unsafe_allow_html=True)
    time.sleep(4)
    splash.empty()
    st.session_state.splash_shown = True

# --- Conexão com Supabase ---
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error("Erro de Conexão. Verifique os Secrets.")
    st.stop()

# --- Funções CRUD ---
def get_data(table_name):
    try:
        response = conn.table(table_name).select("*").execute()
        return response.data
    except: return []

def add_financa(data_obj, tipo, cat, desc, val, resp):
    try:
        # Garante formato YYYY-MM-DD para o banco
        data_iso = data_obj.strftime("%Y-%m-%d")
        conn.table("financas").insert({
            "data": data_iso, "tipo": tipo, "categoria": cat, 
            "descricao": desc, "valor": val, "responsavel": resp
        }).execute()
        st.success("Salvo com sucesso!")
        st.cache_data.clear()
    except Exception as e: st.error(f"Erro: {e}")

def delete_financa(ids):
    try:
        for i in ids: conn.table("financas").delete().eq("id", i).execute()
        st.success("Apagado!")
        st.cache_data.clear()
        time.sleep(1)
        st.rerun()
    except: st.error("Erro ao apagar.")

def add_aux(table, nome):
    try:
        conn.table(table).insert({"nome": nome}).execute()
        st.success("Adicionado!")
        st.cache_data.clear()
    except: st.warning("Já existe.")

# --- Interface ---
st.title("📊 Controle Familiar 2026")
tab1, tab2, tab3 = st.tabs(["📝 Registros", "📈 Dashboard", "⚙️ Configuração"])

# Carregar Listas
cats = [c['nome'] for c in get_data("categorias")] or ["Geral"]
resps = [r['nome'] for r in get_data("responsaveis")] or ["Geral"]

# ABA 1: REGISTROS
with tab1:
    with st.expander("➕ Novo Lançamento"):
        c1, c2, c3 = st.columns(3)
        dt = c1.date_input("Data", datetime.today())
        tp = c1.selectbox("Tipo", ["Despesa", "Receita"])
        ct = c2.selectbox("Categoria", cats)
        vl = c2.number_input("Valor", min_value=0.0, format="%.2f")
        rs = c3.selectbox("Responsável", resps)
        ds = c3.text_input("Descrição")
        if st.button("Salvar", use_container_width=True):
            if ds: 
                add_financa(dt, tp, ct, ds, vl, rs)
                st.rerun()
            else: st.warning("Preencha a descrição")

    st.divider()
    rows = get_data("financas")
    if rows:
        df = pd.DataFrame(rows)
        
        # --- CORREÇÃO DAS DATAS NA VISUALIZAÇÃO ---
        # 1. Converte a string do banco (YYYY-MM-DD) para data real
        df['data_dt'] = pd.to_datetime(df['data'])
        # 2. Cria coluna 'data_show' apenas com a data (sem hora) para o filtro funcionar bem
        df['data_show'] = df['data_dt'].dt.date

        # Filtros
        c1, c2, c3 = st.columns(3)
        mes = c1.selectbox("Mês", ["Todos"] + list(range(1,13)))
        ano = c2.selectbox("Ano", [2025, 2026], index=1)
        resp = c3.selectbox("Resp.", ["Todos"] + resps)

        if mes != "Todos": df = df[df['data_dt'].dt.month == int(mes)]
        df = df[df['data_dt'].dt.year == int(ano)]
        if resp != "Todos": df = df[df['responsavel'] == resp]
        
        df = df.sort_values(by='data_dt', ascending=False)

        # Tabela com formato Brasileiro forçado na coluna Data
        evt = st.dataframe(
            df, 
            use_container_width=True, 
            hide_index=True, 
            selection_mode="multi-row", 
            on_select="rerun",
            column_config={
                "data_show": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "data": None, "data_dt": None, "id": None, "created_at": None # Esconde colunas técnicas
            }
        )
        
        if evt.selection.rows:
            ids = df.iloc[evt.selection.rows]['id'].tolist()
            if st.button("🗑️ Excluir Selecionados", type="primary"): delete_financa(ids)
    else: st.info("Sem dados.")

# ABA 2: DASHBOARD
with tab2:
    if rows:
        df2 = pd.DataFrame(rows)
        df2['data'] = pd.to_datetime(df2['data'])
        
        c1, c2, c3 = st.columns(3)
        a_d = c1.selectbox("Ano", [2025, 2026], index=1, key="d_a")
        m_d = c2.selectbox("Mês", ["Todos"] + list(range(1,13)), key="d_m")
        r_d = c3.selectbox("Resp.", ["Todos"] + resps, key="d_r")

        df_d = df2[df2['data'].dt.year == int(a_d)]
        if m_d != "Todos": df_d = df_d[df_d['data'].dt.month == int(m_d)]
        if r_d != "Todos": df_d = df_d[df_d['responsavel'] == r_d]

        rec = df_d[df_d['tipo']=='Receita']['valor'].sum()
        des = df_d[df_d['tipo']=='Despesa']['valor'].sum()
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Receitas", f"R$ {rec:,.2f}")
        k2.metric("Despesas", f"R$ {des:,.2f}", delta_color="inverse")
        k3.metric("Saldo", f"R$ {rec-des:,.2f}")
        
        if not df_d.empty:
            g1, g2 = st.columns(2)
            desp = df_d[df_d['tipo']=='Despesa']
            if not desp.empty:
                g1.plotly_chart(px.pie(desp, values='valor', names='categoria', title='Por Categoria', hole=0.4), use_container_width=True)
                g2.plotly_chart(px.bar(desp.groupby('responsavel')['valor'].sum().reset_index(), x='responsavel', y='valor', title='Por Responsável'), use_container_width=True)
            
            # Gráfico de Evolução
            evol = df_d.groupby([df_d['data'].dt.to_period("M").astype(str), 'tipo'])['valor'].sum().reset_index()
            st.plotly_chart(px.line(evol, x='data', y='valor', color='tipo', title="Evolução Mensal"), use_container_width=True)

# ABA 3: CONFIGURAÇÃO E IMPORTAÇÃO
with tab3:
    c1, c2 = st.columns(2)
    new_cat = c1.text_input("Nova Categoria")
    if c1.button("Add Categoria") and new_cat: add_aux("categorias", new_cat)
    
    new_resp = c2.text_input("Novo Responsável")
    if c2.button("Add Responsável") and new_resp: add_aux("responsaveis", new_resp)
    
    st.divider()
    st.subheader("📂 Importar CSV/Excel")
    up_file = st.file_uploader("Arquivo", type=['csv', 'xlsx'])
    
    if up_file and st.button("Importar"):
        try:
            # Tenta ler CSV (se falhar tenta Excel)
            if up_file.name.endswith('.csv'):
                # IMPORTANTE: O SEGREDO ESTÁ AQUI
                # Lê o CSV usando ';' como separador e converte vírgula para ponto
                df = pd.read_csv(up_file, sep=';', decimal=',')
            else:
                df = pd.read_excel(up_file)

            # Padronizar nomes das colunas (remove espaços e deixa minúsculo)
            df.columns = df.columns.str.strip().str.lower()
            
            count = 0
            batch = []
            
            for _, row in df.iterrows():
                try:
                    # CORREÇÃO CRÍTICA DA DATA
                    # dayfirst=True força o Pandas a entender 01/02 como 1 de Fev, não 2 de Jan
                    raw_date = row['data']
                    dt_obj = pd.to_datetime(raw_date, dayfirst=True)
                    
                    # Prepara para o banco (Formato ISO YYYY-MM-DD)
                    data_db = dt_obj.strftime("%Y-%m-%d")
                    
                    # Tratamento do valor (se for string "1.000,00" converte para float)
                    val = row['valor']
                    if isinstance(val, str):
                        val = float(val.replace('.', '').replace(',', '.'))
                        
                    batch.append({
                        "data": data_db,
                        "tipo": row['tipo'],
                        "categoria": row['categoria'],
                        "descricao": row['descricao'],
                        "valor": float(val),
                        "responsavel": row['responsavel']
                    })
                    count += 1
                except Exception as e:
                    st.error(f"Erro na linha {_}: {e}")
                    continue

            # Envia em lotes para o Supabase
            if batch:
                conn.table("financas").insert(batch).execute()
                st.success(f"{count} registros importados com as datas CORRETAS!")
                time.sleep(2)
                st.rerun()
                
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")
