import streamlit as st
import pandas as pd
import glob
import math
import re
import os
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. ESTILOS, PRIVACIDAD Y RESPONSIVE ---
st.markdown("""
    <style>
    @media (max-width: 640px) {
        .main .block-container { padding: 10px !important; margin-top: 0px !important; }
        h1 { font-size: 1.5rem !important; }
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
    
    div.stButton > button {
        width: 100% !important;
        height: 180px !important;
        min-height: 180px !important;
        max-height: 180px !important;
        background-color: white !important;
        color: black !important;
        border: 1px solid #ddd !important;
        border-radius: 12px !important;
        padding: 10px !important;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.1) !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        text-align: center !important;
        font-size: 0.85rem !important;
        white-space: pre-line !important;
        overflow: hidden !important;
    }
    div.stButton > button:hover {
        border-color: #28a745 !important;
        transform: translateY(-3px) !important;
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
    res_limpio = str(resultado_str).strip()
    if res_limpio == "" or res_limpio.lower() == "nan": return None
    numeros = re.findall(r'\d+', res_limpio.replace(':', '-'))
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

# --- 4. VENTANAS MODALES ---
@st.dialog("📊 ANÁLISIS DETALLADO SOCCER", width="large")
def ventana_soccer(r, df_h):
    st.title(f"⚽ {r['Match']}")
    st.subheader(f"🏆 {r['League']} | 📅 {r['Date']}")
    st.divider()
    roles = [(r['Home team'], 'Home team', 'Local'), (r['Away team'], 'Away team', 'Visitante')]
    for eq, col_rol, nombre_rol in roles:
        st.markdown(f"#### 📈 Últimos 10 partidos como {nombre_rol}: {eq}")
        df_eq = df_h[df_h[col_rol] == eq].iloc[::-1].head(10).copy()
        if not df_eq.empty:
            for idx, fila in df_eq.iterrows():
                g = extraer_goles(fila['Result'])
                if g:
                    match_prob = re.search(r'\((\d+)%\)', str(fila['Double chance']))
                    prob_str = f" ({match_prob.group(1)}%)" if match_prob else ""
                    if fila['Home team'] == eq:
                        check = "✅" if g[0] >= g[1] else "❌"
                        df_eq.at[idx, 'Double chance'] = f"1X {check}{prob_str}"
                    else:
                        check = "✅" if g[1] >= g[0] else "❌"
                        df_eq.at[idx, 'Double chance'] = f"X2 {check}{prob_str}"
            c1, c2, c3 = st.columns(3)
            m_1x = (df_eq['Double chance'].str.contains('✅').sum() / len(df_eq))
            m_o15 = (df_eq['Over 1.5'].str.contains('✅').sum() / len(df_eq))
            m_btts = (df_eq['Btts'].str.contains('✅').sum() / len(df_eq))
            c1.metric(f"Efectividad {('1X' if nombre_rol=='Local' else 'X2')}", f"{m_1x:.0%}")
            c2.metric("Efectividad O1.5", f"{m_o15:.0%}")
            c3.metric("Efectividad BTTS", f"{m_btts:.0%}")
            cols_mostrar = ['Date', 'Home team', 'Away team', 'Result', 'Double chance', 'Over 1.5', 'Over 2.5', 'Btts']
            st.dataframe(df_eq[cols_mostrar].style.map(color_letras_historial, subset=['Double chance', 'Over 1.5', 'Over 2.5', 'Btts']), use_container_width=True, hide_index=True)
        st.divider()

@st.dialog("🏀 ANÁLISIS DETALLADO BASKET", width="large")
def ventana_basket(r, df_h):
    st.title(f"🏀 {r['Match']}")
    st.subheader(f"🏆 {r['League']} | 📅 {r['Date']}")
    st.divider()
    st.markdown(f"#### 📈 Historial Reciente: {r['Match']}")
    df_eq = df_h[(df_h['Home team'] == r['Home team']) | (df_h['Away team'] == r['Away team'])].iloc[::-1].head(10)
    if not df_eq.empty:
        st.dataframe(df_eq[['Date', 'Home team', 'Away team', 'Result', 'Total Pts']], use_container_width=True, hide_index=True)
    st.divider()

# --- 5. PROCESAMIENTO DE DATOS ---
@st.cache_data(ttl=300)
def cargar_datos_dual():
    archivos = glob.glob("**/*.csv", recursive=True)
    
    # Soccer Data
    s_act, s_hist, s_lgs = [], [], []
    # Basket Data
    b_act, b_hist, b_lgs = [], [], []
    
    fz = {}
    
    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            ln = os.path.basename(arc).replace('.csv','')
            is_basket = "basketball" in arc.lower()
            
            if is_basket:
                if ln not in b_lgs: b_lgs.append(ln)
            else:
                if ln not in s_lgs: s_lgs.append(ln)
            
            df['matchday'] = pd.to_numeric(df.get('matchday', 0), errors='coerce').fillna(0).astype(int)
            df['Fecha_dt'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
            
            # Cálculo de fuerza para Soccer únicamente
            if not is_basket:
                for _, fila in df.iterrows():
                    loc, vis = fila['home_team'], fila['away_team']
                    if loc not in fz: fz[loc] = 1.2
                    if vis not in fz: fz[vis] = 1.2
                    g = extraer_goles(fila.get('result'))
                    if g:
                        fz[loc] += 0.20 if g[0] > g[1] else 0.05
                        fz[vis] += 0.20 if g[1] > g[0] else 0.05

            for _, f in df.iterrows():
                g = extraer_goles(f.get('result'))
                
                if is_basket:
                    if g:
                        b_hist.append({'Date': f['date'], 'League': ln, 'Matchday': f['matchday'], 'Home team': f['home_team'], 'Away team': f['away_team'], 'Result': f['result'], 'Total Pts': g[0]+g[1]})
                    else:
                        b_act.append({'Date': f['date'], 'Fecha_dt': f['Fecha_dt'], 'Time': f.get('time','-'), 'Matchday': f['matchday'], 'League': ln, 'Home team': f['home_team'], 'Away team': f['away_team'], 'Match': f"{f['home_team']} vs {f['away_team']}", 'Local Pts': 110.5, 'Visita Pts': 108.2, 'Puntos Totales': 218.7})
                else:
                    pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz.get(f['home_team'],1.2), fz.get(f['away_team'],1.2))
                    if g:
                        p1x, px2 = pl+pe, pv+pe
                        pk = "1X" if p1x >= px2 else "X2"
                        s_hist.append({'Date': f['date'], 'League': ln, 'Matchday': f['matchday'], 'Home team': f['home_team'], 'Away team': f['away_team'], 'Result': f"{g[0]} - {g[1]}", 'G_L': g[0], 'G_V': g[1], 'Double chance': f"{pk} {'✅' if (g[0]>=g[1] if pk=='1X' else g[1]>=g[0]) else '❌'} ({max(p1x,px2):.0%})", 'Over 1.5': f"{'✅' if (g[0]+g[1])>1.5 else '❌'} ({po15:.0%})", 'Over 2.5': f"{'✅' if (g[0]+g[1])>2.5 else '❌'} ({po25:.0%})", 'Btts': f"{'✅' if (g[0]>0 and g[1]>0) else '❌'} ({pb:.0%})"})
                    else:
                        s_act.append({'Date': f['date'], 'Fecha_dt': f['Fecha_dt'], 'Time': f.get('time','-'), 'Matchday': f['matchday'], 'League': ln, 'Home team': f['home_team'], 'Away team': f['away_team'], 'Match': f"{f['home_team']} vs {f['away_team']}", '1X': pl+pe, 'X2': pv+pe, 'Over 1.5': po15, 'Over 2.5': po25, 'Btts': pb})
        except: continue
    
    return pd.DataFrame(s_act), pd.DataFrame(s_hist), sorted(s_lgs), pd.DataFrame(b_act), pd.DataFrame(b_hist), sorted(b_lgs)

df_p, df_h, lgs, df_pb, df_hb, lgs_b = cargar_datos_dual()

# --- 6. INTERFAZ ---
st.markdown('<h1><span class="giro-balon">⚽</span> Bet Pro League</h1>', unsafe_allow_html=True)
t1, t2 = st.tabs(["SOCCER PREDICTIONS", "BASKETBALL PREDICTIONS"])

with t1:
    if not df_p.empty:
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fechas = df_p[df_p['Fecha_dt'] >= hoy]['Fecha_dt'].unique()
        if len(fechas) > 0:
            f_prox = min(fechas)
            df_t4 = df_p[df_p['Fecha_dt'] == f_prox].copy()
            st.markdown(f"### 🏆 TOP 4 SOCCER ({f_prox.strftime('%d/%m/%Y')})")
            mks = [('1X', '🛡️ Doble Oportunidad'), ('Over 1.5', '🥅 Over 1.5'), ('Over 2.5', '⚽ Over 2.5'), ('Btts', '🤝 Btts')]
            cols = st.columns(4)
            for i, (m, tit) in enumerate(mks):
                with cols[i]:
                    st.markdown(f"#### {tit}")
                    top = df_t4.nlargest(4, m)
                    for idx, r in top.iterrows():
                        etq = ("1X" if r['1X'] >= r['X2'] else "X2") if m == '1X' else "Prob"
                        txt = f"{r['Date']} {r['Time']}\n{r['League']}\n{r['Match']}\n⭐ {etq}: {r[m]:.0%}"
                        if st.button(txt, key=f"s_t4_{m}_{idx}"): ventana_soccer(r, df_h)
        st.divider()
        st.markdown("### 📊 LIGAS Y JORNADAS")
        c1, c2 = st.columns(2)
        with c1: sl = st.selectbox("League:", ["TODAS"] + lgs, key="s_l")
        with c2:
            df_fl = df_p if sl=="TODAS" else df_p[df_p['League']==sl]
            sj = st.selectbox("Matchday:", ["TODAS"] + sorted(df_fl['Matchday'].unique().tolist(), reverse=True) if not df_fl.empty else ["TODAS"], key="s_j")
        df_fin = df_fl if sj=="TODAS" else df_fl[df_fl['Matchday']==sj]
        if not df_fin.empty:
            cols_f = ['1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']
            st.dataframe(df_fin[['Date', 'Time', 'Matchday', 'League', 'Match'] + cols_f].style.map(aplicar_semaforo, subset=cols_f).format({c: '{:.0%}' for c in cols_f}), use_container_width=True, hide_index=True)

with t2:
    if not df_pb.empty:
        hoy_b = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fechas_b = df_pb[df_pb['Fecha_dt'] >= hoy_b]['Fecha_dt'].unique()
        if len(fechas_b) > 0:
            f_prox_b = min(fechas_b)
            df_t4_b = df_pb[df_pb['Fecha_dt'] == f_prox_b].copy()
            st.markdown(f"### 🏀 TOP 4 BASKETBALL ({f_prox_b.strftime('%d/%m/%Y')})")
            mks_b = [('Local Pts', '🏠 Puntos Local'), ('Visita Pts', '🚀 Puntos Visitante'), ('Puntos Totales', '🏀 Puntos Totales')]
            cols_b = st.columns(3)
            for i, (m, tit) in enumerate(mks_b):
                with cols_b[i]:
                    st.markdown(f"#### {tit}")
                    top_b = df_t4_b.nlargest(4, m)
                    for idx, r in top_b.iterrows():
                        txt = f"{r['Date']} {r['Time']}\n{r['League']}\n{r['Match']}\n⭐ {m}: {r[m]:.1f}"
                        if st.button(txt, key=f"b_t4_{m}_{idx}"): ventana_basket(r, df_hb)
        st.divider()
        st.markdown("### 📊 LIGAS Y JORNADAS BASKET")
        cb1, cb2 = st.columns(2)
        with cb1: slb = st.selectbox("League Basket:", ["TODAS"] + lgs_b, key="b_l")
        with cb2:
            df_flb = df_pb if slb=="TODAS" else df_pb[df_pb['League']==slb]
            sjb = st.selectbox("Matchday Basket:", ["TODAS"] + sorted(df_flb['Matchday'].unique().tolist(), reverse=True) if not df_flb.empty else ["TODAS"], key="b_j")
        df_finb = df_flb if sjb=="TODAS" else df_flb[df_flb['Matchday']==sjb]
        if not df_finb.empty:
            cols_b_fmt = ['Local Pts', 'Visita Pts', 'Puntos Totales']
            st.dataframe(df_finb[['Date', 'Time', 'League', 'Match'] + cols_b_fmt], use_container_width=True, hide_index=True)
    else:
        st.info("No se encontraron archivos con 'basketball' en el nombre. Asegúrate de que NBA-Basketball_Estados-Unidos.csv esté en la carpeta.")