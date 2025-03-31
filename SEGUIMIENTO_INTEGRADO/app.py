import rumps
import subprocess
import os
import sys
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import importlib.util

# IMPORTACIONES DE LOS MÓDULOS ORIGINALES (asegúrate de que las rutas sean correctas)
from perfiles.main import ProfileSelector
from sitios_web.main import LinkTracker

# Agregar la ruta de SEGUIMIENTO_INTEGRADO al sys.path para que Python pueda encontrar los módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ================================================
#               Aplicación Tkinter
# ================================================
class Aplicacion:
    def __init__(self, root):
        self.root = root
        self.root.title("SEGUIMIENTO INTEGRADO")
        self.root.geometry("800x600")

        # Inicialmente ocultar el contenedor principal
        self.contenedor = None

        # Configurar layout
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)  # Permitir que el área de contenido se expanda
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=1)  # Permitir que el área de contenido se expanda

        # Crear instancias de ProfileSelector y LinkTracker
        self.link_tracker = LinkTracker(self.root)
        self.profile_selector = ProfileSelector(self.root, self.on_profile_selected)

        # Mostrar ProfileSelector en el frame
        self.profile_selector.grid(row=1, column=0, padx=20, pady=20)

        # Mostrar LinkTracker en el frame
        self.link_tracker.grid(row=1, column=1, padx=20, pady=20)

        # Mostrar la ventana de login
        self.mostrar_login()

    def crear_barra_superior(self):
        # Frame para la barra superior
        self.barra_superior = tk.Frame(self.root, bg="#711655", height=50)
        self.barra_superior.grid(row=0, column=0, columnspan=2, sticky="ew")

        # Cargar el logo
        logo_path = os.path.join(os.path.dirname(__file__), "imagenes/logo.png")
        if os.path.exists(logo_path):
            logo = Image.open(logo_path)
            logo = logo.resize((40, 40), Image.LANCZOS)
            self.logo_tk = ImageTk.PhotoImage(logo)
            tk.Label(self.barra_superior, image=self.logo_tk, bg="#711655").pack(side="left", padx=10)

        # Label del nombre del usuario logueado
        usuario_label = tk.Label(self.barra_superior, text="Manuel H.", bg="#3b5998", fg="white", padx=20, pady=10)
        usuario_label.pack(side="right", padx=20)
        usuario_label.bind("<Button-1>", self.mostrar_menu_desplegable)

        # Crear el menú desplegable
        self.menu_desplegable = tk.Menu(self.barra_superior, tearoff=0)
        self.menu_desplegable.add_command(label="Perfil", command=self.accion_perfil)
        self.menu_desplegable.add_command(label="Configuración", command=self.accion_configuracion)
        self.menu_desplegable.add_command(label="Ayuda", command=self.accion_ayuda)
        self.menu_desplegable.add_separator()
        self.menu_desplegable.add_command(label="Salir", command=self.accion_salir)

    def mostrar_menu_desplegable(self, event):
        self.menu_desplegable.tk_popup(event.x_root, event.y_root)

    def accion_perfil(self):
        print("Acción: Perfil")

    def accion_configuracion(self):
        print("Acción: Configuración")

    def accion_ayuda(self):
        print("Acción: Ayuda")

    def accion_salir(self):
        self.root.quit()

    def crear_menu_principal(self):
        # Frame menú lateral con scrollbar
        frame_menu = tk.Frame(self.contenedor, bg="#711655")
        frame_menu.grid(row=1, column=0, sticky="ns")

        canvas = tk.Canvas(frame_menu, bg="#711655")
        scrollbar = tk.Scrollbar(frame_menu, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#711655")

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Botones del menú
        opciones = [("Inicio", "Inicio"), ("Perfiles", "perfiles"), ("Sitios Web", "sitios_Web"),
                    ("Palabras Claves", "Palabras_Claves"), ("Sincronización", "Sincronizacion")]
        for texto, carpeta in opciones:
            tk.Button(
                scrollable_frame,
                text=texto,
                command=lambda c=carpeta: self.cambiar_contenido(c),
                width=33,
                height=2,
                font=('Helvetica', 12, 'bold'),
                relief="flat"
            ).pack(pady=5, fill="x")

    def cambiar_contenido(self, carpeta):
        # Limpiar contenido actual del frame
        for widget in self.frame_contenido.winfo_children():
            widget.destroy()

        # Ruta del archivo main.py de la carpeta seleccionada
        ruta_script = os.path.join(os.path.dirname(__file__), carpeta, 'main.py')

        # Verificar si el script existe
        if os.path.exists(ruta_script):
            self.cargar_modulo_dinamico(ruta_script)
        else:
            self.mostrar_error(f"No se encuentra el archivo en la ruta: {ruta_script}")

    def cargar_modulo_dinamico(self, ruta_script):
        try:
            # Cargar dinámicamente el archivo main.py
            spec = importlib.util.spec_from_file_location("modulo_dinamico", ruta_script)
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
            print(f"Cargando módulo: {modulo}")

            # Diccionario de clases esperadas
            clases_validas = {"LinkTracker": "LinkTracker", "ProfileSelector": "ProfileSelector", "KeywordTracker": "KeywordTracker"}
            
            for clase in clases_validas:
                if hasattr(modulo, clase):
                    # Si la clase existe, inicializarla
                    if clase == "ProfileSelector":
                        self.profile_selector = getattr(modulo, clase)(self.frame_contenido, self.on_profile_selected)
                        self.profile_selector.pack(fill='both', expand=True)
                        print(f"{clase} cargado con éxito.")
                    elif clase == "LinkTracker":
                        self.link_tracker = getattr(modulo, clase)(self.frame_contenido)
                        self.link_tracker.pack(fill='both', expand=True)
                        print(f"{clase} cargado con éxito.")
                    elif clase == "KeywordTracker":
                        self.keyword_tracker = getattr(modulo, clase)(self.frame_contenido)
                        self.keyword_tracker.pack(fill='both', expand=True)
                        print(f"{clase} cargado con éxito.")
                    
                    # Salir del bucle después de encontrar e inicializar la clase
                    return
                else:
                    # Si la clase no está presente, imprimir un mensaje
                    print(f"Advertencia: {clase} no encontrado en el módulo: {modulo.__name__}")

            # Si ninguna de las clases válidas fue encontrada
            raise AttributeError(f"El módulo no contiene ninguna de las clases esperadas: {', '.join(clases_validas)}")

        except Exception as e:
            self.mostrar_error(f"Error ejecutando el script: {e}")
            print(f"Error detallado: {e}")

    def mostrar_error(self, mensaje):
        tk.Label(self.frame_contenido, text=mensaje, fg="red", font=('Helvetica', 16, 'bold')).pack(pady=20)

    def on_profile_selected(self, ruta_historial):
        print(f"Perfil seleccionado, ruta del historial: {ruta_historial}")
        # Ya no es necesario establecer la ruta_historial en LinkTracker, pues usa una ruta fija

    def mostrar_login(self):
        # Crear una ventana de login
        self.login_window = tk.Toplevel(self.root)
        self.login_window.title("Login")
        self.login_window.geometry("300x200")

        # Crear un frame para el login
        frame_login = tk.Frame(self.login_window)
        frame_login.pack(pady=20)

        # Etiqueta de usuario
        tk.Label(frame_login, text="Usuario:").grid(row=0, column=0, padx=10)
        self.usuario_entry = tk.Entry(frame_login)
        self.usuario_entry.grid(row=0, column=1)

        # Etiqueta de contraseña
        tk.Label(frame_login, text="Contraseña:").grid(row=1, column=0, padx=10)
        self.contrasena_entry = tk.Entry(frame_login, show='*')
        self.contrasena_entry.grid(row=1, column=1)

        # Botón de inicio de sesión
        tk.Button(frame_login, text="Iniciar Sesión", command=self.iniciar_sesion).grid(row=2, columnspan=2, pady=10)

        # Deshabilitar el acceso a la ventana principal hasta que se inicie sesión
        self.root.withdraw()

    def iniciar_sesion(self):
        # Lógica de inicio de sesión
        self.login_window.destroy()
        self.root.deiconify()

        # Crear barra superior y menú principal después de iniciar sesión
        self.crear_barra_superior()
        self.crear_menu_principal()

        # Crear el contenedor para el contenido
        self.frame_contenido = tk.Frame(self.root)
        self.frame_contenido.grid(row=1, column=1, sticky="nsew")


# ================================================
#         Menú de la barra con rumps
# ================================================
class MenuBarApp(rumps.App):
    def __init__(self):
        # Se establece el título y el ícono (ajusta la ruta del ícono si es necesario)
        super().__init__("Mi App", icon="imagenes/logo_sup.jpeg")
        self.menu = ["Abrir Aplicación", "Salir"]

    @rumps.clicked("Abrir Aplicación")
    def abrir_aplicacion(self, _):
        # Se obtiene la ruta absoluta del archivo actual (asumido "app.py")
        ruta_app = os.path.join(os.path.dirname(__file__), "app.py")
        # Se invoca el proceso indicando el argumento "gui" para que se inicie la aplicación Tkinter
        subprocess.Popen(["python3", ruta_app, "gui"])

    @rumps.clicked("Salir")
    def salir(self, _):
        rumps.quit_application()


# ================================================
#             MAIN: Selección de modo
# ================================================
if __name__ == "__main__":
    # Si se invoca el archivo con el argumento "gui" se lanza la aplicación Tkinter,
    # de lo contrario se ejecuta el menú de la barra (modo tray)
    if len(sys.argv) > 1 and sys.argv[1] == "gui":
        root = tk.Tk()
        app = Aplicacion(root)
        root.mainloop()
    else:
        MenuBarApp().run()