import streamlit as st
import pandas as pd
import glob
import re

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. DISEÑO VISUAL (ORIGINAL) ---
fondo_url = "https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"
st.markdown(f"""
    <style>
    .stApp {{ background-image: url("{fondo_url}"); background-attachment: fixed; background-size: cover; }}
    .main .block-container {{ background-color: rgba(255, 255, 255, 0.95); border-radius: 10px; padding: 30px; margin-top: 20px; }}
    h1, h2, h3, h4, p, span, div, label {{ color: #000000 !important; font-weight: bold; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES ---
def aplicar_semaforo(val):
    try:
        p = float(val)
        if p >= 0.75: return 'background-color: #28a745; color: white; font-weight: bold;'
        if p >= 0.60: return 'background-color: #ffc107; color: black; font-weight: bold;'
    except: pass
    return ''

def calcular_probabilidades(df_liga):
    if df_liga.empty: return pd.DataFrame()
    df_jugados = df_liga[df_liga['Resultado'].str.contains('-', na=False)].copy()
    total = len(df_jugados)
    if total == 0: return pd.DataFrame()

    o15 = len(df_jugados[df_jugados['Resultado'].apply(lambda x: sum(map(int, re.findall(r'\d+', str(x)))) > 1.5)]) / total
    o25 = len(df_jugados[df_jugados['Resultado'].apply(lambda x: sum(map(int, re.findall(r'\d+', str(x)))) > 2.5)]) / total
    def b(r):
        g = re.findall(r'\d+', str(r))
        return int(g[0]) > 0 and int(g[1]) > 0 if len(g)==2 else False
    btts = len(df_jugados[df_jugados['Resultado'].apply(b)]) / total

    df_p = df_liga[~df_liga['Resultado'].str.contains('-', na=False)].copy()
    pk = []
    for _, r in df_p.iterrows():
        pk.append({
            'Fecha': r['Fecha'], 'Jornada': r['Jornada'], 'Liga': r['Liga_Nombre'],
            'Partido': f"{r['Equipo Local']} vs {r['Equipo Visitante']}",
            'Pick': "Over 1.5" if o15 > 0.70 else "Local/Empate", 
            'Prob. Pick': o15 if o15 > 0.70 else 0.65,
            'Over 1.5': o15, 'Over 2.5': o25, 'BTTS': btts
        })
    return pd.DataFrame(pk)

# --- 4. CARGA ---
archivos = glob.glob("*.csv")
df_lista_picks, df_lista_historial, lista_ligas = [], [], []
for a in archivos:
    try:
        n = a.replace(".csv", "").replace("-", " ").replace("_", " ")
        t = pd.read_csv(a)
        t['Liga_Nombre'] = n
        df_lista_historial.append(t[t['Resultado'].str.contains('-', na=False)])
        p = calcular_probabilidades(t)
        if not p.empty: df_lista_picks.append(p)
        lista_ligas.append(n)
    except: continue

df_fut = pd.concat(df_lista_picks) if df_lista_picks else pd.DataFrame()
df_his = pd.concat(df_lista_historial) if df_lista_historial else pd.DataFrame()

# --- 5. INTERFAZ ---
st.title("⚽ BET PRO LEAGUE")
t1, t2 = st.tabs(["🎯 PRÓXIMOS PICKS", "📜 HISTORIAL"])

with t1:
    st.header("🎯 PRÓXIMOS PICKS")
    if not df_fut.empty:
        # --- EL TOP 4 ORIGINAL ---
        c1, c2, c3, c4 = st.columns(4)
        m_o15 = df_fut['Over 1.5'].mean()
        m_o25 = df_fut['Over 2.5'].mean()
        m_btts = df_fut['BTTS'].mean()
        c1.metric("Prom. Over 1.5", f"{m_o15:.0%}")
        c2.metric("Prom. Over 2.5", f"{m_o25:.0%}")
        c3.metric("Prom. BTTS", f"{m_btts:.0%}")
        c4.metric("Ligas Activas", len(lista_ligas))

        # Filtros
        f1, f2 = st.columns(2)
        with f1: s_l = st.selectbox("Selecciona Liga:", ["TODAS"] + sorted(lista_ligas), key="lp")
        df_v = df_fut[df_fut['Liga'] == s_l] if s_l != "TODAS" else df_fut
        j_list = sorted(df_v['Jornada'].dropna().unique(), key=lambda x: str(x), reverse=True)
        with f2: s_j = st.selectbox("Selecciona Jornada:", ["TODAS"] + list(j_list), key="jp")
        df_f = df_v if s_j == "TODAS" else df_v[df_v['Jornada'] == s_j]

        # Estilo
        df_f['Pick'] = "⚽ " + df_f['Pick'].astype(str)
        cols_calc = [c for c in ['Prob. Pick', 'Over 1.5', 'Over 2.5', 'BTTS'] if c in df_f.columns]
        
        st.dataframe(
            df_f[['Fecha', 'Jornada', 'Liga', 'Partido', 'Pick'] + cols_calc]
            .style.applymap(aplicar_semaforo, subset=cols_calc)
            .format({c: '{:.0%}' for c in cols_calc}),
            use_container_width=True, hide_index=True
        )

with t2:
    st.header("📜 HISTORIAL")
    if not df_his.empty:
        h1, h2 = st.columns(2)
        with h1: sl_h = st.selectbox("Liga:", ["TODAS"] + sorted(lista_ligas), key="lh")
        df_vh = df_his[df_his['Liga_Nombre'] == sl_h] if sl_h != "TODAS" else df_his
        jh = sorted(df_vh['Jornada'].dropna().unique(), key=lambda x: str(x), reverse=True)
        with h2: sj_h = st.selectbox("Jornada:", ["TODAS"] + list(jh), key="jh")
        df_fh = df_vh if sj_h == "TODAS" else df_vh[df_vh['Jornada'] == sj_h]
        st.dataframe(df_fh[['Fecha', 'Jornada', 'Equipo Local', 'Equipo Visitante', 'Resultado']], use_container_width=True, hide_index=True)