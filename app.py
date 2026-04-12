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

# --- 2. CSS AVANZADO (ANTI-MODO OSCURO, BOTÓN X Y ESTILOS) ---
st.markdown("""
    <style>
    /* Forzar esquema de color claro a nivel de navegador */
    :root { color-scheme: light !important; }

    /* Fondo de pantalla */
    .stApp { 
        background-image: url("https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"); 
        background-attachment: fixed; background-size: cover; 
    }
    
    /* Contenedor principal blanco con sombra */
    .main .block-container { 
        background-color: rgba(255, 255, 255, 0.97) !important; 
        border-radius: 15px; padding: 40px; margin-top: 25px;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.4);
    }

    /* Forzar texto negro en toda la app */
    h1, h2, h3, h4, h5, h6, p, span, label, .stMetric, [data-testid="stHeader"] {
        color: #000000 !important;
        font-weight: bold !important;
    }

    /* Visibilidad total de la X de cerrar en el Modal */
    button[aria-label="Close"] {
        color: #ffffff !important;
        background-color: #000000 !important;
        border: 2px solid #ffffff !important;
        border-radius: 50% !important;
        width: 38px !important;
        height: 38px !important;
        top: 15px !important;
        right: 15px !important;
        opacity: 1 !important;
    }
    button[aria-label="Close"]:hover {
        background-color: #ff4b4b !important;
        transform: scale(1.1);
    }

    /* Tablas y Modales siempre blancos */
    div[data-testid="stDataFrame"], div[role="dialog"], div[data-testid="stDialog"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        border-radius: 12px !important;
    }

    /* Estilo de los Selectores (Filtros) */
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #28a745 !important;
    }

    /* Botones del TOP 4 */
    div.stButton > button {
        width: 100% !important;
        height: 170px !important;
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #e0e0e0 !important;
        border-radius: 15px !important;
        box-shadow: 0px 4px 8px rgba(0,0,0,0.1) !important;
        font-weight: bold !important;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        border-color: #28a745 !important;
        transform: translateY(-5px);
        box-shadow: 0px 8px 15px rgba(0,0,0,0.2) !important;
    }

    /* Ocultar elementos innecesarios */
    header {visibility: hidden !important;}
    footer {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}

    .giro-balon { display: inline-block; animation: rotacion 3s infinite linear; }
    @keyframes rotacion { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA MATEMÁTICA Y PROCESAMIENTO ---
def aplicar_semaforo(val):
    if isinstance(val, (int, float)):
        if val >= 0.75: return 'color: #1e7e34; font-weight: 900; background-color: #d4edda;'
        elif val >= 0.55: return 'color: #856404; font-weight: 700; background-color: #fff3cd;'
        else: return 'color: #721c24; font-weight: 700; background-color: #f8d7da;'
    return 'color: black;'

def color_resultados(val):
    v = str(val)
    if '✅' in v: return 'color: #28a745; font-weight: bold;'
    if '❌' in v: return 'color: #dc3545; font-weight: bold;'
    return 'color: black;'

def extraer_goles(res):
    if pd.isna(res): return None
    nums = re.findall(r'\d+', str(res).replace(':', '-'))
    return (int(nums[0]), int(nums[1])) if len(nums) >= 2 else None

def calcular_poisson(media, x):
    if media <= 0: return 0.0001
    return (math.exp(-media) * (media**x)) / math.factorial(x)

def obtener_probabilidades(e_l, e_v):
    p_l, p_e, p_v, p_o15, p_o25, p_btts = 0, 0, 0, 0, 0, 0
    for gl in range(8):
        ml = calcular_poisson(e_l, gl)
        for gv in range(8):
            p = ml * calcular_poisson(e_v, gv)
            if gl > gv: p_l += p
            elif gl == gv: p_e += p
            else: p_v += p
            if (gl+gv) > 1.5: p_o15 += p
            if (gl+gv) > 2.5: p_o25 += p
            if gl > 0 and gv > 0: p_btts += p
    return p_l, p_e, p_v, p_o15, p_o25, p_btts

# --- 4. GESTIÓN DE DATOS ---
@st.cache_data(ttl=600)
def cargar_master_data():
    archivos = glob.glob("**/*.csv", recursive=True)
    fz_acum, part_cont = {}, {}
    
    # Primera pasada: Fuerza de ataque
    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            for _, f in df.iterrows():
                l, v = f['home_team'], f['away_team']
                g = extraer_goles(f.get('result'))
                if g:
                    fz_acum[l] = fz_acum.get(l, 0) + g[0]; fz_acum[v] = fz_acum.get(v, 0) + g[1]
                    part_cont[l] = part_cont.get(l, 0) + 1; part_cont[v] = part_cont.get(v, 0) + 1
        except: continue
    
    fz_ataque = {eq: (fz_acum[eq]/part_cont[eq]) if part_cont.get(eq,0)>0 else 1.25 for eq in fz_acum}
    actuales, historicos, ligas = [], [], []

    # Segunda pasada: Procesamiento completo
    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            ln = os.path.basename(arc).replace('.csv','')
            if ln not in ligas: ligas.append(ln)
            for _, f in df.iterrows():
                pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz_ataque.get(f['home_team'],1.2), fz_ataque.get(f['away_team'],1.1))
                p1x, px2 = (pl+pe), (pv+pe)
                g = extraer_goles(f.get('result'))
                
                base_info = {
                    'Date': f['date'], 'Time': f.get('time','-'), 'Matchday': int(f.get('matchday',0)), 'League': ln, 
                    'Home team': f['home_team'], 'Away team': f['away_team'], 'Match': f"{f['home_team']} vs {f['away_team']}",
                    '1X': p1x, 'X2': px2, 'Over 1.5': po15, 'Over 2.5': po25, 'Btts': pb
                }

                if g:
                    base_info.update({
                        'Result': f"{g[0]} - {g[1]}", 'G_L': g[0], 'G_V': g[1],
                        '1X_S': f"{'✅' if g[0]>=g[1] else '❌'} {p1x:.0%}",
                        'X2_S': f"{'✅' if g[1]>=g[0] else '❌'} {px2:.0%}",
                        'O15_S': f"{'✅' if (g[0]+g[1])>1.5 else '❌'} {po15:.0%}",
                        'O25_S': f"{'✅' if (g[0]+g[1])>2.5 else '❌'} {po25:.0%}",
                        'BTTS_S': f"{'✅' if (g[0]>0 and g[1]>0) else '❌'} {pb:.0%}"
                    })
                    historicos.append(base_info)
                else:
                    base_info['Fecha_dt'] = pd.to_datetime(f['date'], dayfirst=True, errors='coerce')
                    actuales.append(base_info)
        except: continue
    
    return pd.DataFrame(actuales), pd.DataFrame(historicos), sorted(ligas)

df_p, df_h, lgs = cargar_master_data()

# --- 5. VENTANA DE ANÁLISIS DETALLADO ---
@st.dialog("📊 ANÁLISIS ESTADÍSTICO PROFUNDO", width="large")
def ventana_analisis(r, df_h):
    st.markdown(f"## ⚽ {r['Match']}")
    st.divider()
    
    for eq, col, nom in [(r['Home team'], 'Home team', 'Local'), (r['Away team'], 'Away team', 'Visitante')]:
        st.markdown(f"### 📈 Rendimiento {nom}: {eq}")
        hist_eq = df_h[df_h[col] == eq].iloc[::-1].head(10)
        
        if not hist_eq.empty:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Efect. 1X2", f"{(hist_eq['1X_S' if nom=='Local' else 'X2_S'].str.contains('✅').sum()/len(hist_eq)):.0%}")
            m2.metric("Over 1.5", f"{(hist_eq['O15_S'].str.contains('✅').sum()/len(hist_eq)):.0%}")
            m3.metric("Over 2.5", f"{(hist_eq['O25_S'].str.contains('✅').sum()/len(hist_eq)):.0%}")
            m4.metric("Btts", f"{(hist_eq['BTTS_S'].str.contains('✅').sum()/len(hist_eq)):.0%}")
            
            st.dataframe(hist_eq[['Date', 'Matchday', 'Match', 'Result', '1X_S', 'X2_S', 'O15_S', 'O25_S', 'BTTS_S']].style.map(color_resultados, subset=['1X_S', 'X2_S', 'O15_S', 'O25_S', 'BTTS_S']), use_container_width=True, hide_index=True)
        else:
            st.warning(f"No hay historial suficiente para {eq}")
        st.divider()

# --- 6. INTERFAZ PRINCIPAL ---
st.markdown('<h1><span class="giro-balon">⚽</span> BET PRO FUTBOL AI</h1>', unsafe_allow_html=True)
pest1, pest2 = st.tabs(["📊 PREDICCIONES", "🏀 BASKETBALL (PRO)"])

with pest1:
    if not df_p.empty:
        # SECCIÓN TOP 4
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        df_top = df_p[df_p['Fecha_dt'] >= hoy].copy()
        
        if not df_top.empty:
            f_prox = df_top['Fecha_dt'].min()
            df_dia = df_top[df_top['Fecha_dt'] == f_prox]
            st.markdown(f"### 🏆 SELECCIÓN TOP 4 - {f_prox.strftime('%d/%m/%Y')}")
            
            cols = st.columns(4)
            metodos = [('1X', '🛡️ DOBLE OPORTUNIDAD'), ('Over 1.5', '🥅 OVER 1.5'), ('Over 2.5', '⚽ OVER 2.5'), ('Btts', '🤝 AMBOS MARCAN')]
            
            for i, (campo, titulo) in enumerate(metodos):
                with cols[i]:
                    st.markdown(f"**{titulo}**")
                    top_match = df_dia.nlargest(1, campo).iloc[0]
                    etiqueta = ("1X" if top_match['1X'] >= top_match['X2'] else "X2") if campo == '1X' else "Prob"
                    if st.button(f"{top_match['Time']}\n{top_match['League']}\n{top_match['Match']}\n⭐ {etiqueta}: {top_match[campo]:.0%}", key=f"btn_top_{i}"):
                        ventana_analisis(top_match, df_h)

        st.divider()

        # FILTROS DINÁMICOS
        st.markdown("### 🔍 EXPLORADOR DE LIGAS")
        c1, c2 = st.columns(2)
        with c1: sl = st.selectbox("Seleccione Liga:", ["TODAS"] + lgs, key="liga_act")
        df_fl = df_p if sl=="TODAS" else df_p[df_p['League']==sl]
        with c2: sj = st.selectbox("Seleccione Jornada:", ["TODAS"] + sorted(df_fl['Matchday'].unique().tolist(), reverse=True) if not df_fl.empty else ["TODAS"], key="jor_act")
        df_fin = df_fl if sj=="TODAS" else df_fl[df_fl['Matchday']==sj]

        if not df_fin.empty:
            cols_v = ['1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']
            st.dataframe(df_fin[['Date', 'Time', 'Matchday', 'League', 'Match'] + cols_v].style.map(aplicar_semaforo, subset=cols_v).format({c: '{:.0%}' for c in cols_v}), use_container_width=True, hide_index=True)
            
            # --- BLOQUE PREDICCIÓN BOMBA RECONSTRUIDO ---
            st.divider()
            bomba = df_fin.loc[df_fin[['Over 1.5', 'Over 2.5', 'Btts']].max(axis=1).idxmax()]
            loc, vis = bomba['Home team'], bomba['Away team']
            
            h_l = df_h[(df_h['Home team'] == loc) & (df_h['League'] == bomba['League'])]
            h_v = df_h[(df_h['Away team'] == vis) & (df_h['League'] == bomba['League'])]
            
            if not h_l.empty and not h_v.empty:
                # Estadísticas para el texto detallado
                t_l, g1_l, g2_l, w_l = len(h_l), (h_l['G_L']>=1).sum(), (h_l['G_L']>=2).sum(), (h_l['1X_S'].str.contains('✅')).sum()
                t_v, g1_v, g2_v, w_v = len(h_v), (h_v['G_V']>=1).sum(), (h_v['G_V']>=2).sum(), (h_v['X2_S'].str.contains('✅')).sum()
                pick = f"1X: {bomba['1X']:.0%}" if bomba['1X'] >= bomba['X2'] else f"X2: {bomba['X2']:.0%}"
                
                st.markdown(f"""
                <div style="background-color: #e63946; padding: 35px; border-radius: 15px; border: 4px solid #1d3557; color: white !important;">
                    <h2 style="color: white !important; text-align: center; margin-bottom: 20px;">💣 PREDICCIÓN BOMBA DEL DÍA 💣</h2>
                    <p style="font-size: 1.25rem; line-height: 1.7; text-align: justify; color: white !important;">
                        En la liga <b>{bomba['League']}</b>, el equipo local <b>{loc}</b> ha demostrado un poder ofensivo constante marcando al menos 1 gol en <b>{g1_l} de sus últimos {t_l}</b> partidos en casa, y logrando anotar 2 o más goles en <b>{g2_l}</b> de ellos. Además, ha mantenido su imbatibilidad en casa (1X) en <b>{w_l}</b> encuentros. <br><br>
                        Por su parte, el visitante <b>{vis}</b> no se queda atrás, habiendo marcado al menos 1 gol en <b>{g1_v} de {t_v}</b> salidas recientes, alcanzando los 2 goles en <b>{g2_v}</b> ocasiones. Han logrado puntuar fuera (X2) en <b>{w_v}</b> de esos partidos.
                    </p>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 25px;">
                        <div style="background: white; color: #e63946; padding: 15px; border-radius: 10px; text-align: center; font-weight: 900;">🛡️ {pick}</div>
                        <div style="background: white; color: #e63946; padding: 15px; border-radius: 10px; text-align: center; font-weight: 900;">🥅 O 1.5: {bomba['Over 1.5']:.0%}</div>
                        <div style="background: white; color: #e63946; padding: 15px; border-radius: 10px; text-align: center; font-weight: 900;">⚽ O 2.5: {bomba['Over 2.5']:.0%}</div>
                        <div style="background: white; color: #e63946; padding: 15px; border-radius: 10px; text-align: center; font-weight: 900;">🤝 BTTS: {bomba['Btts']:.0%}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # HISTORIAL DE RESULTADOS
    st.divider()
    st.markdown("### 📜 HISTORIAL DE JORNADAS PASADAS")
    if not df_h.empty:
        c1h, c2h = st.columns(2)
        with c1h: slh = st.selectbox("Liga Histórica:", ["TODAS"] + lgs, key="l_his")
        df_hh = df_h if slh=="TODAS" else df_h[df_h['League']==slh]
        with c2h: sjh = st.selectbox("Jornada Histórica:", ["TODAS"] + sorted(df_hh['Matchday'].unique().tolist(), reverse=True) if not df_hh.empty else ["TODAS"], key="j_his")
        df_res = df_hh if sjh=="TODAS" else df_hh[df_hh['Matchday']==sjh]
        
        st.dataframe(df_res[['Date', 'Time', 'Matchday', 'League', 'Match', 'Result', '1X_S', 'X2_S', 'O15_S', 'O25_S', 'BTTS_S']].style.map(color_resultados, subset=['1X_S', 'X2_S', 'O15_S', 'O25_S', 'BTTS_S']), use_container_width=True, hide_index=True)

with pest2:
    st.info("🏀 Módulo de Baloncesto en fase beta. Próximamente integración con NBA y ligas europeas.")