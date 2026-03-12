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
    @keyframes spin {{ 100% {{ transform:rotate(360deg); }} }}
    .ball-spin {{ display: inline-block; animation: spin 4s linear infinite; }}
    .top4-card {{ padding: 10px; border-radius: 10px; background: rgba(255,255,255,0.6); border: 1px solid #ddd; text-align: center; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES LÓGICAS ---
def aplicar_semaforo(val):
    try:
        p = float(val)
        if p >= 0.75: return 'color: #28a745; font-weight: bold;'
        if p >= 0.60: return 'color: #f7b731; font-weight: bold;'
    except: pass
    return 'color: black;'

def calcular_poisson(media, x):
    if media <= 0: return 0.001
    return (math.exp(-media) * (media**x)) / math.factorial(x)

def extraer_goles(resultado_str):
    numeros = re.findall(r'\d+', str(resultado_str))
    if len(numeros) >= 2: return int(numeros[0]), int(numeros[1])
    return None

def color_resultado(equipo, marcador):
    goles = extraer_goles(marcador)
    if not goles: return "⚪ -"
    g_l, g_v = goles
    # Esta lógica asume que el marcador está en formato Local-Visitante
    # Necesitamos saber si el equipo analizado era local o visitante en ese partido
    return "" # Se maneja dentro del bucle de visualización

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
            
            for _, f in df.iterrows():
                goles = extraer_goles(f['Resultado'])
                if goles:
                    g_l, g_v = goles
                    historicos.append({
                        'Fecha': f['Fecha'], 'Liga': liga_n, 'Local': f['Equipo Local'], 
                        'Visitante': f['Equipo Visitante'], 'Marcador': f"{g_l}-{g_v}"
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
                    
                    p_1x, p_x2 = (p_l + p_e), (p_v + p_e)
                    pendientes_liga = df[~df['Resultado'].str.contains(r'\d', na=False)].copy()
                    prox_jor = pendientes_liga['Jornada'].min() if not pendientes_liga.empty else 0
                    
                    actuales.append({
                        'Fecha': f['Fecha'], 'Jornada': int(f['Jornada']), 'Liga': liga_n, 
                        'Local': f['Equipo Local'], 'Visitante': f['Equipo Visitante'],
                        '1X': p_1x, 'X': p_e, 'X2': p_x2,
                        'Doble_Mejor_Pick': "1X" if p_1x >= p_x2 else "X2",
                        'Doble_Mejor_Val': p_1x if p_1x >= p_x2 else p_x2,
                        'Over 1.5': p_o15, 'Over 2.5': p_o25, 'BTTS': p_btts,
                        'Es_Proxima': (f['Jornada'] == prox_jor)
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
        
        mercados = [('Doble_Mejor_Val', '🛡️', 'Doble Oportunidad'), ('Over 1.5', '🥅', 'Over 1.5'), ('Over 2.5', '💥', 'Over 2.5'), ('BTTS', '🤝', 'Ambos Marcan')]
        cols = st.columns(4)
        
        for i, (campo, ico, tit) in enumerate(mercados):
            with cols[i]:
                st.markdown(f'#### {ico} {tit}')
                for _, r in df_top4_real.nlargest(4, campo).iterrows():
                    # CUADRO CON PORCENTAJE (Como estaba antes)
                    with st.container():
                        p_label = f"{r['Doble_Mejor_Pick']}: " if campo == 'Doble_Mejor_Val' else ""
                        st.markdown(f"""<div class="top4-card">
                            <small>{r['Fecha']}</small><br>
                            <b>{r['Local']} vs {r['Visitante']}</b><br>
                            <span style="font-size:20px; color:#28a745;">{p_label}{r[campo]:.0%}</span>
                        </div>""", unsafe_allow_html=True)
                        
                        # BOTÓN ABAJITO PARA DETALLES
                        with st.popover("📊 Ver Racha Individual"):
                            for eq_tipo in ['Local', 'Visitante']:
                                nombre_eq = r[eq_tipo]
                                st.write(f"**Últimos 5 de {nombre_eq}:**")
                                h_eq = df_his[(df_his['Local'] == nombre_eq) | (df_his['Visitante'] == nombre_eq)].head(5).copy()
                                
                                def format_res(row):
                                    g = extraer_goles(row['Marcador'])
                                    if not g: return "⚪"
                                    if row['Local'] == nombre_eq:
                                        return "🟢 G" if g[0] > g[1] else ("🟡 E" if g[0] == g[1] else "🔴 P")
                                    else:
                                        return "🟢 G" if g[1] > g[0] else ("🟡 E" if g[1] == g[0] else "🔴 P")

                                if not h_eq.empty:
                                    h_eq['Res'] = h_eq.apply(format_res, axis=1)
                                    st.dataframe(h_eq[['Fecha', 'Local', 'Visitante', 'Marcador', 'Res']], hide_index=True)
                                else:
                                    st.write("Sin datos previos.")

        st.markdown("---")
        # (El resto de la tabla de predicciones sigue igual con tus filtros)
        st.subheader("📊 FILTROS DE PREDICCIONES")
        # ... (Mantengo el resto igual que tu archivo original para no alterar estructura)
        c1, c2 = st.columns(2)
        with c1: f_l = st.selectbox("Selecciona Liga:", ["TODAS"] + lista_ligas_total, key="lp")
        with c2:
            df_temp_p = df_pre if f_l == "TODAS" else df_pre[df_pre['Liga'] == f_l]
            j_list_p = sorted(df_temp_p['Jornada'].unique())
            f_j = st.selectbox("Selecciona Jornada:", ["TODAS"] + [int(x) for x in j_list_p], key="jp")
        
        df_v = df_temp_p if f_j == "TODAS" else df_temp_p[df_temp_p['Jornada'] == int(f_j)]
        cols_finales = ['Fecha', 'Jornada', 'Liga', 'Partido', '1X', 'X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']
        st.dataframe(df_v[cols_finales].style.applymap(aplicar_semaforo, subset=['1X', 'X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']).format({c: '{:.0%}' for c in ['1X', 'X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']}), use_container_width=True, hide_index=True)

with tab2:
    st.header("📜 HISTORIAL")
    # ... (Estructura de historial intacta)
    if not df_his.empty:
        st.dataframe(df_his, use_container_width=True, hide_index=True)