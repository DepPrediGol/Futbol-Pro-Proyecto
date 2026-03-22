import streamlit as st
import pandas as pd
import glob
import math
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. ESTILOS (Tarjetas como la imagen y filtros verdes) ---
st.markdown("""
    <style>
    /* Filtros Verdes */
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

    /* Botón-Tarjeta Organizado */
    .stButton > button {
        width: 100% !important;
        height: auto !important;
        background-color: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid #ddd !important;
        border-radius: 15px !important;
        padding: 20px !important;
        color: black !important;
        font-size: 1rem !important;
        line-height: 1.5 !important;
        white-space: pre-wrap !important;
        display: block !important;
    }
    .stButton > button:hover {
        border-color: #28a745 !important;
        background-color: #ffffff !important;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.1) !important;
    }
    .giro-balon { display: inline-block; animation: rotacion 3s infinite linear; }
    @keyframes rotacion { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE DATOS ---
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

def calcular_fuerzas(df_h):
    equipos = pd.concat([df_h['Equipo Local'], df_h['Equipo Visitante']]).unique()
    f = {e: 1.2 for e in equipos}
    for _, fila in df_h.iterrows():
        g = extraer_goles(fila['Resultado'])
        if g:
            f[fila['Equipo Local']] += 0.20 if g[0] > g[1] else 0.05 * g[0]
            f[fila['Equipo Visitante']] += 0.20 if g[1] > g[0] else 0.05 * g[1]
    return f

@st.cache_data(ttl=300)
def cargar_todo():
    archivos = glob.glob("*.csv")
    actuales, historicos, ligas = [], [], []
    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            ln = arc.replace('.csv','')
            if ln not in ligas: ligas.append(ln)
            fz = calcular_fuerzas(df)
            df['Fecha_dt'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            for _, f in df.iterrows():
                pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz.get(f['Equipo Local'],1.2), fz.get(f['Equipo Visitante'],1.2))
                g = extraer_goles(f['Resultado'])
                if g:
                    p1x, px2 = pl+pe, pv+pe
                    pk = "1X" if p1x >= px2 else "X2"
                    pr = max(p1x, px2)
                    historicos.append({
                        'Fecha': f['Fecha'], 'Liga': ln, 'Jornada': str(int(f['Jornada'])),
                        'Equipo Local': f['Equipo Local'], 'Equipo Visitante': f['Equipo Visitante'], 
                        'Marcador': f"{g[0]}-{g[1]}",
                        'Doble Oportunidad': f"{pk} {'✅' if (g[0]>=g[1] if pk=='1X' else g[1]>=g[0]) else '❌'} ({pr:.0%})",
                        'Over 1.5': f"{'✅' if (g[0]+g[1])>1.5 else '❌'} ({po15:.0%})", 
                        'Over 2.5': f"{'✅' if (g[0]+g[1])>2.5 else '❌'} ({po25:.0%})", 
                        'BTTS': f"{'✅' if (g[0]>0 and g[1]>0) else '❌'} ({pb:.0%})"
                    })
                else:
                    actuales.append({
                        'Fecha': f['Fecha'], 'Fecha_dt': f['Fecha_dt'], 'Jornada': int(f['Jornada']), 'Liga': ln, 
                        'Local': f['Equipo Local'], 'Visitante': f['Equipo Visitante'],
                        'Partido': f"{f['Equipo Local']} vs {f['Equipo Visitante']}",
                        '1X': pl+pe, 'X2': pv+pe, 'Over 1.5': po15, 'Over 2.5': po25, 'BTTS': pb
                    })
        except: continue
    return pd.DataFrame(actuales), pd.DataFrame(historicos), sorted(ligas)

df_p, df_h, lgs = cargar_todo()

# --- 4. VENTANA DE ANÁLISIS ---
@st.dialog("📋 Análisis de Racha")
def mostrar_analisis(r):
    st.markdown(f"### {r['Local']} vs {r['Visitante']}")
    st.write(f"🏆 {r['Liga']} | 📅 {r['Fecha']}")
    st.divider()
    for eq in [r['Local'], r['Visitante']]:
        st.markdown(f"**Racha Reciente: {eq}**")
        # Corrección de variable NameError
        df_eq = df_h[(df_h['Equipo Local']==eq)|(df_h['Equipo Visitante']==eq)].iloc[::-1].head(5)
        if not df_eq.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Doble Op.", f"{(df_eq['Doble Oportunidad'].str.contains('✅').sum()/len(df_eq)):.0%}")
            c2.metric("Over 1.5", f"{(df_eq['Over 1.5'].str.contains('✅').sum()/len(df_eq)):.0%}")
            c3.metric("BTTS", f"{(df_eq['BTTS'].str.contains('✅').sum()/len(df_eq)):.0%}")
            st.dataframe(df_eq, use_container_width=True, hide_index=True)

# --- 5. INTERFAZ ---
st.markdown('<h1><span class="giro-balon">⚽</span> Bet Pro League</h1>', unsafe_allow_html=True)

t1, t2 = st.tabs(["PREDICCIONES", "HISTORIAL"])

with t1:
    # FILTROS ARRIBA
    st.markdown('### 📊 FILTROS')
    cf1, cf2 = st.columns(2)
    with cf1: sl = st.selectbox("Selecciona Liga:", ["TODAS"] + lgs, key="p_liga")
    with cf2:
        df_l = df_p if sl=="TODAS" else df_p[df_p['Liga']==sl]
        jorns = sorted(df_l['Jornada'].unique().tolist(), reverse=True) if not df_l.empty else []
        sj = st.selectbox("Selecciona Jornada:", ["TODAS"] + jorns, key="p_jorn")

    # TOP 4 POR MERCADO
    st.markdown('### 🏆 TOP 4 POR MERCADO')
    df_f = df_l[df_l['Jornada']==int(sj)] if sj!="TODAS" else df_l
    
    if not df_f.empty:
        mks = [('DOBLE', '🛡️', 'Doble Oportunidad'), ('Over 1.5', '🥅', 'Over 1.5'), ('Over 2.5', '⚽', 'Over 2.5'), ('BTTS', '🤝', 'Ambos Marcan')]
        cols = st.columns(4)
        for i, (m, ico, tit) in enumerate(mks):
            with cols[i]:
                st.markdown(f'#### {ico} {tit}')
                if m == 'DOBLE':
                    df_f['Mx'] = df_f[['1X', 'X2']].max(axis=1)
                    df_f['Tp'] = df_f.apply(lambda x: '1X' if x['1X'] >= x['X2'] else 'X2', axis=1)
                    top = df_f.nlargest(4, 'Mx')
                else: top = df_f.nlargest(4, m)
                
                for idx, r in top.iterrows():
                    v = f"{r['Tp'] if m=='DOBLE' else ''} {r['Mx']:.0%}" if m=='DOBLE' else f"{r[m]:.0%}"
                    # Texto del cuadro organizado según imagen
                    txt = f"📅 {r['Fecha']}\n{r['Liga']}\n{r['Partido']}\n{v}"
                    if st.button(txt, key=f"t4_{m}_{idx}"):
                        mostrar_analisis(r)

with t2:
    st.markdown('## 📜 HISTORIAL')
    h1, h2 = st.columns(2)
    with h1: slh = st.selectbox("Filtrar Liga:", ["TODAS"] + lgs, key="h_liga")
    with h2:
        # Corrección de NameError definitiva
        df_hh = df_h if slh=="TODAS" else df_h[df_h['Liga']==slh]
        jorns_h = sorted(df_hh['Jornada'].unique().tolist(), key=lambda x: int(x), reverse=True) if not df_hh.empty else []
        sjh = st.selectbox("Filtrar Jornada:", ["TODAS"] + jorns_h, key="h_jorn")
    
    df_res = df_hh if sjh=="TODAS" else df_hh[df_hh['Jornada']==sjh]
    st.dataframe(df_res, use_container_width=True, hide_index=True)