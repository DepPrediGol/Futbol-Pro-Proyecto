import streamlit as st
import pandas as pd
import glob
import math
import re
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. ESTILOS, PRIVACIDAD Y RESPONSIVE ---
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
        width: 100% !important;
        background-color: white !important;
        color: black !important;
        border: 1px solid #ddd !important;
        border-radius: 12px !important;
        padding: 15px !important;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.1) !important;
        transition: all 0.3s ease !important;
        height: auto !important;
        min-height: 120px !important;
        white-space: pre-line !important;
    }
    .stButton > button:hover {
        border-color: #28a745 !important;
        transform: translateY(-3px) !important;
        box-shadow: 4px 4px 12px rgba(0,0,0,0.2) !important;
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

# --- 4. VENTANA MODAL ---
@st.dialog("📊 ANÁLISIS DETALLADO", width="large")
def ventana_analisis(r, df_h):
    st.title(f"⚽ {r['Partido']}")
    st.subheader(f"🏆 {r['Liga']} | 📅 {r['Fecha']}")
    st.divider()
    for eq in [r['Local'], r['Visitante']]:
        st.markdown(f"#### 📈 Rendimiento Reciente: {eq}")
        df_eq = df_h[(df_h['Equipo Local'] == eq) | (df_h['Equipo Visitante'] == eq)].iloc[::-1].head(5)
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

# --- 5. CARGA Y PROCESAMIENTO ---
@st.cache_data(ttl=300)
def cargar_datos_completos():
    archivos = glob.glob("*.csv")
    actuales, historicos, ligas = [], [], []
    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            ln = arc.replace('.csv','')
            if ln not in ligas: ligas.append(ln)
            df['Jornada'] = pd.to_numeric(df['Jornada'], errors='coerce').fillna(0).astype(int)
            df['Fecha_dt'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            
            equipos = pd.concat([df['Equipo Local'], df['Equipo Visitante']]).unique()
            fz = {e: 1.2 for e in equipos}
            for _, fila in df.iterrows():
                g = extraer_goles(fila.get('Resultado'))
                if g:
                    fz[fila['Equipo Local']] += 0.20 if g[0] > g[1] else 0.05
                    fz[fila['Equipo Visitante']] += 0.20 if g[1] > g[0] else 0.05

            for _, f in df.iterrows():
                pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz.get(f['Equipo Local'],1.2), fz.get(f['Equipo Visitante'],1.2))
                g = extraer_goles(f.get('Resultado'))
                if g:
                    p1x, px2 = pl+pe, pv+pe
                    pk = "1X" if p1x >= px2 else "X2"
                    historicos.append({
                        'Fecha': f['Fecha'], 'Liga': ln, 'Jornada': f['Jornada'],
                        'Equipo Local': f['Equipo Local'], 'Equipo Visitante': f['Equipo Visitante'], 
                        'Marcador': f"{g[0]} - {g[1]}", 'G_L': g[0], 'G_V': g[1],
                        'Doble Oportunidad': f"{pk} {'✅' if (g[0]>=g[1] if pk=='1X' else g[1]>=g[0]) else '❌'} ({max(p1x,px2):.0%})",
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

df_p, df_h, lgs = cargar_datos_completos()

# --- 6. INTERFAZ FINAL ---
st.markdown('<h1><span class="giro-balon">⚽</span> Bet Pro League</h1>', unsafe_allow_html=True)
t1, t2 = st.tabs(["PREDICCIONES", "HISTORIAL"])

with t1:
    if not df_p.empty:
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fechas = df_p[df_p['Fecha_dt'] >= hoy]['Fecha_dt'].unique()
        if len(fechas) > 0:
            f_prox = min(fechas)
            df_t4 = df_p[df_p['Fecha_dt'] == f_prox].copy()
            st.markdown(f"### 🏆 TOP 4 POR MERCADO ({f_prox.strftime('%d/%m/%Y')})")
            mks = [('1X', '🛡️ Doble Oportunidad'), ('Over 1.5', '🥅 Over 1.5'), ('Over 2.5', '⚽ Over 2.5'), ('BTTS', '🤝 BTTS')]
            cols = st.columns(4)
            for i, (m, tit) in enumerate(mks):
                with cols[i]:
                    st.markdown(f"#### {tit}")
                    top = df_t4.nlargest(4, m)
                    for idx, r in top.iterrows():
                        txt = f"{r['Fecha']}\n{r['Liga']}\n{r['Partido']}\n⭐ Prob: {r[m]:.0%}"
                        if st.button(txt, key=f"t4_{m}_{idx}"): ventana_analisis(r, df_h)
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1: sl = st.selectbox("Liga:", ["TODAS"] + lgs, key="filt_l")
        with c2:
            df_fl = df_p if sl=="TODAS" else df_p[df_p['Liga']==sl]
            sj = st.selectbox("Jornada:", ["TODAS"] + sorted(df_fl['Jornada'].unique().tolist(), reverse=True), key="filt_j")
        
        df_fin = df_fl if sj=="TODAS" else df_fl[df_fl['Jornada']==sj]
        st.dataframe(df_fin[['Fecha', 'Jornada', 'Liga', 'Partido', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']].style.applymap(aplicar_semaforo, subset=['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']).format({c: '{:.0%}' for c in ['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']}), use_container_width=True, hide_index=True)
        
        if not df_fin.empty:
            st.divider()
            d_top = df_fin.loc[df_fin[['Over 1.5', 'Over 2.5', 'BTTS']].max(axis=1).idxmax()]
            loc, vis = d_top['Local'], d_top['Visitante']
            h_l_home = df_h[(df_h['Equipo Local'] == loc) & (df_h['Liga'] == d_top['Liga'])]
            h_v_away = df_h[(df_h['Equipo Visitante'] == vis) & (df_h['Liga'] == d_top['Liga'])]
            
            if len(h_l_home) > 0 and len(h_v_away) > 0:
                t_l, t_v = len(h_l_home), len(h_v_away)
                m1_l, m2_l, r1_l = (h_l_home['G_L'] >= 1).sum(), (h_l_home['G_L'] >= 2).sum(), (h_l_home['G_V'] >= 1).sum()
                w1x_l = (h_l_home['G_L'] >= h_l_home['G_V']).sum()
                m1_v, m15_v = (h_v_away['G_V'] >= 1).sum(), (h_v_away['G_V'] >= 2).sum()
                wx2_v = (h_v_away['G_V'] >= h_v_away['G_L']).sum()
                
                etiqueta_do = "1X" if d_top['1X'] >= d_top['X2'] else "X2"
                prob_do = d_top['1X'] if etiqueta_do == "1X" else d_top['X2']

                st.markdown(f"""
                <div style="background-color: #ff4b4b; padding: 25px; border-radius: 15px; border-left: 12px solid #8B0000; color: white; text-align: center;">
                    <h2 style="color: white !important; margin: 0;">💣 PREDICCIÓN BOMBA DETECTADA 💣</h2>
                    <p style="font-size: 1.1rem; line-height: 1.6; margin-top: 15px;">
                        El equipo local <b>{loc}</b> lleva {m1_l} de {t_l} marcando al menos 1 gol en casa y de esos {m1_l} partidos {m2_l} ha marcado 2 o más goles, 
                        ha recibido 1 gol en {r1_l} de {t_l} encuentros en casa y ha ganado o empatado en {w1x_l} de {t_l} encuentros como local. 
                        Por otro lado, el equipo visitante <b>{vis}</b> ha marcado al menos 1 gol en {m1_v} de {t_v} partidos como visitante y de esos {m1_v} partidos <b>{m15_v}</b> ha marcado más de 1.5 goles, 
                        ha ganado o empatado en {wx2_v} de {t_v} partidos jugados como visitante.
                    </p>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 20px;">
                        <div style="background: white; color: #ff4b4b; padding: 10px; border-radius: 10px;">🛡️ <b>{etiqueta_do}:</b> {prob_do:.0%}</div>
                        <div style="background: white; color: #ff4b4b; padding: 10px; border-radius: 10px;">🥅 <b>Over 1.5:</b> {d_top['Over 1.5']:.0%}</div>
                        <div style="background: white; color: #ff4b4b; padding: 10px; border-radius: 10px;">⚽ <b>Over 2.5:</b> {d_top['Over 2.5']:.0%}</div>
                        <div style="background: white; color: #ff4b4b; padding: 10px; border-radius: 10px;">🤝 <b>Ambos Marcan:</b> {d_top['BTTS']:.0%}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

with t2:
    st.markdown("## 📜 HISTORIAL DE RESULTADOS")
    if not df_h.empty:
        h1, h2 = st.columns(2)
        with h1: slh = st.selectbox("Liga:", ["TODAS"] + lgs, key="h_l")
        with h2:
            df_hh = df_h if slh=="TODAS" else df_h[df_h['Liga']==slh]
            sjh = st.selectbox("Jornada:", ["TODAS"] + sorted(df_hh['Jornada'].unique().tolist(), reverse=True), key="h_j")
        df_res = df_hh if sjh=="TODAS" else df_hh[df_hh['Jornada']==sjh]
        st.dataframe(df_res[['Fecha', 'Jornada', 'Liga', 'Equipo Local', 'Equipo Visitante', 'Marcador', 'Doble Oportunidad', 'Over 1.5', 'Over 2.5', 'BTTS']].style.applymap(color_letras_historial, subset=['Doble Oportunidad', 'Over 1.5', 'Over 2.5', 'BTTS']), use_container_width=True, hide_index=True)