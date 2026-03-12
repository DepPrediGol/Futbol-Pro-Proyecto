import streamlit as st
import pandas as pd
import glob
import math
import re

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. DISEÑO VISUAL COMPLETO ---
fondo_url = "https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"
st.markdown(f"""
    <style>
    .stApp {{ background-image: url("{fondo_url}"); background-attachment: fixed; background-size: cover; }}
    .main .block-container {{ background-color: rgba(255, 255, 255, 0.95); border-radius: 10px; padding: 30px; margin-top: 20px; }}
    h1, h2, h3, h4, p, span, div, label, .stMetric {{ color: #000000 !important; font-weight: bold; }}
    div[data-baseweb="select"] > div, ul[role="listbox"], div[data-baseweb="popover"] div {{
        background-color: white !important; color: black !important;
    }}
    input[data-baseweb="input"] {{ color: black !important; -webkit-text-fill-color: black !important; }}
    @keyframes spin {{ 100% {{ transform:rotate(360deg); }} }}
    .ball-spin {{ display: inline-block; animation: spin 4s linear infinite; }}
    .top4-card {{ padding: 12px; border-radius: 10px; transition: all 0.3s; background: rgba(255,255,255,0.5); border: 1px solid #ddd; text-align: center; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES LÓGICAS ---
def calcular_poisson(media, x):
    if media <= 0: return 0.001
    return (math.exp(-media) * (media**x)) / math.factorial(x)

def extraer_goles(resultado_str):
    numeros = re.findall(r'\d+', str(resultado_str))
    if len(numeros) >= 2: return int(numeros[0]), int(numeros[1])
    return None

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
            
            pendientes_liga = df[~df['Resultado'].str.contains(r'\d', na=False)].copy()
            prox_jor_liga = pendientes_liga['Jornada'].min() if not pendientes_liga.empty else 0
            
            for _, f in df.iterrows():
                goles = extraer_goles(f['Resultado'])
                if goles:
                    g_l, g_v = goles
                    historicos.append({
                        'Fecha': f['Fecha'], 'Liga': liga_n, 'Jornada': str(int(f['Jornada'])),
                        'Equipo Local': f['Equipo Local'], 'Equipo Visitante': f['Equipo Visitante'], 
                        'Marcador': f"{g_l}-{g_v}"
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
st.markdown('<h1><span class="ball-spin">⚽</span> Bet Pro League</h1>', unsafe_allow_html=True)
tab1, tab2 = st.tabs(["PREDICCIONES", "HISTORIAL"])

with tab1:
    if not df_pre.empty:
        st.subheader("🏆 TOP 4 POR MERCADO (PRÓXIMA JORNADA)")
        df_top4_real = df_pre[df_pre['Es_Proxima'] == True]
        
        mercados = [('Prob. Pick', '🛡️', 'Doble Oportunidad'), ('Over 1.5', '🥅', 'Over 1.5'), ('Over 2.5', '💥', 'Over 2.5'), ('BTTS', '🤝', 'Ambos Marcan')]
        cols = st.columns(4)
        for i, (campo, anim, ico, tit) in enumerate(mercados):
            with cols[i]:
                st.markdown(f'#### {ico} {tit}')
                for _, r in df_top4_real.nlargest(4, campo).iterrows():
                    with st.container():
                        p_txt = f"<b>{r['Pick']}:</b> " if campo == 'Prob. Pick' else ""
                        st.markdown(f"""<div class="top4-card">
                            <small>{r['Fecha']}</small><br>
                            <b>{r['Partido']}</b><br>
                            <span style="font-size:18px;">{p_txt}<b>{r[campo]:.0%}</b></span>
                        </div>""", unsafe_allow_html=True)
                        
                        # BOTÓN DE RACHA CORREGIDO
                        with st.popover("📊 Ver Racha"):
                            for eq_tipo in ['Local', 'Visitante']:
                                nombre_eq = r[eq_tipo]
                                st.write(f"**Últimos de {nombre_eq}:**")
                                # Filtramos usando los nombres de columna exactos del historial
                                h_eq = df_his[(df_his['Equipo Local'] == nombre_eq) | (df_his['Equipo Visitante'] == nombre_eq)].head(5).copy()
                                
                                if not h_eq.empty:
                                    def f_res(row):
                                        g = extraer_goles(row['Marcador'])
                                        if not g: return "⚪"
                                        if row['Equipo Local'] == nombre_eq:
                                            return "🟢 G" if g[0] > g[1] else ("🟡 E" if g[0] == g[1] else "🔴 P")
                                        else:
                                            return "🟢 G" if g[1] > g[0] else ("🟡 E" if g[1] == g[0] else "🔴 P")
                                    
                                    h_eq['Res'] = h_eq.apply(f_res, axis=1)
                                    st.dataframe(h_eq[['Fecha', 'Equipo Local', 'Equipo Visitante', 'Marcador', 'Res']], hide_index=True)
                                else:
                                    st.write("Sin datos previos.")

        st.markdown("---")
        st.subheader("📊 FILTROS DE PREDICCIONES")
        c1, c2 = st.columns(2)
        with c1: f_l = st.selectbox("Selecciona Liga:", ["TODAS"] + lista_ligas_total, key="lp")
        with c2:
            df_temp_p = df_pre if f_l == "TODAS" else df_pre[df_pre['Liga'] == f_l]
            j_list_p = sorted([int(x) for x in df_temp_p['Jornada'].unique()], reverse=True)
            f_j = st.selectbox("Selecciona Jornada:", ["TODAS"] + j_list_p, key="jp")
        
        df_v = df_temp_p if f_j == "TODAS" else df_temp_p[df_temp_p['Jornada'] == int(f_j)]
        cols_mostrar = ['Fecha', 'Jornada', 'Liga', 'Partido', 'Pick', 'Prob. Pick', 'Over 1.5', 'Over 2.5', 'BTTS']
        st.dataframe(df_v[cols_mostrar].style.format({c: '{:.0%}' for c in ['Prob. Pick', 'Over 1.5', 'Over 2.5', 'BTTS']}), use_container_width=True, hide_index=True)

with tab2:
    st.header("📜 HISTORIAL")
    if not df_his.empty:
        st.dataframe(df_his, use_container_width=True, hide_index=True)