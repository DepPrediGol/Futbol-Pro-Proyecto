import streamlit as st
import pandas as pd
import glob
import math
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. ESTILOS ---
st.markdown("""
    <style>
    header {visibility: hidden !important;}
    footer {display: none !important;}
    [data-testid="stStatusWidget"], .stAppDeployButton { display: none !important; visibility: hidden !important; }
    .stApp { 
        background-image: url("https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"); 
        background-attachment: fixed; background-size: cover; 
    }
    .main .block-container { background-color: rgba(255, 255, 255, 0.95); border-radius: 10px; padding: 30px; margin-top: 20px; }
    h1, h2, h3, h4, p, span, div, label, .stMetric { color: #000000 !important; font-weight: bold; }
    .top4-card { padding: 12px; border-radius: 10px; background: rgba(255,255,255,0.8); border: 1px solid #ddd; text-align: center; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES ---
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
    nums = re.findall(r'\d+', str(resultado_str))
    return (int(nums[0]), int(nums[1])) if len(nums) >= 2 else None

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

# --- 4. PROCESAMIENTO ---
@st.cache_data(ttl=300)
def cargar_datos():
    archivos = glob.glob("*.csv")
    actuales, historicos, ligas = [], [], []
    
    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            ln = arc.replace('.csv','')
            if ln not in ligas: ligas.append(ln)
            
            # Limpiar Jornada para que sea entero siempre
            df['Jornada'] = pd.to_numeric(df['Jornada'], errors='coerce').fillna(0).astype(int)
            df['Fecha_dt'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            
            # Calcular fuerzas de equipos
            equipos = pd.concat([df['Equipo Local'], df['Equipo Visitante']]).unique()
            fz = {e: 1.2 for e in equipos}
            for _, fila in df.iterrows():
                g = extraer_goles(fila.get('Resultado'))
                if g:
                    fz[fila['Equipo Local']] += 0.15 if g[0] > g[1] else 0.05
                    fz[fila['Equipo Visitante']] += 0.15 if g[1] > g[0] else 0.05

            for _, f in df.iterrows():
                pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz.get(f['Equipo Local'],1.2), fz.get(f['Equipo Visitante'],1.2))
                g = extraer_goles(f.get('Resultado'))
                
                if g:
                    p1x, px2 = pl+pe, pv+pe
                    pk = "1X" if p1x >= px2 else "X2"
                    pr = max(p1x, px2)
                    historicos.append({
                        'Fecha': f['Fecha'], 'Liga': ln, 'Jornada': f['Jornada'],
                        'Equipo Local': f['Equipo Local'], 'Equipo Visitante': f['Equipo Visitante'], 
                        'Marcador': f"{g[0]}-{g[1]}",
                        'Doble Oportunidad': f"{pk} {'✅' if (g[0]>=g[1] if pk=='1X' else g[1]>=g[0]) else '❌'} ({pr:.0%})",
                        'Over 1.5': f"{'✅' if (g[0]+g[1])>1.5 else '❌'} ({po15:.0%})", 
                        'Over 2.5': f"{'✅' if (g[0]+g[1])>2.5 else '❌'} ({po25:.0%})", 
                        'BTTS': f"{'✅' if (g[0]>0 and g[1]>0) else '❌'} ({pb:.0%})"
                    })
                else:
                    actuales.append({
                        'Fecha': f['Fecha'], 'Fecha_dt': f['Fecha_dt'], 'Jornada': f['Jornada'], 'Liga': ln, 
                        'Local': f['Equipo Local'], 'Visitante': f['Equipo Visitante'],
                        'Partido': f"{f['Equipo Local']} vs {f['Equipo Visitante']}",
                        '1X': pl+pe, 'X2': pv+pe, 'Over 1.5': po15, 'Over 2.5': po25, 'BTTS': pb
                    })
        except: continue
    return pd.DataFrame(actuales), pd.DataFrame(historicos), sorted(ligas)

df_p, df_h, lgs = cargar_datos()

# --- 5. INTERFAZ ---
st.markdown('<h1>⚽ Bet Pro League</h1>', unsafe_allow_html=True)
t1, t2 = st.tabs(["PREDICCIONES", "HISTORIAL"])

with t1:
    # A. TOP 4
    if not df_p.empty:
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fechas = df_p[df_p['Fecha_dt'] >= hoy]['Fecha_dt'].unique()
        if len(fechas) > 0:
            prox = min(fechas)
            df_t4 = df_p[df_p['Fecha_dt'] == prox].copy()
            st.markdown(f"### 🏆 TOP 4 POR MERCADO ({prox.strftime('%d/%m/%Y')})")
            cols = st.columns(4)
            mks = [('1X', '🛡️ 1X'), ('Over 1.5', '🥅 O1.5'), ('Over 2.5', '⚽ O2.5'), ('BTTS', '🤝 BTTS')]
            for i, (m, tit) in enumerate(mks):
                with cols[i]:
                    st.markdown(f"#### {tit}")
                    top = df_t4.nlargest(4, m)
                    for _, r in top.iterrows():
                        st.markdown(f'<div class="top4-card"><b>{r["Partido"]}</b><br><span style="color:#28a745;">{r[m]:.0%}</span></div>', unsafe_allow_html=True)
                        with st.popover("📊 Ver Racha"):
                            for eq in [r['Local'], r['Visitante']]:
                                st.write(f"**{eq}**")
                                racha = df_h[(df_h['Equipo Local']==eq)|(df_h['Equipo Visitante']==eq)].tail(5)
                                st.dataframe(racha[['Marcador', 'Doble Oportunidad', 'Over 1.5', 'BTTS']], hide_index=True)

    # B. FILTROS Y TABLA
    st.divider()
    st.markdown('### 📊 FILTROS')
    c1, c2 = st.columns(2)
    with c1: sl = st.selectbox("Liga:", ["TODAS"] + lgs, key="p_l")
    with c2:
        df_f = df_p if sl=="TODAS" else df_p[df_p['Liga']==sl]
        js = sorted(df_f['Jornada'].unique().tolist(), reverse=True) if not df_f.empty else []
        sj = st.selectbox("Jornada:", ["TODAS"] + js, key="p_j")
    
    df_fin = df_f if sj=="TODAS" else df_f[df_f['Jornada']==sj]
    st.dataframe(df_fin[['Fecha', 'Jornada', 'Liga', 'Partido', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']]
                 .style.applymap(aplicar_semaforo, subset=['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS'])
                 .format({'1X':'{:.0%}', 'X2':'{:.0%}', 'Over 1.5':'{:.0%}', 'Over 2.5':'{:.0%}', 'BTTS':'{:.0%}'}), 
                 use_container_width=True, hide_index=True)

with t2:
    # C. HISTORIAL
    st.markdown('### 📜 HISTORIAL')
    h1, h2 = st.columns(2)
    with h1: slh = st.selectbox("Filtrar Liga:", ["TODAS"] + lgs, key="h_l")
    with h2:
        df_hf = df_h if slh=="TODAS" else df_h[df_h['Liga']==slh]
        jh = sorted(df_hf['Jornada'].unique().tolist(), reverse=True) if not df_hf.empty else []
        sjh = st.selectbox("Filtrar Jornada:", ["TODAS"] + jh, key="h_j")
    
    df_res = df_hf if sjh=="TODAS" else df_hf[df_hf['Jornada']==sjh]
    st.dataframe(df_res.style.applymap(color_letras_historial, subset=['Doble Oportunidad', 'Over 1.5', 'Over 2.5', 'BTTS']), 
                 use_container_width=True, hide_index=True)