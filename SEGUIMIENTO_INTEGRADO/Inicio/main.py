import tkinter as tk

def iniciar_ventana():
    ventana_inicio = tk.Tk()
    ventana_inicio.title("Ventana de Inicio")
    label = tk.Label(ventana_inicio, text="¡Esta es la ventana de Inicio!", font=("Arial", 16))
    label.pack(pady=50)
    ventana_inicio.geometry("400x300")
    ventana_inicio.mainloop()

if __name__ == "__main__":
    iniciar_ventana()
