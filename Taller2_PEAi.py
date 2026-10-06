# -*- coding: utf-8 -*-
"""
PEA-i - Programa Estadístico de Análisis de Investigación
Universidad Popular del Cesar - Ingeniería de Sistemas - Estructura de Datos (Taller 2)

ARCHIVO ÚNICO (programación estructurada, sin POO). Se ejecuta con:   python este_archivo.py
Librerías:  pip install requests beautifulsoup4 pypdf matplotlib

Contenido, en orden:
  1. NÚCLEO DE ESTRUCTURAS  : lista, multilista, pila, cola, hipercubo, CRUD, deshacer, JSON.
  2. IMPORTACIÓN            : listados y detalles de SCIENTI (URL/HTML), PDF y CSV.
  3. INTERFAZ (Tkinter)     : CRUD, filtros por año, dashboard, cola/pila e importación.

Modelo de datos (variables de entrada/salida)
  Grupo        : codigo, nombre, lider, categoria, url, activo | integrantes, productos
  Investigador : id, nombre, cod_rh, email, formacion, categoria, activo | productos
  Integrante   : id_investigador, vinculacion, horas, periodo, activo
  Producto     : id, titulo, tipo, categoria, anio, validado, grupo, investigadores, activo
"""
import csv
import io
import json
import os
import random
import re
import time
import tkinter as tk
import unicodedata
import urllib.parse
import zlib
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk



# ==============================================================
# PARTE 1 - NÚCLEO DE ESTRUCTURAS DE DATOS
# ==============================================================
DIMENSIONES = ("grupo", "investigador", "tipo", "categoria", "anio")

CAMPOS_GRUPO = ("nombre", "lider", "categoria", "url")
CAMPOS_INVESTIGADOR = ("nombre", "cod_rh", "email", "formacion", "categoria")
CAMPOS_INTEGRANTE = ("vinculacion", "horas", "periodo")
CAMPOS_PRODUCTO = ("titulo", "tipo", "categoria", "anio", "validado",
                   "grupo", "investigadores")


# ==========================================================
# 1. LISTA ENLAZADA SIMPLE (CRUD genérico)
# ==========================================================
def lista_crear():
    return {"cabeza": None, "cola": None, "tam": 0}


def lista_insertar_inicio(lista, dato):
    nodo = {"dato": dato, "sig": lista["cabeza"]}
    lista["cabeza"] = nodo
    if lista["cola"] is None:
        lista["cola"] = nodo
    lista["tam"] += 1
    return nodo


def lista_insertar_final(lista, dato):
    nodo = {"dato": dato, "sig": None}
    if lista["cabeza"] is None:
        lista["cabeza"] = nodo
    else:
        lista["cola"]["sig"] = nodo
    lista["cola"] = nodo
    lista["tam"] += 1
    return nodo


def lista_buscar(lista, campo, valor):
    """Devuelve el registro cuyo campo == valor, o None."""
    nodo = lista["cabeza"]
    while nodo is not None:
        if nodo["dato"].get(campo) == valor:
            return nodo["dato"]
        nodo = nodo["sig"]
    return None


def lista_modificar(lista, campo, valor, cambios):
    """Modifica campos existentes. Devuelve los valores anteriores o None si no existe."""
    dato = lista_buscar(lista, campo, valor)
    if dato is None:
        return None
    antes = {}
    for k, v in cambios.items():
        if k in dato:
            antes[k] = dato[k]
            dato[k] = v
    return antes


def lista_desactivar(lista, campo, valor, activo=False):
    """Eliminación lógica. Devuelve el estado anterior o None si no existe."""
    dato = lista_buscar(lista, campo, valor)
    if dato is None:
        return None
    antes = dato["activo"]
    dato["activo"] = activo
    return antes


def lista_eliminar(lista, campo, valor):
    """Eliminación física. Devuelve el registro eliminado o None."""
    anterior = None
    actual = lista["cabeza"]
    while actual is not None:
        if actual["dato"].get(campo) == valor:
            if anterior is None:
                lista["cabeza"] = actual["sig"]
            else:
                anterior["sig"] = actual["sig"]
            if actual is lista["cola"]:
                lista["cola"] = anterior
            lista["tam"] -= 1
            return actual["dato"]
        anterior = actual
        actual = actual["sig"]
    return None


def lista_recorrer(lista, solo_activos=False):
    """Recorre la lista y devuelve los registros en un arreglo de Python."""
    salida = []
    nodo = lista["cabeza"]
    while nodo is not None:
        dato = nodo["dato"]
        if not solo_activos or dato.get("activo", True):
            salida.append(dato)
        nodo = nodo["sig"]
    return salida


# ==========================================================
# 2. PILA (LIFO) - usada como historial para deshacer
# ==========================================================
def pila_crear():
    return {"tope": None, "tam": 0}


def pila_vacia(pila):
    return pila["tope"] is None


def pila_apilar(pila, dato):
    pila["tope"] = {"dato": dato, "sig": pila["tope"]}
    pila["tam"] += 1


def pila_desapilar(pila):
    if pila_vacia(pila):
        return None
    nodo = pila["tope"]
    pila["tope"] = nodo["sig"]
    pila["tam"] -= 1
    return nodo["dato"]


def pila_tope(pila):
    return None if pila_vacia(pila) else pila["tope"]["dato"]


def pila_modificar_tope(pila, cambios):
    if pila_vacia(pila):
        return False
    pila["tope"]["dato"].update(cambios)
    return True


def pila_vaciar(pila):
    pila["tope"] = None
    pila["tam"] = 0


# ==========================================================
# 3. COLA (FIFO) - usada para importaciones pendientes
# ==========================================================
def cola_crear():
    return {"frente": None, "final": None, "tam": 0}


def cola_vacia(cola):
    return cola["frente"] is None


def cola_encolar(cola, dato):
    nodo = {"dato": dato, "sig": None}
    if cola_vacia(cola):
        cola["frente"] = nodo
    else:
        cola["final"]["sig"] = nodo
    cola["final"] = nodo
    cola["tam"] += 1


def cola_desencolar(cola):
    if cola_vacia(cola):
        return None
    nodo = cola["frente"]
    cola["frente"] = nodo["sig"]
    if cola["frente"] is None:
        cola["final"] = None
    cola["tam"] -= 1
    return nodo["dato"]


def cola_frente(cola):
    return None if cola_vacia(cola) else cola["frente"]["dato"]


def cola_modificar_frente(cola, cambios):
    if cola_vacia(cola):
        return False
    cola["frente"]["dato"].update(cambios)
    return True


def cola_recorrer(cola):
    salida = []
    nodo = cola["frente"]
    while nodo is not None:
        salida.append(nodo["dato"])
        nodo = nodo["sig"]
    return salida


# ==========================================================
# 4. HIPERCUBO DE INFORMACIÓN
#    Coordenadas de cada celda: (grupo, investigador, tipo, categoria, anio)
#    Cada celda contiene una LISTA de productos.
#    Un producto con varios autores aparece en una celda por autor
#    (las consultas cuentan productos distintos, nunca duplicados).
# ==========================================================
def cubo_crear():
    return {"dims": DIMENSIONES, "celdas": {}}


def _coordenadas(prod):
    autores = prod["investigadores"] if prod["investigadores"] else ["N/D"]
    coords = []
    for inv in autores:
        coords.append((prod["grupo"], inv, prod["tipo"], prod["categoria"], prod["anio"]))
    return coords


def cubo_poner(cubo, prod):
    for c in _coordenadas(prod):
        if c not in cubo["celdas"]:
            cubo["celdas"][c] = lista_crear()
        lista_insertar_final(cubo["celdas"][c], prod)


def cubo_quitar(cubo, prod):
    """Debe llamarse ANTES de cambiar los campos del producto."""
    for c in _coordenadas(prod):
        celda = cubo["celdas"].get(c)
        if celda is not None:
            lista_eliminar(celda, "id", prod["id"])
            if celda["tam"] == 0:
                del cubo["celdas"][c]


def _coordenada_pasa(coord, filtros):
    grupo, inv, tipo, cat, anio = coord
    if filtros.get("grupo") is not None and grupo != filtros["grupo"]:
        return False
    if filtros.get("investigador") is not None and inv != filtros["investigador"]:
        return False
    if filtros.get("tipo") is not None and tipo != filtros["tipo"]:
        return False
    if filtros.get("categoria") is not None and cat != filtros["categoria"]:
        return False
    if filtros.get("anio") is not None and anio != filtros["anio"]:
        return False
    if filtros.get("anio_desde") is not None and anio < filtros["anio_desde"]:
        return False
    if filtros.get("anio_hasta") is not None and anio > filtros["anio_hasta"]:
        return False
    return True


def _producto_pasa(prod, filtros):
    if filtros.get("solo_activos", True) and not prod["activo"]:
        return False
    if filtros.get("solo_validados", False) and not prod["validado"]:
        return False
    return True


def cubo_consultar(cubo, **filtros):
    """Rebanada/dado del cubo. Filtros: grupo, investigador, tipo, categoria,
    anio, anio_desde, anio_hasta, solo_validados, solo_activos (por defecto True).
    Devuelve productos distintos."""
    vistos = set()
    salida = []
    for coord, celda in cubo["celdas"].items():
        if not _coordenada_pasa(coord, filtros):
            continue
        nodo = celda["cabeza"]
        while nodo is not None:
            p = nodo["dato"]
            if p["id"] not in vistos and _producto_pasa(p, filtros):
                vistos.add(p["id"])
                salida.append(p)
            nodo = nodo["sig"]
    return salida


def cubo_resumen(cubo, dimension, **filtros):
    """Agregación (roll-up) por una dimensión: {valor: cantidad de productos distintos}."""
    pos = DIMENSIONES.index(dimension)
    conjuntos = {}
    for coord, celda in cubo["celdas"].items():
        if not _coordenada_pasa(coord, filtros):
            continue
        nodo = celda["cabeza"]
        while nodo is not None:
            p = nodo["dato"]
            if _producto_pasa(p, filtros):
                if coord[pos] not in conjuntos:
                    conjuntos[coord[pos]] = set()
                conjuntos[coord[pos]].add(p["id"])
            nodo = nodo["sig"]
    resumen = {}
    for valor, ids in conjuntos.items():
        resumen[valor] = len(ids)
    return resumen


def ventana_anios(ultimos_n, anio_actual):
    """'Últimos N años' incluye el año actual. N = 0 significa histórico completo."""
    if ultimos_n <= 0:
        return {}
    return {"anio_desde": anio_actual - ultimos_n + 1, "anio_hasta": anio_actual}


# ==========================================================
# 5. REGISTROS (equivalentes a struct)
# ==========================================================
def nuevo_grupo(codigo, nombre, lider="N/D", categoria="Sin categoría", url=""):
    return {"codigo": codigo, "nombre": nombre, "lider": lider,
            "categoria": categoria, "url": url, "activo": True,
            "integrantes": lista_crear(), "productos": lista_crear()}


def nuevo_investigador(id_inv, nombre, cod_rh="", email="", formacion="",
                       categoria="Sin categoría"):
    return {"id": id_inv, "nombre": nombre, "cod_rh": cod_rh, "email": email,
            "formacion": formacion, "categoria": categoria, "activo": True,
            "productos": lista_crear()}


def nuevo_integrante(id_investigador, vinculacion="Integrante", horas="N/D",
                     periodo="Actual"):
    return {"id_investigador": id_investigador, "vinculacion": vinculacion,
            "horas": horas, "periodo": periodo, "activo": True}


def nuevo_producto(id_prod, titulo, tipo, anio, categoria, validado, grupo,
                   investigadores):
    return {"id": id_prod, "titulo": titulo, "tipo": tipo, "categoria": categoria,
            "anio": anio, "validado": validado, "grupo": grupo,
            "investigadores": list(investigadores), "activo": True}


# --- conversión registro <-> diccionario plano (persistencia y deshacer) ---
def grupo_a_dict(g):
    d = {"codigo": g["codigo"], "activo": g["activo"]}
    for c in CAMPOS_GRUPO:
        d[c] = g[c]
    d["integrantes"] = [dict(i) for i in lista_recorrer(g["integrantes"])]
    return d


def grupo_desde_dict(d):
    g = nuevo_grupo(d["codigo"], d["nombre"], d.get("lider", "N/D"),
                    d.get("categoria", "Sin categoría"), d.get("url", ""))
    g["activo"] = d.get("activo", True)
    for i in d.get("integrantes", []):
        lista_insertar_final(g["integrantes"], dict(i))
    return g


def investigador_a_dict(inv):
    d = {"id": inv["id"], "activo": inv["activo"]}
    for c in CAMPOS_INVESTIGADOR:
        d[c] = inv[c]
    return d


def investigador_desde_dict(d):
    inv = nuevo_investigador(d["id"], d["nombre"], d.get("cod_rh", ""),
                             d.get("email", ""), d.get("formacion", ""),
                             d.get("categoria", "Sin categoría"))
    inv["activo"] = d.get("activo", True)
    return inv


def producto_a_dict(p):
    d = dict(p)
    d["investigadores"] = list(p["investigadores"])
    return d


def producto_desde_dict(d):
    p = nuevo_producto(d["id"], d["titulo"], d["tipo"], d["anio"],
                       d.get("categoria", "Sin categoría"), d.get("validado", False),
                       d["grupo"], d.get("investigadores", []))
    p["activo"] = d.get("activo", True)
    return p


# ==========================================================
# 6. SISTEMA (agrupa todas las estructuras) y utilidades internas
# ==========================================================
def sistema_crear():
    return {"grupos": lista_crear(),
            "investigadores": lista_crear(),
            "productos": lista_crear(),          # lista maestra (multilista)
            "cubo": cubo_crear(),
            "historial": pila_crear(),
            "importaciones": cola_crear(),
            "contador_prod": 0,
            "contador_inv": 0}


def _filtrar(cambios, permitidos):
    salida = {}
    for k, v in cambios.items():
        if k in permitidos:
            salida[k] = v
    return salida


def _registrar(sis, operacion):
    pila_apilar(sis["historial"], operacion)


def _modificar_simple(sis, lista, campo, ent, clave, cambios, permitidos,
                      registrar, mensaje):
    cambios = _filtrar(cambios, permitidos)
    if not cambios:
        return None, "No hay campos válidos para modificar"
    antes = lista_modificar(lista, campo, clave, cambios)
    if antes is None:
        return None, mensaje
    if registrar:
        _registrar(sis, {"op": "modificar", "ent": ent, "clave": clave, "antes": antes})
    return lista_buscar(lista, campo, clave), None


def _desactivar_simple(sis, lista, campo, ent, clave, activo, registrar, mensaje):
    antes = lista_desactivar(lista, campo, clave, activo)
    if antes is None:
        return None, mensaje
    if registrar:
        _registrar(sis, {"op": "desactivar", "ent": ent, "clave": clave, "antes": antes})
    return lista_buscar(lista, campo, clave), None


# ==========================================================
# 7. CRUD DE GRUPOS
# ==========================================================
def grupo_crear(sis, codigo, nombre, lider="N/D", categoria="Sin categoría",
                url="", registrar=True):
    if lista_buscar(sis["grupos"], "codigo", codigo) is not None:
        return None, "Ya existe un grupo con ese código"
    g = nuevo_grupo(codigo, nombre, lider, categoria, url)
    lista_insertar_final(sis["grupos"], g)
    if registrar:
        _registrar(sis, {"op": "crear", "ent": "grupo", "clave": codigo})
    return g, None


def grupo_consultar(sis, codigo):
    return lista_buscar(sis["grupos"], "codigo", codigo)


def grupo_modificar(sis, codigo, cambios, registrar=True):
    return _modificar_simple(sis, sis["grupos"], "codigo", "grupo", codigo, cambios,
                             CAMPOS_GRUPO, registrar, "El grupo no existe")


def grupo_desactivar(sis, codigo, activo=False, registrar=True):
    return _desactivar_simple(sis, sis["grupos"], "codigo", "grupo", codigo, activo,
                              registrar, "El grupo no existe")


def grupo_eliminar(sis, codigo, registrar=True):
    g = lista_buscar(sis["grupos"], "codigo", codigo)
    if g is None:
        return None, "El grupo no existe"
    if g["productos"]["tam"] > 0:
        return None, "El grupo tiene productos: elimínelos o desactive el grupo"
    snapshot = grupo_a_dict(g)
    lista_eliminar(sis["grupos"], "codigo", codigo)
    if registrar:
        _registrar(sis, {"op": "eliminar", "ent": "grupo", "clave": codigo,
                         "snapshot": snapshot})
    return g, None


# ==========================================================
# 8. CRUD DE INVESTIGADORES
# ==========================================================
def investigador_crear(sis, nombre, cod_rh="", email="", formacion="",
                       categoria="Sin categoría", registrar=True):
    sis["contador_inv"] += 1
    id_inv = "INV-%04d" % sis["contador_inv"]
    inv = nuevo_investigador(id_inv, nombre, cod_rh, email, formacion, categoria)
    lista_insertar_final(sis["investigadores"], inv)
    if registrar:
        _registrar(sis, {"op": "crear", "ent": "investigador", "clave": id_inv})
    return inv, None


def investigador_consultar(sis, id_inv):
    return lista_buscar(sis["investigadores"], "id", id_inv)


def investigador_buscar_nombre(sis, nombre):
    return lista_buscar(sis["investigadores"], "nombre", nombre)


def investigador_modificar(sis, id_inv, cambios, registrar=True):
    return _modificar_simple(sis, sis["investigadores"], "id", "investigador", id_inv,
                             cambios, CAMPOS_INVESTIGADOR, registrar,
                             "El investigador no existe")


