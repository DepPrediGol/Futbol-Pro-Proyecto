import pandas as pd
import os
import re

# 1. DICCIONARIO DE RENOMBRADO AUTOMÁTICO
lista_renombrado = {
    '2-bundesliga-de_2025-26.csv': '2-Bundesliga_Alemania.csv',
    '3-liga-de_2025-26.csv': '3-Liga_Alemania.csv',
    'bundesliga-de_2025-26.csv': 'Bundesliga_Alemania.csv',
    'championship-gb-eng_2025-26.csv': 'Championship_Inglaterra.csv',
    'conmebol-libertadores_2026.csv': 'Libertadores.csv',
    'copa-del-rey-es_2025-26.csv': 'CopaDelRey_España.csv',
    'dfb-pokal-de_2025-26.csv': 'DFB-Pokal_Alemania.csv',
    'eerste-divisie-nl_2025-26.csv': 'Eerste-Divisie_Holanda.csv',
    'eredivisie-nl_2025-26.csv': 'Eredivisie_Holanda.csv',
    'fa-cup-gb-eng_2025-26.csv': 'FA-Cup_Inglaterra.csv',
    'j1-league_2026.csv': 'J1-League_Japon.csv',
    'jupiler-pro-league-be_2025-26.csv': 'Jupiler-Pro-League_Belgica.csv',
    'la-liga-es_2025-26.csv': 'La-Liga_España.csv',
    'league-cup-gb-eng_2025-26.csv': 'League-Cup_Inglaterra.csv',
    'league-one-gb-eng_2025-26.csv': 'League-One_Inglaterra.csv',
    'league-two-gb-eng_2025-26.csv': 'League-Two_Inglaterra.csv',
    'liga-mx-mx_2025-26.csv': 'Liga-MX_Mexico.csv',
    'liga-profesional-argentina-ar_2026.csv': 'Liga-Profesional_Argentina.csv',
    'ligue-1-fr_2025-26.csv': 'Ligue-1_Francia.csv',
    'ligue-2-fr_2025-26.csv': 'Ligue-2_Francia.csv',
    'major-league-soccer-us_2026.csv': 'MLS_Estados-Unidos.csv',
    'national-league-gb-eng_2025-26.csv': 'National-League_Inglaterra.csv',
    'premier-league-gb-eng_2025-26.csv': 'Premier-League_Inglaterra.csv',
    'premiership-gb-sct_2025-26.csv': 'Premiership_Escocia.csv',
    'primeira-liga-pt_2025-26.csv': 'Primeira-Liga_Portugal.csv',
    'primera-a_2026.csv': 'Liga-BetPlay_Colombia.csv',
    'primera-b_2026.csv': 'Torneo-BetPlay_Colombia.csv',
    'primera-nacional_2026.csv': 'Primera-Nacional_Argentina.csv',
    'pro-league-sa_2025-26.csv': 'Pro-League_Arabia-Saudita.csv',
    'segunda-division-es_2025-26.csv': 'La-Liga2_España.csv',
    'segunda-liga-pt_2025-26.csv': 'Segunda-Liga_Portugal.csv',
    'serie-a-br_2026.csv': 'Serie-A_Brasil.csv',
    'serie-a-it_2025-26.csv': 'Serie-A_Italia.csv',
    'serie-b-it_2025-26.csv': 'Serie-B_Italia.csv',
    'serie-b_2025.csv': 'Serie-B_Brasil.csv',
    'super-lig-tr_2025-26.csv': 'Super-Lig_Turquia.csv',
    'uefa-champions-league_2025-26.csv': 'Uefa-Champions-League.csv',
    'uefa-europa-conference-league_2025-26.csv': 'Uefa-Europa-Conference-League.csv',
    'uefa-europa-league_2025-26.csv': 'Uefa-Europa-League.csv',
    'usl-championship_2026.csv': 'USL-Championship_Estados-Unidos.csv'
}

# 2. Configuración General
ruta_carpeta = '.' 
carpeta_salida = 'Procesados_Actualizados'
columnas_deseadas = ['matchday', 'date', 'time', 'home_team', 'away_team', 'result', 'status']

def procesar_todo(path=ruta_carpeta, output_folder=carpeta_salida, columns=columnas_deseadas, rename_dict=lista_renombrado):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"📁 Carpeta '{output_folder}' creada.")

    archivos = [f for f in os.listdir(path) if f.endswith('.csv')]
    
    for archivo in archivos:
        if archivo in rename_dict:
            nombre_final = rename_dict[archivo]
            ruta_input = os.path.join(path, archivo)
            ruta_output = os.path.join(output_folder, nombre_final)

            try:
                try:
                    df = pd.read_csv(ruta_input, encoding='utf-8')
                except:
                    df = pd.read_csv(ruta_input, encoding='latin1')

                # A. Filtrar columnas
                columnas_presentes = [col for col in columns if col in df.columns]
                df = df[columnas_presentes].copy()

                # B. Matchday sin decimales
                if 'matchday' in df.columns:
                    df['matchday'] = pd.to_numeric(df['matchday'], errors='coerce').astype('Int64')

                # C. Fecha a DD/MM/YYYY
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%d/%m/%Y')

                # D. Limpiar marcador - CORRECCIÓN AQUÍ PARA EVITAR ERROR 'FLOAT'
                if 'result' in df.columns:
                    # Convertimos a string primero para que no falle con los NaN (floats)
                    df['result'] = df['result'].fillna('').astype(str)
                    df['result'] = df['result'].str.replace(r'\s*\(.*?\)', '', regex=True).str.strip()
                    df['result'] = df['result'].replace(['nan', 'None', '<NA>', ''], '')

                # E. Cambios en Status
                if 'status' in df.columns:
                    df['status'] = df['status'].fillna('').astype(str).str.strip()
                    map_status = {
                        'jugado': 'Final', 'Jugado': 'Final', 'JUGADO': 'Final',
                        'Por jugar': '', 'por jugar': '', 'POR JUGAR': ''
                    }
                    df['status'] = df['status'].replace(map_status)
                    df['status'] = df['status'].replace(['nan', 'None', '<NA>'], '')

                # Guardar
                df.to_csv(ruta_output, index=False, encoding='utf-8')
                print(f"✅ PROCESADO: {archivo} -> {nombre_final}")

            except Exception as e:
                print(f"❌ ERROR en {archivo}: {e}")
        else:
            continue

if __name__ == "__main__":
    procesar_todo(ruta_carpeta, carpeta_salida, columnas_deseadas, lista_renombrado)