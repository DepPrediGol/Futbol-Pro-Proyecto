import streamlit as st
import pandas as pd
import glob
import math
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Bet Pro League", layout="wide", page_icon="⚽")

# --- 2. ESTILOS, PRIVACIDAD Y RESPONSIVE ---
st.markdown("""
    <style>
    /* Estilo de los filtros: Fondo blanco y letras VERDES */
    div[data-baseweb="select"] > div { background-color: white !important; color: #28a745 !important; }
    span[data-baseweb="select-item"], div[role="listbox"] div { color: #28a745 !important; background-color: white !important; font-weight: bold !important; }
    
    @media (max-width: 640px) {
        .main .block-container { padding: 10px !important; margin-top: 0px !important; }
        h1 { font-size: 1.5rem !important; }
        .top4-card { min-height: 100px !important; }
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
    
    /* Diseño Organizado de la Tarjeta Original */
    .top4-card { 
        padding: 15px; border-radius: 12px; background: rgba(255,255,255,0.9); 
        border: 1px solid #eee; text-align: center; 
        box-shadow: 0px 4px 6px rgba(0,0,0,0.05);
    }
    .top4-card:hover { border-color: #28a745; background: white; }
    
    /* Ajuste para que el popover parezca un botón invisible sobre la tarjeta */
    .stPopover button {
        width: 100% !important; background-color: transparent !important; 
        border: none !important; padding: 0px !important; color: inherit !important;
    }
    .giro-balon { display: inline-block; animation: rotacion 3s infinite linear; }
    @keyframes rotacion { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES LÓGICAS (Sin cambios) ---
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
    st.info(f"📅 Predicciones para: {proxima_fecha.strftime('%d/%m/%Y')}")
else:
    df_t4 = pd.DataFrame()

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
                    # EL TRUCO: Un popover que envuelve la tarjeta organizada
                    with st.popover(f"📅 {r['Fecha']} | {r['Partido']} | {v}", use_container_width=True):
                        st.markdown(f"## 📊 Análisis Detallado: {r['Partido']}")
                        st.write(f"**Liga:** {r['Liga']} | **Fecha:** {r['Fecha']}")
                        st.markdown("---")
                        for eq in [r['Local'], r['Visitante']]:
                            st.subheader(f"📈 Racha: {eq}")
                            df_eq = df_h[(df_h['Equipo Local']==eq)|(df_h['Equipo Visitante']==eq)].iloc[::-1].head(5)
                            if not df_eq.empty:
                                c1, c2, c3 = st.columns(3)
                                c1.metric("Doble Op.", f"{(df_eq['Doble Oportunidad'].str.contains('✅').sum()/len(df_eq)):.0%}")
                                c2.metric("Over 1.5", f"{(df_eq['Over 1.5'].str.contains('✅').sum()/len(df_eq)):.0%}")
                                c3.metric("BTTS", f"{(df_eq['BTTS'].str.contains('✅').sum()/len(df_eq)):.0%}")
                                st.dataframe(df_eq, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown('### 📊 FILTROS DE PREDICCIONES')
        c1, c2 = st.columns(2)
        with c1: sl = st.selectbox("Selecciona Liga:", ["TODAS"] + lgs, key="p1")
        with c2:
            df_fl = df_p if sl=="TODAS" else df_p[df_p['Liga']==sl]
            jornadas_p = sorted([int(x) for x in df_fl['Jornada'].unique()], reverse=True) if not df_fl.empty else []
            sj = st.selectbox("Selecciona Jornada:", ["TODAS"] + jornadas_p, key="p2")
        df_fin = df_fl if sj=="TODAS" else df_fl[df_fl['Jornada']==int(sj)]
        st.dataframe(df_fin[['Fecha', 'Jornada', 'Liga', 'Partido', '1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']].style.applymap(aplicar_semaforo, subset=['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']).format({c: '{:.0%}' for c in ['1X', 'X2', 'Over 1.5', 'Over 2.5', 'BTTS']}), use_container_width=True, hide_index=True)

with t2:
    st.markdown('## 📜 HISTORIAL')
    if not df_h.empty:
        h1, h2 = st.columns(2)
        with h1: slh = st.selectbox("Filtrar Liga:", ["TODAS"] + lgs, key="h1")
        with h2:
            df_hist_filtro = df_h if slh=="TODAS" else df_h[df_h['Liga']==slh]
            jornadas_h = sorted(df_hist_filtro['Jornada'].unique().tolist(), key=lambda x: int(x), reverse=True) if not df_hist_filtro.empty else []
            sjh = st.selectbox("Filtrar Jornada:", ["TODAS"] + jornadas_h, key="h2")
        bq = st.text_input("🔍 Buscar equipo en historial:", key="h3")
        df_res = df_hist_filtro if sjh=="TODAS" else df_hist_filtro[df_hist_filtro['Jornada']==sjh]
        if bq: df_res = df_res[(df_res['Equipo Local'].str.contains(bq, case=False)) | (df_res['Equipo Visitante'].str.contains(bq, case=False))]
        st.dataframe(df_res.style.applymap(color_letras_historial, subset=['Doble Oportunidad', 'Over 1.5', 'Over 2.5', 'BTTS']), use_container_width=True, hide_index=True)