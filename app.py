import streamlit as st
import pandas as pd
import glob
import math
import re

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. DISEÑO VISUAL MEJORADO (CSS) ---
fondo_url = "https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"
st.markdown(f"""
    <style>
    /* Fondo de pantalla */
    .stApp {{
        background-image: url("{fondo_url}");
        background-attachment: fixed;
        background-size: cover;
    }}
    
    /* Contenedor principal translúcido */
    .main .block-container {{
        background-color: rgba(255, 255, 255, 0.92);
        border-radius: 15px;
        padding: 30px;
        margin-top: 20px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.3);
    }}

    /* Estilo de textos para máxima legibilidad */
    h1, h2, h3, p, span, label {{
        color: #1a1a1a !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }}

    /* Estilo de las pestañas (Tabs) */
    .stTabs [data-baseweb="tab"] {{
        font-size: 18px;
        font-weight: bold;
        color: #333;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES DE LÓGICA Y CÁLCULO ---
def calcular_probabilidades(df_liga):
    """Calcula estadísticas y picks basados en el historial de la liga"""
    if df_liga.empty: return pd.DataFrame()
    
    # Filtrar solo partidos jugados (que tienen resultado con '-')
    df_jugados = df_liga[df_liga['Resultado'].str.contains('-', na=False)].copy()
    
    # Calcular promedios básicos
    total_partidos = len(df_jugados)
    if total_partidos == 0: return pd.DataFrame()

    overs_15 = len(df_jugados[df_jugados['Resultado'].apply(lambda x: sum(map(int, re.findall(r'\d+', x))) > 1.5)]) / total_partidos
    overs_25 = len(df_jugados[df_jugados['Resultado'].apply(lambda x: sum(map(int, re.findall(r'\d+', x))) > 2.5)]) / total_partidos
    
    def es_btts(res):
        goles = re.findall(r'\d+', res)
        return int(goles[0]) > 0 and int(goles[1]) > 0 if len(goles)==2 else False
    
    btts_prob = len(df_jugados[df_jugados['Resultado'].apply(es_btts)]) / total_partidos

    # Crear predicciones para partidos pendientes
    df_pendientes = df_liga[~df_liga['Resultado'].str.contains('-', na=False)].copy()
    
    picks = []
    for _, row in df_pendientes.iterrows():
        # Lógica simple de ejemplo: Si la liga es over, el pick es over
        pick_text = "Over 1.5" if overs_15 > 0.70 else "Local o Empate"
        prob = overs_15 if "Over" in pick_text else 0.65
        
        picks.append({
            'Fecha': row['Fecha'],
            'Jornada': row['Jornada'],
            'Partido': f"{row['Equipo Local']} vs {row['Equipo Visitante']}",
            'Pick': pick_text,
            'Prob. Pick': prob,
            'Over 1.5': overs_15,
            'Over 2.5': overs_25,
            'BTTS': btts_prob,
            'Liga': row['Liga_Nombre']
        })
    
    return pd.DataFrame(picks)

# --- 4. CARGA DE DATOS ---
archivos = glob.glob("*.csv")
df_lista_picks = []
df_lista_historial = []
lista_ligas_total = []

for arc in archivos:
    try:
        nombre_liga = arc.replace(".csv", "").replace("-", " ").replace("_", " ")
        temp_df = pd.read_csv(arc)
        temp_df['Liga_Nombre'] = nombre_liga
        
        # Separar historial y futuros
        df_lista_historial.append(temp_df[temp_df['Resultado'].str.contains('-', na=False)])
        
        # Calcular picks
        picks_liga = calcular_probabilidades(temp_df)
        if not picks_liga.empty:
            df_lista_picks.append(picks_liga)
        
        lista_ligas_total.append(nombre_liga)
    except:
        continue

df_fut = pd.concat(df_lista_picks) if df_lista_picks else pd.DataFrame()
df_his = pd.concat(df_lista_historial) if df_lista_historial else pd.DataFrame()

# --- 5. INTERFAZ DE USUARIO ---
st.title("⚽ BET PRO LEAGUE")
st.subheader("Análisis Estadístico y Predicciones de Fútbol")

tab1, tab2 = st.tabs(["🎯 PRÓXIMOS PICKS", "📜 HISTORIAL DE LIGAS"])

with tab1:
    st.header("🎯 Sugerencias para hoy")
    if not df_fut.empty:
        # Función para pintar las celdas de probabilidad
        def color_probabilidad(val):
            try:
                p = float(val)
                if p >= 0.75: return 'background-color: #28a745; color: white;' # Verde
                if p >= 0.65: return 'background-color: #ffc107; color: black;' # Amarillo
            except: pass
            return ''

        # Filtros
        c1, c2 = st.columns(2)
        with c1: sel_l = st.selectbox("Filtrar por Liga:", ["TODAS"] + lista_ligas_total)
        
        df_ver = df_fut[df_fut['Liga'] == sel_l] if sel_l != "TODAS" else df_fut
        
        # Formatear y mostrar
        df_ver['Pick'] = "⚽ " + df_ver['Pick']
        
        st.dataframe(
            df_ver[['Fecha', 'Liga', 'Partido', 'Pick', 'Prob. Pick', 'Over 1.5', 'Over 2.5', 'BTTS']]
            .style.applymap(color_probabilidad, subset=['Prob. Pick'])
            .format({'Prob. Pick': '{:.0%}', 'Over 1.5': '{:.0%}', 'Over 2.5': '{:.0%}', 'BTTS': '{:.0%}'}),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay partidos pendientes detectados en los archivos CSV.")

with tab2:
    st.header("📜 Resultados Anteriores")
    if not df_his.empty:
        sel_l_h = st.selectbox("Selecciona Liga para ver resultados:", lista_ligas_total)
        df_h_ver = df_his[df_his['Liga_Nombre'] == sel_l_h].sort_values(by='Jornada', ascending=False)
        st.write(f"Mostrando últimos partidos de: **{sel_l_h}**")
        st.table(df_h_ver[['Fecha', 'Jornada', 'Equipo Local', 'Equipo Visitante', 'Resultado']].head(15))