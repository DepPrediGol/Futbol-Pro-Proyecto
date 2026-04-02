import streamlit as st
import pandas as pd
import glob
import math
import re
import os
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. ESTILOS PERSONALIZADOS Y RESPONSIVE ---
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
    
    .stButton > button {
        width: 100% !important; background-color: white !important; color: black !important;
        border: 1px solid #ddd !important; border-radius: 12px !important; padding: 15px !important;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.1) !important; transition: all 0.3s ease !important;
        height: auto !important; min-height: 120px !important; white-space: pre-line !important;
    }
    .giro-balon { display: inline-block; animation: rotacion 3s infinite linear; }
    @keyframes rotacion { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES DE LÓGICA ---
def aplicar_semaforo(val):
    try:
        if isinstance(val, (int, float)):
            if val >= 0.75: return 'color: #28a745; font-weight: bold;'
            elif val >= 0.55: return 'color: #ffa500; font-weight: bold;'
    except: pass
    return 'color: black;'

def color_letras_historial(val):
    v = str(val)
    if '✅' in v: return 'color: #28a745; font-weight: bold;'
    if '❌' in v: return 'color: #dc3545; font-weight: bold;'
    return 'color: black;'

def extraer_goles(resultado_str):
    if pd.isna(resultado_str): return None
    numeros = re.findall(r'\d+', str(resultado_str).replace(':', '-'))
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

# --- 4. VENTANA MODAL (ANÁLISIS DETALLADO) ---
@st.dialog("📊 ANÁLISIS DETALLADO", width="large")
def ventana_analisis(r, df_h):
    st.title(f"⚽ {r['Partido']}")
    st.subheader(f"🏆 {r['Liga']} | 📅 {r['Fecha']}")
    st.divider()
    for eq in [r['Local'], r['Visitante']]:
        st.markdown(f"#### 📈 Rendimiento Reciente: {eq}")
        df_eq = df_h[(df_h['Local'] == eq) | (df_h['Visitante'] == eq)].iloc[::-1].head(5)
        if not df_eq.empty:
            c1, c2, c3 = st.columns(3)
            m_1x = (df_eq['Doble Oportunidad'].str.contains('✅').sum() / len(df_eq))
            m_o15 = (df_eq['Over 1.5'].str.contains('✅').sum() / len(df_eq))
            m_btts = (df_eq['BTTS'].str.contains('✅').sum() / len(df_eq))
            c1.metric("Efectividad 1X/X2", f"{m_1x:.0%}")
            c2.metric("Efectividad O1.5", f"{m_o15:.0%}")
            c3.metric("Efectividad BTTS", f"{m_btts:.0%}")
            st.dataframe(df_eq, use_container_width=True, hide_index=True)
        st.divider()

# --- 5. CARGA MASIVA RECURSIVA ---
@st.cache_data(ttl=300)
def cargar_datos_proyecto():
    archivos = glob.glob("**/*.csv", recursive=True)
    archivos.sort()
    actuales, historicos, ligas = [], [], []
    fz = {}

    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            ln = os.path.basename(arc).replace('.csv','')
            if ln not in ligas: ligas.append(ln)
            df['Jornada'] = pd.to_numeric(df['Jornada'], errors='coerce').fillna(0).astype(int)
            df['Fecha_dt'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            
            for _, fila in df.iterrows():
                loc, vis = fila['Equipo Local'], fila['Equipo Visitante']
                if loc not in fz: fz[loc] = 1.2
                if vis not in fz: fz[vis] = 1.2
                g = extraer_goles(fila.get('Resultado'))
                if g:
                    fz[loc] += 0.20 if g[0] > g[1] else 0.05
                    fz[vis] += 0.20 if g[1] > g[0] else 0.05
                    pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz[loc], fz[vis])
                    pk = "1X" if (pl+pe) >= (pv+pe) else "X2"
                    historicos.append({
                        'Fecha': fila['Fecha'], 'Liga': ln, 'Jornada': fila['Jornada'],
                        'Local': loc, 'Visitante': vis, 'Marcador': f"{g[0]}-{g[1]}",
                        'Doble Oportunidad': f"{pk} {'✅' if (g[0]>=g[1] if pk=='1X' else g[1]>=g[0]) else '❌'}",
                        'Over 1.5': f"{'✅' if (g[0]+g[1])>1.5 else '❌'}", 
                        'Over 2.5': f"{'✅' if (g[0]+g[1])>2.5 else '❌'}", 
                        'BTTS': f"{'✅' if (g[0]>0 and g[1]>0) else '❌'}",
                        'G_L': g[0], 'G_V': g[1]
                    })
                else:
                    pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz[loc], fz[vis])
                    actuales.append({
                        'Fecha': fila['Fecha'], 'Fecha_dt': fila['Fecha_dt'], 'Jornada': fila['Jornada'], 
                        'Liga': ln, 'Local': loc, 'Visitante': vis, 'Partido': f"{loc} vs {vis}",
                        '1X': pl+pe, 'X2': pv+pe, 'Over 1.5': po15, 'Over 2.5': po25, 'BTTS': pb
                    })
        except: continue
    return pd.DataFrame(actuales), pd.DataFrame(historicos), sorted(ligas)

