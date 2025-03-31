# main.py (Sitios web)
import os
import sqlite3
import shutil  # Para copiar la base de datos
from tkinter import Frame, Label, Button, Toplevel, OptionMenu, StringVar, Entry, messagebox

class LinkTracker(Frame):
    def __init__(self, parent):
        super().__init__(parent)
        # Ruta fija al archivo de historial
        self.ruta_historial = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', 'perfiles', 'Historial', 'History_copia')
        )

        # Variables para opciones de filtro, ordenación y paginación
        self.num_elementos = 5  # Default para "Visualizar 5 elementos"
        self.orden = "Más visitados"
        self.sincronizacion = "Ver todos"
        self.pagina_actual = 1
        self.tamano_pagina = 5  # Tamaño fijo de cada página (5 elementos)
        self.resultados = []  # Almacena los resultados de la consulta
        self.sync_status = {}  # Almacena el estado de sincronización para cada URL (False = no seleccionada, True = seleccionada)

        self.init_ui()

    def init_ui(self):
        # Crear Frame para los controles de búsqueda, visualización, sincronización y ordenación
        control_frame = Frame(self)
        control_frame.pack(pady=10)

        # Título
        Label(control_frame, text="Historial de Sitios Web", font=('Helvetica', 16, 'bold')).grid(row=0, column=0, columnspan=8, pady=10)

        # Campo de búsqueda
        Label(control_frame, text="Buscar:").grid(row=1, column=0)
        self.search_entry = Entry(control_frame)
        self.search_entry.grid(row=1, column=1, padx=5)
        # Ejecutar la búsqueda automáticamente cuando se escribe en el campo
        self.search_entry.bind("<KeyRelease>", lambda event: self.mostrar_urls())

        # Menú de ordenación
        Label(control_frame, text="Ordenar:").grid(row=1, column=2)
        self.orden_var = StringVar(value="Más visitados")
        orden_menu = OptionMenu(
            control_frame,
            self.orden_var,
            "Alfabéticamente",
            "Más visitados",
            "Recientes",
            command=self.actualizar_orden
        )
        orden_menu.grid(row=1, column=3, padx=5)

        # Selección para "Visualizar X elementos"
        Label(control_frame, text="Visualizar").grid(row=1, column=4)
        self.num_elementos_var = StringVar(value="5 elementos")
        num_elementos_menu = OptionMenu(
            control_frame,
            self.num_elementos_var,
            "5 elementos",
            "10 elementos",
            "20 elementos",
            "50 elementos",
            command=self.actualizar_num_elementos
        )
        num_elementos_menu.grid(row=1, column=5, padx=5)

        # Filtro de sincronización
        Label(control_frame, text="Sincronización:").grid(row=1, column=6)
        self.sincronizacion_var = StringVar(value="Ver todos")
        sincronizacion_menu = OptionMenu(
            control_frame,
            self.sincronizacion_var,
            "Ver todos",
            "Ver solo sincronizados",
            "Ver solo no sincronizados",
            command=self.actualizar_sincronizacion
        )
        sincronizacion_menu.grid(row=1, column=7, padx=5)

        # Crear Frame para el área de resultados
        self.resultado_frame = Frame(self)
        self.resultado_frame.pack(pady=10)

        # Controles de paginación debajo del área de resultados
        self.paginacion_frame = Frame(self)
        self.paginacion_frame.pack(pady=10)
        
        # Botón "Siguiente" para procesar la selección y crear la nueva base de datos
        self.siguiente_button = Button(self, text="Siguiente", command=self.procesar_seleccion)
        self.siguiente_button.pack(pady=10)

    def actualizar_num_elementos(self, value):
        # Actualizar el número máximo de elementos a mostrar
        self.num_elementos = int(value.split()[0])
        self.pagina_actual = 1  # Reiniciar a la primera página
        self.mostrar_urls()  # Actualizar resultados

    def actualizar_sincronizacion(self, value):
        # Actualizar el filtro de sincronización
        self.sincronizacion = value
        self.pagina_actual = 1
        self.mostrar_urls()

    def actualizar_orden(self, value):
        # Actualizar el criterio de ordenación
        self.orden = value
        self.pagina_actual = 1
        self.mostrar_urls()

    def obtener_resultados(self):
        # Construir la consulta SQL en función de los filtros seleccionados
        consulta = "SELECT title, url, visit_count FROM urls"
        condiciones = []

        # Agregar búsqueda de texto
        busqueda = self.search_entry.get()
        if busqueda:
            condiciones.append(f"url LIKE '%{busqueda}%'")

        # Agregar filtro de sincronización (NOTA: Requiere columna 'sincronizado' en la tabla si se usa)
        if self.sincronizacion == "Ver solo sincronizados":
            condiciones.append("sincronizado = 'si'")
        elif self.sincronizacion == "Ver solo no sincronizados":
            condiciones.append("sincronizado = 'no'")

        # Construir la condición WHERE si hay condiciones
        if condiciones:
            consulta += " WHERE " + " AND ".join(condiciones)

        # Agregar ordenación
        if self.orden == "Alfabéticamente":
            consulta += " ORDER BY title ASC"
        elif self.orden == "Más visitados":
            consulta += " ORDER BY visit_count DESC"
        elif self.orden == "Recientes":
            consulta += " ORDER BY last_visit_time DESC"

        # Aplicar el límite de elementos a mostrar según la selección de "Visualizar"
        consulta += f" LIMIT {self.num_elementos}"

        # Ejecutar la consulta y asegurar que siempre devuelva una lista
        try:
            conexion = sqlite3.connect(self.ruta_historial)
            cursor = conexion.cursor()
            cursor.execute(consulta)
            resultados = cursor.fetchall()  # Almacenar todos los resultados que cumplen con los filtros
            conexion.close()
            return resultados if resultados else []  # Retornar lista vacía si no hay resultados
        except sqlite3.Error as e:
            Label(self.resultado_frame, text=f"Error de base de datos: {e}").pack()
            return []
        except Exception as e:
            Label(self.resultado_frame, text=f"Error inesperado: {e}").pack()
            return []

    def mostrar_urls(self):
        # Limpiar el cuadro de resultados antes de mostrar los nuevos resultados
        for widget in self.resultado_frame.winfo_children():
            widget.destroy()

        # Obtener todos los resultados limitados por "Visualizar"
        resultados = self.obtener_resultados()

        # Calcular el total de páginas basado en `self.tamano_pagina`
        total_paginas = (len(resultados) + self.tamano_pagina - 1) // self.tamano_pagina
        if total_paginas == 0:
            total_paginas = 1  # Evitar que se muestre 0

        # Ajustar la página actual si excede el total de páginas
        if self.pagina_actual > total_paginas:
            self.pagina_actual = total_paginas

        # Calcular el índice de inicio y fin para los resultados de la página actual
        start_idx = (self.pagina_actual - 1) * self.tamano_pagina
        end_idx = start_idx + self.tamano_pagina
        pagina_resultados = resultados[start_idx:end_idx]

        # Configurar la cabecera de la tabla
        headers = ["Título", "Ver URL", "Visitas", "Sincronizado", "Acción"]
        for idx, header in enumerate(headers):
            Label(self.resultado_frame, text=header, font=('Helvetica', 10, 'bold')).grid(row=0, column=idx, padx=10, pady=5)

        # Mostrar los resultados de la página actual
        for idx, (title, url, visit_count) in enumerate(pagina_resultados, start=1):
            Label(self.resultado_frame, text=title, anchor="w").grid(row=idx, column=0, sticky="w", padx=10, pady=5)
            
            # Botón "Ver URL"
            Button(self.resultado_frame, text="Ver URL", command=lambda u=url: self.mostrar_url_ventana(u)).grid(row=idx, column=1, padx=10)

            # Visitas
            Label(self.resultado_frame, text=str(visit_count), anchor="center").grid(row=idx, column=2, padx=10)

            # Estado de sincronización (por defecto "NO" en la interfaz)
            Label(self.resultado_frame, text="NO", anchor="center").grid(row=idx, column=3, padx=10)

            # Botón de "Agregar/Eliminar"
            action_text = "Agregar" if url not in self.sync_status or not self.sync_status[url] else "Eliminar"
            btn = Button(self.resultado_frame, text=action_text)
            btn.config(command=lambda u=url, b=btn: self.toggle_sync_status(u, b))
            btn.grid(row=idx, column=4, padx=10)

        # Actualizar botones de paginación
        self.actualizar_paginacion(total_paginas)

    def mostrar_url_ventana(self, url):
        # Crear una ventana emergente para mostrar la URL
        url_window = Toplevel(self)
        url_window.title("URL")
        url_label = Label(url_window, text=url, padx=10, pady=10, wraplength=300)
        url_label.pack()

    def toggle_sync_status(self, url, button):
        # Alternar el estado de sincronización y actualizar el texto del botón
        if url not in self.sync_status or not self.sync_status[url]:
            self.sync_status[url] = True
            button.config(text="Eliminar")
        else:
            self.sync_status[url] = False
            button.config(text="Agregar")

    def actualizar_paginacion(self, total_paginas):
        # Limpiar el marco de paginación
        for widget in self.paginacion_frame.winfo_children():
            widget.destroy()

        # Botón de "Anterior"
        if self.pagina_actual > 1:
            Button(self.paginacion_frame, text="Anterior", command=self.pagina_anterior).pack(side='left')

        # Indicador de página
        Label(self.paginacion_frame, text=f"Página {self.pagina_actual} de {total_paginas}").pack(side='left', padx=10)

        # Botón de "Siguiente"
        if self.pagina_actual < total_paginas:
            Button(self.paginacion_frame, text="Siguiente", command=self.pagina_siguiente).pack(side='left')

    def pagina_anterior(self):
        if self.pagina_actual > 1:
            self.pagina_actual -= 1
            self.mostrar_urls()

    def pagina_siguiente(self):
        self.pagina_actual += 1
        self.mostrar_urls()

    # *******************************************
    # NUEVA FUNCIÓN: Crear una base de datos nueva con las URL seleccionadas
    # *******************************************
    def procesar_seleccion(self):
        """
        Al hacer clic en el botón 'Siguiente', en lugar de modificar 'History_copia',
        se creará una nueva base de datos (history_filtrado.db) con la misma estructura.
        Luego, se eliminarán de esa nueva base todas las URLs que NO estén seleccionadas.
        """
        # Obtener la lista de URLs seleccionadas (aquellas en las que el usuario hizo clic en "Agregar")
        selected_urls = [url for url, seleccionado in self.sync_status.items() if seleccionado]

        # Confirmación para continuar
        if not messagebox.askyesno(
            "Confirmar",
            "Se creará una NUEVA base de datos con las URLs seleccionadas. ¿Desea continuar?"
        ):
            return

        try:
            # 1) Definir ruta de la nueva base de datos
            carpeta_base = os.path.dirname(self.ruta_historial)
            ruta_filtrada = os.path.join(carpeta_base, "history_filtrado.db")

            # Si existe una base anterior con el mismo nombre, se elimina para recrearla limpia
            if os.path.exists(ruta_filtrada):
                os.remove(ruta_filtrada)

            # 2) Copiar 'History_copia' a 'history_filtrado.db' (misma estructura y datos)
            shutil.copy2(self.ruta_historial, ruta_filtrada)

            # 3) Conectarse a la nueva base y borrar lo que no se seleccionó
            conexion = sqlite3.connect(ruta_filtrada)
            cursor = conexion.cursor()

            if selected_urls:
                # Eliminar todas las filas en las que la URL NO esté en la lista de seleccionadas
                placeholders = ','.join('?' for _ in selected_urls)
                query = f"DELETE FROM urls WHERE url NOT IN ({placeholders})"
                cursor.execute(query, selected_urls)
            else:
                # Si no se seleccionó ninguna URL, se vacía la tabla 'urls'
                cursor.execute("DELETE FROM urls")

            conexion.commit()
            conexion.close()

            messagebox.showinfo(
                "Proceso completado",
                f"Se ha creado la base de datos filtrada en:\n{ruta_filtrada}\ncon las URLs seleccionadas."
            )

            # Actualizar la vista de resultados (opcional)
            self.mostrar_urls()

        except sqlite3.Error as e:
            messagebox.showerror("Error de base de datos", f"Error: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error inesperado: {e}")