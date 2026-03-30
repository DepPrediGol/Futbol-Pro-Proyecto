import pandas as pd
import re
import glob
import os

def limpiar_nombre_final(texto):
    """Elimina repeticiones de nombres y basura"""
    if not texto or str(texto).lower() == 'nan': return ""
    
    # Quitar saltos de línea y basura común
    texto = texto.replace('Final', '').replace('apla.', '').replace('venc.', '').strip()
    texto = texto.split('\n')[-1].strip()
    
    # Lógica de "Espejo" para PereiraPereira
    n = len(texto)
    for i in range(1, n // 2 + 1):
        if n % i == 0:
            sub = texto[:i]
            if sub * (n // i) == texto:
                return sub.strip()
    return texto.strip()

def procesar_todo():
    # Buscamos todos los archivos CSV
    archivos_csv = glob.glob("*.csv")
    
    for nombre_archivo in archivos_csv:
        try:
            # 1. Verificar si ya está organizado (para no dañarlo si se corre dos veces)
            with open(nombre_archivo, 'r', encoding='utf-8-sig') as f:
                primera_linea = f.readline()
            if primera_linea.startswith("Fecha,Jornada"):
                continue

            # 2. Leer el archivo sucio
            df = pd.read_csv(nombre_archivo, encoding='utf-8-sig', header=None).astype(str)
            datos_finales = []
            fecha_actual, jornada_actual = "", ""

            print(f"Organizando y sobrescribiendo: {nombre_archivo}...")

            for i in range(len(df)):
                linea = df.iloc[i, 0].strip()

                # A. Detectar Fecha (17.01.2026)
                if re.match(r'\d{2}\.\d{2}\.\d{4}', linea):
                    fecha_actual = linea.replace('.', '/')
                    continue

                # B. Detectar Jornada (1. Jornada)
                if 'Jornada' in linea:
                    nums = re.findall(r'\d+', linea)
                    if nums: jornada_actual = nums[0]
                    continue

                # C. Detectar Separador (Marcador 2:1, Hora 01:20 o Aplazado -:-)
                match_sep = re.search(r'(\d{1,2}:\d{1,2}|-:-)', linea)
                
                if match_sep:
                    separador = match_sep.group(1)
                    
                    # REGLA: Si es hora (HH:MM) o -:- el resultado queda VACÍO
                    # Si es marcador (G:G) se pone con guion
                    es_hora = re.match(r'\d{2}:\d{2}', separador)
                    if es_hora or separador == "-:-":
                        res_final = ""
                    else:
                        res_final = separador.replace(':', '-')

                    # Separar equipos
                    partes = linea.split(separador)
                    local_raw = partes[0].strip()
                    visitante_raw = partes[1].strip() if len(partes) > 1 else ""

                    # Limpieza de nombres
                    local = limpiar_nombre_final(local_raw)
                    visitante = limpiar_nombre_final(visitante_raw)

                    if local and 'Jornada' not in local:
                        datos_finales.append({
                            'Fecha': fecha_actual,
                            'Jornada': jornada_actual,
                            'Equipo Local': local,
                            'Equipo Visitante': visitante,
                            'Resultado': res_final
                        })

            # 3. GUARDAR SOBRE EL ORIGINAL
            if datos_finales:
                df_res = pd.DataFrame(datos_finales).drop_duplicates()
                columnas = ['Fecha', 'Jornada', 'Equipo Local', 'Equipo Visitante', 'Resultado']
                df_res = df_res[columnas]
                
                # Aquí ocurre la magia: guardamos con el MISMO nombre de entrada
                df_res.to_csv(nombre_archivo, index=False, encoding='utf-8-sig')
                print(f"   ✅ {nombre_archivo} actualizado correctamente.")

        except Exception as e:
            print(f"   ❌ Error en {nombre_archivo}: {e}")

if __name__ == "__main__":
    procesar_todo()