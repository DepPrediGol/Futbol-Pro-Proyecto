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
        # Añadir todos los archivos actuales al commit
        subprocess.run(["git", "add", "."], check=True)
        
        # Crear el mensaje con la hora actual
        mensaje_commit = f"Auto-Update: {datetime.now().strftime('%H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", mensaje_commit], check=True)
        
        # Empujar a GitHub
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ ¡GitHub actualizado!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en la sincronización: {e}")
        return

    print("\n[3/3] ¡PROCESO TERMINADO!")
    print("Revisa tu web: https://betproleague.streamlit.app/")

if __name__ == "__main__":
    print("===========================================")
    print("      ACTUALIZANDO WEB")
    print("===========================================")
    sincronizar()