import streamlit as st
import pandas as pd
import glob
import math
import re

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. DISEÑO VISUAL Y ANIMACIONES ---
fondo_url = "https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"
st.markdown(f"""
    <style>
    .stApp {{ background-image: url("{fondo_url}"); background-attachment: fixed; background-size: cover; }}
    .main .block-container {{ background-color: rgba(255, 255, 255, 0.95); border-radius: 10px; padding: 30px; margin-top: 20px; }}
    h1, h2, h3, h4, p, span, div, label, .stMetric {{ color: #000000 !important; font-weight: bold; }}
    .top4-card {{ padding: 12px; border-radius: 10px; background: rgba(255,255,255,0.5); border: 1px solid #ddd; text-align: center; margin-bottom: 8px; }}
    
    /* Animación de giro para el balón ⚽ */
    .giro-balon {{ display: inline-block; animation: rotacion 3s infinite linear; font-style: normal; }}
    @keyframes rotacion {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
    
    /* Animación de rebote para el resto de iconos */
    .rebote-icon {{ display: inline-block; animation: bounce 2s infinite; font-style: normal; }}
    @keyframes bounce {{ 0%, 20%, 50%, 80%, 100% {{transform: translateY(0);}} 40% {{transform: translateY(-6px);}} 60% {{transform: translateY(-3px);}} }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES LÓGICAS (Revisadas línea por línea) ---
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

# --- 4. CARGA Y PROCESAMIENTO ---
@st.cache_data(ttl=300)
def cargar_todo():
    archivos = glob.glob("*.csv")
    actuales, historicos, todas_las_ligas = [], [], []
    for archivo in archivos:
        try:
            df = pd.read_csv(archivo)
            liga_n = archivo.replace('.csv','') 
            todas_las_ligas.append(liga_n)
            df['Resultado'] = df['Resultado'].astype(str).str.strip()
            fuerzas = calcular_fuerzas(df)
            pendientes = df[~df['Resultado'].str.contains(r'\d', na=False)].copy()
            prox_jor_liga = pendientes['Jornada'].min() if not pendientes.empty else 0
            
            for _, f in df.iterrows():
                goles = extraer_goles(f['Resultado'])
                if goles:
                    g_l, g_v = goles
                    tipo_real = "1X" if g_l >= g_v else "X2"
                    historicos.append({
                        'Fecha': f['Fecha'], 'Liga': liga_n, 'Jornada': str(int(f['Jornada'])),
                        'Equipo Local': f['Equipo Local'], 'Equipo Visitante': f['Equipo Visitante'], 
                        'Marcador': f"{g_l}-{g_v}",
                        'Doble Oportunidad': f"{tipo_real} ✅" if (g_l >= g_v or g_v >= g_l) else f"{tipo_real} ❌",
                        'Over 1.5': '✅' if (g_l+g_v) > 1.5 else '❌', 'Over 2.5': '✅' if (g_l+g_v) > 2.5 else '❌', 'BTTS': '✅' if (g_l > 0 and g_v > 0) else '❌'
                    })
                else:
                    e_l, e_v = fuerzas.get(f['Equipo Local'], 1.2)*1.1, fuerzas.get(f['Equipo Visitante'], 1.1)*0.9
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
                    pick_label = "1X" if (p_l + p_e) >= (p_v + p_e) else "X2"
                    actuales.append({
                        'Fecha': f['Fecha'], 'Jornada': int(f['Jornada']), 'Liga': liga_n, 
                        'Local': f['Equipo Local'], 'Visitante': f['Equipo Visitante'],
                        'Partido': f"{f['Equipo Local']} vs {f['Equipo Visitante']}",
                        '1X': p_l + p_e, 'X': p_e, 'X2': p_v + p_e, 'Pick_T': pick_label,
                        'Over 1.5': p_o15, 'Over 2.5': p_o25, 'BTTS': p_btts,
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
        st.markdown(f'### <span class="rebote-icon">🏆</span> TOP 4 POR MERCADO (PRÓXIMA JORNADA)', unsafe_allow_html=True)
        df_top4_real = df_pre[df_pre['Es_Proxima'] == True]
        mercados = [('1X', '🛡️', 'Doble Oportunidad'), ('Over 1.5', '🥅', 'Over 1.5'), ('Over 2.5', '🥅', 'Over 2.5'), ('BTTS', '🤝', 'Ambos Marcan')]
        cols_top = st.columns(4)
        for i, (campo, ico, tit) in enumerate(mercados):
            with cols_top[i]:
                st.markdown(f'#### <span class="rebote-icon">{ico}</span> {tit}', unsafe_allow_html=True)
                n_count = min(len(df_top4_real), 4)
                if n_count > 0:
                    for _, r in df_top4_real.nlargest(n_count, campo).iterrows():
                        label = f" ({r['Pick_T']})" if tit == 'Doble Oportunidad' else ""
                        val_display = r['1X'] if tit == 'Doble Oportunidad' and r['Pick_T'] == '1X' else (r['X2'] if tit == 'Doble Oportunidad' else r[campo])
                        st.markdown(f'<div class="top4-card">📅 {r["Fecha"]}<br><b>{r["Partido"]}</b><br><b>{val_display:.0%}{label}</b></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f'### <span class="rebote-icon">📊</span> FILTROS DE PREDICCIONES', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: f_l = st.selectbox("Selecciona Liga:", ["TODAS"] + lista_ligas_total)
        with c2:
            df_t = df_pre if f_l == "TODAS" else df_pre[df_pre['Liga'] == f_l]
            f_j = st.selectbox("Selecciona Jornada:", ["TODAS"] + sorted([int(x) for x in df_t['Jornada'].unique()], reverse=True))
        
        df_v = df_t if f_j == "TODAS" else df_t[df_t['Jornada'] == int(f_j)]
        cols_viz = ['Fecha', 'Jornada', 'Liga', 'Partido', '1X', 'X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']
        st.dataframe(df_v[cols_viz].style.applymap(aplicar_semaforo, subset=['1X', 'X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']).format({c: '{:.0%}' for c in ['1X', 'X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']}), use_container_width=True, hide_index=True)

with tab2:
    st.markdown(f'## <span class="rebote-icon">📜</span> HISTORIAL', unsafe_allow_html=True)
    if not df_his.empty:
        busq = st.text_input("🔍 Buscar equipo para ver su historial y efectividad:")
        h1, h2 = st.columns(2)
        with h1: sel_l_h = st.selectbox("Filtrar Liga:", ["TODAS"] + lista_ligas_total, key="lh")
        with h2:
            df_th = df_his[df_his['Liga'] == sel_l_h] if sel_l_h != "TODAS" else df_his
            sel_j_h = st.selectbox("Filtrar Jornada:", ["TODAS"] + sorted([int(x) for x in df_th['Jornada'].unique()], reverse=True), key="jh")
        
        df_hf = df_th if sel_j_h == "TODAS" else df_th[df_th['Jornada'] == str(sel_j_h)]
        if busq:
            df_hf = df_hf[(df_hf['Equipo Local'].str.contains(busq, case=False)) | (df_hf['Equipo Visitante'].str.contains(busq, case=False))]
            if not df_hf.empty:
                st.write(f"### 📈 Efectividad para: {busq}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Doble Oportunidad", f"{(df_hf['Doble Oportunidad'].str.contains('✅')).mean():.0%}")
                m2.metric("Over 1.5", f"{(df_hf['Over 1.5'] == '✅').mean():.0%}")
                m3.metric("Over 2.5", f"{(df_hf['Over 2.5'] == '✅').mean():.0%}")
                m4.metric("BTTS", f"{(df_hf['BTTS'] == '✅').mean():.0%}")
        st.dataframe(df_hf[['Fecha', 'Jornada', 'Liga', 'Equipo Local', 'Equipo Visitante', 'Marcador', 'Doble Oportunidad', 'Over 1.5', 'Over 2.5', 'BTTS']].style.applymap(color_letras_historial, subset=['Doble Oportunidad', 'Over 1.5', 'Over 2.5', 'BTTS']), use_container_width=True, hide_index=True)