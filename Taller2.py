# ==========================================================
# PEA-i: PROGRAMA ESTADÍSTICO DE ANÁLISIS DE INVESTIGACIÓN
# Con Tarjeta Incrustada en la Interfaz Principal, Logos,
# Vistas, Hipercubos, CRUD y Persistencia.
# ==========================================================

from datetime import datetime
from io import BytesIO
import json
import os
import tkinter as tk
from tkinter import messagebox, ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import requests
from bs4 import BeautifulSoup


class GestorDatosInvestigacion:

  def __init__(self):
    self.lista_grupos = []
    self.multilista_relacional = {}
    self.hipercubo_multidimensional = {}
    self.pila_historial = []
    self.cola_urls = []
    self.archivo_persistencia = "datos_pea_i_tarjetas.json"
    self.cargar_persistencia()

  '''def encolar_url(self, url):
    url_limpia = url.strip()
    if not url_limpia:
      messagebox.showwarning(
          "Aviso", "Por favor ingresa una URL válida para encolar."
      )
      return
    self.cola_urls.append(url_limpia)
    self.pila_historial.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] Encolada URL (FIFO):"
        f" {url_limpia}"
    )
    messagebox.showinfo(
        "Cola FIFO",
        f"URL agregada a la cola. Elementos pendientes: {len(self.cola_urls)}",
    )
    self.guardar_persistencia()

  def procesar_siguiente_cola(self, tree, actualizar_tarjeta_callback):
    if not self.cola_urls:
      messagebox.showwarning(
          "Cola Vacía", "No hay URLs pendientes en la cola (FIFO)."
      )
      return
    url = self.cola_urls.pop(0)
    self.pila_historial.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] Procesando URL de cola: {url}"
    )
    self.crear_o_importar_grupo(url, tree, actualizar_tarjeta_callback)

  def ver_pila_historial(self):
    if not self.pila_historial:
      messagebox.showinfo("Pila LIFO", "La pila de historial está vacía.")
      return
    historial_texto = "\n".join(self.pila_historial[-15:])
    messagebox.showinfo(
        "Pila de Acciones (LIFO - Último en Entrar, Primero en Salir)",
        historial_texto,
    )'''

  def crear_o_importar_grupo(self, url_entrada, tree, actualizar_tarjeta_callback):
    url = url_entrada.strip()
    if not url:
      messagebox.showerror("Error", "Ingresa una URL válida.")
      return
    if not url.startswith("http://") and not url.startswith("https://"):
      url = "https://" + url

    try:
      headers = {
          "User-Agent": (
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          )
      }
      response = requests.get(url, headers=headers, timeout=8)

      nombre_grupo = "Grupo de Investigación Institucional"
      descripcion_breve = (
          "Grupo dedicado a la generación de nuevo conocimiento científico y"
          " desarrollo tecnológico."
      )
      logo_url = ""

      hash_val = abs(hash(url))
      codigo_grupo = f"COL{hash_val % 9000000 + 1000000}"

      if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        # Extracción de Título
        titulo_tag = (
            soup.find("td", class_="celdaCabecera")
            or soup.find("h1")
            or soup.find("title")
        )
        if titulo_tag:
          texto = titulo_tag.get_text(strip=True)
          if texto:
            nombre_grupo = texto

        # Extracción de Descripción Breve
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
          descripcion_breve = meta_desc.get("content")
        else:
          p_tag = soup.find("p")
          if p_tag:
            descripcion_breve = p_tag.get_text(strip=True)[:180] + "..."

        # Extracción de Logo
        img_tag = soup.find(
            "img",
            attrs={
                "src": lambda x: x and ("logo" in x.lower() or "escudo" in x.lower())
            },
        )
        if not img_tag:
          img_tag = soup.find("img")

        if img_tag and img_tag.get("src"):
          logo_url = img_tag.get("src")
          if logo_url.startswith("/"):
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            logo_url = f"{parsed_url.scheme}://{parsed_url.netloc}{logo_url}"

      num_integrantes = (hash_val % 4) + 3
      num_productos = (hash_val % 6) + 4

      nuevo_grupo = {
          "codigo": codigo_grupo,
          "nombre": nombre_grupo,
          "acronimo": f"GRP-{hash_val % 900 + 100}",
          "estado": "Activo",
          "url": url,
          "descripcion": descripcion_breve,
          "logo_url": logo_url,
      }

      integrantes = [
          {
              "cedula": f"1065{hash_val % 9000 + i}",
              "nombre": f"Investigador Colaborador {i+1}",
              "rol": "Líder" if i == 0 else "Investigador Asociado",
          }
          for i in range(num_integrantes)
      ]

      productos = [
          {
              "nombre": f"Artículo Científico Indexado #{i+1}",
              "categoria": "A1" if i % 2 == 0 else "B",
              "anio": 2023 + (i % 4),
          }
          for i in range(num_productos)
      ]

      multidatos = {
          "integrantes": integrantes,
          "productos": productos,
          "proyectos_por_anio": {
              2023: hash_val % 3 + 1,
              2024: hash_val % 4 + 2,
              2025: hash_val % 5 + 3,
              2026: hash_val % 6 + 4,
          },
          "tipologia": {
              "Resultados C-T": 55.0 + (hash_val % 5),
              "Formación": 38.0,
              "Otros": 7.0 - (hash_val % 5),
          },
          "sublineas": {
              "Línea Principal Aplicada": 50.0,
              "Desarrollo Tecnológico": 50.0,
          },
          "roles": {"Líderes": 40.0, "Asociados": 35.0, "Semilleros": 25.0},
      }

      cubo_grupo = {}
      for prod in productos:
        anio_str = str(prod["anio"])
        cat = prod["categoria"]
        if anio_str not in cubo_grupo:
          cubo_grupo[anio_str] = {}
        if cat not in cubo_grupo[anio_str]:
          cubo_grupo[anio_str][cat] = 0
        cubo_grupo[anio_str][cat] += 1

      self.lista_grupos.append(nuevo_grupo)
      self.multilista_relacional[codigo_grupo] = multidatos
      self.hipercubo_multidimensional[codigo_grupo] = cubo_grupo

      self.pila_historial.append(
          f"[{datetime.now().strftime('%H:%M:%S')}] Grupo Importado:"
          f" {nombre_grupo}"
      )
      self.guardar_persistencia()
      self.actualizar_vista_general(tree)

      # Actualizar la tarjeta incrustada en pantalla
      actualizar_tarjeta_callback(nuevo_grupo)
      messagebox.showinfo(
          "Éxito", "Grupo importado y tarjeta actualizada correctamente."
      )

    except Exception as e:
      messagebox.showerror(
          "Error", f"No se pudo procesar la URL para la tarjeta:\n{e}"
      )

  def modificar_grupo(self, codigo, nuevo_nombre, tree):
    for g in self.lista_grupos:
      if g["codigo"] == codigo:
        g["nombre"] = nuevo_nombre
        self.pila_historial.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] Grupo Modificado {codigo}"
        )
        self.guardar_persistencia()
        messagebox.showinfo("Modificación", "Nombre de grupo modificado.")
        self.actualizar_vista_general(tree)
        return
    messagebox.showwarning("Aviso", "Selecciona un grupo válido de la tabla.")

  def desactivar_grupo(self, codigo, tree):
    for g in self.lista_grupos:
      if g["codigo"] == codigo:
        g["estado"] = "Inactivo" if g["estado"] == "Activo" else "Activo"
        self.pila_historial.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] Estado cambiado grupo"
            f" {codigo}"
        )
        self.guardar_persistencia()
        messagebox.showinfo(
            "Estado", f"El estado del grupo cambió a: {g['estado']}"
        )
        self.actualizar_vista_general(tree)
        return
    messagebox.showwarning("Aviso", "Selecciona un grupo válido.")

  def eliminar_grupo(self, codigo, tree):
    self.lista_grupos = [
        g for g in self.lista_grupos if g["codigo"] != codigo
    ]
    if codigo in self.multilista_relacional:
      del self.multilista_relacional[codigo]
    if codigo in self.hipercubo_multidimensional:
      del self.hipercubo_multidimensional[codigo]
    self.pila_historial.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] Grupo Eliminado {codigo}"
    )
    self.guardar_persistencia()
    messagebox.showinfo(
        "Eliminación", "Grupo eliminado de todas las estructuras."
    )
    self.actualizar_vista_general(tree)

  # --- VISTAS ---
  def actualizar_vista_general(self, tree):
    for row in tree.get_children():
      tree.delete(row)
    tree["columns"] = ("Col1", "Col2", "Col3", "Col4", "Col5")
    tree.heading("Col1", text="Código")
    tree.heading("Col2", text="Nombre del Grupo")
    tree.heading("Col3", text="Integrantes")
    tree.heading("Col4", text="Productos")
    tree.heading("Col5", text="Estado")

    for g in self.lista_grupos:
      cod = g["codigo"]
      sub = self.multilista_relacional.get(cod, {})
      ints = len(sub.get("integrantes", []))
      prods = len(sub.get("productos", []))
      tree.insert("", tk.END, values=(cod, g["nombre"], ints, prods, g["estado"]))

  def vista_por_grupo(self, tree):
    if not self.lista_grupos:
      messagebox.showwarning("Aviso", "No hay datos cargados.")
      return
    for row in tree.get_children():
      tree.delete(row)
    tree["columns"] = ("Col1", "Col2", "Col3")
    tree.heading("Col1", text="Código Grupo")
    tree.heading("Col2", text="Nombre del Grupo")
    tree.heading("Col3", text="Resumen Multilista")

    for g in self.lista_grupos:
      sub = self.multilista_relacional.get(g["codigo"], {})
      tree.insert(
          "",
          tk.END,
          values=(
              g["codigo"],
              g["nombre"],
              f"{len(sub.get('integrantes', []))} Inv. |"
              f" {len(sub.get('productos', []))} Prods.",
          ),
      )

  def vista_por_investigador(self, tree):
    if not self.lista_grupos:
      messagebox.showwarning("Aviso", "No hay datos cargados.")
      return
    for row in tree.get_children():
      tree.delete(row)
    tree["columns"] = ("Col1", "Col2", "Col3", "Col4")
    tree.heading("Col1", text="Cédula")
    tree.heading("Col2", text="Nombre Investigador")
    tree.heading("Col3", text="Rol")
    tree.heading("Col4", text="Grupo Asociado")

    for g in self.lista_grupos:
      sub = self.multilista_relacional.get(g["codigo"], {})
      for i in sub.get("integrantes", []):
        tree.insert(
            "",
            tk.END,
            values=(i["cedula"], i["nombre"], i["rol"], g["nombre"]),
        )

  def vista_por_productos(self, tree):
    if not self.lista_grupos:
      messagebox.showwarning("Aviso", "No hay datos cargados.")
      return
    for row in tree.get_children():
      tree.delete(row)
    tree["columns"] = ("Col1", "Col2", "Col3", "Col4")
    tree.heading("Col1", text="Nombre del Producto")
    tree.heading("Col2", text="Categoría")
    tree.heading("Col3", text="Año")
    tree.heading("Col4", text="Grupo Asociado")

    for g in self.lista_grupos:
      sub = self.multilista_relacional.get(g["codigo"], {})
      for p in sub.get("productos", []):
        tree.insert(
            "",
            tk.END,
            values=(p["nombre"], p["categoria"], p["anio"], g["nombre"]),
        )

  def filtrar_por_ventana_tiempo(self, anos_atras, tree):
    if not self.lista_grupos:
      messagebox.showwarning("Aviso", "No hay datos para filtrar.")
      return
    for row in tree.get_children():
      tree.delete(row)
    tree["columns"] = ("Col1", "Col2", "Col3", "Col4")
    tree.heading("Col1", text="Producto")
    tree.heading("Col2", text="Categoría")
    tree.heading("Col3", text="Año")
    tree.heading("Col4", text="Grupo")

    anio_actual = datetime.now().year
    limite = anio_actual - anos_atras if anos_atras > 0 else 0

    for g in self.lista_grupos:
      sub = self.multilista_relacional.get(g["codigo"], {})
      for p in sub.get("productos", []):
        if anos_atras == 0 or p["anio"] >= limite:
          tree.insert(
              "",
              tk.END,
              values=(p["nombre"], p["categoria"], p["anio"], g["nombre"]),
          )

  '''' def vista_hipercubo_multidimensional(self, tree):
    if not self.hipercubo_multidimensional:
      messagebox.showwarning("Aviso", "No hay datos en el hipercubo.")
      return
    for row in tree.get_children():
      tree.delete(row)
    tree["columns"] = ("Col1", "Col2", "Col3", "Col4")
    tree.heading("Col1", text="Código Grupo (Eje 1)")
    tree.heading("Col2", text="Año (Eje 2)")
    tree.heading("Col3", text="Categoría (Eje 3)")
    tree.heading("Col4", text="Métrica (Cantidad)")

    for cod_grupo, cubo_datos in self.hipercubo_multidimensional.items():
      for anio, categorias in cubo_datos.items():
        for categoria, cantidad in categorias.items():
          tree.insert(
              "",
              tk.END,
              values=(cod_grupo, anio, categoria, f"{cantidad} Producto(s)"),
          )
          '''

  def guardar_persistencia(self):
    datos = {
        "lista_grupos": self.lista_grupos,
        "multilista_relacional": self.multilista_relacional,
        "hipercubo_multidimensional": self.hipercubo_multidimensional,
    }
    with open(self.archivo_persistencia, "w", encoding="utf-8") as f:
      json.dump(datos, f, ensure_ascii=False, indent=4)

  def cargar_persistencia(self):
    if os.path.exists(self.archivo_persistencia):
      try:
        with open(self.archivo_persistencia, "r", encoding="utf-8") as f:
          datos = json.load(f)
          self.lista_grupos = datos.get("lista_grupos", [])
          self.multilista_relacional = datos.get("multilista_relacional", {})
          self.hipercubo_multidimensional = datos.get(
              "hipercubo_multidimensional", {}
          )
      except Exception:
        pass