def investigador_desactivar(sis, id_inv, activo=False, registrar=True):
    return _desactivar_simple(sis, sis["investigadores"], "id", "investigador", id_inv,
                              activo, registrar, "El investigador no existe")


def _es_integrante(sis, id_inv):
    for g in lista_recorrer(sis["grupos"]):
        if lista_buscar(g["integrantes"], "id_investigador", id_inv) is not None:
            return True
    return False


def investigador_eliminar(sis, id_inv, registrar=True):
    inv = lista_buscar(sis["investigadores"], "id", id_inv)
    if inv is None:
        return None, "El investigador no existe"
    if inv["productos"]["tam"] > 0:
        return None, "El investigador tiene productos: desactívelo o elimine sus productos"
    if _es_integrante(sis, id_inv):
        return None, "El investigador es integrante de un grupo: retírelo primero"
    snapshot = investigador_a_dict(inv)
    lista_eliminar(sis["investigadores"], "id", id_inv)
    if registrar:
        _registrar(sis, {"op": "eliminar", "ent": "investigador", "clave": id_inv,
                         "snapshot": snapshot})
    return inv, None


# ==========================================================
# 9. CRUD DE INTEGRANTES (sublista del grupo)
# ==========================================================
def integrante_agregar(sis, cod_grupo, id_inv, vinculacion="Integrante",
                       horas="N/D", periodo="Actual"):
    g = lista_buscar(sis["grupos"], "codigo", cod_grupo)
    if g is None:
        return None, "El grupo no existe"
    if lista_buscar(sis["investigadores"], "id", id_inv) is None:
        return None, "El investigador no existe"
    if lista_buscar(g["integrantes"], "id_investigador", id_inv) is not None:
        return None, "El investigador ya es integrante de este grupo"
    reg = nuevo_integrante(id_inv, vinculacion, horas, periodo)
    lista_insertar_final(g["integrantes"], reg)
    return reg, None


def integrante_consultar(sis, cod_grupo, id_inv):
    g = lista_buscar(sis["grupos"], "codigo", cod_grupo)
    if g is None:
        return None
    return lista_buscar(g["integrantes"], "id_investigador", id_inv)


def integrante_modificar(sis, cod_grupo, id_inv, cambios):
    g = lista_buscar(sis["grupos"], "codigo", cod_grupo)
    if g is None:
        return None, "El grupo no existe"
    cambios = _filtrar(cambios, CAMPOS_INTEGRANTE)
    antes = lista_modificar(g["integrantes"], "id_investigador", id_inv, cambios)
    if antes is None:
        return None, "El integrante no existe en el grupo"
    return lista_buscar(g["integrantes"], "id_investigador", id_inv), None


def integrante_desactivar(sis, cod_grupo, id_inv, activo=False):
    g = lista_buscar(sis["grupos"], "codigo", cod_grupo)
    if g is None:
        return None, "El grupo no existe"
    antes = lista_desactivar(g["integrantes"], "id_investigador", id_inv, activo)
    if antes is None:
        return None, "El integrante no existe en el grupo"
    return lista_buscar(g["integrantes"], "id_investigador", id_inv), None


def integrante_eliminar(sis, cod_grupo, id_inv):
    g = lista_buscar(sis["grupos"], "codigo", cod_grupo)
    if g is None:
        return None, "El grupo no existe"
    reg = lista_eliminar(g["integrantes"], "id_investigador", id_inv)
    if reg is None:
        return None, "El integrante no existe en el grupo"
    return reg, None


# ==========================================================
# 10. CRUD DE PRODUCTOS (multilista + hipercubo)
# ==========================================================
def _validar_producto(sis, cod_grupo, ids_inv, anio):
    if lista_buscar(sis["grupos"], "codigo", cod_grupo) is None:
        return "El grupo no existe"
    for i in ids_inv:
        if lista_buscar(sis["investigadores"], "id", i) is None:
            return "El investigador %s no existe" % i
    if not isinstance(anio, int) or isinstance(anio, bool):
        return "El año debe ser un número entero"
    return None


def _producto_enlazar(sis, prod):
    """Inserta el MISMO registro en la lista del grupo, la de cada autor y el cubo."""
    g = lista_buscar(sis["grupos"], "codigo", prod["grupo"])
    lista_insertar_final(g["productos"], prod)
    for id_inv in prod["investigadores"]:
        inv = lista_buscar(sis["investigadores"], "id", id_inv)
        if inv is not None:
            lista_insertar_final(inv["productos"], prod)
    cubo_poner(sis["cubo"], prod)


def _producto_desenlazar(sis, prod):
    g = lista_buscar(sis["grupos"], "codigo", prod["grupo"])
    if g is not None:
        lista_eliminar(g["productos"], "id", prod["id"])
    for id_inv in prod["investigadores"]:
        inv = lista_buscar(sis["investigadores"], "id", id_inv)
        if inv is not None:
            lista_eliminar(inv["productos"], "id", prod["id"])
    cubo_quitar(sis["cubo"], prod)


def producto_crear(sis, cod_grupo, titulo, tipo, anio, categoria="Sin categoría",
                   validado=False, ids_investigadores=None, registrar=True):
    ids = list(ids_investigadores) if ids_investigadores else []
    error = _validar_producto(sis, cod_grupo, ids, anio)
    if error:
        return None, error
    sis["contador_prod"] += 1
    prod = nuevo_producto("PRD-%04d" % sis["contador_prod"], titulo, tipo, anio,
                          categoria, validado, cod_grupo, ids)
    lista_insertar_final(sis["productos"], prod)
    _producto_enlazar(sis, prod)
    if registrar:
        _registrar(sis, {"op": "crear", "ent": "producto", "clave": prod["id"]})
    return prod, None


def producto_consultar(sis, id_prod):
    return lista_buscar(sis["productos"], "id", id_prod)


def producto_modificar(sis, id_prod, cambios, registrar=True):
    prod = lista_buscar(sis["productos"], "id", id_prod)
    if prod is None:
        return None, "El producto no existe"
    cambios = _filtrar(cambios, CAMPOS_PRODUCTO)
    if not cambios:
        return None, "No hay campos válidos para modificar"
    nuevo_grupo_cod = cambios.get("grupo", prod["grupo"])
    nuevos_inv = cambios.get("investigadores", prod["investigadores"])
    nuevo_anio = cambios.get("anio", prod["anio"])
    error = _validar_producto(sis, nuevo_grupo_cod, nuevos_inv, nuevo_anio)
    if error:
        return None, error
    antes = {}
    for k in cambios:
        antes[k] = list(prod[k]) if k == "investigadores" else prod[k]
    _producto_desenlazar(sis, prod)          # usa las coordenadas ANTIGUAS
    for k, v in cambios.items():
        prod[k] = list(v) if k == "investigadores" else v
    _producto_enlazar(sis, prod)             # usa las coordenadas NUEVAS
    if registrar:
        _registrar(sis, {"op": "modificar", "ent": "producto", "clave": id_prod,
                         "antes": antes})
    return prod, None


def producto_desactivar(sis, id_prod, activo=False, registrar=True):
    return _desactivar_simple(sis, sis["productos"], "id", "producto", id_prod, activo,
                              registrar, "El producto no existe")


def producto_validar(sis, id_prod, validado=True, registrar=True):
    return producto_modificar(sis, id_prod, {"validado": validado}, registrar)


def producto_eliminar(sis, id_prod, registrar=True):
    prod = lista_buscar(sis["productos"], "id", id_prod)
    if prod is None:
        return None, "El producto no existe"
    snapshot = producto_a_dict(prod)
    _producto_desenlazar(sis, prod)
    lista_eliminar(sis["productos"], "id", id_prod)
    if registrar:
        _registrar(sis, {"op": "eliminar", "ent": "producto", "clave": id_prod,
                         "snapshot": snapshot})
    return prod, None


# ==========================================================
# 11. DESHACER (usa la PILA de historial)
# ==========================================================
def _eliminar_ent(sis, ent, clave):
    if ent == "grupo":
        return grupo_eliminar(sis, clave, registrar=False)
    if ent == "investigador":
        return investigador_eliminar(sis, clave, registrar=False)
    return producto_eliminar(sis, clave, registrar=False)


def _modificar_ent(sis, ent, clave, antes):
    if ent == "grupo":
        return grupo_modificar(sis, clave, antes, registrar=False)
    if ent == "investigador":
        return investigador_modificar(sis, clave, antes, registrar=False)
    return producto_modificar(sis, clave, antes, registrar=False)


def _desactivar_ent(sis, ent, clave, activo):
    if ent == "grupo":
        return grupo_desactivar(sis, clave, activo, registrar=False)
    if ent == "investigador":
        return investigador_desactivar(sis, clave, activo, registrar=False)
    return producto_desactivar(sis, clave, activo, registrar=False)


def _restaurar_ent(sis, ent, snap):
    if ent == "grupo":
        lista_insertar_final(sis["grupos"], grupo_desde_dict(snap))
        return None
    if ent == "investigador":
        lista_insertar_final(sis["investigadores"], investigador_desde_dict(snap))
        return None
    error = _validar_producto(sis, snap["grupo"], snap["investigadores"], snap["anio"])
    if error:
        return error
    prod = producto_desde_dict(snap)
    lista_insertar_final(sis["productos"], prod)
    _producto_enlazar(sis, prod)
    return None


def deshacer(sis):
    """Revierte la última operación registrada. Devuelve un mensaje."""
    op = pila_desapilar(sis["historial"])
    if op is None:
        return "No hay operaciones para deshacer"
    tipo, ent, clave = op["op"], op["ent"], op["clave"]
    error = None
    if tipo == "crear":
        _, error = _eliminar_ent(sis, ent, clave)
    elif tipo == "modificar":
        _, error = _modificar_ent(sis, ent, clave, op["antes"])
    elif tipo == "desactivar":
        _, error = _desactivar_ent(sis, ent, clave, op["antes"])
    elif tipo == "eliminar":
        error = _restaurar_ent(sis, ent, op["snapshot"])
    if error:
        return "No se pudo deshacer: " + error
    return "Deshecho: %s %s %s" % (tipo, ent, clave)


# ==========================================================
# 12. COLA DE IMPORTACIONES
# ==========================================================
def importacion_encolar(sis, tipo, origen):
    """tipo: 'url' | 'csv' | 'pdf'"""
    cola_encolar(sis["importaciones"], {"tipo": tipo, "origen": origen,
                                        "estado": "pendiente"})


def importacion_siguiente(sis):
    """Saca de la cola la siguiente importación a procesar (FIFO)."""
    return cola_desencolar(sis["importaciones"])


# ==========================================================
# 13. ESTADÍSTICAS (consultas sobre el hipercubo)
# ==========================================================
def estadisticas(sis, **filtros):
    productos = cubo_consultar(sis["cubo"], **filtros)
    validados = 0
    for p in productos:
        if p["validado"]:
            validados += 1
    return {"total": len(productos),
            "validados": validados,
            "por_tipo": cubo_resumen(sis["cubo"], "tipo", **filtros),
            "por_categoria": cubo_resumen(sis["cubo"], "categoria", **filtros),
            "por_anio": cubo_resumen(sis["cubo"], "anio", **filtros),
            "por_grupo": cubo_resumen(sis["cubo"], "grupo", **filtros),
            "por_investigador": cubo_resumen(sis["cubo"], "investigador", **filtros)}


# ==========================================================
# 14. PERSISTENCIA (JSON)
# ==========================================================
def sistema_a_dict(sis):
    return {"version": 1,
            "contador_prod": sis["contador_prod"],
            "contador_inv": sis["contador_inv"],
            "grupos": [grupo_a_dict(g) for g in lista_recorrer(sis["grupos"])],
            "investigadores": [investigador_a_dict(i)
                               for i in lista_recorrer(sis["investigadores"])],
            "productos": [producto_a_dict(p) for p in lista_recorrer(sis["productos"])],
            "importaciones": [dict(i) for i in cola_recorrer(sis["importaciones"])]}


def sistema_desde_dict(d):
    """Reconstruye todas las estructuras. Devuelve (sistema, advertencias)."""
    sis = sistema_crear()
    advertencias = []
    sis["contador_prod"] = d.get("contador_prod", 0)
    sis["contador_inv"] = d.get("contador_inv", 0)
    for g in d.get("grupos", []):
        lista_insertar_final(sis["grupos"], grupo_desde_dict(g))
    for i in d.get("investigadores", []):
        lista_insertar_final(sis["investigadores"], investigador_desde_dict(i))
    for p in d.get("productos", []):
        error = _validar_producto(sis, p.get("grupo"), p.get("investigadores", []),
                                  p.get("anio"))
        if error:
            advertencias.append("Producto %s omitido: %s" % (p.get("id"), error))
            continue
        prod = producto_desde_dict(p)
        lista_insertar_final(sis["productos"], prod)
        _producto_enlazar(sis, prod)
    for imp in d.get("importaciones", []):
        cola_encolar(sis["importaciones"], dict(imp))
    return sis, advertencias


def guardar_json(sis, ruta):
    """Devuelve None si guardó bien, o el mensaje de error."""
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(sistema_a_dict(sis), f, ensure_ascii=False, indent=2)
    except OSError as e:
        return "No se pudo guardar: %s" % e
    return None


def cargar_json(ruta):
    """Devuelve (sistema, advertencias, error). Nunca falla en silencio."""
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return None, [], "No se pudo cargar: %s" % e
    sis, advertencias = sistema_desde_dict(datos)
    return sis, advertencias, None


# ==========================================================
# 15. DEMO / PRUEBA RÁPIDA  (python estructuras.py)
# ==========================================================
def demo():
    sis = sistema_crear()
    grupo_crear(sis, "COL0001", "Grupo de Sistemas", "Ana Pérez", "A")
    grupo_crear(sis, "COL0002", "Grupo de Energía", "Luis Gómez", "B")
    ana, _ = investigador_crear(sis, "Ana Pérez", "0000494917")
    luis, _ = investigador_crear(sis, "Luis Gómez")
    eva, _ = investigador_crear(sis, "Eva Mora")
    integrante_agregar(sis, "COL0001", ana["id"], "Líder")
    integrante_agregar(sis, "COL0001", eva["id"])

    producto_crear(sis, "COL0001", "Redes neuronales en salud", "Artículo", 2026, "A1",
                   True, [ana["id"], eva["id"]])
    producto_crear(sis, "COL0001", "Estructuras de datos", "Libro", 2025, "B", True,
                   [ana["id"]])
    producto_crear(sis, "COL0002", "Paneles solares", "Artículo", 2022, "A2", False,
                   [luis["id"]])
    p4, _ = producto_crear(sis, "COL0002", "Software de riego", "Software", 2024, "C",
                           True, [luis["id"], eva["id"]])

    print("Total histórico:", estadisticas(sis)["total"])
    print("Últimos 2 años :", estadisticas(sis, **ventana_anios(2, 2026))["total"])
    print("Por tipo       :", cubo_resumen(sis["cubo"], "tipo"))
    print("Por grupo      :", cubo_resumen(sis["cubo"], "grupo"))
    print("De Eva Mora    :", [p["titulo"] for p in
                               cubo_consultar(sis["cubo"], investigador=eva["id"])])

    producto_modificar(sis, p4["id"], {"anio": 2026, "tipo": "Artículo"})
    producto_desactivar(sis, "PRD-0003")
    print("Tras modificar/desactivar:", estadisticas(sis)["por_anio"])
    print(deshacer(sis))
    print(deshacer(sis))
    print("Tras deshacer:", estadisticas(sis)["por_anio"])

    importacion_encolar(sis, "url", "https://scienti.minciencias.gov.co/...nro=...")
    importacion_encolar(sis, "csv", "grupos.csv")
    print("Siguiente importación:", importacion_siguiente(sis)["tipo"])

    guardar_json(sis, "demo_pea_i.json")
    sis2, avisos, error = cargar_json("demo_pea_i.json")
    print("Recarga OK:", error is None, "| avisos:", avisos,
          "| total:", estadisticas(sis2)["total"])


# ==============================================================
# PARTE 2 - IMPORTACIÓN DE DATOS (SCIENTI / PDF / CSV)
# ==============================================================
try:
    import requests
    HAY_REQUESTS = True
except ImportError:
    HAY_REQUESTS = False
try:
    from bs4 import BeautifulSoup
    HAY_BS4 = True
except ImportError:
    HAY_BS4 = False
try:
    from pypdf import PdfReader
    HAY_PYPDF = True
except ImportError:
    HAY_PYPDF = False

ENCABEZADOS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept-Language": "es-CO,es;q=0.9",
}

