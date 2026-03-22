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
    .top4-card { padding: 12px; border-radius: 10px; background: rgba(255,255,255,0.8); border: 1px solid #ddd; text-align: center; margin-bottom: 10px; min-height: 120px; }
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

def color_historial(val):
    if '✅' in str(val): return 'color: #28a745; font-weight: bold;'
    if '❌' in str(val): return 'color: #dc3545; font-weight: bold;'
    return 'color: black;'

def extraer_goles(resultado_str):
    if pd.isna(resultado_str): return None
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

# --- 4. CARGA Y PROCESAMIENTO ---
@st.cache_data(ttl=300)
def cargar_y_procesar():
    archivos = glob.glob("*.csv")
    raw_data = []
    ligas = []
    
    # Carga inicial de todos los archivos
    for arc in archivos:
        try:
            temp_df = pd.read_csv(arc)
            ln = arc.replace('.csv','')
            temp_df['Liga'] = ln
            if ln not in ligas: ligas.append(ln)
            raw_data.append(temp_df)
        except: continue
    
    if not raw_data: return pd.DataFrame(), pd.DataFrame(), []
    
    full_df = pd.concat(raw_data, ignore_index=True)
    full_df['Fecha_dt'] = pd.to_datetime(full_df['Fecha'], dayfirst=True, errors='coerce')
    
    # Calcular Fuerzas globales basadas en resultados reales
    fuerzas = {}
    for _, fila in full_df.iterrows():
        goles = extraer_goles(fila.get('Resultado'))
        loc, vis = fila['Equipo Local'], fila['Equipo Visitante']
        if loc not in fuerzas: fuerzas[loc] = 1.2
        if vis not in fuerzas: fuerzas[vis] = 1.2
        if goles:
            fuerzas[loc] += 0.15 if goles[0] > goles[1] else 0.05
            fuerzas[vis] += 0.15 if goles[1] > goles[0] else 0.05

    actuales, historicos = [], []
    for _, f in full_df.iterrows():
        fz_l = fuerzas.get(f['Equipo Local'], 1.2)
        fz_v = fuerzas.get(f['Equipo Visitante'], 1.2)
        pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz_l, fz_v)
        g = extraer_goles(f.get('Resultado'))
        
        if g:
            p1x, px2 = pl+pe, pv+pe
            pk = "1X" if p1x >= px2 else "X2"
            pr = max(p1x, px2)
            historicos.append({
                'Fecha': f['Fecha'], 'Liga': f['Liga'], 'Jornada': str(f['Jornada']),
                'Equipo Local': f['Equipo Local'], 'Equipo Visitante': f['Equipo Visitante'], 
                'Marcador': f"{g[0]}-{g[1]}",
                'Doble Oportunidad': f"{pk} {'✅' if (g[0]>=g[1] if pk=='1X' else g[1]>=g[0]) else '❌'} ({pr:.0%})",
                'Over 1.5': f"{'✅' if (g[0]+g[1])>1.5 else '❌'} ({po15:.0%})", 
                'Over 2.5': f"{'✅' if (g[0]+g[1])>2.5 else '❌'} ({po25:.0%})", 
                'BTTS': f"{'✅' if (g[0]>0 and g[1]>0) else '❌'} ({pb:.0%})"
            })
        else:
            actuales.append({
                'Fecha': f['Fecha'], 'Fecha_dt': f['Fecha_dt'], 'Jornada': f['Jornada'], 'Liga': f['Liga'], 
                'Local': f['Equipo Local'], 'Visitante': f['Equipo Visitante'],
                'Partido': f"{f['Equipo Local']} vs {f['Equipo Visitante']}",
                '1X': pl+pe, 'X2': pv+pe, 'Over 1.5': po15, 'Over 2.5': po25, 'BTTS': pb
            })
            
    return pd.DataFrame(actuales), pd.DataFrame(historicos), sorted(ligas)

df_p, df_h, lgs = cargar_y_procesar()

# --- 5. INTERFAZ ---
st.markdown('<h1><span class="giro-balon">⚽</span> Bet Pro League</h1>', unsafe_allow_html=True)
t1, t2 = st.tabs(["PREDICCIONES", "HISTORIAL"])

with t1:
    # A. TOP 4 (Próximos Partidos)
    if not df_p.empty:
        hoy = datetime.now()
        df_t4 = df_p[df_p['Fecha_dt'] >= hoy].sort_values('Fecha_dt').head(20)
        st.markdown('### 🏆 TOP 4 POR MERCADO')
        c_t4 = st.columns(4)
        mks = [('1X', '🛡️ Doble Op.'), ('Over 1.5', '🥅 Over 1.5'), ('Over 2.5', '⚽ Over 2.5'), ('BTTS', '🤝 BTTS')]
        
        for i, (m, tit) in enumerate(mks):
            with c_t4[i]:
                st.markdown(f"#### {tit}")
                top = df_t4.nlargest(4, m)
                for _, r in top.iterrows():
                    val = f"{r[m]:.0%}"
                    st.markdown(f'''<div class="top4-card">🗓️ {r["Fecha"]}<br><small>{r["Liga"]}</small><br><b>{r["Partido"]}</b><br><span style="color:#28a745; font-size:1.2rem;">{val}</span></div>''', unsafe_allow_html=True)

    # B. FILTROS
    st.divider()
    st.markdown('### 📊 FILTROS DE PREDICCIONES')
    f1, f2 = st.columns(2)
    with f1: sl = st.selectbox("Selecciona Liga:", ["TODAS"] + lgs, key="filt_l")
    with f2:
        df_temp = df_p if sl=="TODAS" else df_p[df_p['Liga']==sl]
        j_list = sorted(df_temp['Jornada'].unique().tolist(), reverse=True) if not df_temp.empty else []
        sj = st.selectbox("Selecciona Jornada:", ["TODAS"] + j_list, key="filt_j")

    # C. TABLA CON PORCENTAJES REALES
    df_fin = df_temp if sj=="TODAS" else df_temp[df_temp['Jornada']==sj]
    if not df_fin.empty:
        st.dataframe(
            df_fin[['Fecha', 'Liga', 'Partido', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']]
            .style.applymap(aplicar_semaforo, subset=['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS'])
            .format({c: '{:.0%}' for c in ['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']}),
            use_container_width=True, hide_index=True
        )

with t2:
    st.markdown('### 📜 HISTORIAL DE RESULTADOS')
    if not df_h.empty:
        h1, h2 = st.columns(2)
        with h1: slh = st.selectbox("Filtrar por Liga:", ["TODAS"] + lgs, key="hist_l")
        with h2:
            df_h_f = df_h if slh=="TODAS" else df_h[df_h['Liga']==slh]
            jh_list = sorted(df_h_f['Jornada'].unique().tolist(), reverse=True) if not df_h_f.empty else []
            sjh = st.selectbox("Filtrar por Jornada:", ["TODAS"] + jh_list, key="hist_j")
        
        # Tabla de historial con colores y porcentajes
        df_res = df_h_f if sjh=="TODAS" else df_h_f[df_h_f['Jornada']==sjh]
        st.dataframe(
            df_res.style.applymap(color_historial, subset=['Doble Oportunidad', 'Over 1.5', 'Over 2.5', 'BTTS']),
            use_container_width=True, hide_index=True
        )