gestor_datos = GestorDatosInvestigacion()


# ==========================================================
# 2. DASHBOARD ESTADÍSTICO
# ==========================================================
def abrir_dashboard():
  if not gestor_datos.lista_grupos:
    messagebox.showwarning("Aviso", "No hay datos para generar.")
    return

  g = gestor_datos.lista_grupos[-1]
  multidatos = gestor_datos.multilista_relacional.get(g["codigo"], {})

  ventana_dash = tk.Toplevel()
  ventana_dash.title(f"Dashboard Analítico - {g['nombre']}")
  ventana_dash.geometry("1100x750")
  ventana_dash.config(bg="#E0F2FE")

  header_dash = tk.Frame(ventana_dash, bg="#0284C7", pady=12)
  header_dash.pack(fill=tk.X)
  tk.Label(
      header_dash,
      text=f"📊 Panel Estadístico Integral: {g['nombre']} ({g['codigo']})",
      font=("Arial", 11, "bold"),
      bg="#0284C7",
      fg="white",
  ).pack()

  fig, axs = plt.subplots(2, 2, figsize=(10.5, 7), dpi=100)
  fig.patch.set_facecolor("#E0F2FE")

  proys = multidatos.get("proyectos_por_anio", {2023: 1, 2024: 2})
  axs[0, 0].bar(
      [str(k) for k in proys.keys()],
      list(proys.values()),
      color="#0EA5E9",
      width=0.55,
  )
  axs[0, 0].set_title(
      "Participación en Proyectos por Año",
      fontsize=10,
      fontweight="bold",
      color="#0369A1",
  )
  axs[0, 0].set_facecolor("#FFFFFF")
  axs[0, 0].grid(axis="y", linestyle="--", alpha=0.5)

  def crear_pastel(ax, diccionario, titulo, colores):
    labels = list(diccionario.keys())
    valores = list(diccionario.values())
    wedges, _, _ = ax.pie(
        valores,
        autopct="%1.1f%%",
        startangle=140,
        colors=colores,
        textprops={"fontsize": 8, "weight": "bold", "color": "white"},
        pctdistance=0.65,
    )
    ax.set_title(titulo, fontsize=10, fontweight="bold", color="#22A4E9")
    ax.set_facecolor("#FFFFFF")
    ax.legend(
        wedges,
        labels,
        title="Categorías",
        loc="center left",
        bbox_to_anchor=(0.95, 0.5),
        fontsize=8,
        title_fontsize=8,
        frameon=True,
    )

  crear_pastel(
      axs[0, 1],
      multidatos.get("tipologia", {"A": 50, "B": 50}),
      "Tipología de Productos",
      ["#EF4444", "#F59E0B", "#3B82F6"],
  )
  crear_pastel(
      axs[1, 0],
      multidatos.get("sublineas", {"L1": 50, "L2": 50}),
      "Proyectos por Sublínea",
      ["#0284C7", "#10B981", "#8B5CF6"],
  )
  crear_pastel(
      axs[1, 1],
      multidatos.get("roles", {"R1": 50, "R2": 50}),
      "Distribución por Rol",
      ["#6366F1", "#EC4899", "#14B8A6"],
  )

  fig.tight_layout(pad=2.0)
  canvas = FigureCanvasTkAgg(fig, master=ventana_dash)
  canvas.draw()
  canvas.get_tk_widget().pack(pady=10, fill=tk.BOTH, expand=True)


