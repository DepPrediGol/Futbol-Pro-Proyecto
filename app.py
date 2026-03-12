import streamlit as st
import pandas as pd
import glob
import math
import re

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. DISEÑO VISUAL (TU ESTILO ORIGINAL) ---
fondo_url = "https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"
st.markdown(f"""
    <style>
    .stApp {{ background-image: url("{fondo_url}"); background-attachment: fixed; background-size: cover; }}
    .main .block-container {{ background-color: rgba(255, 255, 255, 0.95); border-radius: 10px; padding: 30px; margin-top: 20px; }}
    h1, h2, h3, h4, p, span, div, label, .stMetric {{ color: #000000 !important; font-weight: bold; }}
    div[data-baseweb="select"] > div, ul[role="listbox"], div[data-baseweb="popover"] div {{
        background-color: white !important; color: black !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE CÁLCULO ---
def calcular_probabilidades(df_liga):
    if df_liga.empty: return pd.DataFrame()
    df_jugados = df_liga[df_liga['Resultado'].str.contains('-', na=False)].copy()
    total_partidos = len(df_jugados)
    if total_partidos == 0: return pd.DataFrame()

    overs_15 = len(df_jugados[df_jugados['Resultado'].apply(lambda x: sum(map(int, re.findall(r'\d+', x))) > 1.5)]) / total_partidos
    overs_25 = len(df_jugados[df_jugados['Resultado'].apply(lambda x: sum(map(int, re.findall(r'\d+', x))) > 2.5)]) / total_partidos
    
    def es_btts(res):
        goles = re.findall(r'\d+', res)
        return int(goles[0]) > 0 and int(goles[1]) > 0 if len(goles)==2 else False
    
    btts_prob = len(df_jugados[df_jugados['Resultado'].apply(es_btts)]) / total_partidos

    df_pendientes = df_liga[~df_liga['Resultado'].str.contains('-', na=False)].copy()
    picks = []
    for _, row in df_pendientes.iterrows():
        pick_text = "Over 1.5" if overs_15 > 0.70 else "Local o Empate"
        prob = overs_15 if "Over" in pick_text else 0.65
        picks.append({
            'Fecha': row['Fecha'], 'Jornada': row['Jornada'], 'Liga': row['Liga_Nombre'],
            'Partido': f"{row['Equipo Local']} vs {row['Equipo Visitante']}",
            'Pick': pick_text, 'Prob. Pick': prob, 'Over 1.5': overs_15, 'Over 2.5': overs_25, 'BTTS': btts_prob
        })
    return pd.DataFrame(picks)

# --- 4. CARGA DE DATOS ---
archivos = glob.glob("*.csv")
df_lista_picks, df_lista_historial, lista_ligas_total = [], [], []

for arc in archivos:
    try:
        nombre_liga = arc.replace(".csv", "").replace("-", " ").replace("_", " ")
        temp_df = pd.read_csv(arc)
        temp_df['Liga_Nombre'] = nombre_liga
        df_lista_historial.append(temp_df[temp_df['Resultado'].str.contains('-', na=False)])
        picks_liga = calcular_probabilidades(temp_df)
        if not picks_liga.empty: df_lista_picks.append(picks_liga)
        lista_ligas_total.append(nombre_liga)
    except: continue

df_fut = pd.concat(df_lista_picks) if df_lista_picks else pd.DataFrame()
df_his = pd.concat(df_lista_historial) if df_lista_historial else pd.DataFrame()

# --- 5. INTERFAZ ---
st.title("⚽ BET PRO LEAGUE")
tab1, tab2 = st.tabs(["🎯 PRÓXIMOS PICKS", "📜 HISTORIAL"])

# Función de color corregida para aplicar a TODAS las columnas de porcentaje
def aplicar_semaforo(val):
    try:
        p = float(val)
        if p >= 0.75: return 'background-color: #28a745; color: white; font-weight: bold;'
        if p >= 0.60: return 'background-color: #ffc107; color: black; font-weight: bold;'
    except: pass
    return ''

with tab1:
    st.header("🎯 PRÓXIMOS PICKS")
    if not df_fut.empty:
        f1, f2 = st.columns(2)
        with f1: sel_l_p = st.selectbox("Selecciona Liga:", ["TODAS"] + lista_ligas_total, key="lp")
        df_temp_p = df_fut[df_fut['Liga'] == sel_l_p] if sel_l_p != "TODAS" else df_fut
        j_list_p = sorted(df_temp_p['Jornada'].unique(), key=lambda x: int(x), reverse=True)
        with f2: f_j = st.selectbox("Selecciona Jornada:", ["TODAS"] + [int(x) for x in j_list_p], key="jp")
        
        df_v = df_temp_p if f_j == "TODAS" else df_temp_p[df_temp_p['Jornada'] == int(f_j)]
        
        # Agregamos el icono al texto del Pick
        df_v['Pick'] = "⚽ " + df_v['Pick'].astype(str)

        # Columnas a las que aplicaremos el color
        cols_porcentaje = ['Prob. Pick', 'Over 1.5', 'Over 2.5', 'BTTS']

        st.dataframe(
            df_v[['Fecha', 'Jornada', 'Liga', 'Partido', 'Pick', 'Prob. Pick', 'Over 1.5', 'Over 2.5', 'BTTS']]
            .style.applymap(aplicar_semaforo, subset=cols_porcentaje)
            .format({c: '{:.0%}' for c in cols_porcentaje}), 
            use_container_width=True, hide_index=True
        )

with tab2:
    st.header("📜 HISTORIAL")
    if not df_his.empty:
        h1, h2 = st.columns(2)
        with h1: sel_l = st.selectbox("Liga Historial:", ["TODAS"] + lista_ligas_total, key="lh")
        df_temp_h = df_his[df_his['Liga_Nombre'] == sel_l] if sel_l != "TODAS" else df_his
        j_list_h = sorted(df_temp_h['Jornada'].unique(), key=lambda x: int(x), reverse=True)
        with h2: sel_j = st.selectbox("Jornada Historial:", ["TODAS"] + j_list_h, key="jh")
        df_h_v = df_temp_h if sel_j == "TODAS" else df_temp_h[df_temp_h['Jornada'] == sel_j]
        st.dataframe(df_h_v[['Fecha', 'Jornada', 'Equipo Local', 'Equipo Visitante', 'Resultado']], use_container_width=True, hide_index=True)