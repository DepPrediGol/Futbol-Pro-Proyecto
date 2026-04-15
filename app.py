import streamlit as st
import pandas as pd
import numpy as np
import glob
import math
import re
import os
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bet Pro Futbol AI", layout="wide", page_icon="⚽")

# --- 2. CSS PARA CORREGIR MODO OSCURO, CALENDARIO Y BOTÓN DE CIERRE ---
st.markdown("""
    <style>
    :root { color-scheme: light !important; }

    .stApp { 
        background-image: url("https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"); 
        background-attachment: fixed; background-size: cover; 
    }
    
    .main .block-container { 
        background-color: rgba(255, 255, 255, 0.98) !important; 
        border-radius: 15px; padding: 40px; margin-top: 25px;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.4);
    }

    /* FORZAR TEXTO NEGRO */
    h1, h2, h3, h4, h5, h6, p, span, label, .stMetric, [data-testid="stHeader"] {
        color: #000000 !important;
        font-weight: bold !important;
    }

    /* ARREGLO ESPECÍFICO PARA CALENDARIO (MODO OSCURO) */
    div[data-baseweb="calendar"] {
        background-color: white !important;
        color: black !important;
    }
    div[data-baseweb="calendar"] button {
        color: black !important;
    }
    div[data-baseweb="popover"] {
        background-color: white !important;
    }
    input[role="combobox"] {
        color: black !important;
        background-color: white !important;
    }

    /* BOTÓN "X" DE CIERRE VISIBLE */
    button[aria-label="Close"] {
        color: black !important;
        background-color: #f0f0f0 !important;
        border: 2px solid #333 !important;
        border-radius: 50% !important;
        width: 40px !important;
        height: 40px !important;
        top: 15px !important;
        right: 15px !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        z-index: 9999 !important;
    }
    button[aria-label="Close"]:hover {
        background-color: #ff4b4b !important;
        color: white !important;
    }

    /* TABLAS Y MODALES SIEMPRE BLANCOS */
    div[data-testid="stDataFrame"], div[role="dialog"], div[data-testid="stDialog"], div[role="grid"] {
        background-color: white !important;
        color: black !important;
    }

    div[data-baseweb="select"] > div {
        background-color: white !important;
        color: black !important;
        border: 2px solid #28a745 !important;
    }

    /* BOTONES TOP 4 */
    div.stButton > button {
        width: 100% !important;
        height: 180px !important;
        background-color: white !important;
        color: black !important;
        border: 2px solid #eee !important;
        border-radius: 15px !important;
        font-weight: bold !important;
    }
    div.stButton > button:hover { border-color: #28a745 !important; }

    header {visibility: hidden !important;}
    footer {display: none !important;}
    .giro-balon { display: inline-block; animation: rotacion 3s infinite linear; }
    @keyframes rotacion { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES LÓGICAS ---
def aplicar_semaforo(val):
    if isinstance(val, (int, float)):
        if val >= 0.70: return 'color: #28a745; font-weight: bold;'
        elif val >= 0.45: return 'color: #ffa500; font-weight: bold;'
        else: return 'color: #dc3545; font-weight: bold;'
    return 'color: black;'

def color_letras_historial(val):
    v = str(val)
    if '✅' in v: return 'color: #28a745; font-weight: bold;'
    if '❌' in v: return 'color: #dc3545; font-weight: bold;'
    return 'color: black;'

def extraer_goles(resultado_str):
    if pd.isna(resultado_str): return None
    res = re.sub(r'\(.*?\)', '', str(resultado_str)).strip()
    nums = re.findall(r'\d+', res.replace(':', '-'))
    return (int(nums[0]), int(nums[1])) if len(nums) >= 2 else None

def calcular_poisson(media, x):
    if media <= 0: return 0.001
    return (math.exp(-media) * (media**x)) / math.factorial(x)

def obtener_probabilidades(e_l, e_v):
    p_l, p_e, p_v, p_o15, p_o25, p_btts = 0, 0, 0, 0, 0, 0
    for gl in range(7):
        ml = calcular_poisson(e_l, gl)
        for gv in range(7):
            p = ml * calcular_poisson(e_v, gv)
            if gl > gv: p_l += p
            elif gl == gv: p_e += p
            else: p_v += p
            if (gl+gv) > 1.5: p_o15 += p
            if (gl+gv) > 2.5: p_o25 += p
            if gl > 0 and gv > 0: p_btts += p
    return p_l, p_e, p_v, p_o15, p_o25, p_btts

# --- 4. CARGA DE DATOS ---
@st.cache_data(ttl=60)
def cargar_todo():
    archivos = glob.glob("**/*.csv", recursive=True)
    fz_acum, part_cont = {}, {}
    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            for _, f in df.iterrows():
                l, v = f['home_team'], f['away_team']
                g = extraer_goles(f.get('result'))
                if g:
                    fz_acum[l] = fz_acum.get(l, 0) + g[0]
                    fz_acum[v] = fz_acum.get(v, 0) + g[1]
                    part_cont[l] = part_cont.get(l, 0) + 1
                    part_cont[v] = part_cont.get(v, 0) + 1
        except: continue
    
    fz = {eq: (fz_acum[eq]/part_cont[eq]) if part_cont.get(eq,0)>0 else 1.2 for eq in fz_acum}
    actuales, historicos, ligas = [], [], []

    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            ln = os.path.basename(arc).replace('.csv','')
            if ln not in ligas: ligas.append(ln)
            for _, f in df.iterrows():
                pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz.get(f['home_team'],1.2), fz.get(f['away_team'],1.2))
                total = pl+pe+pv+pe
                p1x, px2 = (pl+pe)/total, (pv+pe)/total
                g = extraer_goles(f.get('result'))
                
                fecha_dt = pd.to_datetime(f['date'], dayfirst=True, errors='coerce')
                
                if g:
                    historicos.append({
                        'Date': f['date'], 'Time': f.get('time','-'), 'Matchday': int(f.get('matchday',0)), 'League': ln, 
                        'Home team': f['home_team'], 'Away team': f['away_team'], 'Match': f"{f['home_team']} vs {f['away_team']}",
                        'Result': f"{g[0]} - {g[1]}", 'G_L': g[0], 'G_V': g[1],
                        '1X': f"{'✅' if g[0]>=g[1] else '❌'} {p1x:.0%}",
                        'X2': f"{'✅' if g[1]>=g[0] else '❌'} {px2:.0%}",
                        'Over 1.5': f"{'✅' if (g[0]+g[1])>1.5 else '❌'} {po15:.0%}",
                        'Over 2.5': f"{'✅' if (g[0]+g[1])>2.5 else '❌'} {po25:.0%}",
                        'Btts': f"{'✅' if (g[0]>0 and g[1]>0) else '❌'} {pb:.0%}",
                        'Fecha_dt': fecha_dt
                    })
                else:
                    actuales.append({
                        'Date': f['date'], 'Time': f.get('time','-'), 'Matchday': int(f.get('matchday',0)), 'League': ln, 
                        'Home team': f['home_team'], 'Away team': f['away_team'], 'Match': f"{f['home_team']} vs {f['away_team']}",
                        'Fecha_dt': fecha_dt,
                        '1X': p1x, 'X2': px2, 'Over 1.5': po15, 'Over 2.5': po25, 'Btts': pb
                    })
        except: continue
    return pd.DataFrame(actuales), pd.DataFrame(historicos), sorted(ligas)

df_p, df_h, lgs = cargar_todo()

# --- 5. VENTANA MODAL (ANALISIS DETALLADO) ---
@st.dialog("📊 ANÁLISIS DETALLADO", width="large")
def ventana_analisis(r, df_h):
    st.markdown(f"## ⚽ {r['Match']}")
    st.divider()
    for eq, col, nom in [(r['Home team'], 'Home team', 'Local'), (r['Away team'], 'Away team', 'Visitante')]:
        st.markdown(f"#### 📈 Últimos 10 partidos como {nom}: {eq}")
        df_eq = df_h[df_h[col] == eq].iloc[::-1].head(10)
        if not df_eq.empty:
            c = st.columns(4)
            c[0].metric(f"Efectividad {('1X' if nom=='Local' else 'X2')}", f"{(df_eq['1X' if nom=='Local' else 'X2'].str.contains('✅').sum()/len(df_eq)):.0%}")
            c[1].metric("Over 1.5", f"{(df_eq['Over 1.5'].str.contains('✅').sum()/len(df_eq)):.0%}")
            c[2].metric("Over 2.5", f"{(df_eq['Over 2.5'].str.contains('✅').sum()/len(df_eq)):.0%}")
            c[3].metric("Btts", f"{(df_eq['Btts'].str.contains('✅').sum()/len(df_eq)):.0%}")
            st.dataframe(df_eq[['Date', 'Time', 'Matchday', 'Match', 'Result', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']].style.map(color_letras_historial, subset=['1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']), use_container_width=True, hide_index=True)
        st.divider()

# --- 6. INTERFAZ ---
st.markdown('<h1><span class="giro-balon">⚽</span> Bet Pro Futbol AI</h1>', unsafe_allow_html=True)
t1, t2 = st.tabs(["SOCCER PREDICTIONS", "BASKETBALL PREDICTIONS"])

with t1:
    if not df_p.empty:
        # TOP 4
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        df_f = df_p[df_p['Fecha_dt'] >= hoy]
        if not df_f.empty:
            f_prox = df_f['Fecha_dt'].min()
            df_t4 = df_f[df_f['Fecha_dt'] == f_prox].copy()
            st.markdown(f"### 🏆 TOP 4 ({f_prox.strftime('%d/%m/%Y')})")
            mks = [('1X', '🛡️ Doble Oportunidad'), ('Over 1.5', '🥅 Over 1.5'), ('Over 2.5', '⚽ Over 2.5'), ('Btts', '🤝 Btts')]
            cols = st.columns(4)
            for i, (m, tit) in enumerate(mks):
                with cols[i]:
                    st.markdown(f"#### {tit}")
                    top = df_t4.nlargest(4, m)
                    for _, r in top.iterrows():
                        etq = ("1X" if r['1X'] >= r['X2'] else "X2") if m == '1X' else "Prob"
                        if st.button(f"{r['Date']} {r['Time']}\n{r['League']}\n{r['Match']}\n⭐ {etq}: {r[m]:.0%}", key=f"t4_{m}_{r['Match']}"):
                            ventana_analisis(r, df_h)
        st.divider()
        
        # FILTROS - FECHA PRIMERO + ARREGLO VISIBILIDAD
        st.markdown("### 📊 LIGAS Y JORNADAS")
        cf, c1, c2 = st.columns([1, 1, 1])
        with cf: sf = st.date_input("Filtrar por Fecha:", value=None, key="f_act")
        with c1: sl = st.selectbox("Seleccione Liga:", ["TODAS"] + lgs, key="l_act")
        
        df_fl = df_p if sl=="TODAS" else df_p[df_p['League']==sl]
        if sf: 
            df_fl = df_fl[df_fl['Fecha_dt'].dt.date == sf]
            
        with c2: sj = st.selectbox("Seleccione Jornada:", ["TODAS"] + sorted(df_fl['Matchday'].unique().tolist(), reverse=True) if not df_fl.empty else ["TODAS"], key="j_act")
        df_fin = df_fl if sj=="TODAS" else df_fl[df_fl['Matchday']==sj]
        
        if not df_fin.empty:
            cols_f = ['1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']
            st.dataframe(df_fin[['Date', 'Time', 'Matchday', 'League', 'Match'] + cols_f].style.map(aplicar_semaforo, subset=cols_f).format({c: '{:.0%}' for c in cols_f}), use_container_width=True, hide_index=True)
            st.divider()
            
            # PREDICCIÓN BOMBA COMPLETA
            d_b = df_fin.loc[df_fin[['Over 1.5', 'Over 2.5', 'Btts']].max(axis=1).idxmax()]
            loc, vis = d_b['Home team'], d_b['Away team']
            h_l = df_h[(df_h['Home team'] == loc) & (df_h['League'] == d_b['League'])]
            h_v = df_h[(df_h['Away team'] == vis) & (df_h['League'] == d_b['League'])]
            
            if not h_l.empty and not h_v.empty:
                t_l, g1_l, g2_l, w_l = len(h_l), (h_l['G_L']>=1).sum(), (h_l['G_L']>=2).sum(), (h_l['1X'].str.contains('✅')).sum()
                t_v, g1_v, g2_v, w_v = len(h_v), (h_v['G_V']>=1).sum(), (h_v['G_V']>=2).sum(), (h_v['X2'].str.contains('✅')).sum()
                etq_b = f"1X: {d_b['1X']:.0%}" if d_b['1X'] >= d_b['X2'] else f"X2: {d_b['X2']:.0%}"
                
                st.markdown(f"""
                <div style="background-color: #ff4b4b; padding: 30px; border-radius: 15px; border-left: 15px solid #8B0000;">
                    <h2 style="color: white !important; margin: 0; text-align: center;">💣 PREDICCIÓN BOMBA DETECTADA 💣</h2>
                    <p style="font-size: 1.2rem; line-height: 1.6; margin-top: 20px; color: white !important;">
                        El equipo local <b>{loc}</b> lleva <b>{g1_l} de {t_l}</b> partidos marcando al menos 1 gol en casa, y en <b>{g2_l}</b> ha marcado 2 o más goles. Ha ganado o empatado en <b>{w_l} de {t_l}</b> encuentros como local. <br><br>
                        El visitante <b>{vis}</b> ha marcado al menos 1 gol en <b>{g1_v} de {t_v}</b> salidas, con 2 o más goles en <b>{g2_v}</b> de ellas. Ha mantenido su doble oportunidad en <b>{w_v} de {t_v}</b> encuentros.
                    </p>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 25px;">
                        <div style="background: white; color: #ff4b4b; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold;">🛡️ {etq_b}</div>
                        <div style="background: white; color: #ff4b4b; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold;">🥅 Over 1.5: {d_b['Over 1.5']:.0%}</div>
                        <div style="background: white; color: #ff4b4b; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold;">⚽ Over 2.5: {d_b['Over 2.5']:.0%}</div>
                        <div style="background: white; color: #ff4b4b; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold;">🤝 Btts: {d_b['Btts']:.0%}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    st.divider()
    st.markdown("## 📜 HISTORIAL DE RESULTADOS")
    if not df_h.empty:
        cfh, c1h, c2h = st.columns([1, 1, 1])
        with cfh: sfh = st.date_input("Fecha Historial:", value=None, key="f_his")
        with c1h: slh = st.selectbox("Liga Historial:", ["TODAS"] + lgs, key="l_his")
        
        df_hh = df_h if slh=="TODAS" else df_h[df_h['League']==slh]
        if sfh: 
            df_hh = df_hh[df_hh['Fecha_dt'].dt.date == sfh]
            
        with c2h: sjh = st.selectbox("Jornada Historial:", ["TODAS"] + sorted(df_hh['Matchday'].unique().tolist(), reverse=True) if not df_hh.empty else ["TODAS"], key="j_his")
        df_res = df_hh if sjh=="TODAS" else df_hh[df_hh['Matchday']==sjh]
        st.dataframe(df_res[['Date', 'Time', 'Matchday', 'League', 'Match', 'Result', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']].style.map(color_letras_historial, subset=['1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']), use_container_width=True, hide_index=True)

with t2:
    st.markdown("## 🏀 BASKETBALL PREDICTIONS")
    st.info("Módulo de baloncesto en desarrollo.")