# Palabra clave (sin tildes, minúsculas) -> tipo de producto. El orden importa.
# Los subtítulos que no estén aquí (Informes técnicos, Documentos de trabajo...) se
# conservan con su propio nombre como tipo, tal como los clasifica SCIENTI.
TITULOS_PRODUCTO = [
    ("proyectos de ley", "Proyecto de ley"), ("capitulo", "Capítulo de libro"),
    ("articulo", "Artículo"), ("libro", "Libro"), ("software", "Software"),
    ("patente", "Patente"), ("trabajo de grado", "Trabajo de grado"),
    ("trabajos dirigidos", "Trabajo de grado"), ("tutoria", "Trabajo de grado"),
    ("turoria", "Trabajo de grado"), ("proyecto", "Proyecto"), ("evento", "Evento"),
]
# Registros que NO son productos de investigación (actividades, jurados, cursos...).
SUBSECCIONES_NO_PRODUCTO = (
    "curso", "programa academico", "asesorias", "redes de", "estrategias", "jurado",
    "demas trabajos", "comites", "comite de", "espacios de participacion",
    "participacion ciudadana", "par evaluador",
)
# Títulos de secciones "contenedor" (cortan la sección anterior).
TITULOS_OTROS = [
    "datos basicos", "datos generales", "instituciones", "lineas de investigacion",
    "sectores de aplicacion", "areas de conocimiento", "plan estrategico",
    "plan de trabajo", "formacion academica", "formacion complementaria",
    "experiencia profesional", "areas de actuacion", "idiomas", "reconocimientos",
    "produccion", "apropiacion social", "otros productos", "otra produccion",
    "jurado", "otra informacion", "actividades", "identificacion",
    "redes sociales", "identificadores", "estancias", "otra informacion personal",
]
RE_ANIO = re.compile(r"(?<![\d.\-])(19[5-9]\d|20[0-4]\d)(?![\d\-])")
RE_CORTE_TITULO = re.compile(r"\s+(Autores?|ISSN|ISBN|Vol\.?|Editorial|DOI|Revista)\b\s*:?",
                             re.IGNORECASE)


# ==========================================================
# 1. UTILIDADES DE TEXTO
# ==========================================================
def limpiar(texto):
    return re.sub(r"\s+", " ", (texto or "").replace("\xa0", " ")).strip()


def normalizar(texto):
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().lower()


def decodificar(crudo):
    """GrupLAC/CvLAC pueden venir en UTF-8 o en ISO-8859-1."""
    try:
        return crudo.decode("utf-8")
    except UnicodeDecodeError:
        return crudo.decode("cp1252", errors="replace")


def _param_url(url, nombres):
    consulta = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    for n in nombres:
        if n in consulta:
            return consulta[n][0]
    return ""


def _tokens(nombre):
    return set(normalizar(re.sub(r"[^\w\s]", " ", nombre)).split())


def nombres_coinciden(a, b):
    """Coincidencia tolerante entre 'ANA MARIA PEREZ' y 'PEREZ, ANA M.'"""
    ta, tb = _tokens(a), _tokens(b)
    comunes = ta & tb
    if len(comunes) < 2:
        return False
    return len(comunes) / min(len(ta), len(tb)) >= 0.75


# ==========================================================
# 2. OBTENCIÓN DE FILAS DE TEXTO (HTML / PDF)
#    Todo se reduce a una lista de "filas"; cada fila es una lista de celdas de texto.
# ==========================================================
def descargar_html(url):
    if not HAY_REQUESTS:
        return None, "Falta la librería requests (pip install requests)"
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    try:
        respuesta = requests.get(url, headers=ENCABEZADOS, timeout=25)
    except requests.exceptions.SSLError:
        return None, ("Error de certificado SSL al conectar. Guarde la página desde el "
                      "navegador (Ctrl+S) y cárguela como archivo HTML.")
    except requests.RequestException as e:
        return None, "No se pudo conectar: %s" % e
    if respuesta.status_code != 200:
        return None, "El servidor respondió con el código %d" % respuesta.status_code
    return decodificar(respuesta.content), None


def leer_archivo_html(ruta):
    try:
        with open(ruta, "rb") as f:
            return decodificar(f.read()), None
    except OSError as e:
        return None, "No se pudo abrir el archivo: %s" % e


def filas_desde_texto(texto):
    filas = []
    for linea in texto.splitlines():
        linea = limpiar(linea)
        if linea:
            filas.append([linea])
    return filas


