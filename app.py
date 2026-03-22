import streamlit as st
import pandas as pd
import glob
import math
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. ESTILOS ORIGINALES ---
st.markdown("""
    <style>
    /* Filtros Blancos con texto verde para móvil */
    div[data-baseweb="select"] > div { background-color: white !important; color: #28a745 !important; }
    
    header {visibility: hidden !important;}
    footer {display: none !important;}
    [data-testid="stStatusWidget"], .stAppDeployButton { display: none !important; visibility: hidden !important; }
    
    .stApp { 
        background-image: url("https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"); 
        background-attachment: fixed; background-size: cover; 
    }
    .main .block-container { background-color: rgba(255, 255, 255, 0.95); border-radius: 10px; padding: 30px; margin-top: 20px; }
    h1, h2, h3, h4, p, span, div, label, .stMetric { color: #000000 !important; font-weight: bold; }

    /* Tarjetas del Top 4 Estilo Original */
    .stButton > button {
        width: 100% !important;
        background-color: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid #ddd !important;
        border-radius: 15px !important;
        padding: 15px !important;
        color: black !important;
        font-size: 1rem !important;
        line-height: 1.4 !important;
        white-space: pre-wrap !important;
    }
    .stButton > button:hover { border-color: #28a745 !important; background-color: white !important; }
    
    .giro-balon { display: inline-block; animation: rotacion 3s infinite linear; }
    @keyframes rotacion { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES DE FORMATO ---
def aplicar_semaforo(val):
    if isinstance(val, (int, float)):
        if val >= 0.75: return 'color: #28a745; font-weight: bold;'
        elif val >= 0.55: return 'color: #ffa500; font-weight: bold;'
    return 'color: black;'

def color_historial(val):
    if '✅' in str(val): return 'color: #28a745; font-weight: bold;'
    if '❌' in str(val): return 'color: #dc3545; font-weight: bold;'
    return 'color: black;'

# --- 4. LÓGICA DE DATOS ---
def extraer_goles(resultado_str):
    numeros = re.findall(r'\d+', str(resultado_str))
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

@st.cache_data(ttl=300)
def cargar_datos():
    archivos = glob.glob("*.csv")
    actuales, historicos, ligas = [], [], []
    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            ln = arc.replace('.csv','')
            if ln not in ligas: ligas.append(ln)
            fz = {e: 1.2 for e in pd.concat([df['Equipo Local'], df['Equipo Visitante']]).unique()}
            df['Fecha_dt'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            for _, f in df.iterrows():
                pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz.get(f['Equipo Local'],1.2), fz.get(f['Equipo Visitante'],1.2))
                g = extraer_goles(f['Resultado'])
                if g:
                    p1x, px2 = pl+pe, pv+pe
                    pk = "1X" if p1x >= px2 else "X2"
                    historicos.append({'Fecha': f['Fecha'], 'Liga': ln, 'Jornada': str(int(f['Jornada'])), 'Equipo Local': f['Equipo Local'], 'Equipo Visitante': f['Equipo Visitante'], 'Marcador': f"{g[0]}-{g[1]}", 'Doble Oportunidad': f"{pk} {'✅' if (g[0]>=g[1] if pk=='1X' else g[1]>=g[0]) else '❌'}", 'Over 1.5': f"{'✅' if (g[0]+g[1])>1.5 else '❌'}", 'Over 2.5': f"{'✅' if (g[0]+g[1])>2.5 else '❌'}", 'BTTS': f"{'✅' if (g[0]>0 and g[1]>0) else '❌'}"})
                else:
                    actuales.append({'Fecha': f['Fecha'], 'Fecha_dt': f['Fecha_dt'], 'Jornada': int(f['Jornada']), 'Liga': ln, 'Local': f['Equipo Local'], 'Visitante': f['Equipo Visitante'], 'Partido': f"{f['Equipo Local']} vs {f['Equipo Visitante']}", '1X': pl+pe, 'X2': pv+pe, 'Over 1.5': po15, 'Over 2.5': po25, 'BTTS': pb})
        except: continue
    return pd.DataFrame(actuales), pd.DataFrame(historicos), sorted(ligas)

df_p, df_h, lgs = cargar_datos()

# --- 5. VENTANA DE ANÁLISIS (Dailog Grande) ---
@st.dialog("📊 ANÁLISIS COMPLETO", width="large")
def ventana_analisis(partido_data):
    st.title(f"⚽ {partido_data['Partido']}")
    st.write(f"📅 {partido_data['Fecha']} | 🏆 {partido_data['Liga']}")
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("🛡️ Doble Op.", f"{max(partido_data['1X'], partido_data['X2']):.0%}")
    c2.metric("🥅 Over 1.5", f"{partido_data['Over 1.5']:.0%}")
    c3.metric("🤝 Ambos Marcan", f"{partido_data['BTTS']:.0%}")
    st.markdown("### 📈 Racha Histórica")
    eq = partido_data['Local']
    st.write(f"**Últimos de {eq}:**")
    racha = df_h[(df_h['Equipo Local']==eq)|(df_h['Equipo Visitante']==eq)].head(5)
    st.dataframe(racha, use_container_width=True, hide_index=True)

# --- 6. INTERFAZ ---
st.markdown('<h1><span class="giro-balon">⚽</span> Bet Pro League</h1>', unsafe_allow_html=True)
t1, t2 = st.tabs(["PREDICCIONES", "HISTORIAL"])

with t1:
    # A. TOP 4
    st.markdown('### 🏆 TOP 4 POR MERCADO')
    if not df_p.empty:
        cols = st.columns(4)
        mks = [('1X', '🛡️ 1X/X2'), ('Over 1.5', '🥅 Over 1.5'), ('Over 2.5', '⚽ Over 2.5'), ('BTTS', '🤝 BTTS')]
        for i, (m, tit) in enumerate(mks):
            with cols[i]:
                st.markdown(f"#### {tit}")
                top = df_p.nlargest(4, m)
                for idx, r in top.iterrows():
                    val = f"{r[m]:.0%}"
                    txt = f"🗓️ {r['Fecha']}\n{r['Liga']}\n{r['Partido']}\n{val}"
                    if st.button(txt, key=f"t4_{m}_{idx}"):
                        ventana_analisis(r)

    # B. FILTROS
    st.divider()
    st.markdown('### 📊 FILTROS DE LIGAS')
    f1, f2 = st.columns(2)
    with f1: sl = st.selectbox("Selecciona Liga:", ["TODAS"] + lgs, key="sl_p")
    with f2:
        df_f = df_p if sl=="TODAS" else df_p[df_p['Liga']==sl]
        j_list = sorted(df_f['Jornada'].unique().tolist(), reverse=True) if not df_f.empty else []
        sj = st.selectbox("Selecciona Jornada:", ["TODAS"] + j_list, key="sj_p")

    # C. TABLA CON PORCENTAJES REALES
    st.markdown("### 📋 Predicciones de la Jornada")
    df_fin = df_f if sj=="TODAS" else df_f[df_f['Jornada']==int(sj)]
    if not df_fin.empty:
        cols_mostrar = ['Fecha', 'Liga', 'Partido', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']
        st.dataframe(
            df_fin[cols_mostrar].style.applymap(aplicar_semaforo, subset=['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS'])
            .format({c: '{:.0%}' for c in ['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']}),
            use_container_width=True, hide_index=True
        )

with t2:
    st.markdown('## 📜 HISTORIAL')
    h1, h2 = st.columns(2)
    with h1: slh = st.selectbox("Filtrar Liga:", ["TODAS"] + lgs, key="sl_h")
    with h2:
        # FIX NameError
        df_hist_f = df_h if slh=="TODAS" else df_h[df_h['Liga']==slh]
        jh_list = sorted(df_hist_f['Jornada'].unique().tolist(), key=lambda x: int(x), reverse=True) if not df_hist_f.empty else []
        sjh = st.selectbox("Filtrar Jornada:", ["TODAS"] + jh_list, key="sj_h")
    
    st.dataframe(
        df_hist_f if sjh=="TODAS" else df_hist_f[df_hist_f['Jornada']==sjh],
        use_container_width=True, hide_index=True
    ).style.applymap(color_historial, subset=['Doble Oportunidad', 'Over 1.5', 'Over 2.5', 'BTTS'])