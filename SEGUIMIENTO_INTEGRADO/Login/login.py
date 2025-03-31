import tkinter as tk
from PIL import Image, ImageTk
import os

class Login:
    def __init__(self, root, on_login_success):
        self.root = root
        self.root.title("Login")
        self.root.geometry("400x300")
        self.on_login_success = on_login_success

        # Fondo blanco
        self.root.configure(bg="white")

        # Cargar el logo
        logo_path = os.path.join(os.path.dirname(__file__), '..', 'imagenes', 'logo.png')
        logo_img = Image.open(logo_path)
        logo_img = logo_img.resize((100, 100), Image.Resampling.LANCZOS)
        logo_tk = ImageTk.PhotoImage(logo_img)

        # Mostrar el logo
        logo_label = tk.Label(self.root, image=logo_tk, bg="white")
        logo_label.image = logo_tk  # Para evitar que la imagen se recolecte
        logo_label.pack(pady=30)

        # Botón de ingresar
        ingresar_btn = tk.Button(self.root, text="Ingresar", command=self.ingresar, width=20, height=2)
        ingresar_btn.pack(pady=20)

    def ingresar(self):
        self.root.destroy()  # Cierra la ventana de login
        self.on_login_success()  # Llama a la función para abrir la ventana principal