def filas_desde_html(html):
    if not HAY_BS4:
        return None, "Falta la librería beautifulsoup4 (pip install beautifulsoup4)"
    sopa = BeautifulSoup(html, "html.parser")
    for etiqueta in sopa(["script", "style", "noscript"]):
        etiqueta.decompose()
    filas = []
    for tr in sopa.find_all("tr"):
        if tr.find("table"):
            continue                      # solo filas "hoja", sin tablas anidadas
        celdas = [limpiar(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
        celdas = [c for c in celdas if c]
        if celdas:
            filas.append(celdas)
    if len(filas) < 5:                    # página sin tablas: se usa el texto por líneas
        filas = filas_desde_texto(sopa.get_text("\n"))
    return filas, None


def filas_desde_pdf(ruta):
    if not HAY_PYPDF:
        return None, "Falta la librería pypdf (pip install pypdf)"
    try:
        lector = PdfReader(ruta)
        texto = "\n".join([(pagina.extract_text() or "") for pagina in lector.pages])
    except Exception as e:                # pypdf lanza varios tipos de error
        return None, "No se pudo leer el PDF: %s" % e
    if not texto.strip():
        return None, "El PDF no tiene texto extraíble (¿es una imagen escaneada?)"
    return filas_desde_texto(texto), None


def obtener_html(tipo, origen):
    if tipo == "url":
        return descargar_html(origen)
    if tipo == "html":
        return leer_archivo_html(origen)
    return None, "Tipo de fuente no soportado: %s" % tipo


def obtener_filas(tipo, origen):
    if tipo == "pdf":
        return filas_desde_pdf(origen)
    html, error = obtener_html(tipo, origen)
    if error:
        return None, error
    return filas_desde_html(html)


# ==========================================================
# 3. ANÁLISIS DE SECCIONES
# ==========================================================
def tipo_canonico(texto_normalizado):
    for clave, tipo in TITULOS_PRODUCTO:
        if clave in texto_normalizado:
            return tipo
    return None


def _es_no_producto(texto_normalizado):
    for clave in SUBSECCIONES_NO_PRODUCTO:
        if clave in texto_normalizado:
            return True
    return False


def clasificar_titulo(celdas):
    """Si la fila es el título de una sección devuelve (clase, tipo), si no None."""
    if len(celdas) != 1:
        return None
    texto = normalizar(celdas[0])
    if len(texto) > 90 or re.match(r"^\d+\s*[.\-)]", texto):
        return None
    if texto.startswith("integrantes"):
        return ("integrantes", None)
    for clave in TITULOS_OTROS:
        if texto.startswith(clave):
            return ("otro", None)
    if _es_no_producto(texto):
        return ("otro", None)
    tipo = tipo_canonico(texto)
    if tipo is not None:
        return ("producto", tipo)
    return None


def quitar_numeracion(celdas):
    """'1.- Título...' o ['1', 'Título...'] -> 'Título...'. None si la fila no está numerada."""
    if re.fullmatch(r"\d+\s*[.\-)]*", celdas[0]) and len(celdas) > 1:
        return " ".join(celdas[1:])
    m = re.match(r"^\d+\s*[.\-)]+\s*(.*)", " ".join(celdas))
    if m and m.group(1):
        return m.group(1)
    return None


def _es_subtitulo(celdas):
    return (len(celdas) == 1 and len(celdas[0]) <= 90 and celdas[0][0].isupper()
            and quitar_numeracion(celdas) is None)


def analizar_filas(filas):
    """GrupLAC: integrantes y productos. Los subtítulos no reconocidos dentro de la
    producción se toman como un tipo propio (así no se mezclan con la sección anterior)."""
    seccion = None
    tipo = None
    en_produccion = False
    integrantes = []
    productos = []
    secciones = []
    for celdas in filas:
        titulo = clasificar_titulo(celdas)
        if titulo is None and en_produccion and seccion in ("producto", "otro") \
                and _es_subtitulo(celdas):
            titulo = ("producto", limpiar(celdas[0]))
        if titulo is not None:
            seccion, tipo = titulo
            if seccion == "producto" or normalizar(celdas[0]).startswith("produccion"):
                en_produccion = True
            secciones.append((seccion, tipo, normalizar(celdas[0])))
            continue
        if seccion == "integrantes":
            integrantes.append(celdas)
        elif seccion == "producto":
            texto = quitar_numeracion(celdas)
            if texto is not None:
                productos.append({"tipo": tipo, "texto": texto})
            elif productos and productos[-1]["tipo"] == tipo:
                if len(productos[-1]["texto"]) < 1500:
                    productos[-1]["texto"] += " " + " ".join(celdas)
    return {"integrantes": integrantes, "productos": productos, "secciones": secciones}


# CvLAC: los productos NO van numerados; una fila "descriptor" precede a cada producto
# (p. ej. "Producción bibliográfica - Artículo - Publicado en revista especializada").
RE_DESCRIPTOR_CV = re.compile(
    r"^(Producci[oó]n [\w\sáéíóúñ]+|Trabajos dirigidos/Tutor[ií]as|Apropiaci[oó]n social[\w\sáéíóúñ]*)"
    r"\s+-\s+.+", re.IGNORECASE)


def tipo_desde_descriptor(descriptor):
    partes = [p.strip() for p in descriptor.split(" - ") if p.strip()]
    if normalizar(partes[0]).startswith("apropiacion social"):
        return "Apropiación social del conocimiento"
    for p in partes:
        tipo = tipo_canonico(normalizar(p))
        if tipo is not None:
            return tipo
    return recortar(partes[1] if len(partes) > 1 else partes[0], 60)


def analizar_filas_cvlac(filas):
    productos = []
    descriptor = None
    for celdas in filas:
        texto = limpiar(" ".join(celdas))
        if len(celdas) == 1 and len(texto) <= 170 and RE_DESCRIPTOR_CV.match(texto):
            descriptor = texto
            continue
        if descriptor is not None:
            if not _es_no_producto(normalizar(descriptor)) \
                    and "evento" not in normalizar(descriptor):
                productos.append({"tipo": tipo_desde_descriptor(descriptor),
                                  "texto": texto, "cv": True})
            descriptor = None
        elif texto.startswith("Tipo:") and "capitulo" in normalizar(texto[:40]):
            productos.append({"tipo": "Capítulo de libro", "texto": texto, "cv": True})
    return {"productos": productos}


def buscar_valor(filas, etiquetas):
    """Busca 'Etiqueta | Valor' o 'Etiqueta: Valor' y devuelve el valor."""
    for celdas in filas:
        for i, celda in enumerate(celdas):
            n = normalizar(celda).rstrip(": ")
            for e in etiquetas:
                if n == e and i + 1 < len(celdas):
                    return celdas[i + 1]
                if normalizar(celda).startswith(e + ":"):
                    resto = celda.split(":", 1)[1].strip()
                    if resto:
                        return resto
    return ""


def parsear_integrante(celdas):
    if re.fullmatch(r"\d+\s*[.\-)]*", celdas[0]) and len(celdas) > 1:
        celdas = celdas[1:]
    nombre = limpiar(re.sub(r"^\d+\s*[.\-)]+\s*", "", celdas[0]))
    if len(nombre) < 5 or re.search(r"\d", nombre):
        return None
    if normalizar(nombre).startswith(("nombre", "vinculacion", "integrante", "horas")):
        return None
    periodo = celdas[3] if len(celdas) > 3 else "Actual"
    return {"nombre": nombre,
            "vinculacion": celdas[1] if len(celdas) > 1 else "Integrante",
            "horas": celdas[2] if len(celdas) > 2 else "N/D",
            "periodo": periodo,
            "activo": not re.search(r"-\s*(19|20)\d\d", periodo)}


YEAR = r"(?:19[5-9]\d|20[0-4]\d)"
PATRONES_ANIO = [r"A[ñn]o(?: de inicio)?:\s*(Y)", r",\s*(Y)(?=[,\s/.])",
                 r"[Dd]esde\s+(?:\d{1,2}\s+)?(Y)", r"\s(Y)(?=[,.])", r"(Y)/\d{1,2}\s*-",
                 r"\s(Y)-\d{2}-\d{2}"]
RE_CORTE = re.compile(
    r"\s+,\s|\s+\S+,\s*(?:19|20)\d\d\b|\s+(?:19|20)\d\d,|\s+(?:19|20)\d\d[/-]\d"
    r"|\s+(?:Autores?|ISSN|ISBN|Vol\.?|Editorial|DOI|A[ñn]o|Estado|Disponibilidad"
    r"|Instituci[oó]n(?:es)?|Nro\.|N[uú]mero)\s*:"
    r"|\s+(?:Desde|desde)\s+\d|\.\s+En:|,\s*Nombre comercial")


def extraer_anio(texto):
    """Año de publicación probando patrones de más a menos fiables."""
    limite = datetime.now().year + 1
    for patron in PATRONES_ANIO:
        for m in re.finditer(patron.replace("Y", YEAR), texto):
            if int(m.group(1)) <= limite:
                return int(m.group(1))
    for candidato in RE_ANIO.findall(texto):
        if int(candidato) <= limite:
            return int(candidato)
    return None


def _cortar_titulo(texto):
    m = RE_CORTE.search(texto)
    if m and m.start() > 2:
        texto = texto[:m.start()]
    return recortar(limpiar(texto).strip(" ,;:-\"“”"), 200)


def extraer_titulo(texto):
    m = re.match(r"^([^:,\d]{2,70}):\s+(.+)", texto)       # quita 'Tipo de producto :'
    if m:
        texto = m.group(2)
    return _cortar_titulo(texto)


def titulo_cvlac(texto):
    m = re.match(r"^Nombre del producto:\s*(.+?),\s*Fecha", texto)
    if m:
        return recortar(limpiar(m.group(1)), 200)
    comillas = re.search(r"[\"“](.{5,}?)[\"”]", texto)
    if comillas:
        return recortar(limpiar(comillas.group(1)), 200)
    partes = texto.split(", ")
    i = 0
    while i < len(partes) - 1 and len(partes[i]) > 3 and partes[i] == partes[i].upper() \
            and any(c.isalpha() for c in partes[i]):
        i += 1                                               # autores en mayúsculas
    return _cortar_titulo(", ".join(partes[i:]))


def producto_desde_item(item):
    texto = item["texto"]
    titulo = titulo_cvlac(texto) if item.get("cv") else extraer_titulo(texto)
    autores = []
    m = re.search(r"Autores?\s*:\s*(.+)", texto, re.IGNORECASE)
    if m:
        for nombre in re.split(r"[;,]", m.group(1)):
            nombre = limpiar(nombre)
            if len(nombre) > 4:
                autores.append(nombre)
    return {"titulo": titulo, "tipo": item["tipo"], "anio": extraer_anio(texto),
            "autores": autores}


def _productos_unicos(items):
    vistos = set()
    salida = []
    for item in items:
        p = producto_desde_item(item)
        clave = (normalizar(p["titulo"]), p["tipo"])
        if p["titulo"] and clave not in vistos:
            vistos.add(clave)
            salida.append(p)
    return salida


# ==========================================================
# 4. LECTORES POR TIPO DE PÁGINA
# ==========================================================
def categoria_desde_texto(texto):
    n = normalizar(texto)
    m = re.match(r"^(a1|a|b|c)\b", n)
    if m:
        return m.group(1).upper()
    if "reconocido" in n:
        return "Reconocido"
    return "Sin categoría"


def encabezado_html(html):
    """Nombre del grupo: el detalle de GrupLAC lo muestra en un <span class=celdaEncabezado>."""
    if not HAY_BS4:
        return ""
    elemento = BeautifulSoup(html, "html.parser").find("span", class_="celdaEncabezado")
    return limpiar(elemento.get_text(" ")) if elemento else ""


def parsear_grupo(filas, fuente, codigo_hint="", nombre_hint=""):
    advertencias = []
    nombre = nombre_hint or buscar_valor(filas, ["nombre del grupo"])
    if not nombre:
        nombre = "Grupo importado"
        advertencias.append("No se encontró el nombre del grupo.")
    codigo = codigo_hint
    if not codigo:
        inicio = " ".join([" ".join(f) for f in filas[:80]])
        m = re.search(r"COL\d{7}", inicio)
        codigo = m.group(0) if m else ""
    if not codigo:
        codigo = "IMP-%06X" % (zlib.crc32(normalizar(nombre).encode("utf-8")) & 0xFFFFFF)
        advertencias.append("La página de detalle no trae el código COL; se usó %s. Si "
                            "ya importó el listado, el grupo se asocia por nombre." % codigo)
    lider = buscar_valor(filas, ["lider"]) or "N/D"
    categoria = categoria_desde_texto(buscar_valor(filas, ["clasificacion"]))

    analisis = analizar_filas(filas)
    integrantes = []
    vistos = set()
    for celdas in analisis["integrantes"]:
        reg = parsear_integrante(celdas)
        if reg is None or normalizar(reg["nombre"]) in vistos:
            continue
        vistos.add(normalizar(reg["nombre"]))
        if lider != "N/D" and nombres_coinciden(reg["nombre"], lider):
            reg["vinculacion"] = "Líder"
        integrantes.append(reg)
    productos = _productos_unicos(analisis["productos"])
    if not integrantes:
        advertencias.append("No se reconocieron integrantes.")
    return {"modo": "grupo", "codigo": codigo, "nombre": nombre, "lider": lider,
            "categoria": categoria, "url": fuente if fuente.startswith("http") else "",
            "integrantes": integrantes, "productos": productos,
            "advertencias": advertencias}


def parsear_cvlac(filas, fuente):
    advertencias = []
    cod_rh = re.sub(r"\D", "", _param_url(fuente, ("cod_rh",)))
    nombre = buscar_valor(filas, ["nombre", "nombre completo"])
    if not nombre or len(nombre) > 100:
        nombre = ""
        advertencias.append("No se encontró el nombre del investigador.")
    categoria = limpiar(re.split(r"\s+con vigencia", buscar_valor(filas, ["categoria"]))[0])
    if not categoria or len(categoria) > 40 or "sin categoria" in normalizar(categoria):
        categoria = "Sin categoría"
    analisis = analizar_filas_cvlac(filas)
    return {"modo": "investigador", "nombre": nombre, "cod_rh": cod_rh,
            "categoria": categoria, "productos": _productos_unicos(analisis["productos"]),
            "advertencias": advertencias}


# ----------------------------------------------------------
# Listados ("directorios") de SCIENTI: son las páginas de resultados de búsqueda.
#   - Grupos:        busquedaAvanzadaGrupos.do  (una fila por grupo, con enlace al detalle)
#   - Investigadores: enRecursoHumanoBusqueda.do (una fila por CvLAC)
# Se leen con BeautifulSoup directamente porque hay que conservar los enlaces.
# ----------------------------------------------------------
MODO_NO_DETECTADO = "NO_DETECTADO"


def categoria_grupo(texto):
    n = normalizar(texto)
    if n.startswith("categoria "):
        return n[len("categoria "):].strip().upper()
    if "reconocido" in n:
        return "Reconocido"
    return limpiar(texto).capitalize() if n else "Sin categoría"


def categoria_investigador(texto):
    n = normalizar(texto)
    if not n or "sin categoria" in n:
        return "Sin categoría"
    return limpiar(texto).title()


def _total_resultados(texto):
    m = re.search(r"Resultados\s+(\d+)\s*-\s*(\d+)\s+de\s+([\d.,]+)", texto)
    if not m:
        return 0, 0, 0
    return int(m.group(1)), int(m.group(2)), int(re.sub(r"\D", "", m.group(3)) or 0)


def detectar_pagina(html, origen=""):
    """Devuelve directorio_grupos | directorio_investigadores | grupo | investigador | None."""
    if "gruposAvanzada_row" in html or 'name="gruposAvanzadaForm"' in html:
        return "directorio_grupos"
    if "investigadores_row" in html:
        return "directorio_investigadores"
    o = origen.lower()
    if "visualizagr" in o:
        return "grupo"
    if "generarcurriculocv" in o:
        return "investigador"
    return None


def parsear_directorio_grupos(html):
    if not HAY_BS4:
        return None, "Falta la librería beautifulsoup4 (pip install beautifulsoup4)"
    sopa = BeautifulSoup(html, "html.parser")
    grupos = []
    for tr in sopa.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 7:
            continue
        codigo = limpiar(tds[1].get_text(" "))
        if not re.fullmatch(r"COL\d{7}", codigo):
            continue
        enlace = tds[2].find("a")
        enlace_lider = tds[3].find("a")
        href_lider = enlace_lider.get("href", "") if enlace_lider else ""
        grupos.append({
            "codigo": codigo,
            "nombre": limpiar(tds[2].get_text(" ")),
            "url": enlace.get("href", "") if enlace else "",
            "lider": limpiar(tds[3].get_text(" ")),
            "cod_rh_lider": re.sub(r"\D", "", _param_url(href_lider, ("cod_rh",))),
            "categoria": categoria_grupo(tds[6].get_text(" ")),
            "convocatoria": limpiar(tds[7].get_text(" ")) if len(tds) > 7 else ""})
    if not grupos:
        return None, "No se encontraron grupos en el listado."
    _, _, total = _total_resultados(sopa.get_text(" "))
    return {"modo": "directorio_grupos", "grupos": grupos, "productos": [],
            "total_resultados": total, "advertencias": []}, None


def parsear_directorio_investigadores(html):
    if not HAY_BS4:
        return None, "Falta la librería beautifulsoup4 (pip install beautifulsoup4)"
    sopa = BeautifulSoup(html, "html.parser")
    investigadores = []
    for tr in sopa.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        enlace = tds[1].find("a")
        if enlace is None or "cod_rh=" not in enlace.get("href", ""):
            continue
        investigadores.append({
            "nombre": limpiar(tds[1].get_text(" ")),
            "cod_rh": re.sub(r"\D", "", _param_url(enlace["href"], ("cod_rh",))),
            "categoria": categoria_investigador(tds[3].get_text(" "))})
    if not investigadores:
        return None, "No se encontraron investigadores en el listado."
    _, _, total = _total_resultados(sopa.get_text(" "))
    advertencias = []
    if total > 1000:
        advertencias.append(
            "Este listado tiene %s investigadores de TODO el país (no está filtrado por "
            "institución). Para la UPC es mejor importar los integrantes de cada grupo."
            % format(total, ","))
    return {"modo": "directorio_investigadores", "investigadores": investigadores,
            "productos": [], "total_resultados": total,
            "advertencias": advertencias}, None


CSV_COLUMNAS = ["grupo", "titulo", "tipo", "categoria", "anio", "validado", "autores"]


def _valor(fila, mapa, clave):
    original = mapa.get(clave)
    return limpiar(fila.get(original, "") or "") if original else ""


def leer_csv(ruta):
    """CSV de productos. Columnas: grupo;titulo;tipo;categoria;anio;validado;autores
    (autores separados por | ). Obligatorias: grupo, titulo, anio."""
    try:
        with open(ruta, "rb") as f:
            texto = decodificar(f.read()).lstrip("\ufeff")
    except OSError as e:
        return None, "No se pudo abrir el archivo: %s" % e
    if not texto.strip():
        return None, "El CSV está vacío"
    primera = texto.splitlines()[0]
    delimitador = ";" if primera.count(";") > primera.count(",") else ","
    lector = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
    mapa = {}
    for columna in lector.fieldnames or []:
        mapa[normalizar(columna)] = columna
    faltan = [c for c in ("grupo", "titulo", "anio") if c not in mapa]
    if faltan:
        return None, ("Faltan columnas obligatorias: %s.\nColumnas esperadas: %s"
                      % (", ".join(faltan), ", ".join(CSV_COLUMNAS)))
    productos = []
    advertencias = []
    for numero, fila in enumerate(lector, start=2):
        titulo = _valor(fila, mapa, "titulo")
        grupo = _valor(fila, mapa, "grupo")
        if not titulo or not grupo:
            advertencias.append("Fila %d omitida: falta grupo o título." % numero)
            continue
        try:
            anio = int(_valor(fila, mapa, "anio"))
        except ValueError:
            advertencias.append("Fila %d omitida: año inválido." % numero)
            continue
        autores = [limpiar(a) for a in re.split(r"[|;]", _valor(fila, mapa, "autores"))
                   if limpiar(a)]
        productos.append({
            "grupo": grupo, "titulo": titulo, "anio": anio,
            "tipo": _valor(fila, mapa, "tipo") or "Artículo",
            "categoria": _valor(fila, mapa, "categoria") or "Sin categoría",
            "validado": normalizar(_valor(fila, mapa, "validado")) in
                        ("si", "1", "true", "verdadero", "x", "yes"),
            "autores": autores})
    if not productos:
        return None, "El CSV no tiene filas válidas.\n" + "\n".join(advertencias[:5])
    return {"modo": "csv", "productos": productos, "advertencias": advertencias}, None


def crear_plantilla_csv(ruta):
    """Devuelve None si todo salió bien o el mensaje de error."""
    try:
        with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
            f.write(";".join(CSV_COLUMNAS) + "\n")
            f.write("COL0001;Ejemplo de artículo;Artículo;A1;2025;si;Ana Pérez|Eva Mora\n")
            f.write("COL0001;Ejemplo de libro;Libro;B;2024;no;Ana Pérez\n")
    except OSError as e:
        return "No se pudo crear la plantilla: %s" % e
    return None


# ==========================================================
# 5. FASE 1: LEER Y DESCRIBIR (vista previa)
# ==========================================================
def leer_origen(tipo, origen, modo="auto", pista=None):
    """tipo: url|html|pdf|csv.  modo: auto | grupo | investigador (detalle de una página).
    En modo auto se reconocen los listados de SCIENTI por su contenido; si no se puede
    decidir devuelve (None, MODO_NO_DETECTADO) y la interfaz pregunta al usuario.
    pista: dict opcional del elemento de la cola ({"modo", "codigo"})."""
    pista = pista or {}
    if tipo == "csv":
        return leer_csv(origen)
    if tipo in ("url", "html"):
        html, error = obtener_html(tipo, origen)
        if error:
            return None, error
        if modo == "auto":
            modo = pista.get("modo") or detectar_pagina(html, origen) or "auto"
        if modo == "directorio_grupos":
            return parsear_directorio_grupos(html)
        if modo == "directorio_investigadores":
            return parsear_directorio_investigadores(html)
        filas, error = filas_desde_html(html)
        encabezado = encabezado_html(html) if modo == "grupo" else ""
    else:
        encabezado = ""
        filas, error = filas_desde_pdf(origen)
        if modo == "auto":
            modo = pista.get("modo") or "auto"
    if error:
        return None, error
    if modo not in ("grupo", "investigador"):
        return None, MODO_NO_DETECTADO
    if modo == "grupo":
        datos = parsear_grupo(filas, origen, pista.get("codigo", ""), encabezado)
    else:
        datos = parsear_cvlac(filas, origen)
    if not datos["productos"] and not datos.get("integrantes"):
        return None, ("No se reconocieron integrantes ni productos en la fuente.\n"
                      "Use «Diagnóstico de una fuente» para ver la estructura que recibió "
                      "el programa y ajustar el lector.")
    return datos, None


def describir_directorio(datos):
    lineas = []
    if datos["modo"] == "directorio_grupos":
        lineas.append("LISTADO DE GRUPOS DE SCIENTI: %d grupos" % len(datos["grupos"]))
        lineas.append("")
        for g in datos["grupos"][:10]:
            lineas.append("  • %s  %s  [%s]" % (g["codigo"], recortar(g["nombre"], 55),
                                                 g["categoria"]))
        if len(datos["grupos"]) > 10:
            lineas.append("  ... y %d más" % (len(datos["grupos"]) - 10))
        lineas.append("")
        lineas.append("Se crearán/actualizarán los grupos y sus líderes, y el enlace de "
                      "detalle de cada grupo quedará en la COLA para procesarlos uno a uno.")
    else:
        lineas.append("LISTADO DE INVESTIGADORES DE SCIENTI: %d en esta página"
                      % len(datos["investigadores"]))
        lineas.append("")
        for i in datos["investigadores"][:10]:
            lineas.append("  • %s  (cod_rh %s)  [%s]" % (recortar(i["nombre"], 45),
                                                          i["cod_rh"], i["categoria"]))
    if datos["advertencias"]:
        lineas.append("")
        lineas.append("Advertencias:")
        for a in datos["advertencias"]:
            lineas.append("  ! " + a)
    return "\n".join(lineas)


def describir_datos(datos):
    if datos["modo"] in ("directorio_grupos", "directorio_investigadores"):
        return describir_directorio(datos)
    lineas = []
    if datos["modo"] == "grupo":
        lineas.append("GRUPO: %s - %s" % (datos["codigo"], datos["nombre"]))
        lineas.append("Líder: %s   |   Categoría: %s" % (datos["lider"], datos["categoria"]))
        lineas.append("Integrantes detectados: %d" % len(datos["integrantes"]))
    elif datos["modo"] == "investigador":
        lineas.append("INVESTIGADOR: %s" % (datos["nombre"] or "(sin nombre)"))
        lineas.append("Código CvLAC: %s   |   Categoría: %s"
                      % (datos["cod_rh"] or "N/D", datos["categoria"]))
    else:
        lineas.append("ARCHIVO CSV")
    productos = datos["productos"]
    con_anio = [p for p in productos if p["anio"] is not None]
    lineas.append("Productos detectados: %d (con año: %d, sin año: %d)"
                  % (len(productos), len(con_anio), len(productos) - len(con_anio)))
    por_tipo = {}
    for p in productos:
        por_tipo[p["tipo"]] = por_tipo.get(p["tipo"], 0) + 1
    if por_tipo:
        lineas.append("Por tipo: " + ", ".join(["%s: %d" % kv for kv in por_tipo.items()]))
    lineas.append("")
    lineas.append("Primeros productos:")
    for p in productos[:5]:
        lineas.append("  • (%s) %s" % (p["anio"] if p["anio"] is not None else "s/a",
                                       recortar(p["titulo"], 80)))
    if datos["advertencias"]:
        lineas.append("")
        lineas.append("Advertencias:")
        for a in datos["advertencias"][:6]:
            lineas.append("  ! " + a)
    return "\n".join(lineas)


def diagnosticar_origen(tipo, origen):
    """Informe de texto para ver qué estructura recibió el programa."""
    filas, error = obtener_filas(tipo, origen)
    if error:
        return "ERROR: " + error
    analisis = analizar_filas(filas)
    lineas = ["DIAGNÓSTICO DE LA FUENTE", "Fuente: %s" % origen,
              "Filas de texto detectadas: %d" % len(filas), ""]
    lineas.append("Secciones reconocidas (en orden):")
    for clase, tipo_sec, titulo in analisis["secciones"]:
        lineas.append("  - [%s%s] %s" % (clase, "/" + tipo_sec if tipo_sec else "",
                                          recortar(titulo, 70)))
    if not analisis["secciones"]:
        lineas.append("  (ninguna)")
    por_tipo = {}
    for item in analisis["productos"]:
        por_tipo[item["tipo"]] = por_tipo.get(item["tipo"], 0) + 1
    lineas.append("")
    lineas.append("Filas de integrantes: %d" % len(analisis["integrantes"]))
    lineas.append("Productos por tipo: %s" % (por_tipo or "(ninguno)"))
    sin_clasificar = []
    for celdas in filas:
        if len(celdas) == 1 and len(celdas[0]) <= 90 and clasificar_titulo(celdas) is None \
                and quitar_numeracion(celdas) is None and celdas[0] not in sin_clasificar:
            sin_clasificar.append(celdas[0])
    lineas.append("")
    lineas.append("Filas cortas NO reconocidas (posibles títulos de sección):")
    for texto in sin_clasificar[:40]:
        lineas.append("  ? " + texto)
    lineas.append("")
    lineas.append("--- Primeras 80 filas (celdas separadas por ' | ') ---")
    for n, celdas in enumerate(filas[:80], 1):
        lineas.append("%3d: %s" % (n, recortar(" | ".join(celdas), 160)))
    return "\n".join(lineas)


# ==========================================================
# 6. FASE 2: IMPORTAR A LAS ESTRUCTURAS
#    (la importación no pasa por la pila de deshacer)
# ==========================================================
def _informe_nuevo():
    return {"grupos_nuevos": 0, "grupos_actualizados": 0, "inv_nuevos": 0,
            "inv_actualizados": 0, "integrantes_nuevos": 0, "productos_nuevos": 0,
            "productos_repetidos": 0, "productos_actualizados": 0, "sin_anio": 0,
            "encolados": 0, "advertencias": []}


def _investigador_por_nombre(sis, nombre):
    for inv in lista_recorrer(sis["investigadores"]):
        if nombres_coinciden(inv["nombre"], nombre):
            return inv
    return None


def _producto_repetido(sis, cod_grupo, titulo, anio):
    g = grupo_consultar(sis, cod_grupo)
    if g is None:
        return None
    for p in lista_recorrer(g["productos"]):
        if p["anio"] == anio and normalizar(p["titulo"]) == normalizar(titulo):
            return p
    return None


def _ids_autores_en_grupo(sis, cod_grupo, nombres):
    g = grupo_consultar(sis, cod_grupo)
    ids = []
    for nombre in nombres:
        for integrante in lista_recorrer(g["integrantes"]):
            inv = investigador_consultar(sis, integrante["id_investigador"])
            if inv is not None and nombres_coinciden(inv["nombre"], nombre) \
                    and inv["id"] not in ids:
                ids.append(inv["id"])
    return ids


def _asegurar_investigador(sis, nombre, cod_rh, categoria, informe):
    """Busca por cod_rh y luego por nombre; si no existe lo crea."""
    inv = None
    if cod_rh:
        inv = lista_buscar(sis["investigadores"], "cod_rh", cod_rh)
    if inv is None and nombre:
        inv = _investigador_por_nombre(sis, nombre)
    if inv is None:
        inv, _ = investigador_crear(sis, nombre, cod_rh, "", "", categoria, registrar=False)
        informe["inv_nuevos"] += 1
    elif cod_rh and not inv["cod_rh"]:
        investigador_modificar(sis, inv["id"], {"cod_rh": cod_rh}, registrar=False)
        informe["inv_actualizados"] += 1
    return inv


def _ya_en_cola(sis, origen):
    for item in cola_recorrer(sis["importaciones"]):
        if item["origen"] == origen:
            return True
    return False


def _importar_directorio_grupos(sis, datos, encolar):
    informe = _informe_nuevo()
    for g in datos["grupos"]:
        existente = grupo_consultar(sis, g["codigo"])
        if existente is None:
            _, error = grupo_crear(sis, g["codigo"], g["nombre"], g["lider"] or "N/D",
                                   g["categoria"], g["url"], registrar=False)
            if error:
                informe["advertencias"].append("%s: %s" % (g["codigo"], error))
                continue
            informe["grupos_nuevos"] += 1
        else:
            nuevos = {"nombre": g["nombre"], "lider": g["lider"] or "N/D",
                      "categoria": g["categoria"], "url": g["url"]}
            cambios = {}
            for k, v in nuevos.items():
                if existente[k] != v:
                    cambios[k] = v
            if cambios:
                grupo_modificar(sis, g["codigo"], cambios, registrar=False)
                informe["grupos_actualizados"] += 1
        if g["lider"]:
            lider = _asegurar_investigador(sis, g["lider"], g["cod_rh_lider"],
                                           "Sin categoría", informe)
            _, error = integrante_agregar(sis, g["codigo"], lider["id"], "Líder")
            if error is None:
                informe["integrantes_nuevos"] += 1
        if encolar and g["url"] and not _ya_en_cola(sis, g["url"]):
            cola_encolar(sis["importaciones"], {"tipo": "url", "origen": g["url"],
                                                "estado": "pendiente", "modo": "grupo",
                                                "codigo": g["codigo"]})
            informe["encolados"] += 1
    return informe, None


def _importar_directorio_investigadores(sis, datos):
    informe = _informe_nuevo()
    for i in datos["investigadores"]:
        _asegurar_investigador(sis, i["nombre"], i["cod_rh"], i["categoria"], informe)
    return informe, None


def _grupo_por_nombre(sis, nombre):
    n = normalizar(nombre)
    for g in lista_recorrer(sis["grupos"]):
        otro = normalizar(g["nombre"])
        corto, largo = (otro, n) if len(otro) <= len(n) else (n, otro)
        if len(corto) >= 5 and (corto == largo or corto in largo):
            return g
    return None


def _importar_grupo(sis, datos):
    informe = _informe_nuevo()
    codigo = datos["codigo"]
    if grupo_consultar(sis, codigo) is None:
        existente = _grupo_por_nombre(sis, datos["nombre"])
        if existente is not None:
            codigo = existente["codigo"]
    if grupo_consultar(sis, codigo) is None:
        _, error = grupo_crear(sis, codigo, datos["nombre"], datos["lider"],
                               datos["categoria"], datos["url"], registrar=False)
        if error:
            return None, error
        informe["grupos_nuevos"] += 1
    for it in datos["integrantes"]:
        inv = _investigador_por_nombre(sis, it["nombre"])
        if inv is None:
            inv, _ = investigador_crear(sis, it["nombre"], registrar=False)
            informe["inv_nuevos"] += 1
        _, error = integrante_agregar(sis, codigo, inv["id"], it["vinculacion"],
                                      it["horas"], it["periodo"])
        if error is None:
            informe["integrantes_nuevos"] += 1
            if not it.get("activo", True):
                integrante_desactivar(sis, codigo, inv["id"], False)
    for p in datos["productos"]:
        if p["anio"] is None:
            informe["sin_anio"] += 1
            continue
        if _producto_repetido(sis, codigo, p["titulo"], p["anio"]) is not None:
            informe["productos_repetidos"] += 1
            continue
        autores = _ids_autores_en_grupo(sis, codigo, p["autores"])
        _, error = producto_crear(sis, codigo, p["titulo"], p["tipo"], p["anio"],
                                  "Sin categoría", False, autores, registrar=False)
        if error:
            informe["advertencias"].append(error)
        else:
            informe["productos_nuevos"] += 1
    return informe, None


def _importar_investigador(sis, datos, cod_grupo):
    informe = _informe_nuevo()
    if not cod_grupo or grupo_consultar(sis, cod_grupo) is None:
        return None, "Seleccione un grupo existente al que asociar los productos"
    if not datos["nombre"]:
        return None, "No se pudo leer el nombre del investigador"
    inv = None
    if datos["cod_rh"]:
        inv = lista_buscar(sis["investigadores"], "cod_rh", datos["cod_rh"])
    if inv is None:
        inv = _investigador_por_nombre(sis, datos["nombre"])
    if inv is None:
        inv, _ = investigador_crear(sis, datos["nombre"], datos["cod_rh"], "", "",
                                    datos["categoria"], registrar=False)
        informe["inv_nuevos"] += 1
    elif datos["cod_rh"] and not inv["cod_rh"]:
        investigador_modificar(sis, inv["id"], {"cod_rh": datos["cod_rh"]}, registrar=False)
    for p in datos["productos"]:
        if p["anio"] is None:
            informe["sin_anio"] += 1
            continue
        repetido = _producto_repetido(sis, cod_grupo, p["titulo"], p["anio"])
        if repetido is None:
            _, error = producto_crear(sis, cod_grupo, p["titulo"], p["tipo"], p["anio"],
                                      "Sin categoría", False, [inv["id"]], registrar=False)
            if error:
                informe["advertencias"].append(error)
            else:
                informe["productos_nuevos"] += 1
        elif inv["id"] not in repetido["investigadores"]:
            producto_modificar(sis, repetido["id"],
                               {"investigadores": repetido["investigadores"] + [inv["id"]]},
                               registrar=False)
            informe["productos_actualizados"] += 1
        else:
            informe["productos_repetidos"] += 1
    return informe, None


def _importar_csv(sis, datos):
    informe = _informe_nuevo()
    for p in datos["productos"]:
        if grupo_consultar(sis, p["grupo"]) is None:
            grupo_crear(sis, p["grupo"], p["grupo"], registrar=False)
            informe["grupos_nuevos"] += 1
            informe["advertencias"].append("Se creó el grupo %s (sin nombre)." % p["grupo"])
        ids = []
        for nombre in p["autores"]:
            inv = _investigador_por_nombre(sis, nombre)
            if inv is None:
                inv, _ = investigador_crear(sis, nombre, registrar=False)
                informe["inv_nuevos"] += 1
            if inv["id"] not in ids:
                ids.append(inv["id"])
        if _producto_repetido(sis, p["grupo"], p["titulo"], p["anio"]) is not None:
            informe["productos_repetidos"] += 1
            continue
        _, error = producto_crear(sis, p["grupo"], p["titulo"], p["tipo"], p["anio"],
                                  p["categoria"], p["validado"], ids, registrar=False)
        if error:
            informe["advertencias"].append(error)
        else:
            informe["productos_nuevos"] += 1
    return informe, None


def importar_datos(sis, datos, modo=None, cod_grupo=None, encolar=True):
    """Devuelve (informe, error). 'modo' se conserva por compatibilidad: manda datos['modo']."""
    if datos["modo"] == "directorio_grupos":
        informe, error = _importar_directorio_grupos(sis, datos, encolar)
    elif datos["modo"] == "directorio_investigadores":
        informe, error = _importar_directorio_investigadores(sis, datos)
    elif datos["modo"] == "grupo":
        informe, error = _importar_grupo(sis, datos)
    elif datos["modo"] == "investigador":
        informe, error = _importar_investigador(sis, datos, cod_grupo)
    else:
        informe, error = _importar_csv(sis, datos)
    if error:
        return None, error
    informe["advertencias"] = list(datos["advertencias"]) + informe["advertencias"]
    return informe, None


def informe_texto(informe):
    lineas = ["IMPORTACIÓN COMPLETADA", ""]
    if informe["grupos_nuevos"] or informe["grupos_actualizados"]:
        lineas.append("• Grupos nuevos: %d  |  actualizados con datos de SCIENTI: %d"
                      % (informe["grupos_nuevos"], informe["grupos_actualizados"]))
    lineas.append("• Investigadores nuevos: %d" % informe["inv_nuevos"])
    if informe["inv_actualizados"]:
        lineas.append("• Investigadores a los que se completó el código CvLAC: %d"
                      % informe["inv_actualizados"])
    lineas.append("• Integrantes agregados: %d" % informe["integrantes_nuevos"])
    lineas.append("• Productos nuevos: %d" % informe["productos_nuevos"])
    lineas.append("• Productos ya existentes (omitidos): %d" % informe["productos_repetidos"])
    if informe["productos_actualizados"]:
        lineas.append("• Productos existentes a los que se agregó autor: %d"
                      % informe["productos_actualizados"])
    if informe["encolados"]:
        lineas.append("• Páginas de detalle agregadas a la COLA: %d" % informe["encolados"])
    if informe["sin_anio"]:
        lineas.append("• Productos omitidos por no tener año detectable: %d"
                      % informe["sin_anio"])
    if informe["advertencias"]:
        lineas.append("")
        lineas.append("Advertencias:")
        for a in informe["advertencias"][:10]:
            lineas.append("  ! " + a)
    lineas.append("")
    lineas.append("Nota: la importación no se puede deshacer con el historial.")
    return "\n".join(lineas)


# ==============================================================
# PARTE 3 - INTERFAZ GRÁFICA (TKINTER)
# ==============================================================
try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    from matplotlib.ticker import MaxNLocator
    HAY_MATPLOTLIB = True
except ImportError:
    HAY_MATPLOTLIB = False

# ----------------------------------------------------------
# Constantes de presentación (cambie aquí los colores institucionales)
# ----------------------------------------------------------
COLOR_PRIMARIO = "#14532D"
COLOR_ACENTO = "#16A34A"
COLOR_FONDO = "#F3F4F6"
COLORES_GRAFICA = ["#16A34A", "#2563EB", "#D97706", "#9333EA", "#DC2626", "#0891B2"]
ARCHIVO_LOGO = "logo_upc.png"          # opcional: PNG de ~60 px de alto junto al programa

TIPOS_PRODUCTO = ["Artículo", "Libro", "Capítulo de libro", "Software", "Proyecto",
                  "Trabajo de grado", "Patente", "Evento"]
CATEGORIAS_PRODUCTO = ["A1", "A2", "B", "C", "Sin categoría"]
CATEGORIAS_GRUPO = ["A1", "A", "B", "C", "Reconocido", "Sin categoría"]
CATEGORIAS_INVESTIGADOR = ["Investigador Senior", "Investigador Asociado",
                           "Investigador Junior", "Emérito", "Sin categoría"]
FORMACIONES = ["Pregrado", "Especialización", "Maestría", "Doctorado", "Posdoctorado"]
VINCULACIONES = ["Líder", "Investigador", "Joven investigador", "Estudiante",
                 "Colaborador", "Integrante"]
VENTANAS = ["Histórico completo", "Últimos 2 años", "Últimos 3 años",
            "Últimos 5 años", "Últimos 10 años", "Personalizado..."]
VISTAS = ["Global", "Por grupo", "Por investigador", "Por producto"]
CANCELADO = "CANCELADO"

# Estado global de la aplicación (equivale a las variables globales de un programa en C)
APP = {"sis": None, "ruta": "pea_i_datos.json", "sucio": False,
       "ventana_n": 0, "mensaje": ""}


# ==========================================================
# 1. UTILIDADES
# ==========================================================
def anio_actual():
    return datetime.now().year


def clave_de(texto):
    """'COL0001 - Nombre' -> 'COL0001'"""
    if texto is None:
        return None
    return texto.split(" - ")[0].strip()


def texto_ventana(n):
    return "Histórico completo" if n == 0 else "Últimos %d años" % n


def recortar(texto, largo=30):
    return texto if len(texto) <= largo else texto[:largo - 1] + "…"


def si_no(valor):
    return "Sí" if valor else "No"


def nombre_investigador(id_inv):
    inv = lista_buscar(APP["sis"]["investigadores"], "id", id_inv)
    return inv["nombre"] if inv is not None else id_inv


def texto_grupo(codigo):
    g = lista_buscar(APP["sis"]["grupos"], "codigo", codigo)
    return "%s - %s" % (codigo, g["nombre"]) if g is not None else codigo


def opciones_grupos(solo_activos=True):
    salida = []
    for g in lista_recorrer(APP["sis"]["grupos"], solo_activos):
        salida.append("%s - %s" % (g["codigo"], g["nombre"]))
    return salida


def opciones_investigadores(solo_activos=True):
    salida = []
    for i in lista_recorrer(APP["sis"]["investigadores"], solo_activos):
        salida.append("%s - %s" % (i["id"], i["nombre"]))
    return salida


def solo_cambios(nuevos, actual):
    """Devuelve únicamente los campos cuyo valor cambió (así el historial queda limpio)."""
    cambios = {}
    for k, v in nuevos.items():
        if isinstance(v, list):
            if sorted(v) != sorted(actual[k]):
                cambios[k] = v
        elif v != actual[k]:
            cambios[k] = v
    return cambios


def resolver(error, mensaje=""):
    """Muestra el error si lo hay; si no, marca cambios y refresca toda la pantalla."""
    if error:
        messagebox.showerror("No se pudo completar la operación", error,
                             parent=APP["raiz"])
        return False
    APP["mensaje"] = mensaje
    APP["sucio"] = True
    refrescar_todo()
    return True


# ==========================================================
# 2. COMPONENTES GENÉRICOS (tabla, botones, formulario)
# ==========================================================
def crear_tabla(padre, columnas):
    """columnas: lista de (clave, título, ancho). Devuelve (marco, tabla)."""
    marco = ttk.Frame(padre)
    claves = [c[0] for c in columnas]
    tabla = ttk.Treeview(marco, columns=claves, show="headings", selectmode="browse")
    for clave, titulo, ancho in columnas:
        tabla.heading(clave, text=titulo)
        tabla.column(clave, width=ancho, anchor="w")
    scroll = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=scroll.set)
    tabla.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    tabla.tag_configure("inactivo", foreground="#9CA3AF")
    return marco, tabla


def llenar_tabla(tabla, filas):
    """filas: lista de (iid, valores, inactivo). Conserva la selección si sigue existiendo."""
    seleccion = tabla.selection()
    previo = seleccion[0] if seleccion else None
    for iid in tabla.get_children():
        tabla.delete(iid)
    for iid, valores, inactivo in filas:
        etiquetas = ("inactivo",) if inactivo else ()
        tabla.insert("", "end", iid=str(iid), values=valores, tags=etiquetas)
    if previo is not None and tabla.exists(previo):
        tabla.selection_set(previo)


def exigir_seleccion(tabla, ventana=None):
    seleccion = tabla.selection()
    if not seleccion:
        messagebox.showinfo("Seleccione un registro",
                            "Primero seleccione un registro de la tabla.",
                            parent=ventana or APP["raiz"])
        return None
    return seleccion[0]


def barra_botones(padre, botones):
    """botones: lista de (texto, comando, destacado)."""
    barra = ttk.Frame(padre)
    for texto, comando, destacado in botones:
        estilo = "Accent.TButton" if destacado else "TButton"
        ttk.Button(barra, text=texto, command=comando, style=estilo).pack(
            side="left", padx=(0, 6))
    return barra


def dialogo_formulario(titulo, campos, valores=None):
    """Formulario modal genérico.
    campos: lista de dicts {clave, etiqueta, tipo, [opciones], [editable], [obligatorio], [defecto]}
    tipos: texto | entero | bool | combo | multi.  Devuelve dict o None si se cancela."""
    valores = valores or {}
    raiz = APP["raiz"]
    ventana = tk.Toplevel(raiz)
    ventana.title(titulo)
    ventana.configure(bg=COLOR_FONDO, padx=16, pady=14)
    ventana.transient(raiz)
    ventana.resizable(False, False)
    controles = {}

    for fila, c in enumerate(campos):
        etiqueta = c["etiqueta"] + (" *" if c.get("obligatorio") else "")
        ttk.Label(ventana, text=etiqueta).grid(row=fila, column=0, sticky="ne",
                                               padx=(0, 10), pady=4)
        tipo = c["tipo"]
        defecto = [] if tipo == "multi" else ""
        inicial = valores.get(c["clave"], c.get("defecto", defecto))
        if tipo in ("texto", "entero"):
            var = tk.StringVar(value=str(inicial))
            ttk.Entry(ventana, textvariable=var, width=46).grid(row=fila, column=1,
                                                                sticky="w", pady=4)
            controles[c["clave"]] = var
        elif tipo == "bool":
            var = tk.BooleanVar(value=bool(inicial))
            ttk.Checkbutton(ventana, variable=var).grid(row=fila, column=1,
                                                         sticky="w", pady=4)
            controles[c["clave"]] = var
        elif tipo == "combo":
            var = tk.StringVar(value=str(inicial))
            estado = "normal" if c.get("editable") else "readonly"
            ttk.Combobox(ventana, textvariable=var, values=c["opciones"], state=estado,
                         width=43).grid(row=fila, column=1, sticky="w", pady=4)
            controles[c["clave"]] = var
        elif tipo == "multi":
            lista = tk.Listbox(ventana, selectmode="multiple", exportselection=False,
                               height=6, width=46)
            for posicion, opcion in enumerate(c["opciones"]):
                lista.insert("end", opcion)
                if clave_de(opcion) in inicial:
                    lista.selection_set(posicion)
            lista.grid(row=fila, column=1, sticky="w", pady=4)
            controles[c["clave"]] = lista

    resultado = {"valores": None}

    def aceptar():
        salida = {}
        for c in campos:
            control = controles[c["clave"]]
            tipo = c["tipo"]
            if tipo == "multi":
                salida[c["clave"]] = [clave_de(c["opciones"][i])
                                      for i in control.curselection()]
                continue
            valor = control.get()
            if tipo in ("texto", "combo", "entero"):
                valor = valor.strip()
            if tipo == "entero":
                try:
                    valor = int(valor)
                except ValueError:
                    messagebox.showerror("Dato inválido",
                                         "«%s» debe ser un número entero." % c["etiqueta"],
                                         parent=ventana)
                    return
            if c.get("obligatorio") and valor in ("", None):
                messagebox.showerror("Dato obligatorio",
                                     "«%s» es obligatorio." % c["etiqueta"],
                                     parent=ventana)
                return
            salida[c["clave"]] = valor
        resultado["valores"] = salida
        ventana.destroy()

    fila_botones = ttk.Frame(ventana)
    fila_botones.grid(row=len(campos), column=0, columnspan=2, pady=(12, 0), sticky="e")
    ttk.Button(fila_botones, text="Cancelar", command=ventana.destroy).pack(
        side="right", padx=(6, 0))
    ttk.Button(fila_botones, text="Aceptar", style="Accent.TButton",
               command=aceptar).pack(side="right")
    ventana.bind("<Escape>", lambda e: ventana.destroy())
    ventana.wait_visibility()
    ventana.grab_set()
    raiz.wait_window(ventana)
    return resultado["valores"]


# ==========================================================
# 3. GRUPOS
# ==========================================================
def campos_grupo(con_codigo):
    campos = []
    if con_codigo:
        campos.append({"clave": "codigo", "etiqueta": "Código", "tipo": "texto",
                       "obligatorio": True})
    campos.append({"clave": "nombre", "etiqueta": "Nombre", "tipo": "texto",
                   "obligatorio": True})
    campos.append({"clave": "lider", "etiqueta": "Líder", "tipo": "texto"})
    campos.append({"clave": "categoria", "etiqueta": "Categoría", "tipo": "combo",
                   "opciones": CATEGORIAS_GRUPO, "editable": True,
                   "defecto": "Sin categoría"})
    campos.append({"clave": "url", "etiqueta": "URL GrupLAC", "tipo": "texto"})
    return campos


def accion_grupo_nuevo():
    v = dialogo_formulario("Nuevo grupo de investigación", campos_grupo(True))
    if v is None:
        return
    _, error = grupo_crear(APP["sis"], v["codigo"], v["nombre"], v["lider"] or "N/D",
                           v["categoria"] or "Sin categoría", v["url"])
    resolver(error, "Grupo %s creado" % v["codigo"])


def accion_grupo_editar():
    codigo = exigir_seleccion(APP["tabla_grupos"])
    if codigo is None:
        return
    g = grupo_consultar(APP["sis"], codigo)
    v = dialogo_formulario("Editar grupo %s" % codigo, campos_grupo(False), g)
    if v is None:
        return
    cambios = solo_cambios(v, g)
    if not cambios:
        messagebox.showinfo("Sin cambios", "No modificó ningún dato.", parent=APP["raiz"])
        return
    _, error = grupo_modificar(APP["sis"], codigo, cambios)
    resolver(error, "Grupo %s modificado" % codigo)


def accion_grupo_alternar():
    codigo = exigir_seleccion(APP["tabla_grupos"])
    if codigo is None:
        return
    activo_actual = grupo_consultar(APP["sis"], codigo)["activo"]
    _, error = grupo_desactivar(APP["sis"], codigo, not activo_actual)
    resolver(error, "Grupo %s %s" % (codigo, "desactivado" if activo_actual else "activado"))


def accion_grupo_eliminar():
    codigo = exigir_seleccion(APP["tabla_grupos"])
    if codigo is None:
        return
    if not messagebox.askyesno("Eliminar grupo",
                               "¿Eliminar definitivamente el grupo %s?" % codigo,
                               parent=APP["raiz"]):
        return
    _, error = grupo_eliminar(APP["sis"], codigo)
    resolver(error, "Grupo %s eliminado (puede deshacerlo)" % codigo)


def refrescar_grupos():
    filas = []
    ver_todo = APP["ver_inactivos"].get()
    for g in lista_recorrer(APP["sis"]["grupos"], solo_activos=not ver_todo):
        valores = (g["codigo"], g["nombre"], g["lider"], g["categoria"],
                   g["integrantes"]["tam"], g["productos"]["tam"], si_no(g["activo"]))
        filas.append((g["codigo"], valores, not g["activo"]))
    llenar_tabla(APP["tabla_grupos"], filas)


def abrir_integrantes():
    """Ventana de gestión de la sublista de integrantes de un grupo."""
    codigo = exigir_seleccion(APP["tabla_grupos"])
    if codigo is None:
        return
    g = grupo_consultar(APP["sis"], codigo)
    ventana = tk.Toplevel(APP["raiz"])
    ventana.title("Integrantes - %s" % g["nombre"])
    ventana.geometry("860x420")
    ventana.configure(bg=COLOR_FONDO)
    columnas = [("id", "ID", 90), ("nombre", "Nombre", 240), ("vinculacion", "Vinculación", 140),
                ("horas", "Horas", 70), ("periodo", "Periodo", 130), ("activo", "Activo", 60)]
    marco, tabla = crear_tabla(ventana, columnas)

    def llenar():
        filas = []
        for i in lista_recorrer(g["integrantes"]):
            valores = (i["id_investigador"], nombre_investigador(i["id_investigador"]),
                       i["vinculacion"], i["horas"], i["periodo"], si_no(i["activo"]))
            filas.append((i["id_investigador"], valores, not i["activo"]))
        llenar_tabla(tabla, filas)

    def terminar(error, mensaje):
        if resolver(error, mensaje):
            llenar()

    def agregar():
        opciones = opciones_investigadores()
        if not opciones:
            messagebox.showinfo("Sin investigadores", "Primero registre investigadores.",
                                parent=ventana)
            return
        campos = [{"clave": "inv", "etiqueta": "Investigador", "tipo": "combo",
                   "opciones": opciones, "obligatorio": True},
                  {"clave": "vinculacion", "etiqueta": "Vinculación", "tipo": "combo",
                   "opciones": VINCULACIONES, "editable": True, "defecto": "Integrante"},
                  {"clave": "horas", "etiqueta": "Horas dedicación", "tipo": "texto"},
                  {"clave": "periodo", "etiqueta": "Periodo", "tipo": "texto",
                   "defecto": "Actual"}]
        v = dialogo_formulario("Agregar integrante", campos)
        if v is None:
            return
        _, error = integrante_agregar(APP["sis"], codigo, clave_de(v["inv"]),
                                      v["vinculacion"] or "Integrante",
                                      v["horas"] or "N/D", v["periodo"] or "Actual")
        terminar(error, "Integrante agregado")

    def editar():
        id_inv = exigir_seleccion(tabla, ventana)
        if id_inv is None:
            return
        actual = integrante_consultar(APP["sis"], codigo, id_inv)
        campos = [{"clave": "vinculacion", "etiqueta": "Vinculación", "tipo": "combo",
                   "opciones": VINCULACIONES, "editable": True},
                  {"clave": "horas", "etiqueta": "Horas dedicación", "tipo": "texto"},
                  {"clave": "periodo", "etiqueta": "Periodo", "tipo": "texto"}]
        v = dialogo_formulario("Editar integrante", campos, actual)
        if v is None:
            return
        _, error = integrante_modificar(APP["sis"], codigo, id_inv, v)
        terminar(error, "Integrante modificado")

    def alternar():
        id_inv = exigir_seleccion(tabla, ventana)
        if id_inv is None:
            return
        activo = integrante_consultar(APP["sis"], codigo, id_inv)["activo"]
        _, error = integrante_desactivar(APP["sis"], codigo, id_inv, not activo)
        terminar(error, "Integrante %s" % ("desactivado" if activo else "activado"))

    def quitar():
        id_inv = exigir_seleccion(tabla, ventana)
        if id_inv is None:
            return
        if messagebox.askyesno("Quitar integrante", "¿Retirar a este integrante del grupo?",
                               parent=ventana):
            _, error = integrante_eliminar(APP["sis"], codigo, id_inv)
            terminar(error, "Integrante retirado")

    botones = barra_botones(ventana, [("Agregar", agregar, True), ("Editar", editar, False),
                                      ("Activar / Desactivar", alternar, False),
                                      ("Retirar del grupo", quitar, False)])
    botones.pack(fill="x", padx=10, pady=(10, 4))
    marco.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    llenar()


# ==========================================================
# 4. INVESTIGADORES
# ==========================================================
def campos_investigador():
    return [{"clave": "nombre", "etiqueta": "Nombre completo", "tipo": "texto",
             "obligatorio": True},
            {"clave": "cod_rh", "etiqueta": "Código CvLAC (cod_rh)", "tipo": "texto"},
            {"clave": "email", "etiqueta": "Correo", "tipo": "texto"},
            {"clave": "formacion", "etiqueta": "Formación", "tipo": "combo",
             "opciones": FORMACIONES, "editable": True},
            {"clave": "categoria", "etiqueta": "Categoría", "tipo": "combo",
             "opciones": CATEGORIAS_INVESTIGADOR, "editable": True,
             "defecto": "Sin categoría"}]


def accion_inv_nuevo():
    v = dialogo_formulario("Nuevo investigador", campos_investigador())
    if v is None:
        return
    _, error = investigador_crear(APP["sis"], v["nombre"], v["cod_rh"], v["email"],
                                  v["formacion"], v["categoria"] or "Sin categoría")
    resolver(error, "Investigador %s creado" % v["nombre"])


def accion_inv_editar():
    id_inv = exigir_seleccion(APP["tabla_inv"])
    if id_inv is None:
        return
    inv = investigador_consultar(APP["sis"], id_inv)
    v = dialogo_formulario("Editar investigador %s" % id_inv, campos_investigador(), inv)
    if v is None:
        return
    cambios = solo_cambios(v, inv)
    if not cambios:
        messagebox.showinfo("Sin cambios", "No modificó ningún dato.", parent=APP["raiz"])
        return
    _, error = investigador_modificar(APP["sis"], id_inv, cambios)
    resolver(error, "Investigador %s modificado" % id_inv)


def accion_inv_alternar():
    id_inv = exigir_seleccion(APP["tabla_inv"])
    if id_inv is None:
        return
    activo = investigador_consultar(APP["sis"], id_inv)["activo"]
    _, error = investigador_desactivar(APP["sis"], id_inv, not activo)
    resolver(error, "Investigador %s %s" % (id_inv, "desactivado" if activo else "activado"))


def accion_inv_eliminar():
    id_inv = exigir_seleccion(APP["tabla_inv"])
    if id_inv is None:
        return
    if not messagebox.askyesno("Eliminar investigador",
                               "¿Eliminar definitivamente a %s?" % id_inv,
                               parent=APP["raiz"]):
        return
    _, error = investigador_eliminar(APP["sis"], id_inv)
    resolver(error, "Investigador %s eliminado (puede deshacerlo)" % id_inv)


def accion_inv_ver_productos():
    id_inv = exigir_seleccion(APP["tabla_inv"])
    if id_inv is None:
        return
    for texto in opciones_investigadores(False):
        if clave_de(texto) == id_inv:
            APP["f_inv"].set(texto)
    APP["f_grupo"].set("Todos")
    APP["f_tipo"].set("Todos")
    APP["tabs"].select(APP["tab_productos"])
    refrescar_productos()


def refrescar_investigadores():
    filas = []
    ver_todo = APP["ver_inactivos"].get()
    for i in lista_recorrer(APP["sis"]["investigadores"], solo_activos=not ver_todo):
        valores = (i["id"], i["nombre"], i["cod_rh"], i["email"], i["formacion"],
                   i["categoria"], i["productos"]["tam"], si_no(i["activo"]))
        filas.append((i["id"], valores, not i["activo"]))
    llenar_tabla(APP["tabla_inv"], filas)


# ==========================================================
# 5. PRODUCTOS
# ==========================================================
def campos_producto(solo_activos):
    return [{"clave": "grupo", "etiqueta": "Grupo", "tipo": "combo",
             "opciones": opciones_grupos(solo_activos), "obligatorio": True},
            {"clave": "titulo", "etiqueta": "Título", "tipo": "texto", "obligatorio": True},
            {"clave": "tipo", "etiqueta": "Tipo", "tipo": "combo",
             "opciones": TIPOS_PRODUCTO, "editable": True, "obligatorio": True},
            {"clave": "categoria", "etiqueta": "Categoría", "tipo": "combo",
             "opciones": CATEGORIAS_PRODUCTO, "editable": True,
             "defecto": "Sin categoría"},
            {"clave": "anio", "etiqueta": "Año", "tipo": "entero", "obligatorio": True,
             "defecto": anio_actual()},
            {"clave": "validado", "etiqueta": "Validado", "tipo": "bool"},
            {"clave": "investigadores", "etiqueta": "Autores", "tipo": "multi",
             "opciones": opciones_investigadores(solo_activos)}]


def accion_prod_nuevo():
    if not opciones_grupos():
        messagebox.showinfo("Sin grupos", "Primero cree un grupo de investigación.",
                            parent=APP["raiz"])
        return
    v = dialogo_formulario("Nuevo producto de investigación", campos_producto(True))
    if v is None:
        return
    _, error = producto_crear(APP["sis"], clave_de(v["grupo"]), v["titulo"], v["tipo"],
                              v["anio"], v["categoria"] or "Sin categoría", v["validado"],
                              v["investigadores"])
    resolver(error, "Producto creado")


def accion_prod_editar():
    id_prod = exigir_seleccion(APP["tabla_prod"])
    if id_prod is None:
        return
    p = producto_consultar(APP["sis"], id_prod)
    valores = dict(p)
    valores["grupo"] = texto_grupo(p["grupo"])
    v = dialogo_formulario("Editar producto %s" % id_prod, campos_producto(False), valores)
    if v is None:
        return
    v["grupo"] = clave_de(v["grupo"])
    cambios = solo_cambios(v, p)
    if not cambios:
        messagebox.showinfo("Sin cambios", "No modificó ningún dato.", parent=APP["raiz"])
        return
    _, error = producto_modificar(APP["sis"], id_prod, cambios)
    resolver(error, "Producto %s modificado" % id_prod)


def accion_prod_validar():
    id_prod = exigir_seleccion(APP["tabla_prod"])
    if id_prod is None:
        return
    validado = producto_consultar(APP["sis"], id_prod)["validado"]
    _, error = producto_validar(APP["sis"], id_prod, not validado)
    resolver(error, "Producto %s %s" % (id_prod, "marcado como no validado" if validado
                                        else "validado"))


def accion_prod_alternar():
    id_prod = exigir_seleccion(APP["tabla_prod"])
    if id_prod is None:
        return
    activo = producto_consultar(APP["sis"], id_prod)["activo"]
    _, error = producto_desactivar(APP["sis"], id_prod, not activo)
    resolver(error, "Producto %s %s" % (id_prod, "desactivado" if activo else "activado"))


def accion_prod_eliminar():
    id_prod = exigir_seleccion(APP["tabla_prod"])
    if id_prod is None:
        return
    if not messagebox.askyesno("Eliminar producto",
                               "¿Eliminar definitivamente el producto %s?" % id_prod,
                               parent=APP["raiz"]):
        return
    _, error = producto_eliminar(APP["sis"], id_prod)
    resolver(error, "Producto %s eliminado (puede deshacerlo)" % id_prod)


def filtros_productos():
    f = ventana_anios(APP["ventana_n"], anio_actual())
    if APP["f_grupo"].get() not in ("", "Todos"):
        f["grupo"] = clave_de(APP["f_grupo"].get())
    if APP["f_inv"].get() not in ("", "Todos"):
        f["investigador"] = clave_de(APP["f_inv"].get())
    if APP["f_tipo"].get() not in ("", "Todos"):
        f["tipo"] = APP["f_tipo"].get()
    f["solo_validados"] = APP["f_validados"].get()
    f["solo_activos"] = not APP["ver_inactivos"].get()
    return f


def limpiar_filtros_productos():
    APP["f_grupo"].set("Todos")
    APP["f_inv"].set("Todos")
    APP["f_tipo"].set("Todos")
    APP["f_validados"].set(False)
    refrescar_productos()


def refrescar_filtros_productos():
    tipos = list(TIPOS_PRODUCTO)
    for p in lista_recorrer(APP["sis"]["productos"]):
        if p["tipo"] not in tipos:
            tipos.append(p["tipo"])
    conjuntos = [("f_grupo", ["Todos"] + opciones_grupos(False)),
                 ("f_inv", ["Todos"] + opciones_investigadores(False)),
                 ("f_tipo", ["Todos"] + tipos)]
    for clave, valores in conjuntos:
        APP["cb_" + clave]["values"] = valores
        if APP[clave].get() not in valores:
            APP[clave].set("Todos")


def refrescar_productos():
    productos = cubo_consultar(APP["sis"]["cubo"], **filtros_productos())
    productos.sort(key=lambda p: p["id"])
    filas = []
    for p in productos:
        autores = ", ".join([nombre_investigador(i) for i in p["investigadores"]])
        valores = (p["id"], p["titulo"], p["tipo"], p["categoria"], p["anio"],
                   si_no(p["validado"]), p["grupo"], autores or "N/D", si_no(p["activo"]))
        filas.append((p["id"], valores, not p["activo"]))
    llenar_tabla(APP["tabla_prod"], filas)


# ==========================================================
# 6. ESTADÍSTICAS (dashboard sobre el hipercubo)
# ==========================================================
def filtros_dashboard():
    f = ventana_anios(APP["ventana_n"], anio_actual())
    vista = APP["vista"].get()
    seleccion = APP["vista_sel"].get()
    if vista == "Por grupo" and seleccion:
        f["grupo"] = clave_de(seleccion)
    elif vista == "Por investigador" and seleccion:
        f["investigador"] = clave_de(seleccion)
    elif vista == "Por producto" and seleccion and seleccion != "Todos los tipos":
        f["tipo"] = seleccion
    return f


def actualizar_selector_vista():
    vista = APP["vista"].get()
    combo = APP["cb_vista_sel"]
    if vista == "Por grupo":
        valores = opciones_grupos(False)
    elif vista == "Por investigador":
        valores = opciones_investigadores(False)
    elif vista == "Por producto":
        valores = ["Todos los tipos"] + sorted(cubo_resumen(APP["sis"]["cubo"],
                                                             "tipo").keys())
    else:
        valores = []
    combo["values"] = valores
    if not valores:
        APP["vista_sel"].set("")
        combo.configure(state="disabled")
    else:
        combo.configure(state="readonly")
        if APP["vista_sel"].get() not in valores:
            APP["vista_sel"].set(valores[0])


def etiqueta_dimension(dimension, valor):
    if dimension == "grupo":
        g = lista_buscar(APP["sis"]["grupos"], "codigo", valor)
        return recortar(g["nombre"] if g is not None else str(valor))
    if dimension == "investigador":
        if valor == "N/D":
            return "N/D"
        return recortar(nombre_investigador(valor))
    return str(valor)


def dibujar_panel(eje, dimension, titulo, est, indice):
    color = COLORES_GRAFICA[indice % len(COLORES_GRAFICA)]
    if dimension == "validacion":
        datos = {"Validados": est["validados"],
                 "No validados": est["total"] - est["validados"]}
    else:
        datos = est["por_" + dimension]
    eje.set_title(titulo, fontsize=10, fontweight="bold", color=COLOR_PRIMARIO)
    if not datos or sum(datos.values()) == 0:
        eje.text(0.5, 0.5, "Sin datos", ha="center", va="center",
                 transform=eje.transAxes, color="#6B7280")
        eje.set_xticks([])
        eje.set_yticks([])
        return
    if dimension == "anio":
        datos = {a: datos.get(a, 0) for a in range(min(datos), max(datos) + 1)}
        etiquetas = [str(a) for a in datos]
        barras = eje.bar(etiquetas, list(datos.values()), color=color)
        eje.tick_params(axis="x", labelsize=8)
        eje.yaxis.set_major_locator(MaxNLocator(integer=True))
    elif dimension in ("grupo", "investigador"):
        ordenados = sorted(datos.items(), key=lambda kv: kv[1], reverse=True)[:8]
        etiquetas = [etiqueta_dimension(dimension, k) for k, _ in ordenados]
        valores = [v for _, v in ordenados]
        barras = eje.barh(etiquetas[::-1], valores[::-1], color=color)
        eje.tick_params(axis="y", labelsize=8)
        eje.xaxis.set_major_locator(MaxNLocator(integer=True))
    else:
        ordenados = sorted(datos.items(), key=lambda kv: kv[1], reverse=True)
        if len(ordenados) > 8:
            resto = sum([v for _, v in ordenados[7:]])
            ordenados = ordenados[:7] + [("Otros", resto)]
        etiquetas = [recortar(str(k), 22) for k, _ in ordenados]
        valores = [v for _, v in ordenados]
        barras = eje.bar(etiquetas, valores, color=color)
        rotacion = 20 if len(etiquetas) > 3 else 0
        eje.tick_params(axis="x", labelsize=8, labelrotation=rotacion)
        eje.yaxis.set_major_locator(MaxNLocator(integer=True))
    eje.bar_label(barras, padding=2, fontsize=8)
    eje.spines["top"].set_visible(False)
    eje.spines["right"].set_visible(False)


PANELES = {
    "Global": [("anio", "Productos por año (histograma)"), ("tipo", "Por tipo"),
               ("categoria", "Por categoría"), ("grupo", "Por grupo")],
    "Por grupo": [("anio", "Productos por año (histograma)"), ("tipo", "Por tipo"),
                  ("categoria", "Por categoría"), ("investigador", "Por investigador")],
    "Por investigador": [("anio", "Productos por año (histograma)"), ("tipo", "Por tipo"),
                         ("categoria", "Por categoría"), ("grupo", "Por grupo")],
    "Por producto": [("anio", "Productos por año (histograma)"),
                     ("categoria", "Por categoría"), ("grupo", "Por grupo"),
                     ("validacion", "Validación")],
}


def refrescar_dashboard():
    actualizar_selector_vista()
    f = filtros_dashboard()
    est = estadisticas(APP["sis"], **f)
    grupos_activos = len(lista_recorrer(APP["sis"]["grupos"], True))
    inv_activos = len(lista_recorrer(APP["sis"]["investigadores"], True))
    APP["lbl_resumen"].config(
        text="Productos: %d   |   Validados: %d   |   Ventana: %s   |   "
             "Grupos activos: %d   |   Investigadores activos: %d"
             % (est["total"], est["validados"], texto_ventana(APP["ventana_n"]),
                grupos_activos, inv_activos))
    if not HAY_MATPLOTLIB:
        return
    fig = APP["fig"]
    fig.clear()
    for indice, (dimension, titulo) in enumerate(PANELES[APP["vista"].get()]):
        eje = fig.add_subplot(2, 2, indice + 1)
        dibujar_panel(eje, dimension, titulo, est, indice)
    fig.tight_layout(pad=2.0)
    APP["canvas"].draw()


# ==========================================================
# 7. COLA (importaciones) y PILA (historial)
# ==========================================================
def pila_a_arreglo(pila):
    salida = []
    nodo = pila["tope"]
    while nodo is not None:
        salida.append(nodo["dato"])
        nodo = nodo["sig"]
    return salida


def accion_encolar_url():
    url = simpledialog.askstring("Importar desde URL",
                                 "Pegue la URL de GrupLAC o CvLAC:", parent=APP["raiz"])
    if url and url.strip():
        importacion_encolar(APP["sis"], "url", url.strip())
        resolver(None, "URL agregada a la cola de importaciones")


def accion_encolar_archivo():
    ruta = filedialog.askopenfilename(title="Seleccione un archivo CSV o PDF",
                                      filetypes=[("CSV o PDF", "*.csv *.pdf"),
                                                 ("CSV", "*.csv"), ("PDF", "*.pdf")])
    if ruta:
        tipo = "pdf" if ruta.lower().endswith(".pdf") else "csv"
        importacion_encolar(APP["sis"], tipo, ruta)
        resolver(None, "Archivo agregado a la cola de importaciones")


def accion_cola_editar():
    item = cola_frente(APP["sis"]["importaciones"])
    if item is None:
        messagebox.showinfo("Cola vacía", "No hay importaciones pendientes.",
                            parent=APP["raiz"])
        return
    nuevo = simpledialog.askstring("Editar origen", "Nuevo origen para el primero de la cola:",
                                   initialvalue=item["origen"], parent=APP["raiz"])
    if nuevo and nuevo.strip():
        cola_modificar_frente(APP["sis"]["importaciones"], {"origen": nuevo.strip()})
        resolver(None, "Origen modificado")


def accion_cola_quitar():
    if cola_vacia(APP["sis"]["importaciones"]):
        messagebox.showinfo("Cola vacía", "No hay importaciones pendientes.",
                            parent=APP["raiz"])
        return
    if messagebox.askyesno("Quitar de la cola", "¿Quitar el primero de la cola?",
                           parent=APP["raiz"]):
        cola_desencolar(APP["sis"]["importaciones"])
        resolver(None, "Importación retirada de la cola")


def mostrar_texto(titulo, texto):
    """Ventana con texto seleccionable y botón para copiarlo."""
    ventana = tk.Toplevel(APP["raiz"])
    ventana.title(titulo)
    ventana.geometry("920x580")
    ventana.configure(bg=COLOR_FONDO)

    def copiar():
        ventana.clipboard_clear()
        ventana.clipboard_append(texto)

    barra = ttk.Frame(ventana)
    barra.pack(fill="x", padx=10, pady=(10, 4))
    ttk.Button(barra, text="Copiar todo", style="Accent.TButton", command=copiar).pack(
        side="left")
    cuerpo = ttk.Frame(ventana)
    cuerpo.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    caja = tk.Text(cuerpo, wrap="word", font=("Consolas", 10))
    scroll = ttk.Scrollbar(cuerpo, orient="vertical", command=caja.yview)
    caja.configure(yscrollcommand=scroll.set)
    caja.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    caja.insert("1.0", texto)
    caja.configure(state="disabled")


def tipo_por_extension(ruta):
    ruta = ruta.lower()
    if ruta.endswith(".csv"):
        return "csv"
    if ruta.endswith(".pdf"):
        return "pdf"
    return "html"


def leer_con_modo(tipo, origen, item):
    """Lee la fuente; si no reconoce el tipo de página, pregunta al usuario."""
    datos, error = leer_origen(tipo, origen, "auto", item)
    if error != MODO_NO_DETECTADO:
        return datos, error
    campos = [{"clave": "modo", "etiqueta": "Contenido", "tipo": "combo",
               "opciones": ["Un grupo (GrupLAC)", "Un investigador (CvLAC)"],
               "obligatorio": True}]
    v = dialogo_formulario("¿Qué contiene esta fuente?", campos)
    if v is None:
        return None, CANCELADO
    modo = "grupo" if v["modo"].startswith("Un grupo") else "investigador"
    return leer_origen(tipo, origen, modo, item)


def importar_origen(tipo, origen, item=None, confirmar=True):
    """Flujo completo: leer -> vista previa -> importar.
    Devuelve 'ok', 'cancelado' o 'error: mensaje'."""
    raiz = APP["raiz"]
    raiz.config(cursor="watch")
    raiz.update_idletasks()
    datos, error = leer_con_modo(tipo, origen, item)
    raiz.config(cursor="")
    if error == CANCELADO:
        return "cancelado"
    if error:
        if confirmar:
            messagebox.showerror("No se pudo leer la fuente", error, parent=raiz)
        return "error: " + error.splitlines()[0]
    cod_grupo = None
    if datos["modo"] == "investigador":
        opciones = opciones_grupos()
        if not opciones:
            messagebox.showinfo("Sin grupos", "Primero cree o importe un grupo para "
                                "asociar los productos del investigador.", parent=raiz)
            return "cancelado"
        campos = [{"clave": "grupo", "etiqueta": "Asociar productos al grupo",
                   "tipo": "combo", "opciones": opciones, "obligatorio": True}]
        v = dialogo_formulario("Grupo del investigador", campos)
        if v is None:
            return "cancelado"
        cod_grupo = clave_de(v["grupo"])
    if confirmar and not messagebox.askyesno(
            "Vista previa de la importación",
            describir_datos(datos) + "\n\n¿Importar estos datos?", parent=raiz):
        return "cancelado"
    informe, error = importar_datos(APP["sis"], datos, None, cod_grupo)
    if error:
        if confirmar:
            messagebox.showerror("No se pudo importar", error, parent=raiz)
        return "error: " + error.splitlines()[0]
    if confirmar:
        mostrar_texto("Resultado de la importación", informe_texto(informe))
    return "ok"


def accion_importar_url():
    url = simpledialog.askstring("Importar desde URL",
                                 "Pegue la URL de SCIENTI (listado, GrupLAC o CvLAC):",
                                 parent=APP["raiz"])
    if url and url.strip():
        estado = importar_origen("url", url.strip())
        resolver(None, "Importación completada" if estado == "ok" else "")


def accion_importar_archivo():
    ruta = filedialog.askopenfilename(
        title="Importar desde archivo",
        filetypes=[("HTML, PDF o CSV", "*.html *.htm *.pdf *.csv"), ("Todos", "*.*")])
    if ruta:
        estado = importar_origen(tipo_por_extension(ruta), ruta)
        resolver(None, "Importación completada" if estado == "ok" else "")


def accion_diagnostico_url():
    url = simpledialog.askstring("Diagnóstico", "Pegue la URL a diagnosticar:",
                                 parent=APP["raiz"])
    if url and url.strip():
        APP["raiz"].config(cursor="watch")
        APP["raiz"].update_idletasks()
        informe = diagnosticar_origen("url", url.strip())
        APP["raiz"].config(cursor="")
        mostrar_texto("Diagnóstico de la fuente", informe)


def accion_diagnostico_archivo():
    ruta = filedialog.askopenfilename(title="Archivo a diagnosticar",
                                      filetypes=[("HTML o PDF", "*.html *.htm *.pdf")])
    if ruta:
        mostrar_texto("Diagnóstico de la fuente",
                      diagnosticar_origen(tipo_por_extension(ruta), ruta))


def accion_plantilla_csv():
    ruta = filedialog.asksaveasfilename(title="Guardar plantilla CSV",
                                        defaultextension=".csv",
                                        initialfile="plantilla_productos.csv",
                                        filetypes=[("CSV", "*.csv")])
    if ruta:
        error = crear_plantilla_csv(ruta)
        if error:
            messagebox.showerror("Plantilla", error, parent=APP["raiz"])
        else:
            messagebox.showinfo("Plantilla creada", "Plantilla guardada en:\n" + ruta,
                                parent=APP["raiz"])


def accion_cola_procesar():
    cola = APP["sis"]["importaciones"]
    item = cola_frente(cola)
    if item is None:
        messagebox.showinfo("Cola vacía", "No hay importaciones pendientes.",
                            parent=APP["raiz"])
        return
    estado = importar_origen(item["tipo"], item["origen"], item, True)
    if estado == "ok":
        cola_desencolar(cola)
        resolver(None, "Importación procesada y retirada de la cola")
    elif estado.startswith("error"):
        fallido = cola_desencolar(cola)          # pasa al final para no bloquear la cola
        fallido["estado"] = estado[:60]
        cola_encolar(cola, fallido)
        resolver(None, "La importación falló y pasó al final de la cola")
    else:
        refrescar_todo()


def accion_cola_procesar_todo():
    cola = APP["sis"]["importaciones"]
    if cola_vacia(cola):
        messagebox.showinfo("Cola vacía", "No hay importaciones pendientes.",
                            parent=APP["raiz"])
        return
    total = cola["tam"]
    if not messagebox.askyesno(
            "Procesar toda la cola",
            "Se procesarán %d importaciones de una en una, con una pausa de 2 segundos "
            "entre cada una para no saturar el servidor de SCIENTI.\n\n¿Continuar?" % total,
            parent=APP["raiz"]):
        return
    fallidas = []
    correctas = 0
    for numero in range(total):
        item = cola_desencolar(cola)
        APP["mensaje"] = "Importando %d de %d: %s" % (numero + 1, total,
                                                      item.get("codigo", item["origen"]))
        actualizar_estado()
        APP["raiz"].update()
        estado = importar_origen(item["tipo"], item["origen"], item, False)
        if estado == "ok":
            correctas += 1
        else:
            item["estado"] = estado[:60]
            fallidas.append(item)
        time.sleep(2)
    for item in fallidas:
        cola_encolar(cola, item)
    resolver(None, "Cola procesada: %d correctas, %d con error (siguen en la cola)"
             % (correctas, len(fallidas)))


def refrescar_cola_pila():
    filas = []
    for posicion, item in enumerate(cola_recorrer(APP["sis"]["importaciones"]), 1):
        filas.append((posicion, (posicion, item["tipo"].upper(), item.get("codigo", ""),
                                 item["origen"], item["estado"]), False))
    llenar_tabla(APP["tabla_cola"], filas)
    lista = APP["lista_pila"]
    lista.delete(0, "end")
    for posicion, op in enumerate(pila_a_arreglo(APP["sis"]["historial"]), 1):
        marca = "▶ " if posicion == 1 else "   "
        lista.insert("end", "%s%d. %s %s %s" % (marca, posicion, op["op"], op["ent"],
                                                op["clave"]))


def accion_deshacer():
    if pila_vacia(APP["sis"]["historial"]):
        messagebox.showinfo("Deshacer", "No hay operaciones para deshacer.",
                            parent=APP["raiz"])
        return
    mensaje = deshacer(APP["sis"])
    resolver(None, mensaje)


# ==========================================================
# 8. ARCHIVO (persistencia y datos de ejemplo)
# ==========================================================
def confirmar_perdida():
    if not APP["sucio"]:
        return True
    return messagebox.askyesno("Cambios sin guardar",
                               "Hay cambios sin guardar que se perderán. ¿Continuar?",
                               parent=APP["raiz"])


def nuevo_vacio():
    if not confirmar_perdida():
        return
    APP["sis"] = sistema_crear()
    APP["sucio"] = False
    resolver(None, "Sistema iniciado sin datos")
    APP["sucio"] = False
    actualizar_estado()


def abrir_archivo():
    if not confirmar_perdida():
        return
    ruta = filedialog.askopenfilename(title="Abrir datos de PEA-i",
                                      filetypes=[("JSON", "*.json")])
    if not ruta:
        return
    sis, avisos, error = cargar_json(ruta)
    if error:
        messagebox.showerror("No se pudo abrir", error, parent=APP["raiz"])
        return
    APP["sis"] = sis
    APP["ruta"] = ruta
    resolver(None, "Datos cargados desde %s" % os.path.basename(ruta))
    APP["sucio"] = False
    actualizar_estado()
    if avisos:
        messagebox.showwarning("Datos omitidos", "\n".join(avisos), parent=APP["raiz"])


def guardar():
    error = guardar_json(APP["sis"], APP["ruta"])
    if error:
        messagebox.showerror("No se pudo guardar", error, parent=APP["raiz"])
        return False
    APP["sucio"] = False
    APP["mensaje"] = "Guardado en %s" % os.path.abspath(APP["ruta"])
    actualizar_estado()
    return True


def guardar_como():
    ruta = filedialog.asksaveasfilename(title="Guardar datos de PEA-i",
                                        defaultextension=".json",
                                        filetypes=[("JSON", "*.json")])
    if ruta:
        APP["ruta"] = ruta
        guardar()


def poblar_ejemplo(sis):
    """Datos ficticios para probar y para la demostración en video."""
    rnd = random.Random(2026)
    grupos = [("COL0001", "Grupo de Ejemplo - Sistemas", "Ana Pérez", "A"),
              ("COL0002", "Grupo de Ejemplo - Energía", "Luis Gómez", "B"),
              ("COL0003", "Grupo de Ejemplo - Salud", "Marta Rojas", "C")]
    nombres = ["Ana Pérez", "Luis Gómez", "Eva Mora", "Carlos Díaz", "Marta Rojas",
               "Pablo Núñez"]
    for codigo, nombre, lider, categoria in grupos:
        grupo_crear(sis, codigo, nombre, lider, categoria)
    ids = []
    for nombre in nombres:
        inv, _ = investigador_crear(sis, nombre, "", "", rnd.choice(FORMACIONES),
                                    rnd.choice(CATEGORIAS_INVESTIGADOR))
        ids.append(inv["id"])
    equipos = {"COL0001": [0, 1, 2], "COL0002": [2, 3, 4], "COL0003": [4, 5, 0]}
    for codigo, posiciones in equipos.items():
        for p in posiciones:
            integrante_agregar(sis, codigo, ids[p], "Investigador")
    for k in range(32):
        codigo = rnd.choice(list(equipos.keys()))
        miembros = [ids[p] for p in equipos[codigo]]
        autores = rnd.sample(miembros, rnd.randint(1, 2))
        producto_crear(sis, codigo, "Producto de ejemplo %02d" % (k + 1),
                       rnd.choice(TIPOS_PRODUCTO[:5]), rnd.randint(2019, anio_actual()),
                       rnd.choice(["A1", "A2", "B", "C"]), rnd.random() < 0.7, autores)
    sis["historial"] = pila_crear()      # el ejemplo no debe poder deshacerse


def cargar_ejemplo():
    if lista_recorrer(APP["sis"]["grupos"]) and not messagebox.askyesno(
            "Datos de ejemplo", "Se reemplazarán los datos actuales por datos de ejemplo. "
                                "¿Continuar?", parent=APP["raiz"]):
        return
    APP["sis"] = sistema_crear()
    poblar_ejemplo(APP["sis"])
    resolver(None, "Datos de ejemplo cargados")


def cerrar_app():
    if APP["sucio"]:
        respuesta = messagebox.askyesnocancel("Salir", "¿Desea guardar los cambios antes "
                                                       "de salir?", parent=APP["raiz"])
        if respuesta is None:
            return
        if respuesta and not guardar():
            return
    APP["raiz"].destroy()


def preguntar_inicio():
    texto = ("¿Desea cargar los datos desde un archivo?\n\n"
             "Sí: elegir un archivo JSON guardado.\nNo: iniciar sin datos.")
    if messagebox.askyesno("PEA-i - Inicio", texto, parent=APP["raiz"]):
        abrir_archivo()


# ==========================================================
# 9. REFRESCO GENERAL Y BARRA DE ESTADO
# ==========================================================
def actualizar_estado():
    sis = APP["sis"]
    conteos = ("Grupos: %d  |  Investigadores: %d  |  Productos: %d  |  "
               "Historial (pila): %d  |  Cola: %d"
               % (sis["grupos"]["tam"], sis["investigadores"]["tam"],
                  sis["productos"]["tam"], sis["historial"]["tam"],
                  sis["importaciones"]["tam"]))
    prefijo = APP["mensaje"] + "      •      " if APP["mensaje"] else ""
    APP["estado"].set(prefijo + conteos)
    APP["raiz"].title("PEA-i - Universidad Popular del Cesar" +
                      (" *" if APP["sucio"] else ""))


def refrescar_todo():
    refrescar_grupos()
    refrescar_investigadores()
    refrescar_filtros_productos()
    refrescar_productos()
    refrescar_cola_pila()
    refrescar_dashboard()
    actualizar_estado()


def cambiar_ventana():
    texto = APP["ventana_txt"].get()
    if texto == "Histórico completo":
        n = 0
    elif texto == "Personalizado...":
        n = simpledialog.askinteger("Ventana de observación",
                                    "¿Cuántos años hacia atrás? (incluye el año actual)",
                                    parent=APP["raiz"], minvalue=1, maxvalue=100)
        if n is None:
            APP["ventana_txt"].set(texto_ventana(APP["ventana_n"]))
            return
        APP["ventana_txt"].set(texto_ventana(n))
    else:
        n = int(texto.split()[1])
    APP["ventana_n"] = n
    APP["mensaje"] = "Ventana de observación: %s" % texto_ventana(n)
    refrescar_todo()


# ==========================================================
# 10. CONSTRUCCIÓN DE LA INTERFAZ
# ==========================================================
def construir_estilo():
    estilo = ttk.Style()
    estilo.theme_use("clam")
    estilo.configure(".", background=COLOR_FONDO, font=("Segoe UI", 10))
    estilo.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
    estilo.configure("Treeview.Heading", background=COLOR_PRIMARIO, foreground="white",
                     font=("Segoe UI", 10, "bold"))
    estilo.map("Treeview", background=[("selected", COLOR_ACENTO)],
               foreground=[("selected", "white")])
    estilo.configure("Accent.TButton", background=COLOR_ACENTO, foreground="white")
    estilo.map("Accent.TButton", background=[("active", COLOR_PRIMARIO)])
    estilo.configure("TNotebook.Tab", padding=(16, 7), font=("Segoe UI", 10, "bold"))


def construir_menu():
    raiz = APP["raiz"]
    menu = tk.Menu(raiz)
    archivo = tk.Menu(menu, tearoff=0)
    archivo.add_command(label="Nuevo (sin datos)", command=nuevo_vacio)
    archivo.add_command(label="Abrir datos...", command=abrir_archivo)
    archivo.add_command(label="Guardar", command=guardar, accelerator="Ctrl+S")
    archivo.add_command(label="Guardar como...", command=guardar_como)
    archivo.add_separator()
    archivo.add_command(label="Cargar datos de ejemplo", command=cargar_ejemplo)
    archivo.add_separator()
    archivo.add_command(label="Salir", command=cerrar_app)
    menu.add_cascade(label="Archivo", menu=archivo)
    importar = tk.Menu(menu, tearoff=0)
    importar.add_command(label="Desde URL de SCIENTI...", command=accion_importar_url)
    importar.add_command(label="Desde archivo (HTML / PDF / CSV)...",
                         command=accion_importar_archivo)
    importar.add_separator()
    importar.add_command(label="Diagnóstico de una URL...", command=accion_diagnostico_url)
    importar.add_command(label="Diagnóstico de un archivo...",
                         command=accion_diagnostico_archivo)
    importar.add_separator()
    importar.add_command(label="Crear plantilla CSV...", command=accion_plantilla_csv)
    menu.add_cascade(label="Importar", menu=importar)
    edicion = tk.Menu(menu, tearoff=0)
    edicion.add_command(label="Deshacer", command=accion_deshacer, accelerator="Ctrl+Z")
    menu.add_cascade(label="Edición", menu=edicion)
    raiz.config(menu=menu)
    raiz.bind("<Control-s>", lambda e: guardar())
    raiz.bind("<Control-z>", lambda e: accion_deshacer())


def construir_encabezado():
    marco = tk.Frame(APP["raiz"], bg=COLOR_PRIMARIO)
    marco.pack(fill="x")
    if os.path.exists(ARCHIVO_LOGO):
        try:
            APP["logo"] = tk.PhotoImage(file=ARCHIVO_LOGO)
            tk.Label(marco, image=APP["logo"], bg=COLOR_PRIMARIO).pack(side="left",
                                                                      padx=(14, 6), pady=6)
        except tk.TclError:
            pass
    textos = tk.Frame(marco, bg=COLOR_PRIMARIO)
    textos.pack(side="left", padx=14, pady=8)
    tk.Label(textos, text="Universidad Popular del Cesar", bg=COLOR_PRIMARIO, fg="white",
             font=("Segoe UI", 15, "bold")).pack(anchor="w")
    tk.Label(textos, text="PEA-i · Programa Estadístico de Análisis de Investigación  |  "
                          "Ingeniería de Sistemas · Estructura de Datos",
             bg=COLOR_PRIMARIO, fg="#BBF7D0", font=("Segoe UI", 10)).pack(anchor="w")


def construir_barra_herramientas():
    barra = ttk.Frame(APP["raiz"])
    barra.pack(fill="x", padx=10, pady=(8, 0))
    ttk.Label(barra, text="Ventana de observación:").pack(side="left")
    APP["ventana_txt"] = tk.StringVar(value=texto_ventana(0))
    combo = ttk.Combobox(barra, textvariable=APP["ventana_txt"], values=VENTANAS,
                         state="readonly", width=20)
    combo.pack(side="left", padx=6)
    combo.bind("<<ComboboxSelected>>", lambda e: cambiar_ventana())
    ttk.Checkbutton(barra, text="Mostrar inactivos en las tablas",
                    variable=APP["ver_inactivos"], command=refrescar_todo).pack(
        side="left", padx=16)
    ttk.Button(barra, text="↶ Deshacer", command=accion_deshacer).pack(side="right")


def construir_estado():
    APP["estado"] = tk.StringVar()
    tk.Label(APP["raiz"], textvariable=APP["estado"], anchor="w", bg="#E5E7EB",
             fg="#374151", font=("Segoe UI", 9), padx=10, pady=4).pack(side="bottom",
                                                                      fill="x")


def construir_tab_grupos(padre):
    botones = barra_botones(padre, [
        ("Nuevo", accion_grupo_nuevo, True), ("Editar", accion_grupo_editar, False),
        ("Integrantes", abrir_integrantes, False),
        ("Activar / Desactivar", accion_grupo_alternar, False),
        ("Eliminar", accion_grupo_eliminar, False)])
    botones.pack(fill="x", padx=10, pady=10)
    columnas = [("codigo", "Código", 90), ("nombre", "Nombre del grupo", 330),
                ("lider", "Líder", 190), ("categoria", "Categoría", 90),
                ("integrantes", "Integrantes", 90), ("productos", "Productos", 80),
                ("activo", "Activo", 60)]
    marco, APP["tabla_grupos"] = crear_tabla(padre, columnas)
    marco.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    APP["tabla_grupos"].bind("<Double-1>", lambda e: abrir_integrantes())


def construir_tab_investigadores(padre):
    botones = barra_botones(padre, [
        ("Nuevo", accion_inv_nuevo, True), ("Editar", accion_inv_editar, False),
        ("Ver sus productos", accion_inv_ver_productos, False),
        ("Activar / Desactivar", accion_inv_alternar, False),
        ("Eliminar", accion_inv_eliminar, False)])
    botones.pack(fill="x", padx=10, pady=10)
    columnas = [("id", "ID", 80), ("nombre", "Nombre", 230), ("cod_rh", "Cod. CvLAC", 110),
                ("email", "Correo", 200), ("formacion", "Formación", 120),
                ("categoria", "Categoría", 150), ("productos", "Productos", 80),
                ("activo", "Activo", 60)]
    marco, APP["tabla_inv"] = crear_tabla(padre, columnas)
    marco.pack(fill="both", expand=True, padx=10, pady=(0, 10))


def construir_tab_productos(padre):
    botones = barra_botones(padre, [
        ("Nuevo", accion_prod_nuevo, True), ("Editar", accion_prod_editar, False),
        ("Validar / Invalidar", accion_prod_validar, False),
        ("Activar / Desactivar", accion_prod_alternar, False),
        ("Eliminar", accion_prod_eliminar, False)])
    botones.pack(fill="x", padx=10, pady=(10, 4))

    filtros = ttk.Frame(padre)
    filtros.pack(fill="x", padx=10, pady=(0, 8))
    definiciones = [("f_grupo", "Grupo:", 26), ("f_inv", "Investigador:", 26),
                    ("f_tipo", "Tipo:", 16)]
    for clave, etiqueta, ancho in definiciones:
        ttk.Label(filtros, text=etiqueta).pack(side="left", padx=(0, 4))
        APP[clave] = tk.StringVar(value="Todos")
        combo = ttk.Combobox(filtros, textvariable=APP[clave], values=["Todos"],
                             state="readonly", width=ancho)
        combo.pack(side="left", padx=(0, 12))
        combo.bind("<<ComboboxSelected>>", lambda e: refrescar_productos())
        APP["cb_" + clave] = combo
    APP["f_validados"] = tk.BooleanVar(value=False)
    ttk.Checkbutton(filtros, text="Solo validados", variable=APP["f_validados"],
                    command=refrescar_productos).pack(side="left", padx=6)
    ttk.Button(filtros, text="Limpiar filtros", command=limpiar_filtros_productos).pack(
        side="left", padx=6)

    columnas = [("id", "ID", 80), ("titulo", "Título", 300), ("tipo", "Tipo", 110),
                ("categoria", "Categoría", 90), ("anio", "Año", 55),
                ("validado", "Validado", 70), ("grupo", "Grupo", 80),
                ("autores", "Autores", 240), ("activo", "Activo", 60)]
    marco, APP["tabla_prod"] = crear_tabla(padre, columnas)
    marco.pack(fill="both", expand=True, padx=10, pady=(0, 10))


def construir_tab_estadisticas(padre):
    barra = ttk.Frame(padre)
    barra.pack(fill="x", padx=10, pady=(10, 4))
    ttk.Label(barra, text="Vista:").pack(side="left")
    APP["vista"] = tk.StringVar(value="Global")
    combo = ttk.Combobox(barra, textvariable=APP["vista"], values=VISTAS,
                         state="readonly", width=18)
    combo.pack(side="left", padx=6)
    combo.bind("<<ComboboxSelected>>", lambda e: refrescar_dashboard())
    ttk.Label(barra, text="Elemento:").pack(side="left", padx=(14, 0))
    APP["vista_sel"] = tk.StringVar()
    APP["cb_vista_sel"] = ttk.Combobox(barra, textvariable=APP["vista_sel"],
                                       state="disabled", width=48)
    APP["cb_vista_sel"].pack(side="left", padx=6)
    APP["cb_vista_sel"].bind("<<ComboboxSelected>>", lambda e: refrescar_dashboard())
    APP["lbl_resumen"] = ttk.Label(padre, text="", font=("Segoe UI", 10, "bold"),
                                   foreground=COLOR_PRIMARIO)
    APP["lbl_resumen"].pack(anchor="w", padx=12, pady=(2, 0))
    if HAY_MATPLOTLIB:
        APP["fig"] = Figure(figsize=(10, 6), dpi=100, facecolor=COLOR_FONDO)
        APP["canvas"] = FigureCanvasTkAgg(APP["fig"], master=padre)
        APP["canvas"].get_tk_widget().pack(fill="both", expand=True, padx=10, pady=6)
    else:
        ttk.Label(padre, text="Instale matplotlib para ver las gráficas:\n"
                              "pip install matplotlib", font=("Segoe UI", 12)).pack(pady=40)


def construir_tab_cola_pila(padre):
    izquierda = ttk.LabelFrame(padre, text=" Cola de importaciones (FIFO) ")
    izquierda.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)
    botones = barra_botones(izquierda, [
        ("Encolar URL", accion_encolar_url, True),
        ("Encolar archivo", accion_encolar_archivo, False),
        ("Procesar siguiente", accion_cola_procesar, False),
        ("Procesar toda la cola", accion_cola_procesar_todo, False)])
    botones.pack(fill="x", padx=8, pady=(8, 4))
    botones2 = barra_botones(izquierda, [
        ("Editar siguiente", accion_cola_editar, False),
        ("Quitar siguiente", accion_cola_quitar, False)])
    botones2.pack(fill="x", padx=8, pady=(0, 6))
    columnas = [("pos", "#", 36), ("tipo", "Tipo", 55), ("ref", "Grupo", 90),
                ("origen", "Origen", 300), ("estado", "Estado", 110)]
    marco, APP["tabla_cola"] = crear_tabla(izquierda, columnas)
    marco.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    derecha = ttk.LabelFrame(padre, text=" Historial de operaciones (PILA, LIFO) ")
    derecha.pack(side="left", fill="both", expand=True, padx=(5, 10), pady=10)
    ttk.Button(derecha, text="↶ Deshacer la última (desapilar)", style="Accent.TButton",
               command=accion_deshacer).pack(anchor="w", padx=8, pady=8)
    APP["lista_pila"] = tk.Listbox(derecha, font=("Consolas", 10), activestyle="none")
    APP["lista_pila"].pack(fill="both", expand=True, padx=8, pady=(0, 8))