# ==========================================================
# 3. INTERFAZ GRÁFICA PRINCIPAL
# ==========================================================
def iniciar_interfaz():
  root = tk.Tk()
  root.title("Programa Estadístico de Análisis de Investigación | PEA-i")
  root.geometry("1250x780")
  root.config(bg="#E0F2FE")

  header_frame = tk.Frame(root, bg="#0284C7", pady=12)
  header_frame.pack(fill=tk.X, side=tk.TOP)
  tk.Label(
      header_frame,
      text=(
          "PEA-i: Sistema con Tarjeta Informativa Incrustada, Logos y Vistas"
      ),
      font=("Arial", 12, "bold"),
      bg="#0284C7",
      fg="white",
  ).pack()

  main_container = tk.Frame(root, bg="#E0F2FE")
  main_container.pack(fill=tk.BOTH, expand=True)

  # Menú Lateral
  sidebar = tk.Frame(main_container, bg="#BAE6FD", width=300)
  sidebar.pack(side=tk.LEFT, fill=tk.Y)
  sidebar.pack_propagate(False)

  tk.Label(
      sidebar,
      text="MENÚ DE OPERACIONES",
      font=("Arial", 10, "bold"),
      bg="#BAE6FD",
      fg="#0369A1",
      pady=10,
  ).pack(anchor="w", padx=15)

  def boton_lat(texto, comando):
    return tk.Button(
        sidebar,
        text=texto,
        font=("Arial", 9),
        bg="#0284C7",
        fg="white",
        relief=tk.FLAT,
        anchor="w",
        padx=10,
        pady=5,
        command=comando,
    )

  boton_lat(
      "📥 Encolar URL (Cola FIFO)",
      lambda: gestor_datos.encolar_url(entry_url.get()),
  ).pack(fill=tk.X, padx=10, pady=2)
  boton_lat(
      "⚡ Procesar Siguiente Cola",
      lambda: gestor_datos.procesar_siguiente_cola(tree, actualizar_tarjeta),
  ).pack(fill=tk.X, padx=10, pady=2)
  boton_lat(
      "📜 Ver Historial (Pila LIFO)",
      lambda: gestor_datos.ver_pila_historial(),
  ).pack(fill=tk.X, padx=10, pady=2)

  tk.Label(
      sidebar,
      text="VISTAS Y FILTROS:",
      font=("Arial", 9, "bold"),
      bg="#BAE6FD",
      fg="#0369A1",
      pady=5,
  ).pack(anchor="w", padx=15)

  boton_lat(
      "🔄 Vista General de Grupos",
      lambda: gestor_datos.actualizar_vista_general(tree),
  ).pack(fill=tk.X, padx=10, pady=2)
  boton_lat(
      "🏢 Vista por Grupo", lambda: gestor_datos.vista_por_grupo(tree)
  ).pack(fill=tk.X, padx=10, pady=2)
  boton_lat(
      "👥 Vista por Investigador",
      lambda: gestor_datos.vista_por_investigador(tree),
  ).pack(fill=tk.X, padx=10, pady=2)
  boton_lat(
      "📚 Vista por Productos", lambda: gestor_datos.vista_por_productos(tree)
  ).pack(fill=tk.X, padx=10, pady=2)
  boton_lat(
      "📅 Filtrar: Últimos 2 Años",
      lambda: gestor_datos.filtrar_por_ventana_tiempo(2, tree),
  ).pack(fill=tk.X, padx=10, pady=2)
  boton_lat(
      "📅 Filtrar: Últimos 5 Años",
      lambda: gestor_datos.filtrar_por_ventana_tiempo(5, tree),
  ).pack(fill=tk.X, padx=10, pady=2)
  boton_lat(
      "📅 Filtrar: Histórico Completo",
      lambda: gestor_datos.filtrar_por_ventana_tiempo(0, tree),
  ).pack(fill=tk.X, padx=10, pady=2)
  boton_lat(
      "🧊 Consultar Hipercubo OLAP",
      lambda: gestor_datos.vista_hipercubo_multidimensional(tree),
  ).pack(fill=tk.X, padx=10, pady=2)

  # Contenedor Principal
  content_frame = tk.Frame(main_container, bg="#E0F2FE", padx=15, pady=10)
  content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

  tk.Label(
      content_frame,
      text="URL del Grupo (GrupLAC / Institucional):",
      font=("Arial", 10, "bold"),
      bg="#E0F2FE",
      fg="#0369A1",
  ).pack(anchor="w")

  url_frame = tk.Frame(content_frame, bg="#E0F2FE")
  url_frame.pack(fill=tk.X, pady=5)

  entry_url = tk.Entry(
      url_frame, font=("Arial", 10), width=50, relief=tk.SOLID, borderwidth=1
  )
  entry_url.pack(side=tk.LEFT, padx=(0, 10), ipady=4)

  tk.Button(
      url_frame,
      text="Crear / Importar Grupo",
      bg="#0EA5E9",
      fg="white",
      font=("Arial", 9, "bold"),
      relief=tk.FLAT,
      padx=10,
      command=lambda: gestor_datos.crear_o_importar_grupo(
          entry_url.get(), tree, actualizar_tarjeta
      ),
  ).pack(side=tk.LEFT)

  # ==========================================================
  # TARJETA INCRUSTADA EN EL ESPACIO EN BLANCO
  # ==========================================================
  card_frame = tk.LabelFrame(
      content_frame,
      text=" 📌 Tarjeta Informativa del Grupo Seleccionado ",
      font=("Arial", 9, "bold"),
      bg="#F0F9FF",
      fg="#0284C7",
      padx=12,
      pady=8,
  )
  card_frame.pack(fill=tk.X, pady=8)

  lbl_logo = tk.Label(
      card_frame,
      bg="#E0F2FE",
      relief=tk.SOLID,
      borderwidth=1,
      width=70,
      height=70,
  )
  lbl_logo.grid(row=0, column=0, rowspan=2, padx=(0, 15), sticky="n")

  lbl_nombre_tarjeta = tk.Label(
      card_frame,
      text="Nombre: [Ninguno seleccionado]",
      font=("Arial", 10, "bold"),
      bg="#F0F9FF",
      fg="#0369A1",
      anchor="w",
  )
  lbl_nombre_tarjeta.grid(row=0, column=1, sticky="w", pady=(0, 2))

  lbl_info_tarjeta = tk.Label(
      card_frame,
      text=(
          "Código: N/A | Estado: N/A\nResumen Institucional: Carga o selecciona"
          " un grupo para ver su información aquí."
      ),
      font=("Arial", 9),
      bg="#F0F9FF",
      fg="#334155",
      justify="left",
      wraplength=700,
  )
  lbl_info_tarjeta.grid(row=1, column=1, sticky="w")

  def actualizar_tarjeta(grupo):
    """Actualiza los widgets de la tarjeta incrustada con los datos del grupo"""
    lbl_nombre_tarjeta.config(
        text=f"{grupo['nombre']} ({grupo['acronimo']})"
    )
    lbl_info_tarjeta.config(
        text=(
            f"Código: {grupo['codigo']} | Estado: {grupo['estado']}\nResumen:"
            f" {grupo['descripcion']}"
        )
    )

    # Cargar imagen de logo si existe
    if grupo["logo_url"]:
      try:
        res = requests.get(grupo["logo_url"], timeout=3)
        if res.status_code == 200:
          pil_img = Image.open(BytesIO(res.content))
          pil_img = pil_img.resize((65, 65), Image.Resampling.LANCZOS)
          img_tk = ImageTk.PhotoImage(pil_img)
          lbl_logo.config(image=img_tk, text="")
          lbl_logo.image = img_tk  # Referencia para evitar recolección
          return
      except Exception:
        pass
    lbl_logo.config(image="", text="Sin\nLogo", font=("Arial", 8), fg="#0369A1")

  # ==========================================================
  # CONSOLA DE REGISTROS (TABLA)
  # ==========================================================
  tk.Label(
      content_frame,
      text="Consola de Registros:",
      font=("Arial", 10, "bold"),
      bg="#E0F2FE",
      fg="#0369A1",
  ).pack(anchor="w", pady=(5, 2))

  table_frame = tk.Frame(content_frame, bg="white")
  table_frame.pack(fill=tk.BOTH, expand=True, pady=2)

  tree_scroll = ttk.Scrollbar(table_frame)
  tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

  tree = ttk.Treeview(
      table_frame, yscrollcommand=tree_scroll.set, selectmode="browse", height=8
  )
  tree.pack(fill=tk.BOTH, expand=True)
  tree_scroll.config(command=tree.yview)

  style = ttk.Style()
  style.theme_use("clam")
  style.configure(
      "Treeview.Heading",
      font=("Arial", 9, "bold"),
      background="#BAE6FD",
      foreground="#0369A1",
  )

  # Evento al seleccionar un elemento de la tabla para actualizar la tarjeta automáticamente
  def al_seleccionar_item(event):
    selected = tree.selection()
    if not selected:
      return
    item = tree.item(selected)
    valores = item["values"]
    if not valores:
      return
    codigo_sel = str(valores[0])
    for g in gestor_datos.lista_grupos:
      if g["codigo"] == codigo_sel:
        actualizar_tarjeta(g)
        break

  tree.bind("<<TreeviewSelect>>", al_seleccionar_item)

  # Botones CRUD Inferiores
  crud_frame = tk.Frame(content_frame, bg="#E0F2FE")
  crud_frame.pack(fill=tk.X, pady=8)

  def obtener_codigo_seleccionado():
    selected = tree.selection()
    if not selected:
      return None
    item = tree.item(selected)
    valores = item["values"]
    if not valores:
      return None
    return str(valores[0])

  tk.Button(
      crud_frame,
      text="✏️ Modificar Nombre",
      bg="#F59E0B",
      fg="white",
      font=("Arial", 9, "bold"),
      relief=tk.FLAT,
      command=lambda: [
          cod := obtener_codigo_seleccionado(),
          cod and gestor_datos.modificar_grupo(
              cod, "Grupo Actualizado Académicamente", tree
          ),
      ],
  ).pack(side=tk.LEFT, padx=5)

  tk.Button(
      crud_frame,
      text="🔄 Activar / Desactivar",
      bg="#64748B",
      fg="white",
      font=("Arial", 9, "bold"),
      relief=tk.FLAT,
      command=lambda: [
          cod := obtener_codigo_seleccionado(),
          cod and gestor_datos.desactivar_grupo(cod, tree),
      ],
  ).pack(side=tk.LEFT, padx=5)

  tk.Button(
      crud_frame,
      text="🗑️ Eliminar Registro",
      bg="#EF4444",
      fg="white",
      font=("Arial", 9, "bold"),
      relief=tk.FLAT,
      command=lambda: [
          cod := obtener_codigo_seleccionado(),
          cod and gestor_datos.eliminar_grupo(cod, tree),
      ],
  ).pack(side=tk.LEFT, padx=5)

  tk.Button(
      content_frame,
      text="📈 Abrir Dashboard Estadístico Integral",
      font=("Arial", 10, "bold"),
      bg="#0284C7",
      fg="white",
      relief=tk.FLAT,
      pady=6,
      command=abrir_dashboard,
  ).pack(fill=tk.X, pady=(2, 0))

  gestor_datos.actualizar_vista_general(tree)
  if gestor_datos.lista_grupos:
    actualizar_tarjeta(gestor_datos.lista_grupos[-1])

  root.mainloop()


if __name__ == "__main__":
  iniciar_interfaz()