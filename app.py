import streamlit as st
import pandas as pd
import glob
import math
import re
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. ESTILOS ORIGINALES COMPLETOS ---
st.markdown("""
    <style>
    @media (max-width: 640px) {
        .main .block-container { padding: 10px !important; margin-top: 0px !important; }
        h1 { font-size: 1.5rem !important; }
        .top4-card { min-height: 80px !important; font-size: 0.8rem !important; }
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
    
    /* Botones del Top 4 que parecen tarjetas */
    .stButton > button {
        width: 100% !important;
        background-color: rgba(255, 255, 255, 0.8) !important;
        border: 1px solid #ddd !important;
        border-radius: 12px !important;
        padding: 10px !important;
        color: black !important;
        text-align: center !important;
        line-height: 1.2 !important;
    }
    .stButton > button:hover { border-color: #28a745 !important; background-color: white !important; }
    
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

# --- 4. VENTANA MODAL (EL CAMBIO QUE QUERÍAS) ---
@st.dialog("📊 DETALLES Y RACHA", width="large")
def mostrar_modal_racha(partido_info, df_hist):
    st.write(f"### {partido_info['Partido']}")
    st.write(f"🏆 {partido_info['Liga']} | 📅 {partido_info['Fecha']}")
    st.divider()
    
    col1, col2 = st.columns(2)
    for i, eq in enumerate([partido_info['Local'], partido_info['Visitante']]):
        with [col1, col2][i]:
            st.markdown(f"#### 📈 Racha: {eq}")
            df_eq = df_hist[(df_hist['Equipo Local']==eq)|(df_hist['Equipo Visitante']==eq)].iloc[::-1].head(5)
            if not df_eq.empty:
                st.dataframe(df_eq[['Fecha', 'Marcador', 'Doble Oportunidad', 'Over 1.5']], use_container_width=True, hide_index=True)
            else:
                st.info("Sin historial disponible.")

# --- 5. CARGA DE DATOS ---
@st.cache_data(ttl=300)
def cargar_todo():
    archivos = glob.glob("*.csv")
    if not archivos: return pd.DataFrame(), pd.DataFrame(), []
    
    # Unimos todo para calcular fuerzas globales REALES
    lista_dfs = []
    for arc in archivos:
        try:
            d = pd.read_csv(arc)
            d['Liga'] = arc.replace('.csv','')
            lista_dfs.append(d)
        except: continue
    
    full_data = pd.concat(lista_dfs, ignore_index=True)
    equipos = pd.concat([full_data['Equipo Local'], full_data['Equipo Visitante']]).unique()
    fz = {e: 1.2 for e in equipos}
    for _, fila in full_data.iterrows():
        g = extraer_goles(fila.get('Resultado'))
        if g:
            fz[fila['Equipo Local']] += 0.20 if g[0] > g[1] else 0.05
            fz[fila['Equipo Visitante']] += 0.20 if g[1] > g[0] else 0.05

    actuales, historicos, ligas = [], [], sorted(full_data['Liga'].unique().tolist())
    
    full_data['Fecha_dt'] = pd.to_datetime(full_data['Fecha'], dayfirst=True, errors='coerce')
    # FIX JORNADA: Forzar a entero para quitar el .0
    full_data['Jornada'] = pd.to_numeric(full_data['Jornada'], errors='coerce').fillna(0).astype(int)

    for _, f in full_data.iterrows():
        pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz.get(f['Equipo Local'],1.2), fz.get(f['Equipo Visitante'],1.2))
        g = extraer_goles(f.get('Resultado'))
        
        if g:
            p1x, px2 = pl+pe, pv+pe
            pk = "1X" if p1x >= px2 else "X2"
            pr = max(p1x, px2)
            historicos.append({
                'Fecha': f['Fecha'], 'Liga': f['Liga'], 'Jornada': f['Jornada'],
                'Equipo Local': f['Equipo Local'], 'Equipo Visitante': f['Equipo Visitante'], 
                'Marcador': f"{g[0]} - {g[1]}", # Separador de guion
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
            
    return pd.DataFrame(actuales), pd.DataFrame(historicos), ligas

df_p, df_h, lgs = cargar_todo()

# --- 6. INTERFAZ ---
st.markdown('<h1><span class="giro-balon">⚽</span> Bet Pro League</h1>', unsafe_allow_html=True)
t1, t2 = st.tabs(["PREDICCIONES", "HISTORIAL"])

with t1:
    if not df_p.empty:
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fechas_futuras = df_p[df_p['Fecha_dt'] >= hoy]['Fecha_dt'].unique()
        
        if len(fechas_futuras) > 0:
            prox_f = min(fechas_futuras)
            df_t4 = df_p[df_p['Fecha_dt'] == prox_f].copy()
            st.markdown(f'### 🏆 TOP 4 POR MERCADO ({prox_f.strftime("%d/%m/%Y")})')
            
            mks = [('1X', '🛡️ Doble Op.'), ('Over 1.5', '🥅 Over 1.5'), ('Over 2.5', '⚽ Over 2.5'), ('BTTS', '🤝 BTTS')]
            cols = st.columns(4)
            for i, (m, tit) in enumerate(mks):
                with cols[i]:
                    st.markdown(f'#### {tit}')
                    top = df_t4.nlargest(4, m)
                    for idx, r in top.iterrows():
                        # BOTÓN QUE ACTIVA EL DIALOG
                        btn_label = f"{r['Partido']}\n{r[m]:.0%}"
                        if st.button(btn_label, key=f"t4_{m}_{idx}"):
                            mostrar_modal_racha(r, df_h)

        st.divider()
        st.markdown('### 📊 FILTROS')
        c1, c2 = st.columns(2)
        with c1: sl = st.selectbox("Liga:", ["TODAS"] + lgs, key="p1")
        with c2:
            df_fl = df_p if sl=="TODAS" else df_p[df_p['Liga']==sl]
            j_list = sorted(df_fl['Jornada'].unique().tolist(), reverse=True) if not df_fl.empty else []
            sj = st.selectbox("Jornada:", ["TODAS"] + j_list, key="p2")
        
        df_fin = df_fl if sj=="TODAS" else df_fl[df_fl['Jornada']==sj]
        st.dataframe(df_fin[['Fecha', 'Jornada', 'Liga', 'Partido', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']]
                     .style.applymap(aplicar_semaforo, subset=['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS'])
                     .format({c: '{:.0%}' for c in ['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']}), 
                     use_container_width=True, hide_index=True)

with t2:
    st.markdown('## 📜 HISTORIAL')
    if not df_h.empty:
        h1, h2 = st.columns(2)
        with h1: slh = st.selectbox("Liga:", ["TODAS"] + lgs, key="h1")
        with h2:
            df_hh = df_h if slh=="TODAS" else df_h[df_h['Liga']==slh]
            jh_list = sorted(df_hh['Jornada'].unique().tolist(), reverse=True) if not df_hh.empty else []
            sjh = st.selectbox("Jornada:", ["TODAS"] + jh_list, key="h2")
        
        df_res = df_hh if sjh=="TODAS" else df_hh[df_hh['Jornada']==sjh]
        st.dataframe(df_res.style.applymap(color_letras_historial, subset=['Doble Oportunidad', 'Over 1.5', 'Over 2.5', 'BTTS']), 
                     use_container_width=True, hide_index=True)