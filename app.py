import streamlit as st
import pandas as pd
import glob
import math
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. ESTILOS Y DISEÑO ORGANIZADO ---
st.markdown("""
    <style>
    /* Filtros: Fondo blanco y letras verdes para celular */
    div[data-baseweb="select"] > div { background-color: white !important; color: #28a745 !important; }
    span[data-baseweb="select-item"], div[role="listbox"] div { color: #28a745 !important; background-color: white !important; font-weight: bold !important; }
    
    header {visibility: hidden !important;}
    footer {display: none !important;}
    [data-testid="stStatusWidget"], .stAppDeployButton { display: none !important; visibility: hidden !important; }
    
    .stApp { 
        background-image: url("https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop"); 
        background-attachment: fixed; background-size: cover; 
    }
    .main .block-container { background-color: rgba(255, 255, 255, 0.95); border-radius: 10px; padding: 30px; margin-top: 20px; }
    h1, h2, h3, h4, p, span, div, label, .stMetric { color: #000000 !important; font-weight: bold; }
    
    /* Diseño del Cuadro Organizado (Original) */
    .top4-container {
        padding: 15px;
        border-radius: 15px;
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid #ddd;
        text-align: center;
        margin-bottom: 10px;
        cursor: pointer;
        transition: 0.3s;
    }
    .top4-container:hover { border-color: #28a745; background: white; }

    /* Hacer que el botón de Streamlit sea invisible y cubra todo el cuadro */
    .stButton > button {
        width: 100%;
        background: transparent !important;
        border: none !important;
        color: black !important;
        padding: 0px !important;
    }
    .giro-balon { display: inline-block; animation: rotacion 3s infinite linear; }
    @keyframes rotacion { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES LÓGICAS (Sin cambios) ---
def extraer_goles(resultado_str):
    numeros = re.findall(r'\d+', str(resultado_str))
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

def calcular_fuerzas(df_h):
    equipos = pd.concat([df_h['Equipo Local'], df_h['Equipo Visitante']]).unique()
    f = {e: 1.2 for e in equipos}
    for _, fila in df_h.iterrows():
        g = extraer_goles(fila['Resultado'])
        if g:
            f[fila['Equipo Local']] += 0.20 if g[0] > g[1] else 0.05 * g[0]
            f[fila['Equipo Visitante']] += 0.20 if g[1] > g[0] else 0.05 * g[1]
    return f

# --- 4. CARGA DE DATOS ---
@st.cache_data(ttl=300)
def cargar_todo():
    archivos = glob.glob("*.csv")
    actuales, historicos, ligas = [], [], []
    for arc in archivos:
        try:
            df = pd.read_csv(arc)
            ln = arc.replace('.csv','')
            if ln not in ligas: ligas.append(ln)
            fz = calcular_fuerzas(df)
            df['Fecha_dt'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
            for _, f in df.iterrows():
                pl, pe, pv, po15, po25, pb = obtener_probabilidades(fz.get(f['Equipo Local'],1.2), fz.get(f['Equipo Visitante'],1.2))
                g = extraer_goles(f['Resultado'])
                if g:
                    p1x, px2 = pl+pe, pv+pe
                    pk = "1X" if p1x >= px2 else "X2"
                    pr = max(p1x, px2)
                    historicos.append({
                        'Fecha': f['Fecha'], 'Liga': ln, 'Jornada': str(int(f['Jornada'])),
                        'Equipo Local': f['Equipo Local'], 'Equipo Visitante': f['Equipo Visitante'], 
                        'Marcador': f"{g[0]}-{g[1]}",
                        'Doble Oportunidad': f"{pk} {'✅' if (g[0]>=g[1] if pk=='1X' else g[1]>=g[0]) else '❌'} ({pr:.0%})",
                        'Over 1.5': f"{'✅' if (g[0]+g[1])>1.5 else '❌'} ({po15:.0%})", 
                        'Over 2.5': f"{'✅' if (g[0]+g[1])>2.5 else '❌'} ({po25:.0%})", 
                        'BTTS': f"{'✅' if (g[0]>0 and g[1]>0) else '❌'} ({pb:.0%})"
                    })
                else:
                    actuales.append({
                        'Fecha': f['Fecha'], 'Fecha_dt': f['Fecha_dt'], 'Jornada': int(f['Jornada']), 'Liga': ln, 
                        'Local': f['Equipo Local'], 'Visitante': f['Equipo Visitante'],
                        'Partido': f"{f['Equipo Local']} vs {f['Equipo Visitante']}",
                        '1X': pl+pe, 'X2': pv+pe, 'Over 1.5': po15, 'Over 2.5': po25, 'BTTS': pb
                    })
        except: continue
    return pd.DataFrame(actuales), pd.DataFrame(historicos), sorted(ligas)

df_p, df_h, lgs = cargar_todo()

# --- 5. INTERFAZ ---
st.markdown('<h1><span class="giro-balon">⚽</span> Bet Pro League</h1>', unsafe_allow_html=True)

hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
fechas_futuras = df_p[df_p['Fecha_dt'] >= hoy]['Fecha_dt'].unique() if not df_p.empty else []

if len(fechas_futuras) > 0:
    proxima_fecha = min(fechas_futuras)
    df_t4 = df_p[df_p['Fecha_dt'] == proxima_fecha].copy()
else:
    df_t4 = pd.DataFrame()

# FUNCIÓN PARA LA "PÁGINA APARTE" (MODAL)
@st.dialog("Análisis del Partido")
def mostrar_analisis(partido_data):
    st.title(f"📊 {partido_data['Partido']}")
    st.write(f"**Liga:** {partido_data['Liga']} | **Fecha:** {partido_data['Fecha']}")
    st.markdown("---")
    for eq in [partido_data['Local'], partido_data['Visitante']]:
        st.subheader(f"📈 Racha: {eq}")
        df_eq = df_h[(df_h['Equipo Local']==eq)|(df_h['Equipo Visitante']==eq)].iloc[::-1].head(5)
        if not df_eq.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Doble Op.", f"{(df_eq['Doble Oportunidad'].str.contains('✅').sum()/len(df_eq)):.0%}")
            c2.metric("Over 1.5", f"{(df_eq['Over 1.5'].str.contains('✅').sum()/len(df_eq)):.0%}")
            c3.metric("BTTS", f"{(df_eq['BTTS'].str.contains('✅').sum()/len(df_eq)):.0%}")
            st.dataframe(df_eq, use_container_width=True, hide_index=True)

t1, t2 = st.tabs(["PREDICCIONES", "HISTORIAL"])

with t1:
    if not df_t4.empty:
        st.markdown('### 🏆 TOP 4 POR MERCADO')
        mks = [('DOBLE', '🛡️', 'Doble Oportunidad'), ('Over 1.5', '🥅', 'Over 1.5'), ('Over 2.5', '⚽', 'Over 2.5'), ('BTTS', '🤝', 'Ambos Marcan')]
        cols = st.columns(4)
        
        for i, (m, ico, tit) in enumerate(mks):
            with cols[i]:
                st.markdown(f'#### {ico} {tit}')
                if m == 'DOBLE':
                    df_t4['Mx'] = df_t4[['1X', 'X2']].max(axis=1)
                    df_t4['Tp'] = df_t4.apply(lambda x: '1X' if x['1X'] >= x['X2'] else 'X2', axis=1)
                    top = df_t4.nlargest(4, 'Mx')
                else: top = df_t4.nlargest(4, m)
                
                for idx, r in top.iterrows():
                    v = f"{r['Tp'] if m=='DOBLE' else ''} {r['Mx']:.0%}" if m=='DOBLE' else f"{r[m]:.0%}"
                    # EL CUADRO ORGANIZADO
                    with st.container():
                        st.markdown(f"""
                            <div class="top4-container">
                                📅 {r['Fecha']}<br>
                                <small>{r['Liga']}</small><br>
                                <b>{r['Partido']}</b><br>
                                <span style="color:#1a73e8; font-size: 1.1rem;">{v}</span>
                            </div>
                        """, unsafe_allow_html=True)
                        # Botón invisible sobre el cuadro para abrir la "página aparte"
                        if st.button(" ", key=f"btn_{m}_{idx}"):
                            mostrar_analisis(r)

with t2:
    st.markdown('## 📜 HISTORIAL')
    if not df_h.empty:
        h1, h2 = st.columns(2)
        with h1: st.selectbox("Filtrar Liga:", ["TODAS"] + lgs, key="h1")
        # El resto del historial se mantiene igual...