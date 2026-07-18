import streamlit as st
import pandas as pd
import numpy as np
import glob
import math
import re
import os
from datetime import datetime, timedelta
import requests

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bet Pro Futbol AI", layout="wide", page_icon="⚽")

# --- 2. CSS PERSONALIZADO (MANTENIDO ÍNTEGRO PARA DISEÑO PREMIUM) ---
st.markdown("""
    <style>
    .stApp { 
        background-image: url("https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"); 
        background-attachment: fixed; background-size: cover; 
    }
    
    .main .block-container { 
        background-color: rgba(255, 255, 255, 0.98) !important; 
        border-radius: 15px; padding: 40px; margin-top: 25px;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.4);
    }

    h1, h2, h3, h4, h5, h6, p, span, label, .stMetric {
        color: #000000 !important;
        font-weight: bold !important;
    }

    .titulo-top4 {
        font-size: 42px !important;
        font-weight: 900 !important;
        color: #000000 !important;
        margin-bottom: 20px !important;
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    div.stButton > button {
        width: 100% !important;
        min-height: 200px !important;
        max-height: 200px !important;
        background-color: white !important;
        color: black !important;
        border: 2px solid #eee !important;
        border-radius: 15px !important;
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        font-size: 14px !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.1) !important;
        transition: transform 0.2s !important;
    }
    
    div.stButton > button:hover {
        transform: scale(1.02);
        border-color: #28a745 !important;
    }

    div[data-testid="stDateInput"] input {
        background-color: white !important;
        color: black !important;
        border: 2px solid #28a745 !important;
        -webkit-text-fill-color: black !important;
    }

    div[role="dialog"] {
        background-color: #1e1e1e !important;
        color: white !important;
        border: 1px solid #444 !important;
    }
    
    div[role="dialog"] h1, div[role="dialog"] h2, div[role="dialog"] h3, 
    div[role="dialog"] h4, div[role="dialog"] p, div[role="dialog"] span,
    div[role="dialog"] .stMetric div {
        color: white !important;
    }

    header {visibility: hidden !important;}
    footer {display: none !important;}
    .giro-balon { display: inline-block; animation: rotacion 3s infinite linear; }
    @keyframes rotacion { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES LÓGICAS Y MATEMÁTICAS ---
def aplicar_semaforo(val):
    try:
        # Extraer solo el número del porcentaje
        str_val = str(val).split('%')[0].split('(')[0].strip()
        num = float(str_val)
        
        # Colores para el texto (fuente)
        if num >= 70: color = '#28a745' # Verde
        elif num >= 50: color = '#ffc107' # Amarillo
        else: color = '#dc3545' # Rojo
        
        return f'color: {color}; font-weight: bold'
    except: return None

def color_letras_historial(val):
    v = str(val)
    if '✅' in v: return 'color: #28a745; font-weight: bold;'
    if '❌' in v: return 'color: #dc3545; font-weight: bold;'
    return 'color: white;'

def extraer_goles(resultado_str):
    if pd.isna(resultado_str): return None
    res = re.sub(r'\(.*?\)', '', str(resultado_str)).strip()
    nums = re.findall(r'\d+', res.replace(':', '-'))
    return (int(nums[0]), int(nums[1])) if len(nums) >= 2 else None

def calcular_poisson(media, x):
    if media <= 0: return 0.001
    return (math.exp(-media) * (media**x)) / math.factorial(x)

def obtener_probabilidades(e_l, e_v):
    p_l, p_e, p_v, p_o15, p_o25, p_btts = 0, 0, 0, 0, 0, 0
    for gl in range(7):
        ml = calcular_poisson(e_l, gl)
        for gv in range(7):
            p = ml * calcular_poisson(e_v, gv)
            if gl > gv: p_l += p
            elif gl == gv: p_e += p
            else: p_v += p
            if (gl+gv) > 1.5: p_o15 += p
            if (gl+gv) > 2.5: p_o25 += p
            if gl > 0 and gv > 0: p_btts += p
    return p_l, p_e, p_v, p_o15, p_o25, p_btts

@st.cache_data(show_spinner=False)
def generar_tabla_posiciones(df_historial, liga):
    df_liga = df_historial[df_historial['League'] == liga]
    if df_liga.empty: return pd.DataFrame()
    stats = []
    for _, r in df_liga.iterrows():
        gl, gv = r.get('G_L'), r.get('G_V')
        if pd.isna(gl) or pd.isna(gv): continue
        pts_l = 3 if gl > gv else (1 if gl == gv else 0)
        stats.append({'Equipo': r['Home team'], 'PJ': 1, 'G': 1 if gl>gv else 0, 'E': 1 if gl==gv else 0, 'P': 1 if gl<gv else 0, 'GF': gl, 'GC': gv, 'Pts': pts_l})
        pts_v = 3 if gv > gl else (1 if gv == gl else 0)
        stats.append({'Equipo': r['Away team'], 'PJ': 1, 'G': 1 if gv>gl else 0, 'E': 1 if gv==gl else 0, 'P': 1 if gv<gl else 0, 'GF': gv, 'GC': gl, 'Pts': pts_v})
    if not stats: return pd.DataFrame()
    tabla = pd.DataFrame(stats).groupby('Equipo').sum().reset_index()
    tabla['DG'] = tabla['GF'] - tabla['GC']
    tabla = tabla.sort_values(by=['Pts', 'DG', 'GF'], ascending=[False, False, False]).reset_index(drop=True)
    tabla.index = tabla.index + 1
    tabla.index.name = 'Pos'
    return tabla

# --- 4. CARGA Y PROCESAMIENTO DE DATOS (MÓDULO CENTRAL) ---
@st.cache_data(ttl=60, show_spinner="Sincronizando Base de Datos...")
def cargar_todo():
    archivos = glob.glob("**/*.csv", recursive=True)
    fz_acum, part_cont = {}, {}
    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            for _, f in df.iterrows():
                l, v = f['home_team'], f['away_team']
                g = extraer_goles(f.get('result'))
                if g:
                    fz_acum[l] = fz_acum.get(l, 0) + g[0]
                    fz_acum[v] = fz_acum.get(v, 0) + g[1]
                    part_cont[l] = part_cont.get(l, 0) + 1
                    part_cont[v] = part_cont.get(v, 0) + 1
        except: continue
    
    fz = {eq: (fz_acum[eq]/part_cont[eq]) if part_cont.get(eq,0)>0 else 1.2 for eq in fz_acum}
    actuales, historicos, ligas = [], [], []

    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            ln = os.path.basename(arc).replace('.csv','')
            if ln not in ligas: ligas.append(ln)
            for _, f in df.iterrows():
                pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz.get(f['home_team'],1.2), fz.get(f['away_team'],1.2))
                total = (pl+pe+pv+pe) if (pl+pe+pv+pe) > 0 else 1
                p1x, px2 = (pl+pe)/total, (pv+pe)/total
                g = extraer_goles(f.get('result'))
                fecha_str, hora_str = str(f['date']), str(f.get('time','00:00'))
                try: fecha_dt = pd.to_datetime(f"{fecha_str} {hora_str}", dayfirst=True)
                except: fecha_dt = pd.to_datetime(fecha_str, dayfirst=True)
                
                match_data = {'Date': f['date'], 'Time': hora_str, 'Matchday': int(f.get('matchday',0)), 'League': ln, 
                              'Home team': f['home_team'], 'Away team': f['away_team'], 'Match': f"{f['home_team']} vs {f['away_team']}", 'Fecha_dt': fecha_dt}

                if g:
                    match_data.update({'Result': f"{g[0]} - {g[1]}", 'G_L': g[0], 'G_V': g[1], 
                                      '1X': f"{'✅' if g[0]>=g[1] else '❌'} {p1x:.0%}", 'X2': f"{'✅' if g[1]>=g[0] else '❌'} {px2:.0%}", 
                                      'Over 1.5': f"{'✅' if (g[0]+g[1])>1.5 else '❌'} {po15:.0%}", 
                                      'Over 2.5': f"{'✅' if (g[0]+g[1])>2.5 else '❌'} {po25:.0%}", 'Btts': f"{'✅' if (g[0]>0 and g[1]>0) else '❌'} {pb:.0%}"})
                    historicos.append(match_data)
                else:
                    match_data.update({'1X': p1x, 'X2': px2, 'Over 1.5': po15, 'Over 2.5': po25, 'Btts': pb})
                    actuales.append(match_data)
        except: continue
    return pd.DataFrame(actuales), pd.DataFrame(historicos), sorted(ligas)

df_p, df_h, lgs = cargar_todo()

# --- 5. VENTANA FLOTANTE (ANALISIS PRO) ---
@st.dialog("📊 ANÁLISIS DETALLADO", width="large")
def ventana_analisis(r, df_h):
    st.markdown(f"## ⚽ {r['Match']}")
    st.divider()
    for eq, col, nom in [(r['Home team'], 'Home team', 'Local'), (r['Away team'], 'Away team', 'Visitante')]:
        st.markdown(f"#### 📈 Últimos 10 partidos como {nom}: {eq}")
        df_eq = df_h[df_h[col] == eq].iloc[::-1].head(10)
        if not df_eq.empty:
            c = st.columns(4)
            c[0].metric(f"Efectividad {('1X' if nom=='Local' else 'X2')}", f"{(df_eq['1X' if nom=='Local' else 'X2'].str.contains('✅').sum()/len(df_eq)):.0%}")
            c[1].metric("Over 1.5", f"{(df_eq['Over 1.5'].str.contains('✅').sum()/len(df_eq)):.0%}")
            c[2].metric("Over 2.5", f"{(df_eq['Over 2.5'].str.contains('✅').sum()/len(df_eq)):.0%}")
            c[3].metric("Btts", f"{(df_eq['Btts'].str.contains('✅').sum()/len(df_eq)):.0%}")
            st.dataframe(df_eq[['Date', 'Time', 'Matchday', 'Match', 'Result', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']].style.map(color_letras_historial, subset=['1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']), use_container_width=True, hide_index=True)
        st.divider()

# --- NUEVA FUNCIÓN PARA THE ODDS API (Corregida) ---
def obtener_cuotas_api(liga_key):
    API_KEY = "87d5d052809a75023bff788995f4d350"
    # Cambia el parámetro 'markets' en tu URL de la API:
    url = f"https://api.the-odds-api.com/v4/sports/{liga_key}/odds/?apiKey={API_KEY}&regions=eu&markets=h2h,totals,btts"
    
    # --- AQUÍ PEGAS LA NUEVA FUNCIÓN DE CRUCE ---
def agregar_cuotas_a_tabla(df, datos_api):
    for col in ['Cuota_L', 'Cuota_E', 'Cuota_V']: df[col] = None
    
    for partido in datos_api:
        # Buscamos el mercado 'h2h' (head to head)
        market = next((m for m in partido['bookmakers'][0]['markets'] if m['key'] == 'h2h'), None)
        if not market: continue
            
        for i, row in df.iterrows():
            if partido['home_team'].lower() in row['Match'].lower():
                # Asignamos según el nombre del equipo
                for outcome in market['outcomes']:
                    if outcome['name'] == partido['home_team']: df.at[i, 'Cuota_L'] = outcome['price']
                    elif outcome['name'] == 'Draw': df.at[i, 'Cuota_E'] = outcome['price']
                    else: df.at[i, 'Cuota_V'] = outcome['price']
    return df

# ==========================================
# BLOQUES DE LA INTERFAZ
# ==========================================

# region 1. BLOQUE TOP 4
@st.fragment
def bloque_top4(df_p, df_h):
    if not df_p.empty:
        ahora = datetime.now()
        df_top_pool = df_p[df_p['Fecha_dt'] >= (ahora - timedelta(hours=2))].sort_values('Fecha_dt')
        if not df_top_pool.empty:
            st.markdown('<p class="titulo-top4">🏆 TOP 4 </p>', unsafe_allow_html=True)
            mks = [('1X', '🛡️ Doble Oportunidad'), ('Over 1.5', '🥅 Over 1.5'), ('Over 2.5', '⚽ Over 2.5'), ('Btts', '🤝 Btts')]
            cols = st.columns(4)
            df_dia = df_top_pool[df_top_pool['Fecha_dt'].dt.date == ahora.date()]
            if len(df_dia) < 4: df_dia = df_top_pool.head(20)
            for i, (m, tit) in enumerate(mks):
                with cols[i]:
                    st.markdown(f"#### {tit}")
                    top = df_dia.nlargest(4, m).reset_index(drop=True)
                    for idx, r in top.iterrows():
                        etq = ("1X" if r['1X'] >= r['X2'] else "X2") if m == '1X' else "Prob"
                        if st.button(f"{r['Date']} {r['Time']}\n{r['League']}\n{r['Match']}\n⭐ {etq}: {r[m]:.0%}", key=f"t4_{m}_{idx}_{r['Match']}"):
                            ventana_analisis(r, df_h)
# endregion

# Pon esto al principio de tu script o antes de donde creas el menú desplegable
traductor_ligas = {
    "Eliteserien_Noruega": "soccer_norway_eliteserien",
    "Liga_Betplay_Colombia": "soccer_colombia_primera_a",
    # Agrega aquí los nombres EXACTOS tal cual aparecen en tu menú desplegable
    # A la izquierda: lo que ves en el menú. A la derecha: la 'key' de la API.
}

# region 2. BLOQUE LIGAS Y JORNADAS
def bloque_ligas_jornadas(df_p, df_h, lgs):
    st.markdown("### 📊 LIGAS Y JORNADAS")
    
    f_col1, f_col2, f_col3, f_col4 = st.columns([1, 1, 1, 1])
    
    with f_col1: sf = st.date_input("Filtrar por Fecha:", value=None, key="f_act_s")
    with f_col2: sl = st.selectbox("Seleccione Liga:", ["TODAS"] + lgs, key="l_act_s")
    
    df_fl = df_p if sl=="TODAS" else df_p[df_p['League']==sl]
    if sf: df_fl = df_fl[df_fl['Fecha_dt'].dt.date == sf]
    
    with f_col3: sj = st.selectbox("Seleccione Jornada:", ["TODAS"] + sorted(df_fl['Matchday'].unique().tolist(), reverse=True) if not df_fl.empty else ["TODAS"], key="j_act_s")
    df_fin = df_fl if sj=="TODAS" else df_fl[df_fl['Matchday']==sj]

    # --- BOTÓN DE CUOTAS ---
    with f_col4:
        st.markdown("<br>", unsafe_allow_html=True) 
        liga_api = traductor_ligas.get(sl) 
        if st.button("🔄 Actualizar Cuotas", key="btn_final"):
            if liga_api:
                with st.spinner(f"Conectando a la API para {sl}..."):
                    datos_cuotas = obtener_cuotas_api(liga_api)
                    if datos_cuotas:
                        st.session_state['cuotas_actuales'] = datos_cuotas
                        st.success("¡Cuotas cargadas!")
            else:
                st.warning("No tengo la configuración de API para esta liga.")

    # --- BUSCADOR INTELIGENTE ---
    if 'cuotas_crudas' in st.session_state:
        busqueda = st.text_input("🔍 Busca tu liga (ej: Colombia, España):")
        if busqueda:
            datos = st.session_state['cuotas_crudas']
            resultados = [d for d in datos if busqueda.lower() in d['title'].lower()]
            for res in resultados:
                st.success(f"Liga: {res['title']} | Key: `{res['key']}`")

   # --- PROCESAMIENTO Y VISUALIZACIÓN ---
if not df_fin.empty:
    # 1. Aplicamos cuotas si están cargadas
    if 'cuotas_actuales' in st.session_state:
        df_fin = agregar_cuotas_a_tabla(df_fin, st.session_state['cuotas_actuales'])
    
    # 2. Creamos copia para mostrar y buscamos el nombre correcto de la columna de empate
    df_display = df_fin.copy()
    # Cambia 'Empate_Prob' por el nombre exacto que aparece en tu lista de columnas
    col_empate = 'Empate_Prob' if 'Empate_Prob' in df_fin.columns else 'Empate'
    
    # 3. Creamos columnas combinadas (Porcentaje + Cuota)
    # Usamos .get para evitar errores si la columna de cuota no existe
    df_display['Local'] = [f"{v:.0%} ({c})" if c else f"{v:.0%}" for v, c in zip(df_fin['1X'], df_fin.get('Cuota_L', [None]*len(df_fin)))]
    df_display['Empate'] = [f"{v:.0%} ({c})" if c else "-" for v, c in zip(df_fin[col_empate], df_fin.get('Cuota_E', [None]*len(df_fin)))]
    df_display['Visita'] = [f"{v:.0%} ({c})" if c else f"{v:.0%}" for v, c in zip(df_fin['X2'], df_fin.get('Cuota_V', [None]*len(df_fin)))]
    
    # 4. Formateo de las columnas de goles
    for col in ['Over 1.5', 'Over 2.5', 'Btts']:
        if col in df_fin.columns:
            df_display[col] = df_fin[col].apply(lambda x: f"{x:.0%}")
    
    cols_mostrar = ['Date', 'Time', 'Matchday', 'League', 'Match', 'Local', 'Empate', 'Visita', 'Over 1.5', 'Over 2.5', 'Btts']
    
    # 5. Visualización con colores aplicados a los números (usando df_fin para el cálculo)
    # Nota: aplicamos el estilo sobre df_display pero basado en los datos originales
    st.dataframe(
        df_display[cols_mostrar].style.map(
            aplicar_semaforo, 
            subset=['Local', 'Visita', 'Over 1.5', 'Over 2.5', 'Btts']
        ), 
        use_container_width=True, 
        hide_index=True
    )
# endregion

# region 3. BLOQUE PREDICCIÓN BOMBA
def bloque_prediccion_bomba(df_fin, df_h):
    d_b = df_fin.loc[df_fin[['Over 1.5', 'Over 2.5', 'Btts']].max(axis=1).idxmax()]
    h_l = df_h[(df_h['Home team'] == d_b['Home team']) & (df_h['League'] == d_b['League'])]
    h_v = df_h[(df_h['Away team'] == d_b['Away team']) & (df_h['League'] == d_b['League'])]
    if not h_l.empty and not h_v.empty:
        t_l, g1_l, g2_l, w_l = len(h_l), (h_l['G_L']>=1).sum(), (h_l['G_L']>=2).sum(), (h_l['G_L']>=h_l['G_V']).sum()
        t_v, g1_v, g2_v, w_v = len(h_v), (h_v['G_V']>=1).sum(), (h_v['G_V']>=2).sum(), (h_v['G_V']>=h_v['G_L']).sum()
        etq_b = f"1X: {d_b['1X']:.0%}" if d_b['1X'] >= d_b['X2'] else f"X2: {d_b['X2']:.0%}"
        
        st.markdown(f"""
        <div style="background-color: #ff4b4b; padding: 30px; border-radius: 15px; border-left: 15px solid #8B0000; position: relative;">
            <div style="position: absolute; top: 15px; left: 15px; background-color: rgba(255, 255, 255, 0.25); color: white; padding: 5px 15px; border-radius: 8px; font-size: 0.9rem; font-weight: bold; border: 1px solid rgba(255, 255, 255, 0.5); box-shadow: 0px 2px 5px rgba(0,0,0,0.2);">
                🏆 {d_b['League']}
            </div>
            <h2 style="color: white !important; margin: 0; text-align: center; padding-top: 15px;">💣 PREDICCIÓN BOMBA DETECTADA 💣</h2>
            <p style="font-size: 1.15rem; line-height: 1.6; margin-top: 20px; color: white !important;">
                El equipo local <b>{d_b['Home team']}</b> lleva <b>{g1_l} de {t_l}</b> partidos marcando al menos 1 gol en casa y de esos <b>{g1_l}</b> partidos <b>{g2_l}</b> ha marcado 2 o más goles, ha ganado o empatado en <b>{w_l} de {t_l}</b> encuentros como local. <br>
                El equipo visitante <b>{d_b['Away team']}</b>, lleva <b>{g1_v} de {t_v}</b> partidos marcando al menos 1 gol como visitante y de esos <b>{g1_v}</b> partidos <b>{g2_v}</b> ha marcado 2 o más goles, ha ganado o empatado en <b>{w_v} de {t_v}</b> encuentros como visitante.
            </p>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 25px;">
                <div style="background: white; color: #ff4b4b; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold;">🛡️ {etq_b}</div>
                <div style="background: white; color: #ff4b4b; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold;">🥅 Over 1.5: {d_b['Over 1.5']:.0%}</div>
                <div style="background: white; color: #ff4b4b; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold;">⚽ Over 2.5: {d_b['Over 2.5']:.0%}</div>
                <div style="background: white; color: #ff4b4b; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold;">🤝 Btts: {d_b['Btts']:.0%}</div>
            </div>
        </div>""", unsafe_allow_html=True)
# endregion

# region 4. BLOQUE HISTORIAL DE RESULTADOS
@st.fragment
def bloque_historial(df_h, lgs):
    st.markdown("## 📜 HISTORIAL DE RESULTADOS")
    h_c1, h_c2, h_c3 = st.columns([1, 1, 1])
    with h_c1: sfh = st.date_input("Fecha Historial:", value=None, key="fh_s")
    with h_c2: slh = st.selectbox("Liga Historial:", ["TODAS"] + lgs, key="lh_s")
    df_hh = df_h if slh=="TODAS" else df_h[df_h['League']==slh]
    if sfh: df_hh = df_hh[df_hh['Fecha_dt'].dt.date == sfh]
    with h_c3: sjh = st.selectbox("Jornada Historial:", ["TODAS"] + sorted(df_hh['Matchday'].unique().tolist(), reverse=True) if not df_hh.empty else ["TODAS"], key="jh_s")
    df_res = df_hh if sjh=="TODAS" else df_hh[df_hh['Matchday']==sjh]
    st.dataframe(df_res[['Date', 'Time', 'Matchday', 'League', 'Match', 'Result', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']].style.map(color_letras_historial, subset=['1X', 'X2', 'Over 1.5', 'Over 2.5', 'Btts']), use_container_width=True, hide_index=True)
# endregion

# region 5. BLOQUE BASKETBALL
@st.fragment
def bloque_basketball():
    st.markdown("## 🏀 BASKETBALL PREDICTIONS")
    st.info("Módulo en desarrollo para la próxima actualización.")
# endregion


# ==========================================
# RENDERIZADO PRINCIPAL (app.py)
# ==========================================

st.markdown('<h1><span class="giro-balon">⚽</span> Bet Pro Futbol AI</h1>', unsafe_allow_html=True)
tab_soccer, tab_basket = st.tabs(["SOCCER PREDICTIONS", "BASKETBALL PREDICTIONS"])

with tab_soccer:
    # 1. Mostrar TOP 4
    bloque_top4(df_p, df_h)
    st.divider()
    
    # 2. Mostrar Ligas y Jornadas (y guardar datos filtrados)
    df_filtrado = bloque_ligas_jornadas(df_p, df_h, lgs)
    st.divider()
    
    # 3. Mostrar Predicción Bomba (si hay datos)
    if df_filtrado is not None and not df_filtrado.empty:
        bloque_prediccion_bomba(df_filtrado, df_h)
    st.divider()
    
    # 4. Mostrar Historial
    bloque_historial(df_h, lgs)


with tab_basket:
    # 5. Mostrar módulo de Basketball
    bloque_basketball()