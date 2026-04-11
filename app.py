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
        if val >= 0.70: return 'color: #28a745; font-weight: bold;'
        elif val >= 0.45: return 'color: #ffa500; font-weight: bold;'
    return 'color: black;'

def color_letras_historial(val):
    if '✅' in str(val): return 'color: #28a745; font-weight: bold;'
    if '❌' in str(val): return 'color: #dc3545; font-weight: bold;'
    return 'color: black;'

def extraer_goles(resultado_str):
    if pd.isna(resultado_str): return None
    res_limpio = str(resultado_str).strip()
    if res_limpio == "" or res_limpio.lower() == "nan": return None
    res_limpio = re.sub(r'\(.*?\)', '', res_limpio).strip()
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

# --- 4. VENTANA MODAL ---
@st.dialog("📊 ANÁLISIS DETALLADO", width="large")
def ventana_analisis(r, df_h):
    st.title(f"⚽ {r['Match']}")
    st.subheader(f"🏆 {r['League']} | 📅 {r['Date']}")
    st.divider()
    roles = [(r['Home team'], 'Home team', 'Local'), (r['Away team'], 'Away team', 'Visitante')]
    for eq, col_rol, nombre_rol in roles:
        st.markdown(f"#### 📈 Últimos partidos como {nombre_rol}: {eq}")
        df_eq = df_h[df_h[col_rol] == eq].iloc[::-1].head(10).copy()
        if not df_eq.empty:
            # Métricas superiores ajustadas con el punto solicitado
            c1, c2, c3, c4 = st.columns(4)
            m_1x = (df_eq['1X'].str.contains('✅').sum() / len(df_eq))
            m_o15 = (df_eq['Over 1.5'].str.contains('✅').sum() / len(df_eq))
            m_o25 = (df_eq['Over 2.5'].str.contains('✅').sum() / len(df_eq))
            m_btts = (df_eq['Btts'].str.contains('✅').sum() / len(df_eq))
            
            c1.metric(f"Efectividad. {('1X' if nombre_rol=='Local' else 'X2')}", f"{m_1x:.0%}")
            c2.metric("Efectividad. Over 1.5", f"{m_o15:.0%}")
            c3.metric("Efectividad. Over 2.5", f"{m_o25:.0%}")
            c4.metric("Efectividad. Btts", f"{m_btts:.0%}")
            
            cols_mostrar = ['Date', 'Time', 'Matchday', 'League', 'Match', 'Result', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']
            st.dataframe(
                df_eq[cols_mostrar].style.map(color_letras_historial, subset=['1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']), 
                use_container_width=True, hide_index=True
            )
        else:
            st.info(f"No hay historial suficiente para {eq} como {nombre_rol}.")
        st.divider()

# --- 5. CARGA Y PROCESAMIENTO RECURSIVO ---
@st.cache_data(ttl=300)
def cargar_datos_completos():
    archivos = glob.glob("**/*.csv", recursive=True)
    actuales, historicos, ligas = [], [], []
    fz_acumulada = {}
    partidos_contados = {}
    
    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            for _, fila in df.iterrows():
                loc, vis = fila['home_team'], fila['away_team']
                if loc not in fz_acumulada: fz_acumulada[loc], partidos_contados[loc] = 0, 0
                if vis not in fz_acumulada: fz_acumulada[vis], partidos_contados[vis] = 0, 0
                g = extraer_goles(fila.get('result'))
                if g:
                    fz_acumulada[loc] += g[0]
                    fz_acumulada[vis] += g[1]
                    partidos_contados[loc] += 1
                    partidos_contados[vis] += 1
        except: continue

    fz = {eq: (fz_acumulada[eq] / partidos_contados[eq] if partidos_contados[eq] > 0 else 1.2) for eq in fz_acumulada}

    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            ln = os.path.basename(arc).replace('.csv','')
            if ln not in ligas: ligas.append(ln)
            df['matchday'] = pd.to_numeric(df['matchday'], errors='coerce').fillna(0).astype(int)
            df['Fecha_dt'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
            
            for _, f in df.iterrows():
                pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz.get(f['home_team'],1.2), fz.get(f['away_team'],1.2))
                p1x_raw, px2_raw = pl + pe, pv + pe
                total_sum = p1x_raw + px2_raw
                p1x = p1x_raw / total_sum if total_sum > 0 else 0.5
                px2 = px2_raw / total_sum if total_sum > 0 else 0.5
                
                g = extraer_goles(f.get('result'))
                if g:
                    historicos.append({
                        'Date': f['date'], 'Time': f.get('time','-'), 'Matchday': f['matchday'], 'League': ln, 
                        'Home team': f['home_team'], 'Away team': f['away_team'],
                        'Match': f"{f['home_team']} vs {f['away_team']}",
                        'Result': f"{g[0]} - {g[1]}", 'G_L': g[0], 'G_V': g[1],
                        '1X_p': p1x, 'X2_p': px2, 
                        'Over 1.5': f"{'✅' if (g[0]+g[1])>1.5 else '❌'} {po15:.0%}", 
                        'Over 2.5': f"{'✅' if (g[0]+g[1])>2.5 else '❌'} {po25:.0%}", 
                        'Btts': f"{'✅' if (g[0]>0 and g[1]>0) else '❌'} {pb:.0%}"
                    })
                else:
                    actuales.append({
                        'Date': f['date'], 'Fecha_dt': f['Fecha_dt'], 'Time': f.get('time','-'), 'Matchday': f['matchday'], 'League': ln, 
                        'Home team': f['home_team'], 'Away team': f['away_team'],
                        'Match': f"{f['home_team']} vs {f['away_team']}",
                        '1X': p1x, 'X2': px2, 'Over 1.5': po15, 'Over 2.5': po25, 'Btts': pb
                    })
        except: continue
    return pd.DataFrame(actuales), pd.DataFrame(historicos), sorted(ligas)

df_p, df_h, lgs = cargar_datos_completos()

if not df_h.empty:
    for idx, row in df_h.iterrows():
        g_l, g_v = row['G_L'], row['G_V']
        df_h.at[idx, '1X'] = f"{'✅' if g_l >= g_v else '❌'} {row['1X_p']:.0%}"
        df_h.at[idx, 'X2'] = f"{'✅' if g_v >= g_l else '❌'} {row['X2_p']:.0%}"

# --- 6. INTERFAZ FINAL ---
st.markdown('<h1><span class="giro-balon">⚽</span> Bet Pro League</h1>', unsafe_allow_html=True)
t1, t2 = st.tabs(["SOCCER PREDICTIONS", "BASKETBALL PREDICTIONS"])

with t1:
    if not df_p.empty:
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fechas = df_p[df_p['Fecha_dt'] >= hoy]['Fecha_dt'].unique()
        if len(fechas) > 0:
            f_prox = min(fechas)
            df_t4 = df_p[df_p['Fecha_dt'] == f_prox].copy()
            st.markdown(f"### 🏆 TOP 4 ({f_prox.strftime('%d/%m/%Y')})")
            mks = [('1X', '🛡️ Doble Oportunidad'), ('Over 1.5', '🥅 Over 1.5'), ('Over 2.5', '⚽ Over 2.5'), ('Btts', '🤝 Btts')]
            cols = st.columns(4)
            for i, (m, tit) in enumerate(mks):
                with cols[i]:
                    st.markdown(f"#### {tit}")
                    top = df_t4.nlargest(4, m)
                    for idx, r in top.iterrows():
                        etq = ("1X" if r['1X'] >= r['X2'] else "X2") if m == '1X' else "Prob"
                        txt = f"{r['Date']} {r['Time']}\n{r['League']}\n{r['Match']}\n⭐ {etq}: {r[m]:.0%}"
                        if st.button(txt, key=f"t4_{m}_{idx}"): ventana_analisis(r, df_h)
        st.divider()
        
        st.markdown("### 📊 LIGAS Y JORNADAS")
        c1, c2 = st.columns(2)
        with c1: sl = st.selectbox("League:", ["TODAS"] + lgs, key="filt_l")
        with c2:
            df_fl = df_p if sl=="TODAS" else df_p[df_p['League']==sl]
            sj = st.selectbox("Matchday:", ["TODAS"] + sorted(df_fl['Matchday'].unique().tolist(), reverse=True) if not df_fl.empty else ["TODAS"], key="filt_j")
        df_fin = df_fl if sj=="TODAS" else df_fl[df_fl['Matchday']==sj]
        
        if not df_fin.empty:
            cols_fmt = ['1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']
            st.dataframe(df_fin[['Date', 'Time', 'Matchday', 'League', 'Match'] + cols_fmt].style.map(aplicar_semaforo, subset=cols_fmt).format({c: '{:.0%}' for c in cols_fmt}), use_container_width=True, hide_index=True)
            st.divider()
            
            # --- PREDICCIÓN BOMBA ---
            d_top = df_fin.loc[df_fin[['Over 1.5', 'Over 2.5', 'Btts']].max(axis=1).idxmax()]
            loc, vis = d_top['Home team'], d_top['Away team']
            h_l_home = df_h[(df_h['Home team'] == loc) & (df_h['League'] == d_top['League'])]
            h_v_away = df_h[(df_h['Away team'] == vis) & (df_h['League'] == d_top['League'])]
            
            if not h_l_home.empty and not h_v_away.empty:
                t_l, m1_l, m2_l, w1x_l = len(h_l_home), (h_l_home['G_L'] >= 1).sum(), (h_l_home['G_L'] >= 2).sum(), (h_l_home['G_L'] >= h_l_home['G_V']).sum()
                t_v, m1_v, m2_v, wx2_v = len(h_v_away), (h_v_away['G_V'] >= 1).sum(), (h_v_away['G_V'] >= 2).sum(), (h_v_away['G_V'] >= h_v_away['G_L']).sum()
                etiqueta_texto = f"1X: {d_top['1X']:.0%}" if d_top['1X'] >= d_top['X2'] else f"X2: {d_top['X2']:.0%}"
                
                st.markdown(f"""
                <div style="background-color: #ff4b4b; padding: 25px; border-radius: 15px; border-left: 12px solid #8B0000; color: white; text-align: center;">
                    <h2 style="color: white !important; margin: 0;">💣 PREDICCIÓN BOMBA DETECTADA 💣</h2>
                    <p style="font-size: 1.1rem; line-height: 1.6; margin-top: 15px;">
                        El equipo local <b>{loc}</b> lleva {m1_l} de {t_l} partidos marcando al menos 1 gol en casa y de esos {m1_l} partidos {m2_l} ha marcado 2 o más goles, ha ganado o empatado en {w1x_l} de {t_l} encuentros como local. 
                        El equipo visitante <b>{vis}</b> lleva {m1_v} de {t_v} partidos marcando al menos 1 gol como visitante y de esos {m1_v} partidos {m2_v} ha marcado 2 o más goles, ha ganado o empatado en {wx2_v} de {t_v} encuentros como visitante.
                    </p>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 20px;">
                        <div style="background: white; color: #ff4b4b; padding: 10px; border-radius: 10px;">🛡️ <b>{etiqueta_texto}</b></div>
                        <div style="background: white; color: #ff4b4b; padding: 10px; border-radius: 10px;">🥅 <b>Over 1.5: {d_top['Over 1.5']:.0%}</b></div>
                        <div style="background: white; color: #ff4b4b; padding: 10px; border-radius: 10px;">⚽ <b>Over 2.5: {d_top['Over 2.5']:.0%}</b></div>
                        <div style="background: white; color: #ff4b4b; padding: 10px; border-radius: 10px;">🤝 <b>Btts: {d_top['Btts']:.0%}</b></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else: st.info("No hay predicciones futuras para esta selección.")
    
    st.divider()
    st.markdown("## 📜 HISTORIAL DE RESULTADOS")
    if not df_h.empty:
        h1, h2 = st.columns(2)
        with h1: slh = st.selectbox("League Historial:", ["TODAS"] + lgs, key="h_l")
        with h2:
            df_hh = df_h if slh=="TODAS" else df_h[df_h['League']==slh]
            sjh = st.selectbox("Matchday Historial:", ["TODAS"] + sorted(df_hh['Matchday'].unique().tolist(), reverse=True) if not df_hh.empty else ["TODAS"], key="h_j")
        df_res = df_hh if sjh=="TODAS" else df_hh[df_hh['Matchday']==sjh]
        
        if not df_res.empty:
            cols_h = ['Date', 'Time', 'Matchday', 'League', 'Match', 'Result', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']
            st.dataframe(
                df_res[cols_h].style.map(color_letras_historial, subset=['1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']), 
                use_container_width=True, hide_index=True
            )

with t2:
    st.markdown("## 🏀 BASKETBALL PREDICTIONS")
    st.info("Esta sección está siendo preparada para ligas de baloncesto. Próximamente.")