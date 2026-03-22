import streamlit as st
import pandas as pd
import glob
import math
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. ESTILOS (Tarjetas limpias y filtros verdes) ---
st.markdown("""
    <style>
    /* Filtros: Blanco con letras verdes para celular */
    div[data-baseweb="select"] > div { background-color: white !important; color: #28a745 !important; }
    span[data-baseweb="select-item"], div[role="listbox"] div { color: #28a745 !important; background-color: white !important; font-weight: bold !important; }
    
    header {visibility: hidden !important;}
    footer {display: none !important;}
    [data-testid="stStatusWidget"], .stAppDeployButton { display: none !important; visibility: hidden !important; }
    
    .stApp { 
        background-image: url("https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"); 
        background-attachment: fixed; background-size: cover; 
    }
    .main .block-container { background-color: rgba(255, 255, 255, 0.95); border-radius: 10px; padding: 30px; margin-top: 20px; }
    h1, h2, h3, h4, p, span, div, label, .stMetric { color: #000000 !important; font-weight: bold; }

    /* Botón-Tarjeta Estilo Original */
    .stButton > button {
        width: 100% !important;
        background-color: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid #ddd !important;
        border-radius: 15px !important;
        padding: 20px !important;
        color: black !important;
        font-size: 1rem !important;
        white-space: pre-wrap !important;
        transition: 0.3s;
    }
    .stButton > button:hover { border-color: #28a745 !important; background-color: white !important; }
    
    .giro-balon { display: inline-block; animation: rotacion 3s infinite linear; }
    @keyframes rotacion { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA (Poisson y Fuerzas) ---
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
            p = calcular_poisson(e_l, gl) * calcular_poisson(gv, gv) # Corrección lógica simple
            p_p = calcular_poisson(e_l, gl) * calcular_poisson(e_v, gv)
            if gl > gv: p_l += p_p
            elif gl == gv: p_e += p_p
            else: p_v += p_p
            if (gl+gv) > 1.5: p_o15 += p_p
            if (gl+gv) > 2.5: p_o25 += p_p
            if gl > 0 and gv > 0: p_btts += p_p
    return p_l, p_e, p_v, p_o15, p_o25, p_btts

@st.cache_data(ttl=300)
def cargar_todo():
    archivos = glob.glob("*.csv")
    actuales, historicos, ligas = [], [], []
    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            ln = arc.replace('.csv','')
            if ln not in ligas: ligas.append(ln)
            # Cálculo de fuerzas simplificado para el ejemplo
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

df_p, df_h, lgs = cargar_todo()

# --- 4. DIÁLOGO GRANDE (Página aparte) ---
@st.dialog("📋 ANÁLISIS COMPLETO DEL PARTIDO", width="large")
def mostrar_detalle(r):
    st.title(f"⚽ {r['Partido']}")
    st.write(f"🏆 {r['Liga']} | 📅 {r['Fecha']}")
    st.divider()
    c1, c2 = st.columns(2)
    with c1: st.metric("Prob. Over 1.5", f"{r['Over 1.5']:.0%}")
    with c2: st.metric("Prob. BTTS", f"{r['BTTS']:.0%}")
    st.markdown("### 📈 Racha Histórica")
    # Filtrar racha real de los equipos
    racha = df_h[(df_h['Equipo Local'] == r['Local']) | (df_h['Equipo Visitante'] == r['Local'])].head(5)
    st.table(racha[['Fecha', 'Equipo Local', 'Equipo Visitante', 'Marcador']])

# --- 5. INTERFAZ ---
st.markdown('<h1><span class="giro-balon">⚽</span> Bet Pro League</h1>', unsafe_allow_html=True)

t1, t2 = st.tabs(["PREDICCIONES", "HISTORIAL"])

with t1:
    # A. TOP 4 PRIMERO
    st.markdown('### 🏆 TOP 4 POR MERCADO')
    if not df_p.empty:
        mks = [('1X', '🛡️', 'Doble Op.'), ('Over 1.5', '🥅', 'Over 1.5'), ('Over 2.5', '⚽', 'Over 2.5'), ('BTTS', '🤝', 'BTTS')]
        cols = st.columns(4)
        for i, (m, ico, tit) in enumerate(mks):
            with cols[i]:
                st.markdown(f"#### {ico} {tit}")
                top = df_p.nlargest(4, m)
                for idx, r in top.iterrows():
                    txt = f"🗓️ {r['Fecha']}\n{r['Liga']}\n{r['Partido']}\n{r[m]:.0%}"
                    if st.button(txt, key=f"top_{m}_{idx}"):
                        mostrar_detalle(r)

    # B. FILTROS DEBAJO DEL TOP 4
    st.divider()
    st.markdown('### 📊 FILTROS DE LIGAS')
    f1, f2 = st.columns(2)
    with f1: sl = st.selectbox("Liga:", ["TODAS"] + lgs, key="p_l")
    with f2:
        df_f = df_p if sl=="TODAS" else df_p[df_p['Liga']==sl]
        j_list = sorted(df_f['Jornada'].unique().tolist(), reverse=True) if not df_f.empty else []
        sj = st.selectbox("Jornada:", ["TODAS"] + j_list, key="p_j")

    # C. CUADRO DE EQUIPOS (EL QUE SE HABÍA PERDIDO)
    st.markdown("### 📋 Listado de Partidos")
    df_final = df_f if sj=="TODAS" else df_f[df_f['Jornada']==int(sj)]
    if not df_final.empty:
        st.dataframe(df_final[['Fecha', 'Liga', 'Partido', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']], use_container_width=True, hide_index=True)

with t2:
    st.markdown('### 📜 HISTORIAL')
    h1, h2 = st.columns(2)
    with h1: slh = st.selectbox("Filtrar Liga:", ["TODAS"] + lgs, key="h_l")
    with h2:
        # CORRECCIÓN DE ERROR df_th
        df_hist_filtro = df_h if slh=="TODAS" else df_h[df_h['Liga']==slh]
        jh_list = sorted(df_hist_filtro['Jornada'].unique().tolist(), key=lambda x: int(x), reverse=True) if not df_hist_filtro.empty else []
        sjh = st.selectbox("Filtrar Jornada:", ["TODAS"] + jh_list, key="h_j")
    
    st.dataframe(df_hist_filtro if sjh=="TODAS" else df_hist_filtro[df_hist_filtro['Jornada']==sjh], use_container_width=True, hide_index=True)