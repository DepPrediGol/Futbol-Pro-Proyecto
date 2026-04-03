import os
import subprocess
from datetime import datetime

# Se eliminó la importación de Organizador_de_archivos porque ya no se usará

def sincronizar():
    print("--- INICIANDO ACTUALIZACIÓN PRO ---")
    
    # [1/3] PASO OMITIDO: Ya tienes los archivos organizados manualmente
    print("[1/3] Saltando limpieza (Archivos ya listos)...")
    
    # [2/3] Subiendo cambios a la nube
    print("[2/3] Subiendo cambios a la nube...")
    try:
        # Añadir todos los archivos
        subprocess.run(["git", "add", "."], check=True)
        
        # Revisar si hay cambios reales antes de hacer el commit
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
        if not status:
            print("⚠️ No se detectaron cambios nuevos en los archivos.")
        else:
            mensaje_commit = f"Auto-Update: {datetime.now().strftime('%H:%M:%S')}"
            subprocess.run(["git", "commit", "-m", mensaje_commit], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("✅ ¡GitHub actualizado con éxito!")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en la sincronización: {e}")

    print("\n[3/3] ¡PROCESO TERMINADO!")
    print("Revisa tu web: https://betproleague.streamlit.app/")

if __name__ == "__main__":
    print("===========================================")
    print("      ACTUALIZANDO WEB")
    print("===========================================")
    sincronizar()