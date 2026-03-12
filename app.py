import streamlit as st
import pandas as pd
import glob
import math
import re

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. DISEÑO VISUAL (Tu original intacto) ---
fondo_url = "https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"
st.markdown(f"""
    <style>
    .stApp {{ background-image: url("{fondo_url}"); background-attachment: fixed; background-size: cover; }}
    .main .block-container {{ background-color: rgba(255, 255, 255, 0.95); border-radius: 10px; padding: 30px; margin-top: 20px; }}
    h1, h2, h3, h4, p, span, div, label, .stMetric {{ color: #000000 !important; font-weight: bold; }}
    .top4-card {{ padding: 12px; border-radius: 10px; background: rgba(255,255,255,0.5); border: 1px solid #ddd; text-align: center; margin-bottom: 8px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES LÓGICAS ---
def color_texto_semaforo(val):
    if isinstance(val, (int, float)):
        if val >= 0.75: return 'color: #28a745; font-weight: bold;'
        elif val >= 0.55: return 'color: #ffa500; font-weight: bold;'
    return 'color: black;'

def color_letras_historial(val):
    if val == '✅': return 'color: #28a745; font-weight: bold;'
    if val == '❌': return 'color: #dc3545; font-weight: bold;'
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
            df['Resultado'] = df['Resultado'].astype(str).str.strip()
            fuerzas = calcular_fuerzas(df)
            
            pendientes = df[~df['Resultado'].str.contains(r'\d', na=False)].copy()
            prox_jor_liga = pendientes['Jornada'].min() if not pendientes.empty else 0
            
            for _, f in df.iterrows():
                goles = extraer_goles(f['Resultado'])
                if goles:
                    g_l, g_v = goles
                    historicos.append({
                        'Fecha': f['Fecha'], 'Liga': liga_n, 'Jornada': str(int(f['Jornada'])),
                        'Equipo Local': f['Equipo Local'], 'Equipo Visitante': f['Equipo Visitante'], 
                        'Marcador': f"{g_l}-{g_v}",
                        'Doble Op.': '✅' if g_l >= g_v else '❌',
                        'Over 1.5': '✅' if (g_l+g_v) > 1.5 else '❌',
                        'Over 2.5': '✅' if (g_l+g_v) > 2.5 else '❌',
                        'BTTS': '✅' if (g_l > 0 and g_v > 0) else '❌'
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
                    p_1x, p_x2 = p_l + p_e, p_v + p_e
                    actuales.append({
                        'Fecha': f['Fecha'], 'Jornada': int(f['Jornada']), 'Liga': liga_n, 
                        'Local': f['Equipo Local'], 'Visitante': f['Equipo Visitante'],
                        'Partido': f"{f['Equipo Local']} vs {f['Equipo Visitante']}",
                        'Pick': "1X" if p_1x >= p_x2 else "X2", 'Prob. Pick': p_1x if p_1x >= p_x2 else p_x2, 
                        'Over 1.5': p_o15, 'Over 2.5': p_o25, 'BTTS': p_btts,
                        'Es_Proxima': (f['Jornada'] == prox_jor_liga)
                    })
        except: continue
    return pd.DataFrame(actuales), pd.DataFrame(historicos), sorted(list(set(todas_las_ligas)))

df_pre, df_his, lista_ligas_total = cargar_todo()

# --- 5. INTERFAZ ---
st.markdown('<h1>⚽ Bet Pro League</h1>', unsafe_allow_html=True)
tab1, tab2 = st.tabs(["PREDICCIONES", "HISTORIAL"])

with tab1:
    if not df_pre.empty:
        st.subheader("🏆 TOP 4 POR MERCADO (PRÓXIMA JORNADA)")
        df_top4_real = df_pre[df_pre['Es_Proxima'] == True]
        mercados = [('Prob. Pick', '🛡️', 'Doble Oportunidad'), ('Over 1.5', '🥅', 'Over 1.5'), ('Over 2.5', '💥', 'Over 2.5'), ('BTTS', '🤝', 'Ambos Marcan')]
        cols = st.columns(4)
        for i, (campo, ico, tit) in enumerate(mercados):
            with cols[i]:
                st.markdown(f'#### {ico} {tit}')
                n_count = min(len(df_top4_real), 4)
                if n_count > 0:
                    for _, r in df_top4_real.nlargest(n_count, campo).iterrows():
                        st.markdown(f'<div class="top4-card">📅 {r["Fecha"]}<br><b>{r["Partido"]}</b><br><b>{r[campo]:.0%}</b></div>', unsafe_allow_html=True)
                        with st.popover("📊 Racha"):
                            for eq_tipo in ['Local', 'Visitante']:
                                nom = r[eq_tipo]
                                st.write(f"**{nom}**")
                                h_eq = df_his[(df_his['Equipo Local'] == nom) | (df_his['Equipo Visitante'] == nom)].head(5).copy()
                                if not h_eq.empty:
                                    def fr(row):
                                        g = extraer_goles(row['Marcador'])
                                        if row['Equipo Local'] == nom:
                                            return "🟢 G" if g[0]>g[1] else ("🟡 E" if g[0]==g[1] else "🔴 P")
                                        return "🟢 G" if g[1]>g[0] else ("🟡 E" if g[1]==g[0] else "🔴 P")
                                    h_eq['Res'] = h_eq.apply(fr, axis=1)
                                    st.dataframe(h_eq[['Fecha', 'Equipo Local', 'Equipo Visitante', 'Marcador', 'Res']], hide_index=True)
                                else: st.write("Sin datos.")

        st.markdown("---")
        st.subheader("📊 FILTROS DE PREDICCIONES")
        c1, c2 = st.columns(2)
        with c1: f_l = st.selectbox("Liga:", ["TODAS"] + lista_ligas_total, key="lp")
        with c2:
            df_t = df_pre if f_l == "TODAS" else df_pre[df_pre['Liga'] == f_l]
            j_list = sorted([int(x) for x in df_t['Jornada'].unique()], reverse=True)
            f_j = st.selectbox("Jornada:", ["TODAS"] + j_list, key="jp")
        
        df_v = df_t if f_j == "TODAS" else df_t[df_t['Jornada'] == int(f_j)]
        st.dataframe(df_v[['Fecha', 'Jornada', 'Liga', 'Partido', 'Pick', 'Prob. Pick', 'Over 1.5', 'Over 2.5', 'BTTS']].style.applymap(color_texto_semaforo, subset=['Prob. Pick', 'Over 1.5', 'Over 2.5', 'BTTS']).format({c: '{:.0%}' for c in ['Prob. Pick', 'Over 1.5', 'Over 2.5', 'BTTS']}), use_container_width=True, hide_index=True)

with tab2:
    st.header("📜 HISTORIAL Y RENDIMIENTO")
    if not df_his.empty:
        busqueda = st.text_input("🔍 Buscar equipo para analizar su efectividad:")
        h1, h2 = st.columns(2)
        with h1: sel_l = st.selectbox("Filtrar Liga:", ["TODAS"] + lista_ligas_total, key="lh")
        with h2:
            df_th = df_his[df_his['Liga'] == sel_l] if sel_l != "TODAS" else df_his
            j_h = sorted([int(x) for x in df_th['Jornada'].unique()], reverse=True)
            sel_j = st.selectbox("Filtrar Jornada:", ["TODAS"] + j_h, key="jh")
        
        df_hf = df_th if sel_j == "TODAS" else df_th[df_th['Jornada'] == str(sel_j)]
        
        if busqueda:
            df_equipo = df_hf[(df_hf['Equipo Local'].str.contains(busqueda, case=False)) | (df_hf['Equipo Visitante'].str.contains(busqueda, case=False))]
            if not df_equipo.empty:
                st.markdown(f"### 📊 Resumen de acierto: {busqueda}")
                m1, m2, m3, m4 = st.columns(4)
                def calc_p(col): return (df_equipo[col] == '✅').mean()
                m1.metric("Efectividad 1X/X2", f"{calc_p('Doble Op.'):.0%}")
                m2.metric("Efectividad O 1.5", f"{calc_p('Over 1.5'):.0%}")
                m3.metric("Efectividad O 2.5", f"{calc_p('Over 2.5'):.0%}")
                m4.metric("Efectividad BTTS", f"{calc_p('BTTS'):.0%}")
                df_hf = df_equipo

        st.dataframe(
            df_hf[['Fecha', 'Jornada', 'Liga', 'Equipo Local', 'Equipo Visitante', 'Marcador', 'Doble Op.', 'Over 1.5', 'Over 2.5', 'BTTS']].style.applymap(color_letras_historial, subset=['Doble Op.', 'Over 1.5', 'Over 2.5', 'BTTS']),
            use_container_width=True, hide_index=True
        )