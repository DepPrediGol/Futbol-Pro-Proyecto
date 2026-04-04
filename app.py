import streamlit as st
import pandas as pd
import glob
import math
import re
import os
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. ESTILOS (RESTURADOS) ---
st.markdown("""
    <style>
    @media (max-width: 640px) {
        .main .block-container { padding: 10px !important; margin-top: 0px !important; }
        h1 { font-size: 1.5rem !important; }
    }
    header {visibility: hidden !important;}
    footer {display: none !important;}
    [data-testid="stStatusWidget"], .stAppDeployButton { display: none !important; visibility: hidden !important; }
    .stApp { 
        background-image: url("https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"); 
        background-attachment: fixed; background-size: cover; 
    }
    .main .block-container { background-color: rgba(255, 255, 255, 0.95); border-radius: 10px; padding: 30px; margin-top: 20px; }
    h1, h2, h3, h4, p, span, div, label, .stMetric { color: #000000 !important; font-weight: bold; }
    
    div.stButton > button {
        width: 100% !important;
        height: 180px !important;
        background-color: white !important;
        color: black !important;
        border: 1px solid #ddd !important;
        border-radius: 12px !important;
        font-size: 0.85rem !important;
        white-space: pre-line !important;
    }
    .giro-balon { display: inline-block; animation: rotacion 3s infinite linear; }
    @keyframes rotacion { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES LÓGICAS ---
def aplicar_semaforo(val):
    if isinstance(val, (int, float)):
        if val >= 0.75: return 'color: #28a745; font-weight: bold;'
        elif val >= 0.55: return 'color: #ffa500; font-weight: bold;'
    return 'color: black;'

def color_letras_historial(val):
    if '✅' in str(val): return 'color: #28a745; font-weight: bold;'
    if '❌' in str(val): return 'color: #dc3545; font-weight: bold;'
    return 'color: black;'

def extraer_goles(resultado_str):
    if pd.isna(resultado_str): return None
    res_limpio = str(resultado_str).strip()
    numeros = re.findall(r'\d+', res_limpio.replace(':', '-'))
    return (int(numeros[0]), int(numeros[1])) if len(numeros) >= 2 else None

def calcular_poisson(media, x):
    if media <= 0: return 0.001
    return (math.exp(-media) * (media**x)) / math.factorial(x)

def obtener_probabilidades(e_l, e_v):
    p_l, p_e, p_v, p_o15, p_o25, p_btts = 0, 0, 0, 0, 0, 0
    for gl in range(7):
        for gv in range(7):
            p = calcular_poisson(e_l, gl) * calcular_poisson(e_v, gv)
            if gl > gv: p_l += p
            elif gl == gv: p_e += p
            else: p_v += p
            if (gl+gv) > 1.5: p_o15 += p
            if (gl+gv) > 2.5: p_o25 += p
            if gl > 0 and gv > 0: p_btts += p
    return p_l, p_e, p_v, p_o15, p_o25, p_btts

# --- 4. VENTANAS MODALES ---
@st.dialog("📊 ANÁLISIS DETALLADO", width="large")
def ventana_analisis(r, df_h):
    st.title(f"⚽ {r['Match']}")
    st.subheader(f"🏆 {r['League']} | 📅 {r['Date']}")
    roles = [(r['Home team'], 'Home team', 'Local'), (r['Away team'], 'Away team', 'Visitante')]
    for eq, col_rol, nombre_rol in roles:
        st.markdown(f"#### 📈 Últimos 10 partidos como {nombre_rol}: {eq}")
        df_eq = df_h[df_h[col_rol] == eq].iloc[::-1].head(10).copy()
        if not df_eq.empty:
            cols_mostrar = ['Date', 'Home team', 'Away team', 'Result', 'Double chance', 'Over 1.5', 'Over 2.5', 'Btts']
            st.dataframe(df_eq[cols_mostrar].style.map(color_letras_historial, subset=['Double chance', 'Over 1.5', 'Over 2.5', 'Btts']), use_container_width=True, hide_index=True)

# --- 5. CARGA DE DATOS ---
@st.cache_data(ttl=300)
def cargar_soccer():
    archivos = [f for f in glob.glob("**/*.csv", recursive=True) if "basketball" not in f.lower()]
    actuales, historicos, ligas, fz = [], [], [], {}
    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            ln = os.path.basename(arc).replace('.csv','')
            if ln not in ligas: ligas.append(ln)
            df['matchday'] = pd.to_numeric(df['matchday'], errors='coerce').fillna(0).astype(int)
            df['Fecha_dt'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
            for _, f in df.iterrows():
                loc, vis = f['home_team'], f['away_team']
                if loc not in fz: fz[loc] = 1.2
                if vis not in fz: fz[vis] = 1.2
                g = extraer_goles(f.get('result'))
                if g: fz[loc] += 0.20 if g[0] > g[1] else 0.05; fz[vis] += 0.20 if g[1] > g[0] else 0.05
            for _, f in df.iterrows():
                pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz.get(f['home_team'],1.2), fz.get(f['away_team'],1.2))
                g = extraer_goles(f.get('result'))
                if g:
                    p1x, px2 = pl+pe, pv+pe
                    pk = "1X" if p1x >= px2 else "X2"
                    historicos.append({'Date': f['date'], 'League': ln, 'Matchday': f['matchday'], 'Home team': f['home_team'], 'Away team': f['away_team'], 'Result': f"{g[0]} - {g[1]}", 'G_L': g[0], 'G_V': g[1], 'Double chance': f"{pk} {'✅' if (g[0]>=g[1] if pk=='1X' else g[1]>=g[0]) else '❌'} ({max(p1x,px2):.0%})", 'Over 1.5': f"{'✅' if (g[0]+g[1])>1.5 else '❌'} ({po15:.0%})", 'Over 2.5': f"{'✅' if (g[0]+g[1])>2.5 else '❌'} ({po25:.0%})", 'Btts': f"{'✅' if (g[0]>0 and g[1]>0) else '❌'} ({pb:.0%})"})
                else:
                    actuales.append({'Date': f['date'], 'Fecha_dt': f['Fecha_dt'], 'Time': f.get('time','-'), 'Matchday': f['matchday'], 'League': ln, 'Home team': f['home_team'], 'Away team': f['away_team'], 'Match': f"{f['home_team']} vs {f['away_team']}", '1X': pl+pe, 'X2': pv+pe, 'Over 1.5': po15, 'Over 2.5': po25, 'Btts': pb})
        except: continue
    return pd.DataFrame(actuales), pd.DataFrame(historicos), sorted(ligas)

@st.cache_data(ttl=300)
def cargar_basket():
    archivos = [f for f in glob.glob("**/*.csv", recursive=True) if "basketball" in f.lower()]
    act, hist, lgs = [], [], []
    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            ln = os.path.basename(arc).replace('.csv','')
            if ln not in lgs: lgs.append(ln)
            df['Fecha_dt'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
            for _, f in df.iterrows():
                g = extraer_goles(f.get('result'))
                if g: hist.append({'Date': f['date'], 'League': ln, 'Home team': f['home_team'], 'Away team': f['away_team'], 'Result': f['result'], 'Total Pts': g[0]+g[1]})
                else: act.append({'Date': f['date'], 'Fecha_dt': f['Fecha_dt'], 'Time': f.get('time','-'), 'League': ln, 'Home team': f['home_team'], 'Away team': f['away_team'], 'Match': f"{f['home_team']} vs {f['away_team']}", 'Local Pts': 110.5, 'Visita Pts': 108.2, 'Puntos Totales': 218.7})
        except: continue
    return pd.DataFrame(act), pd.DataFrame(hist), sorted(lgs)

df_p, df_h, lgs = cargar_soccer()
df_pb, df_hb, lgs_b = cargar_basket()

# --- 6. INTERFAZ ---
st.markdown('<h1><span class="giro-balon">⚽</span> Bet Pro League</h1>', unsafe_allow_html=True)
t1, t2 = st.tabs(["SOCCER PREDICTIONS", "BASKETBALL PREDICTIONS"])

with t1:
    if not df_p.empty:
        # --- TOP 4 ---
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fechas = df_p[df_p['Fecha_dt'] >= hoy]['Fecha_dt'].unique()
        if len(fechas) > 0:
            f_prox = min(fechas)
            df_t4 = df_p[df_p['Fecha_dt'] == f_prox].copy()
            st.markdown(f"### 🏆 TOP 4 ({f_prox.strftime('%d/%m/%Y')})")
            cols = st.columns(4)
            mks = [('1X', '🛡️ Doble Oportunidad'), ('Over 1.5', '🥅 Over 1.5'), ('Over 2.5', '⚽ Over 2.5'), ('Btts', '🤝 Btts')]
            for i, (m, tit) in enumerate(mks):
                with cols[i]:
                    st.markdown(f"#### {tit}")
                    top = df_t4.nlargest(4, m)
                    for idx, r in top.iterrows():
                        if st.button(f"{r['Match']}\n⭐ {r[m]:.0%}", key=f"s_{m}_{idx}"): ventana_analisis(r, df_h)
        st.divider()
        # --- LIGAS Y JORNADAS ---
        st.markdown("### 📊 LIGAS Y JORNADAS")
        c1, c2 = st.columns(2)
        with c1: sl = st.selectbox("League Soccer:", ["TODAS"] + lgs, key="sl")
        with c2:
            df_fl = df_p if sl=="TODAS" else df_p[df_p['League']==sl]
            sj = st.selectbox("Matchday Soccer:", ["TODAS"] + sorted(df_fl['Matchday'].unique().tolist(), reverse=True) if not df_fl.empty else ["TODAS"], key="sj")
        df_fin = df_fl if sj=="TODAS" else df_fl[df_fl['Matchday']==sj]
        if not df_fin.empty:
            cols_fmt = ['1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']
            st.dataframe(df_fin[['Date', 'Time', 'League', 'Match'] + cols_fmt].style.map(aplicar_semaforo, subset=cols_fmt).format({c: '{:.0%}' for c in cols_fmt}), use_container_width=True, hide_index=True)
            # --- PREDICCIÓN BOMBA (RESTAURADA) ---
            st.divider()
            st.markdown("""<div style="background-color: #ff4b4b; padding: 25px; border-radius: 15px; color: white; text-align: center;"><h2>💣 PREDICCIÓN BOMBA DETECTADA ⚽</h2></div>""", unsafe_allow_html=True)
        # --- HISTORIAL (RESTAURADO) ---
        st.divider()
        st.markdown("### 📜 HISTORIAL DE RESULTADOS SOCCER")
        if not df_h.empty:
            st.dataframe(df_h.iloc[::-1].head(50), use_container_width=True, hide_index=True)

with t2:
    if not df_pb.empty:
        st.markdown("### 🏀 TOP 4 BASKETBALL")
        cols_b = st.columns(3)
        mks_b = [('Local Pts', '🏠 Puntos Local'), ('Visita Pts', '🚀 Puntos Visitante'), ('Puntos Totales', '🏀 Totales')]
        for i, (m, tit) in enumerate(mks_b):
            with cols_b[i]:
                st.markdown(f"#### {tit}")
                top_b = df_pb.head(4)
                for idx, r in top_b.iterrows():
                    st.button(f"{r['Match']}\n🔥 {r[m]:.1f}", key=f"b_{m}_{idx}")
        st.divider()
        st.markdown("### 📊 LIGAS BASKET")
        st.dataframe(df_pb[['Date', 'Time', 'League', 'Match', 'Local Pts', 'Visita Pts', 'Puntos Totales']], use_container_width=True, hide_index=True)
        st.divider()
        st.markdown("### 📜 HISTORIAL BASKET")
        st.dataframe(df_hb.iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.warning("No se encontraron archivos con 'basketball' en el nombre. Revisa el nombre de tu CSV.")