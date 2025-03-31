import tkinter as tk

def ejecutar_sincronizacion():
    ventana = tk.Tk()
    ventana.title("Sincronización")
    ventana.geometry("300x200")
    label = tk.Label(ventana, text="Pestaña Sincronización", font=("Arial", 14))
    label.pack(pady=20)
    ventana.mainloop()

if __name__ == "__main__":
    ejecutar_sincronizacion()
