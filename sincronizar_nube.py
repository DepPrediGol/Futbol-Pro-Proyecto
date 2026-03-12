import subprocess
import os
import time
from Organizador_de_archivos import procesar_todo

def sincronizar():
    print("--- INICIANDO ACTUALIZACIÓN PRO ---")
    
    # 1. Organizar y limpiar los CSV que bajó el PAD
    print("[1/3] Limpiando datos de las ligas...")
    procesar_todo()
    
    # 2. Subir todo a GitHub
    print("[2/3] Subiendo cambios a la nube...")
    try:
        # Forzamos la subida de los CSV ahora que quitamos el bloqueo
        subprocess.run("git add .", shell=True, check=True)
        mensaje = f"Auto-Update: {time.strftime('%H:%M:%S')}"
        subprocess.run(f'git commit -m "{mensaje}"', shell=True)
        subprocess.run("git push origin main", shell=True, check=True)
        print("✅ ¡GitHub actualizado!")
    except Exception as e:
        print(f"❌ Error al subir: {e}")

    print("\n[3/3] ¡PROCESO TERMINADO!")
    print(f"Revisa tu web: https://betproleague.streamlit.app/")
    time.sleep(5)

if __name__ == "__main__":
    sincronizar()