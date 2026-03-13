import streamlit as st
import pandas as pd
import glob
import math
import re

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. ESTILOS ---
st.markdown("""
    <style>
    .stApp { background-image: url("https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"); background-attachment: fixed; background-size: cover; }
    .main .block-container { background-color: rgba(255, 255, 255, 0.95); border-radius: 10px; padding: 30px; margin-top: 20px; }
    h1, h2, h3, h4, p, span, div, label, .stMetric { color: #000000 !important; font-weight: bold; }
    .top4-card { padding: 12px; border-radius: 10px; background: rgba(255,255,255,0.7); border: 1px solid #ddd; text-align: center; margin-bottom: 8px; min-height: 110px; }
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
    numeros = re.findall(r'\d+', str(resultado_str))
    if len(numeros) >= 2: return int(numeros[0]), int(numeros[1])
    return None

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
        goles = extraer_goles(fila['Resultado'])
        if goles:
            g_l, g_v = goles
            f[fila['Equipo Local']] += 0.20 if g_l > g_v else 0.05 * g_l
            f[fila['Equipo Visitante']] += 0.20 if g_v > g_l else 0.05 * g_v
    return f

# --- 4. CARGA DE DATOS ---
@st.cache_data(ttl=300)
def cargar_todo():
    archivos = glob.glob("*.csv")
    actuales, historicos, todas_las_ligas = [], [], []
    for archivo in archivos:
        try:
            df = pd.read_csv(archivo)
            liga_n = archivo.replace('.csv','') 
            todas_las_ligas.append(liga_n)
            fuerzas = calcular_fuerzas(df)
            
            pendientes = df[~df['Resultado'].astype(str).str.contains(r'\d', na=False)].copy()
            prox_jor_liga = pendientes['Jornada'].min() if not pendientes.empty else 0
            
            for _, f in df.iterrows():
                e_l_f = fuerzas.get(f['Equipo Local'], 1.2)
                e_v_f = fuerzas.get(f['Equipo Visitante'], 1.2)
                pl, pe, pv, po15, po25, pbtts = obtener_probabilidades(e_l_f, e_v_f)
                
                goles = extraer_goles(f['Resultado'])
                if goles:
                    g_l, g_v = goles
                    p_1x, p_x2 = pl + pe, pv + pe
                    pick_d = "1X" if p_1x >= p_x2 else "X2"
                    prob_d = max(p_1x, p_x2)
                    acerto = (g_l >= g_v) if pick_d == "1X" else (g_v >= g_l)
                    
                    historicos.append({
                        'Fecha': f['Fecha'], 'Liga': liga_n, 'Jornada': str(int(f['Jornada'])),
                        'Equipo Local': f['Equipo Local'], 'Equipo Visitante': f['Equipo Visitante'], 
                        'Marcador': f"{g_l}-{g_v}",
                        'Doble Oportunidad': f"{pick_d} {'✅' if acerto else '❌'} ({prob_d:.0%})",
                        'Over 1.5': f"{'✅' if (g_l+g_v) > 1.5 else '❌'} ({po15:.0%})", 
                        'Over 2.5': f"{'✅' if (g_l+g_v) > 2.5 else '❌'} ({po25:.0%})", 
                        'BTTS': f"{'✅' if (g_l > 0 and g_v > 0) else '❌'} ({pbtts:.0%})"
                    })
                else:
                    actuales.append({
                        'Fecha': f['Fecha'], 'Jornada': int(f['Jornada']), 'Liga': liga_n, 
                        'Local': f['Equipo Local'], 'Visitante': f['Equipo Visitante'],
                        'Partido': f"{f['Equipo Local']} vs {f['Equipo Visitante']}",
                        '1X': pl + pe, 'X2': pv + pe, 'Over 1.5': po15, 'Over 2.5': po25, 'BTTS': pbtts,
                        'Es_Proxima': (f['Jornada'] == prox_jor_liga)
                    })
        except: continue
    return pd.DataFrame(actuales), pd.DataFrame(historicos), sorted(list(set(todas_las_ligas)))

df_pre, df_his, lista_ligas_total = cargar_todo()

# --- 5. INTERFAZ ---
st.markdown('<h1><span class="giro-balon">⚽</span> Bet Pro League</h1>', unsafe_allow_html=True)
tab1, tab2 = st.tabs(["PREDICCIONES", "HISTORIAL"])

with tab1:
    if not df_pre.empty:
        st.markdown('### 🏆 TOP 4 POR MERCADO (PRÓXIMAS FECHAS)')
        df_top4_real = df_pre[df_pre['Es_Proxima'] == True].copy()
        mercados = [('DOBLE', '🛡️', 'Doble Oportunidad'), ('Over 1.5', '🥅', 'Over 1.5'), ('Over 2.5', '⚽', 'Over 2.5'), ('BTTS', '🤝', 'Ambos Marcan')]
        cols_top = st.columns(4)
        for i, (campo, ico, tit) in enumerate(mercados):
            with cols_top[i]:
                st.markdown(f'#### {ico} {tit}')
                if campo == 'DOBLE':
                    df_top4_real['Max_Doble'] = df_top4_real[['1X', 'X2']].max(axis=1)
                    df_top4_real['Tipo_Doble'] = df_top4_real.apply(lambda x: '1X' if x['1X'] >= x['X2'] else 'X2', axis=1)
                    top_partidos = df_top4_real.nlargest(4, 'Max_Doble')
                else:
                    top_partidos = df_top4_real.nlargest(4, campo)
                for _, r in top_partidos.iterrows():
                    val_txt = f"{r['Tipo_Doble']} - {r['Max_Doble']:.0%}" if campo == 'DOBLE' else f"{r[campo]:.0%}"
                    st.markdown(f'<div class="top4-card">📅 {r["Fecha"]}<br><small>{r["Liga"]}</small><br><b>{r["Partido"]}</b><br><span style="color: #1a73e8;">{val_txt}</span></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('### 📊 FILTROS DE PREDICCIONES')
        c1, c2 = st.columns(2)
        with c1: sel_liga = st.selectbox("Selecciona Liga:", ["TODAS"] + lista_ligas_total, key="sl_pre")
        with c2:
            df_fl = df_pre if sel_liga == "TODAS" else df_pre[df_pre['Liga'] == sel_liga]
            sel_jornada = st.selectbox("Selecciona Jornada:", ["TODAS"] + sorted([int(x) for x in df_fl['Jornada'].unique()], reverse=True), key="sj_pre")
        df_final = df_fl if sel_jornada == "TODAS" else df_fl[df_fl['Jornada'] == int(sel_jornada)]
        st.dataframe(df_final[['Fecha', 'Jornada', 'Liga', 'Partido', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']].style.applymap(aplicar_semaforo, subset=['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']).format({c: '{:.0%}' for c in ['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']}), use_container_width=True, hide_index=True)

with tab2:
    st.markdown('## 📜 HISTORIAL')
    if not df_his.empty:
        # --- FILTROS DE HISTORIAL (RESTAURADOS TOTALMENTE) ---
        h1, h2 = st.columns(2)
        with h1: sel_l_h = st.selectbox("Filtrar Liga:", ["TODAS"] + lista_ligas_total, key="lh_his")
        with h2:
            df_th = df_his if sel_l_h == "TODAS" else df_his[df_his['Liga'] == sel_l_h]
            sel_j_h = st.selectbox("Filtrar Jornada:", ["TODAS"] + sorted(df_th['Jornada'].unique().tolist(), key=lambda x: int(x), reverse=True), key="jh_his")
        
        busq = st.text_input("🔍 Buscar equipo en historial:", key="bus_his")
        
        df_hf = df_th if sel_j_h == "TODAS" else df_th[df_th['Jornada'] == sel_j_h]
        if busq: df_hf = df_hf[(df_hf['Equipo Local'].str.contains(busq, case=False)) | (df_hf['Equipo Visitante'].str.contains(busq, case=False))]
        
        st.dataframe(df_hf.style.applymap(color_letras_historial, subset=['Doble Oportunidad', 'Over 1.5', 'Over 2.5', 'BTTS']), use_container_width=True, hide_index=True)