df_p, df_h, lgs = cargar_datos_proyecto()

# --- 6. INTERFAZ ---
st.markdown('<h1><span class="giro-balon">⚽</span> Bet Pro League</h1>', unsafe_allow_html=True)
t1, t2 = st.tabs(["PREDICCIONES", "HISTORIAL"])

with t1:
    if not df_p.empty:
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fechas_futuras = df_p[df_p['Fecha_dt'] >= hoy]['Fecha_dt'].unique()
        if len(fechas_futuras) > 0:
            f_prox = min(fechas_futuras)
            df_t4 = df_p[df_p['Fecha_dt'] == f_prox].copy()
            st.markdown(f"### 🏆 TOP 4 POR MERCADO ({f_prox.strftime('%d/%m/%Y')})")
            mks = [('1X', '🛡️ 1X/X2'), ('Over 1.5', '🥅 Over 1.5'), ('Over 2.5', '⚽ Over 2.5'), ('BTTS', '🤝 BTTS')]
            cols = st.columns(4)
            for i, (m, tit) in enumerate(mks):
                with cols[i]:
                    st.markdown(f"#### {tit}")
                    top = df_t4.nlargest(4, m)
                    for idx, r in top.iterrows():
                        if st.button(f"{r['Partido']}\n⭐ Prob: {r[m]:.0%}", key=f"t4_{m}_{idx}"): ventana_analisis(r, df_h)

        st.divider()
        st.markdown("### 📊 LIGAS Y JORNADAS")
        c1, c2 = st.columns(2)
        with c1: sl = st.selectbox("Liga:", ["TODAS"] + lgs, key="filt_l1")
        with c2:
            df_fl = df_p if sl=="TODAS" else df_p[df_p['Liga']==sl]
            lj = sorted(df_fl['Jornada'].unique().tolist(), reverse=True) if not df_fl.empty else [0]
            sj = st.selectbox("Jornada:", ["TODAS"] + lj, key="filt_j1")
        
        df_fin = df_fl if sj=="TODAS" else df_fl[df_fl['Jornada']==sj]
        st.dataframe(df_fin[['Fecha', 'Jornada', 'Liga', 'Partido', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']].style.applymap(aplicar_semaforo, subset=['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']).format({c: '{:.0%}' for c in ['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']}), use_container_width=True, hide_index=True)

        if not df_fin.empty:
            st.divider()
            d_top = df_fin.loc[df_fin[['Over 1.5', 'Over 2.5', 'BTTS']].max(axis=1).idxmax()]
            loc, vis = d_top['Local'], d_top['Visitante']
            h_l, h_v = df_h[df_h['Local'] == loc], df_h[df_h['Visitante'] == vis]
            if not h_l.empty and not h_v.empty:
                m1_l, m2_l = (h_l['G_L'] >= 1).sum(), (h_l['G_L'] >= 2).sum()
                w_l = (h_l['G_L'] >= h_l['G_V']).sum()
                st.markdown(f"""
                <div style="background-color: #ff4b4b; padding: 25px; border-radius: 15px; color: white; text-align: center;">
                    <h2>💣 PREDICCIÓN BOMBA: {d_top['Partido']} 💣</h2>
                    <p>El local marcando en {m1_l}/{len(h_l)} y marcando +1.5 en {m2_l} partidos. Invicto en casa: {w_l}/{len(h_l)}.</p>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                        <div style="background: white; color: black; padding: 10px; border-radius: 10px;">🛡️ <b>Prob. 1X/X2: {max(d_top['1X'], d_top['X2']):.0%}</b></div>
                        <div style="background: white; color: black; padding: 10px; border-radius: 10px;">🥅 <b>Over 1.5: {d_top['Over 1.5']:.0%}</b></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

with t2:
    st.markdown("### 📜 HISTORIAL DE RESULTADOS")
    if not df_h.empty:
        c3, c4 = st.columns(2)
        with c3: slh = st.selectbox("Liga:", ["TODAS"] + lgs, key="filt_l2")
        with c4:
            df_hh = df_h if slh=="TODAS" else df_h[df_h['Liga']==slh]
            ljh = sorted(df_hh['Jornada'].unique().tolist(), reverse=True) if not df_hh.empty else [0]
            sjh = st.selectbox("Jornada:", ["TODAS"] + ljh, key="filt_j2")
        df_res = df_hh if sjh=="TODAS" else df_hh[df_hh['Jornada']==sjh]
        st.dataframe(df_res[['Fecha', 'Jornada', 'Liga', 'Local', 'Visitante', 'Marcador', 'Doble Oportunidad', 'Over 1.5', 'Over 2.5', 'BTTS']].style.applymap(color_letras_historial, subset=['Doble Oportunidad', 'Over 1.5', 'Over 2.5', 'BTTS']), use_container_width=True, hide_index=True)