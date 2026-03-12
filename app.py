import streamlit as st
import pandas as pd
import glob
import math
import re

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. DISEÑO VISUAL COMPLETO (Sigue tu esquema original) ---
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
    @keyframes pulse {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.1); }} 100% {{ transform: scale(1); }} }}
    .ball-spin {{ display: inline-block; animation: spin 4s linear infinite; }}
    .ico-pulse {{ display: inline-block; animation: pulse 2s ease-in-out infinite; }}
    .top4-card {{ padding: 12px; border-radius: 10px; transition: all 0.3s; background: rgba(255,255,255,0.5); border: 1px solid #ddd; }}
    .top4-card:hover {{ transform: scale(1.02); background: white; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES LÓGICAS ---
def aplicar_semaforo(val):
    try:
        p = float(val)
        if p >= 0.75: return 'color: #28a745; font-weight: bold;' # Verde
        if p >= 0.60: return 'color: #f7b731; font-weight: bold;' # Amarillo
    except: pass
    return 'color: black;'

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
                        'Partido': f"{f['Equipo Local']} vs {f['Equipo Visitante']}", 'Marcador': f"{g_l}-{g_v}",
                        'Doble Op.': '✅' if g_l >= g_v else '❌', 'Over 1.5': '✅' if (g_l+g_v)>1.5 else '❌',
                        'Over 2.5': '✅' if (g_l+g_v)>2.5 else '❌', 'BTTS': '✅' if (g_l>0 and g_v>0) else '❌'
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
                    
                    actuales.append({
                        'Fecha': f['Fecha'], 'Jornada': int(f['Jornada']), 'Liga': liga_n, 
                        'Partido': f"{f['Equipo Local']} vs {f['Equipo Visitante']}",
                        'Pick': "1X", 'Prob. Pick': (p_l + p_e), 
                        '% Empate (X)': p_e, '% X2': (p_v + p_e),
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
        
        mercados = [('Prob. Pick', 'ico-pulse', '🛡️', 'Doble Oportunidad'), ('Over 1.5', 'ico-bounce', '🥅', 'Over 1.5'), ('Over 2.5', 'ico-pulse', '💥', 'Over 2.5'), ('BTTS', 'ico-shake', '🤝', 'Ambos Marcan')]
        cols = st.columns(4)
        for i, (campo, anim, ico, tit) in enumerate(mercados):
            with cols[i]:
                st.markdown(f'#### <span class="{anim}">{ico}</span> {tit}', unsafe_allow_html=True)
                for _, r in df_top4_real.nlargest(4, campo).iterrows():
                    p_txt = f"<b>{r['Pick']}:</b> " if campo == 'Prob. Pick' else ""
                    st.markdown(f'<div class="top4-card">📅 {r["Fecha"]}<br>{r["Partido"]}<br>{p_txt}<b>{r[campo]:.0%}</b></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("📊 FILTROS DE PREDICCIONES")
        c1, c2 = st.columns(2)
        with c1: f_l = st.selectbox("Selecciona Liga:", ["TODAS"] + lista_ligas_total, key="lp")
        with c2:
            df_temp_p = df_pre if f_l == "TODAS" else df_pre[df_pre['Liga'] == f_l]
            j_list_p = sorted(df_temp_p['Jornada'].unique())
            f_j = st.selectbox("Selecciona Jornada:", ["TODAS"] + [int(x) for x in j_list_p], key="jp")
        
        df_v = df_temp_p if f_j == "TODAS" else df_temp_p[df_temp_p['Jornada'] == int(f_j)]
        
        # Columnas a mostrar (Incluyendo las nuevas de Empate y X2)
        cols_mostrar = ['Fecha', 'Jornada', 'Liga', 'Partido', 'Pick', 'Prob. Pick', '% Empate (X)', '% X2', 'Over 1.5', 'Over 2.5', 'BTTS']
        cols_prob = ['Prob. Pick', '% Empate (X)', '% X2', 'Over 1.5', 'Over 2.5', 'BTTS']
        
        st.dataframe(
            df_v[cols_mostrar].style.applymap(aplicar_semaforo, subset=cols_prob)
            .format({c: '{:.0%}' for c in cols_prob}), 
            use_container_width=True, hide_index=True
        )

with tab2:
    # (El historial se mantiene igual para no alterar tu esquema)
    st.header("📜 HISTORIAL")
    if not df_his.empty:
        h1, h2 = st.columns(2)
        with h1: sel_l = st.selectbox("Liga Historial:", ["TODAS"] + lista_ligas_total, key="lh")
        with h2:
            df_temp_h = df_his[df_his['Liga'] == sel_l] if sel_l != "TODAS" else df_his
            j_list_h = sorted(df_temp_h['Jornada'].unique(), key=lambda x: int(x), reverse=True)
            sel_j = st.selectbox("Jornada Historial:", ["TODAS"] + j_list_h, key="jh")
        
        df_hf = df_temp_h if sel_j == "TODAS" else df_temp_h[df_temp_h['Jornada'] == sel_j]
        if not df_hf.empty:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Doble Oportunidad", f"{(df_hf['Doble Op.'] == '✅').mean():.1%}")
            m2.metric("Over 1.5", f"{(df_hf['Over 1.5'] == '✅').mean():.1%}")
            m3.metric("Over 2.5", f"{(df_hf['Over 2.5'] == '✅').mean():.1%}")
            m4.metric("BTTS", f"{(df_hf['BTTS'] == '✅').mean():.1%}")
            st.dataframe(df_hf, use_container_width=True, hide_index=True)