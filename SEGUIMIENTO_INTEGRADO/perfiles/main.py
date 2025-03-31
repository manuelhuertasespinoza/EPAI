import os
import json
import shutil  # Para copiar archivos
from tkinter import Frame, Label, OptionMenu, StringVar, Button, messagebox

def obtener_perfiles_chrome():
    ruta_perfil_chrome = os.path.expanduser('/Users/manuelhuertasespinoza/Library/Application Support/Google/Chrome/')
    local_state_path = os.path.join(ruta_perfil_chrome, 'Local State')

    try:
        # Verificar si tenemos permisos para acceder a 'Local State'
        if not os.access(local_state_path, os.R_OK):
            raise PermissionError(f"No se tienen permisos de lectura para acceder a: {local_state_path}")

        with open(local_state_path, 'r') as f:
            local_state_data = json.load(f)

        # Crear un diccionario con el nombre del perfil y la ruta completa al archivo "History"
        perfiles = {
            profile['name']: os.path.join(ruta_perfil_chrome, profile_dir, 'History')
            for profile_dir, profile in local_state_data['profile']['info_cache'].items()
        }

        # Filtrar perfiles que no tengan un archivo "History"
        perfiles_validos = {}
        for nombre, ruta in perfiles.items():
            if os.path.exists(ruta) and os.access(ruta, os.R_OK):
                perfiles_validos[nombre] = ruta

        if not perfiles_validos:
            return {"Error": "No se encontraron perfiles con historial válido."}
        
        return perfiles_validos

    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {"Error": str(e)}
    except PermissionError as e:
        return {"Error": f"Permiso denegado: {e}"}
    except Exception as e:
        return {"Error": f"Ocurrió un error: {e}"}

def copiar_historial_local(ruta_historial):
    # Crear la carpeta "Historial" en la carpeta principal del proyecto si no existe
    carpeta_destino = os.path.join(os.path.dirname(__file__), 'Historial')
    if not os.path.exists(carpeta_destino):
        os.makedirs(carpeta_destino)

    # Definir el nombre del archivo de destino en la carpeta "Historial"
    archivo_destino = os.path.join(carpeta_destino, 'History_copia')

    try:
        # Copiar el archivo de historial a la carpeta "Historial"
        shutil.copy2(ruta_historial, archivo_destino)
        print(f"Copia del archivo 'History' realizada con éxito en: {archivo_destino}")
    except Exception as e:
        print(f"Error al copiar el archivo de historial: {e}")
        messagebox.showerror("Error", f"No se pudo copiar el archivo de historial: {e}")

class ProfileSelector(Frame):
    def __init__(self, parent, on_profile_selected_callback):
        super().__init__(parent)
        self.on_profile_selected_callback = on_profile_selected_callback
        self.init_ui()

    def init_ui(self):
        Label(self, text="Seleccione un Perfil de Chrome", font=('Helvetica', 12)).pack(pady=10)

        self.perfiles = obtener_perfiles_chrome()
        if "Error" in self.perfiles:
            messagebox.showerror("Error", self.perfiles["Error"])
            return

        self.opcion_seleccionada = StringVar(self)
        opciones = list(self.perfiles.keys())
        if opciones:
            self.opcion_seleccionada.set(opciones[0])  # Seleccionar la primera opción

        self.menu = OptionMenu(self, self.opcion_seleccionada, *opciones)
        self.menu.pack(pady=10)

        Button(self, text="Confirmar Selección", command=self.confirmar_seleccion).pack(pady=10)

    def confirmar_seleccion(self):
        perfil_seleccionado = self.opcion_seleccionada.get()
        ruta_history = self.perfiles.get(perfil_seleccionado)
        if ruta_history and self.on_profile_selected_callback:
            # Enviar la ruta completa del archivo History al callback y copiar el historial localmente
            self.on_profile_selected_callback(ruta_history)
            copiar_historial_local(ruta_history)
        else:
            messagebox.showerror("Error", "No se pudo obtener la ruta del archivo de historial.")