def construir_pestanas():
    cuaderno = ttk.Notebook(APP["raiz"])
    cuaderno.pack(fill="both", expand=True, padx=10, pady=8)
    APP["tabs"] = cuaderno
    constructores = [("  Grupos  ", construir_tab_grupos),
                     ("  Investigadores  ", construir_tab_investigadores),
                     ("  Productos  ", construir_tab_productos),
                     ("  Estadísticas  ", construir_tab_estadisticas),
                     ("  Cola y Pila  ", construir_tab_cola_pila)]
    for titulo, construir in constructores:
        marco = ttk.Frame(cuaderno)
        cuaderno.add(marco, text=titulo)
        construir(marco)
        if titulo.strip() == "Productos":
            APP["tab_productos"] = marco


# ==========================================================
# 11. PROGRAMA PRINCIPAL
# ==========================================================
def iniciar():
    raiz = tk.Tk()
    APP["raiz"] = raiz
    APP["sis"] = sistema_crear()
    APP["ver_inactivos"] = tk.BooleanVar(value=True)
    raiz.title("PEA-i - Universidad Popular del Cesar")
    raiz.geometry("1280x780")
    raiz.minsize(1000, 620)
    raiz.configure(bg=COLOR_FONDO)
    construir_estilo()
    construir_menu()
    construir_encabezado()
    construir_barra_herramientas()
    construir_estado()
    construir_pestanas()
    refrescar_todo()
    raiz.protocol("WM_DELETE_WINDOW", cerrar_app)
    raiz.after(300, preguntar_inicio)
    raiz.mainloop()


if __name__ == "__main__":
    iniciar()
