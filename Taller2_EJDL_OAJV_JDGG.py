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
import argparse
import csv
import io
import json
import os
import random
import re
import time
import sys
import unicodedata
import urllib.parse
import zlib
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
except ImportError:                      # modo consola (--cli): no hace falta la interfaz
    tk = filedialog = messagebox = simpledialog = ttk = None



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
            "integrantes": lista_crear(), "productos": lista_crear(),
            "ficha": lista_crear()}


def nuevo_investigador(id_inv, nombre, cod_rh="", email="", formacion="",
                       categoria="Sin categoría"):
    return {"id": id_inv, "nombre": nombre, "cod_rh": cod_rh, "email": email,
            "formacion": formacion, "categoria": categoria, "activo": True,
            "productos": lista_crear(), "ficha": lista_crear()}


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
    d["ficha"] = [dict(f) for f in lista_recorrer(g["ficha"])]
    return d


def grupo_desde_dict(d):
    g = nuevo_grupo(d["codigo"], d["nombre"], d.get("lider", "N/D"),
                    d.get("categoria", "Sin categoría"), d.get("url", ""))
    g["activo"] = d.get("activo", True)
    for i in d.get("integrantes", []):
        lista_insertar_final(g["integrantes"], dict(i))
    for f in d.get("ficha", []):
        lista_insertar_final(g["ficha"], dict(f))
    return g


def investigador_a_dict(inv):
    d = {"id": inv["id"], "activo": inv["activo"]}
    for c in CAMPOS_INVESTIGADOR:
        d[c] = inv[c]
    d["ficha"] = [dict(f) for f in lista_recorrer(inv["ficha"])]
    return d


def investigador_desde_dict(d):
    inv = nuevo_investigador(d["id"], d["nombre"], d.get("cod_rh", ""),
                             d.get("email", ""), d.get("formacion", ""),
                             d.get("categoria", "Sin categoría"))
    inv["activo"] = d.get("activo", True)
    for f in d.get("ficha", []):
        lista_insertar_final(inv["ficha"], dict(f))
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


# --- FICHA: información descriptiva de grupos e investigadores --------------------
def ficha_agregar(entidad, seccion, campo, valor):
    valor = str(valor).strip()
    if not valor:
        return
    for f in lista_recorrer(entidad["ficha"]):
        if f["seccion"] == seccion and f["campo"] == campo and f["valor"] == valor:
            return
    lista_insertar_final(entidad["ficha"], {"seccion": seccion, "campo": campo, "valor": valor})


def ficha_limpiar(entidad, secciones):
    conservar = [f for f in lista_recorrer(entidad["ficha"]) if f["seccion"] not in secciones]
    entidad["ficha"] = lista_crear()
    for f in conservar:
        lista_insertar_final(entidad["ficha"], f)


def ficha_reemplazar(entidad, items):
    secciones = set([i["seccion"] for i in items])
    ficha_limpiar(entidad, secciones)
    for i in items:
        ficha_agregar(entidad, i["seccion"], i["campo"], i["valor"])


def ficha_valor(entidad, seccion, campo):
    for f in lista_recorrer(entidad["ficha"]):
        if f["seccion"] == seccion and f["campo"] == campo:
            return f["valor"]
    return ""


def ficha_por_seccion(entidad):
    orden = []
    grupos = {}
    for f in lista_recorrer(entidad["ficha"]):
        if f["seccion"] not in grupos:
            grupos[f["seccion"]] = []
            orden.append(f["seccion"])
        grupos[f["seccion"]].append(f)
    return [(s, grupos[s]) for s in orden]


# ==========================================================
# 6. SISTEMA (agrupa todas las estructuras) y utilidades internas
# ==========================================================
def sistema_crear():
    return {"grupos": lista_crear(),
            "investigadores": lista_crear(),
            "productos": lista_crear(),
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


def grupo_eliminar_cascada(sis, codigo, registrar=True):
    g = lista_buscar(sis["grupos"], "codigo", codigo)
    if g is None:
        return None, "El grupo no existe"
    productos = [producto_a_dict(p) for p in lista_recorrer(g["productos"])]
    snapshot = grupo_a_dict(g)
    for p in productos:
        producto_eliminar(sis, p["id"], registrar=False)
    _, error = grupo_eliminar(sis, codigo, registrar=False)
    if error:
        return None, error
    if registrar:
        _registrar(sis, {"op": "eliminar", "ent": "grupo", "clave": codigo,
                         "snapshot": snapshot, "productos": productos})
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
    _producto_desenlazar(sis, prod)
    for k, v in cambios.items():
        prod[k] = list(v) if k == "investigadores" else v
    _producto_enlazar(sis, prod)
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


def _restaurar_ent(sis, ent, snap, productos=None):
    if ent == "grupo":
        lista_insertar_final(sis["grupos"], grupo_desde_dict(snap))
        for p in (productos or []):
            error = _validar_producto(sis, p["grupo"], p["investigadores"], p["anio"])
            if error:
                return error
            prod = producto_desde_dict(p)
            lista_insertar_final(sis["productos"], prod)
            _producto_enlazar(sis, prod)
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
        error = _restaurar_ent(sis, ent, op["snapshot"], op.get("productos"))
    if error:
        return "No se pudo deshacer: " + error
    return "Deshecho: %s %s %s" % (tipo, ent, clave)


# ==========================================================
# 12. COLA DE IMPORTACIONES
# ==========================================================
def importacion_encolar(sis, tipo, origen):
    cola_encolar(sis["importaciones"], {"tipo": tipo, "origen": origen,
                                        "estado": "pendiente"})


def importacion_siguiente(sis):
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
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(sistema_a_dict(sis), f, ensure_ascii=False, indent=2)
    except OSError as e:
        return "No se pudo guardar: %s" % e
    return None


def cargar_json(ruta):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return None, [], "No se pudo cargar: %s" % e
    sis, advertencias = sistema_desde_dict(datos)
    return sis, advertencias, None


# ==========================================================
# 14b. INTERCAMBIO CON C++  (archivo de texto, campos separados por |)
# ==========================================================
FORMATO_TXT = "#PEA-i-TXT v1"


def _t(valor):
    return str(valor).replace("|", "/").replace("\r", " ").replace("\n", " ").strip()


def _b(valor):
    return "1" if valor else "0"


def exportar_txt(sis, ruta):
    lineas = [FORMATO_TXT,
              "# Campos separados por |  (ver especificación en Taller2_PEAi.py, sección 14b)",
              "C|%d|%d" % (sis["contador_prod"], sis["contador_inv"])]
    n_g = n_i = n_m = n_p = 0
    for g in lista_recorrer(sis["grupos"]):
        lineas.append("G|%s|%s|%s|%s|%s|%s" % (_t(g["codigo"]), _t(g["nombre"]),
                      _t(g["lider"]), _t(g["categoria"]), _t(g["url"]), _b(g["activo"])))
        n_g += 1
    for i in lista_recorrer(sis["investigadores"]):
        lineas.append("I|%s|%s|%s|%s|%s|%s|%s" % (_t(i["id"]), _t(i["nombre"]),
                      _t(i["cod_rh"]), _t(i["email"]), _t(i["formacion"]),
                      _t(i["categoria"]), _b(i["activo"])))
        n_i += 1
    for g in lista_recorrer(sis["grupos"]):
        for m in lista_recorrer(g["integrantes"]):
            lineas.append("M|%s|%s|%s|%s|%s|%s" % (_t(g["codigo"]), _t(m["id_investigador"]),
                          _t(m["vinculacion"]), _t(m["horas"]), _t(m["periodo"]),
                          _b(m["activo"])))
            n_m += 1
    n_f = 0
    for g in lista_recorrer(sis["grupos"]):
        for f in lista_recorrer(g["ficha"]):
            lineas.append("F|G|%s|%s|%s|%s" % (_t(g["codigo"]), _t(f["seccion"]),
                                               _t(f["campo"]), _t(f["valor"])))
            n_f += 1
    for i in lista_recorrer(sis["investigadores"]):
        for f in lista_recorrer(i["ficha"]):
            lineas.append("F|I|%s|%s|%s|%s" % (_t(i["id"]), _t(f["seccion"]),
                                               _t(f["campo"]), _t(f["valor"])))
            n_f += 1
    for p in lista_recorrer(sis["productos"]):
        lineas.append("P|%s|%s|%s|%s|%d|%s|%s|%s|%s" % (
            _t(p["id"]), _t(p["titulo"]), _t(p["tipo"]), _t(p["categoria"]), p["anio"],
            _b(p["validado"]), _t(p["grupo"]), ";".join(p["investigadores"]),
            _b(p["activo"])))
        n_p += 1
    for q in cola_recorrer(sis["importaciones"]):
        lineas.append("Q|%s|%s|%s|%s|%s" % (_t(q.get("tipo", "")), _t(q.get("origen", "")),
                      _t(q.get("estado", "")), _t(q.get("modo", "")),
                      _t(q.get("codigo", ""))))
    lineas.append("FIN|%d|%d|%d|%d|%d" % (n_g, n_i, n_m, n_p, n_f))
    try:
        with open(ruta, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lineas) + "\n")
    except OSError as e:
        return "No se pudo exportar: %s" % e
    return None


def importar_txt(ruta):
    try:
        with open(ruta, "r", encoding="utf-8-sig") as f:
            lineas = f.read().splitlines()
    except (OSError, UnicodeDecodeError) as e:
        return None, [], "No se pudo abrir el archivo: %s" % e
    if not lineas or not lineas[0].startswith("#PEA-i-TXT"):
        return None, [], "El archivo no tiene el formato PEA-i-TXT"
    datos = {"grupos": [], "investigadores": [], "productos": [], "importaciones": [],
             "contador_prod": 0, "contador_inv": 0}
    grupos = {}
    invs = {}
    advertencias = []
    for n, linea in enumerate(lineas, 1):
        if not linea.strip() or linea.startswith("#"):
            continue
        c = linea.split("|")
        try:
            if c[0] == "C":
                datos["contador_prod"] = int(c[1])
                datos["contador_inv"] = int(c[2])
            elif c[0] == "G":
                g = {"codigo": c[1], "nombre": c[2], "lider": c[3], "categoria": c[4],
                     "url": c[5], "activo": c[6] == "1", "integrantes": [], "ficha": []}
                datos["grupos"].append(g)
                grupos[c[1]] = g
            elif c[0] == "I":
                invs[c[1]] = {"id": c[1], "nombre": c[2], "cod_rh": c[3], "email": c[4],
                              "formacion": c[5], "categoria": c[6], "activo": c[7] == "1",
                              "ficha": []}
                datos["investigadores"].append(invs[c[1]])
            elif c[0] == "F":
                destino = grupos.get(c[2]) if c[1] == "G" else invs.get(c[2])
                if destino is not None:
                    destino["ficha"].append({"seccion": c[3], "campo": c[4], "valor": c[5]})
            elif c[0] == "M":
                if c[1] in grupos:
                    grupos[c[1]]["integrantes"].append(
                        {"id_investigador": c[2], "vinculacion": c[3], "horas": c[4],
                         "periodo": c[5], "activo": c[6] == "1"})
                else:
                    advertencias.append("Línea %d: integrante de un grupo inexistente" % n)
            elif c[0] == "P":
                datos["productos"].append({
                    "id": c[1], "titulo": c[2], "tipo": c[3], "categoria": c[4],
                    "anio": int(c[5]), "validado": c[6] == "1", "grupo": c[7],
                    "investigadores": [x for x in c[8].split(";") if x],
                    "activo": c[9] == "1"})
            elif c[0] == "Q":
                item = {"tipo": c[1], "origen": c[2], "estado": c[3] or "pendiente"}
                if c[4]:
                    item["modo"] = c[4]
                if c[5]:
                    item["codigo"] = c[5]
                datos["importaciones"].append(item)
        except (IndexError, ValueError):
            advertencias.append("Línea %d inválida: %s" % (n, linea[:60]))
    sis, avisos = sistema_desde_dict(datos)
    return sis, advertencias + avisos, None


# ==========================================================
# 15. DEMO / PRUEBA RÁPIDA
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

TITULOS_PRODUCTO = [
    ("proyectos de ley", "Proyecto de ley"), ("capitulo", "Capítulo de libro"),
    ("articulo", "Artículo"), ("libro", "Libro"), ("software", "Software"),
    ("patente", "Patente"), ("trabajo de grado", "Trabajo de grado"),
    ("trabajos dirigidos", "Trabajo de grado"), ("tutoria", "Trabajo de grado"),
    ("turoria", "Trabajo de grado"), ("proyecto", "Proyecto"), ("evento", "Evento"),
]
SUBSECCIONES_NO_PRODUCTO = (
    "curso", "programa academico", "asesorias", "redes de", "estrategias", "jurado",
    "demas trabajos", "comites", "comite de", "espacios de participacion",
    "participacion ciudadana", "par evaluador",
)
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


def limpiar(texto):
    return re.sub(r"\s+", " ", (texto or "").replace("\xa0", " ")).strip()


def normalizar(texto):
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().lower()


def decodificar(crudo):
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
    ta, tb = _tokens(a), _tokens(b)
    comunes = ta & tb
    if len(comunes) < 2:
        return False
    return len(comunes) / min(len(ta), len(tb)) >= 0.75


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
            continue
        celdas = [limpiar(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
        celdas = [c for c in celdas if c]
        if celdas:
            filas.append(celdas)
    if len(filas) < 5:
        filas = filas_desde_texto(sopa.get_text("\n"))
    return filas, None


def filas_desde_pdf(ruta):
    if not HAY_PYPDF:
        return None, "Falta la librería pypdf (pip install pypdf)"
    try:
        lector = PdfReader(ruta)
        texto = "\n".join([(pagina.extract_text() or "") for pagina in lector.pages])
    except Exception as e:
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
    m = re.match(r"^([^:,\d]{2,70}):\s+(.+)", texto)
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
        i += 1
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


def categoria_desde_texto(texto):
    n = normalizar(texto)
    m = re.match(r"^(a1|a|b|c)\b", n)
    if m:
        return m.group(1).upper()
    if "reconocido" in n:
        return "Reconocido"
    return "Sin categoría"


def encabezado_html(html):
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
        advertencias.append("La página de detalle no trae el código COL; se usó %s." % codigo)
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


CATEGORIAS_BIBLIO_GRUPO = [
    "Artículos publicados", "Libros publicados",
    "Traducciones Filológicas y Edición de Fuentes", "Capítulos de libro publicados",
    "Documentos de trabajo", "Otra publicación divulgativa", "Otros artículos publicados",
    "Libros de formación", "Libros de divulgación y/o Compilación de divulgación",
    "Manuales y Guías Especializadas", "Otros Libros publicados", "Traducciones",
    "Notas científicas"]

ANCLAS_BIBLIO_CV = [
    ("articulos", "Artículos publicados", r"^articulos?\b"),
    ("libros", "Libros publicados", r"^libros\b"),
    ("capitulos", "Capítulos de libro publicados", r"^capitulos?\b"),
    ("nota_cientifica", "Notas científicas", r"^notas?\s+cientific"),
    ("textos", "Textos en publicaciones no científicas", r"^textos\b"),
    ("otra_prod_biblio", "Otra producción bibliográfica", r"^otra\s+produccion"),
    ("lib_tra", "Traducciones Filológicas y Edición de Fuentes", r"^traduc"),
    ("lib_cre", "Libro de creación (Piloto)", r"^libros?\s+de\s+creacion"),
    ("lib_for", "Libros de formación", r"^libros?\s+de\s+formacion"),
    ("lib_div", "Libros de divulgación y/o Compilación de divulgación",
     r"^libros?\s+de\s+divulgacion"),
    ("lib_man", "Manuales y Guías Especializadas", r"^manuales"),
]
SECCIONES_CV = [
    ("formacion_acad", "Formación académica", r"^formacion academica"),
    ("formacion_comp", "Formación complementaria", r"^formacion complementaria"),
    ("estancias_posdoctorales", "Estancias postdoctorales", r"^estancias"),
    ("experiencia", "Experiencia profesional", r"^experiencia profesional"),
    ("otra_info_personal", "Otra información personal",
     r"^(otra informacion|areas de actuacion|idiomas|lineas de investigacion|reconocimientos)"),
]


def _texto(elemento, separador=" "):
    return limpiar(elemento.get_text(separador, strip=True))


def _sin_numeracion(texto):
    return limpiar(re.sub(r"^\d+\s*[.\-)]+\s*", "", texto))


def _tabla_por_encabezado(tablas, texto, exacto=False):
    buscado = normalizar(texto)
    for t in tablas:
        c = t.find("td", class_="celdaEncabezado")
        if c is None:
            continue
        e = normalizar(_texto(c))
        if (e == buscado) if exacto else (buscado in e):
            return t
    return None


def _tabla_ancla(sopa, nombre, patron=None):
    ancla = sopa.find("a", attrs={"name": nombre})
    if ancla is None:
        return None
    tabla = ancla.find_next("table")
    if tabla is None:
        return None
    if patron and not re.match(patron, normalizar(_texto(tabla))):
        return None
    return tabla


def _filas_texto(tabla, titulo_seccion):
    salida = []
    for fila in tabla.find_all("tr"):
        tds = fila.find_all("td")
        if not tds:
            continue
        texto = limpiar((tds[1] if len(tds) >= 2 else tds[0]).get_text(" | ", strip=True))
        n = normalizar(texto)
        if texto and n != normalizar(titulo_seccion) and not n.startswith(normalizar(titulo_seccion) + " "):
            salida.append(texto)
    return salida


MAPA_SECCIONES_CV = {
    "hoja de vida": "Identificación", "formacion academica": "Formación académica",
    "formacion complementaria": "Formación complementaria",
    "experiencia profesional": "Experiencia profesional", "articulos": "Artículos publicados",
    "libros": "Libros publicados", "capitulos de libro": "Capítulos de libro publicados",
}
OTRA_INFO_CV = ("areas de actuacion", "idiomas", "lineas de investigacion", "reconocimientos")


def _secciones_grupo(tablas):
    macro = ""
    salida = []
    for t in tablas:
        c = t.find("td", class_="celdaEncabezado")
        if c is None:
            continue
        titulo = _texto(c)
        if not titulo:
            continue
        filas = []
        for tr in t.find_all("tr")[1:]:
            celdas = [x for x in [_texto(td) for td in tr.find_all("td")] if x]
            if celdas:
                filas.append((celdas, tr))
        if not filas:
            if titulo == titulo.upper() and len(titulo) > 8:
                macro = titulo
            continue
        salida.append((macro, titulo, filas))
    return salida


def parsear_grupo_html(html, fuente, codigo_hint="", nombre_hint=""):
    sopa = BeautifulSoup(html, "html.parser")
    for e in sopa(["script", "style", "noscript"]):
        e.decompose()
    ficha = []
    advertencias = []
    basicos = {}
    integrantes = []
    items = []
    seccion_integrantes = []
    for macro, titulo, filas in _secciones_grupo(sopa.find_all("table")):
        n = normalizar(titulo)
        if n == "datos basicos":
            for celdas, tr in filas:
                if len(celdas) == 2:
                    campo = celdas[0].rstrip(":").strip()
                    ficha.append({"seccion": "Datos básicos", "campo": campo, "valor": celdas[1]})
                    basicos[normalizar(campo)] = celdas[1]
                else:
                    ficha.append({"seccion": "Datos básicos", "campo": "",
                                  "valor": " | ".join(celdas)})
            continue
        if n.startswith("integrantes del grupo"):
            seccion_integrantes = filas
            continue
        seccion = titulo if not macro else macro.capitalize() + " / " + titulo
        for celdas, tr in filas:
            ficha.append({"seccion": seccion, "campo": "", "valor": " | ".join(celdas)})
        if macro and not _es_no_producto(n):
            for celdas, tr in filas:
                texto = " ".join(celdas)
                if re.match(r"^\d+\s*[.\-)]+\s*\S", texto):
                    items.append({"tipo": titulo, "texto": _sin_numeracion(texto)})

    lider = basicos.get("lider", "") or "N/D"
    vistos = set()
    for celdas, tr in seccion_integrantes:
        tds = tr.find_all("td")
        if len(tds) != 4:
            continue
        nombre = _sin_numeracion(_texto(tds[0]))
        periodo = _texto(tds[3])
        if len(nombre) < 5 or normalizar(nombre) in vistos:
            continue
        vistos.add(normalizar(nombre))
        enlace = tds[0].find("a")
        href = enlace.get("href", "") if enlace is not None else ""
        vinculacion = _texto(tds[1]) or "Integrante"
        if lider != "N/D" and nombres_coinciden(nombre, lider):
            vinculacion = "Líder"
        integrantes.append({"nombre": nombre, "vinculacion": vinculacion,
                            "horas": _texto(tds[2]) or "N/D", "periodo": periodo or "Actual",
                            "activo": not re.search(r"-\s*(19|20)\d\d", periodo),
                            "cod_rh": re.sub(r"\D", "", _param_url(href, ("cod_rh",))),
                            "url_cvlac": href if href.startswith("http") else ""})
    if not integrantes:
        advertencias.append("No se reconocieron integrantes.")

    nombre = nombre_hint or "Grupo importado"
    if not nombre_hint:
        advertencias.append("No se encontró el nombre del grupo.")
    codigo = codigo_hint
    if not codigo:
        m = re.search(r"COL\d{7}", sopa.get_text(" ")[:3000])
        codigo = m.group(0) if m else ""
    if not codigo:
        codigo = "IMP-%06X" % (zlib.crc32(normalizar(nombre).encode("utf-8")) & 0xFFFFFF)
        advertencias.append("La página de detalle no trae el código COL; se usó %s." % codigo)
    return {"modo": "grupo", "codigo": codigo, "nombre": nombre, "lider": lider,
            "categoria": categoria_desde_texto(basicos.get("clasificacion", "")),
            "url": fuente if fuente.startswith("http") else "",
            "integrantes": integrantes, "productos": _productos_unicos(items), "ficha": ficha,
            "advertencias": advertencias}


def parsear_cvlac_html(html, fuente):
    sopa = BeautifulSoup(html, "html.parser")
    for e in sopa(["script", "style", "noscript"]):
        e.decompose()
    ficha = []
    items = []
    advertencias = []
    nombre = ""
    categoria = "Sin categoría"
    for h in sopa.find_all("h3"):
        titulo = _texto(h)
        tabla = h.find_parent("table")
        if tabla is None or len(tabla.find_all("h3")) > 1:
            tabla = h.find_next("table")
        if not titulo or tabla is None:
            continue
        n = normalizar(titulo)
        if n == "hoja de vida":
            for tr in tabla.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) == 2:
                    campo = _texto(tds[0]).rstrip(":").strip()
                    valor = _texto(tds[1])
                    if not campo or not valor:
                        continue
                    if normalizar(campo) == "categoria":
                        valor = limpiar(re.split(r"\s+con vigencia", valor)[0])
                        categoria = valor or "Sin categoría"
                    if normalizar(campo) == "nombre":
                        nombre = valor
                    ficha.append({"seccion": "Identificación", "campo": campo, "valor": valor})
                else:
                    texto = _texto(tr, " | ")
                    if texto and normalizar(texto) != n:
                        ficha.append({"seccion": "Identificación", "campo": "", "valor": texto})
            continue
        if n == "identificadores de autor":
            for a in tabla.find_all("a"):
                href = a.get("href", "") or ""
                if href.startswith("http"):
                    ficha.append({"seccion": "Identificadores de autor",
                                  "campo": _texto(a), "valor": href})
            continue
        if n in OTRA_INFO_CV:
            seccion, campo_fijo = "Otra información personal", titulo
        else:
            seccion, campo_fijo = MAPA_SECCIONES_CV.get(n, titulo), ""
        if tabla.find("blockquote") is not None:
            descriptor = ""
            for tr in tabla.find_all("tr"):
                bq = tr.find("blockquote")
                if bq is None:
                    texto = _texto(tr, " | ")
                    if texto and normalizar(texto) != n:
                        descriptor = texto if len(texto) < 170 else ""
                    continue
                texto = _texto(bq)
                if len(texto) <= 5:
                    continue
                ficha.append({"seccion": seccion, "campo": descriptor or campo_fijo, "valor": texto})
                if not _es_no_producto(n):
                    items.append({"tipo": seccion, "texto": texto, "cv": True})
        else:
            for tr in tabla.find_all("tr"):
                if tr.find("table") is not None:
                    continue
                texto = _texto(tr, " | ")
                if texto and normalizar(texto) != n:
                    ficha.append({"seccion": seccion, "campo": campo_fijo, "valor": texto})
    if not nombre:
        advertencias.append("No se encontró el nombre del investigador.")
    cod_rh = re.sub(r"\D", "", _param_url(fuente, ("cod_rh",)))
    return {"modo": "investigador", "nombre": nombre, "cod_rh": cod_rh, "categoria": categoria,
            "productos": _productos_unicos(items), "ficha": ficha, "advertencias": advertencias}


def _validar_detalle(datos):
    if not datos["productos"] and not datos.get("integrantes") and not datos.get("ficha"):
        return None, ("No se reconoció información en la fuente.")
    return datos, None


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
            "estado": limpiar(tds[6].get_text(" ")),
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
            "nacionalidad": limpiar(tds[2].get_text(" ")),
            "categoria": categoria_investigador(tds[3].get_text(" "))})
    if not investigadores:
        return None, "No se encontraron investigadores en el listado."
    _, _, total = _total_resultados(sopa.get_text(" "))
    advertencias = []
    if total > 1000:
        advertencias.append("Este listado tiene %s investigadores." % format(total, ","))
    return {"modo": "directorio_investigadores", "investigadores": investigadores,
            "productos": [], "total_resultados": total,
            "advertencias": advertencias}, None


CSV_COLUMNAS = ["grupo", "titulo", "tipo", "categoria", "anio", "validado", "autores"]


def _valor(fila, mapa, clave):
    original = mapa.get(clave)
    return limpiar(fila.get(original, "") or "") if original else ""


def leer_csv(ruta):
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
        return None, "Faltan columnas obligatorias: %s" % ", ".join(faltan)
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
        return None, "El CSV no tiene filas válidas."
    return {"modo": "csv", "productos": productos, "advertencias": advertencias}, None


def crear_plantilla_csv(ruta):
    try:
        with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
            f.write(";".join(CSV_COLUMNAS) + "\n")
            f.write("COL0001;Ejemplo de artículo;Artículo;A1;2025;si;Ana Pérez|Eva Mora\n")
            f.write("COL0001;Ejemplo de libro;Libro;B;2024;no;Ana Pérez\n")
    except OSError as e:
        return "No se pudo crear la plantilla: %s" % e
    return None


def leer_origen(tipo, origen, modo="auto", pista=None):
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
        if modo == "grupo":
            return _validar_detalle(parsear_grupo_html(
                html, origen, pista.get("codigo", ""), encabezado_html(html)))
        if modo == "investigador":
            return _validar_detalle(parsear_cvlac_html(html, origen))
        return None, MODO_NO_DETECTADO
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
        return None, "No se reconocieron integrantes ni productos en la fuente."
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
    if datos.get("ficha"):
        por_sec = {}
        for f in datos["ficha"]:
            por_sec[f["seccion"]] = por_sec.get(f["seccion"], 0) + 1
        lineas.append("Información descriptiva: " +
                      ", ".join(["%s (%d)" % kv for kv in por_sec.items()]))
    productos = datos["productos"]
    con_anio = [p for p in productos if p["anio"] is not None]
    lineas.append("Productos detectados: %d (con año: %d, sin año: %d)"
                  % (len(productos), len(con_anio), len(productos) - len(con_anio)))
    por_tipo = {}
    for p in productos:
        por_tipo[p["tipo"]] = por_tipo.get(p["tipo"], 0) + 1
    if por_tipo:
        lineas.append("Por tipo: " + ", ".join(["%s: %d" % kv for kv in por_tipo.items()]))
    return "\n".join(lineas)


def diagnosticar_origen(tipo, origen):
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
    return "\n".join(lineas)


def _informe_nuevo():
    return {"grupos_nuevos": 0, "grupos_actualizados": 0, "inv_nuevos": 0,
            "inv_actualizados": 0, "integrantes_nuevos": 0, "productos_nuevos": 0,
            "productos_repetidos": 0, "productos_actualizados": 0, "sin_anio": 0,
            "encolados": 0, "fichas": 0, "advertencias": []}


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
        extra = []
        if g.get("estado"):
            extra.append({"seccion": "Listado", "campo": "Estado", "valor": g["estado"]})
        if g.get("convocatoria"):
            extra.append({"seccion": "Listado", "campo": "Clasificado en",
                          "valor": g["convocatoria"]})
        if extra:
            ficha_reemplazar(grupo_consultar(sis, g["codigo"]), extra)
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
        inv = _asegurar_investigador(sis, i["nombre"], i["cod_rh"], i["categoria"], informe)
        if i.get("nacionalidad") and not ficha_valor(inv, "Identificación", "Nacionalidad"):
            ficha_agregar(inv, "Identificación", "Nacionalidad", i["nacionalidad"])
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
    if datos.get("ficha"):
        ficha_reemplazar(grupo_consultar(sis, codigo), datos["ficha"])
        informe["fichas"] += len(datos["ficha"])
    for it in datos["integrantes"]:
        inv = None
        if it.get("cod_rh"):
            inv = lista_buscar(sis["investigadores"], "cod_rh", it["cod_rh"])
        if inv is None:
            inv = _investigador_por_nombre(sis, it["nombre"])
        if inv is None:
            inv, _ = investigador_crear(sis, it["nombre"], it.get("cod_rh", ""), registrar=False)
            informe["inv_nuevos"] += 1
        elif it.get("cod_rh") and not inv["cod_rh"]:
            investigador_modificar(sis, inv["id"], {"cod_rh": it["cod_rh"]}, registrar=False)
        if it.get("url_cvlac") and not ficha_valor(inv, "Identificación", "Nombre") \
                and not _ya_en_cola(sis, it["url_cvlac"]):
            cola_encolar(sis["importaciones"], {"tipo": "url", "origen": it["url_cvlac"],
                                                "estado": "pendiente", "modo": "investigador",
                                                "codigo": codigo})
            informe["encolados"] += 1
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
    if datos.get("ficha"):
        ficha_reemplazar(inv, datos["ficha"])
        informe["fichas"] += len(datos["ficha"])
    if datos["categoria"] != "Sin categoría" and inv["categoria"] == "Sin categoría":
        investigador_modificar(sis, inv["id"], {"categoria": datos["categoria"]}, registrar=False)
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
        lineas.append("• Grupos nuevos: %d  |  actualizados: %d"
                      % (informe["grupos_nuevos"], informe["grupos_actualizados"]))
    lineas.append("• Investigadores nuevos: %d" % informe["inv_nuevos"])
    lineas.append("• Integrantes agregados: %d" % informe["integrantes_nuevos"])
    lineas.append("• Productos nuevos: %d" % informe["productos_nuevos"])
    lineas.append("• Productos ya existentes (omitidos): %d" % informe["productos_repetidos"])
    if informe["advertencias"]:
        lineas.append("")
        lineas.append("Advertencias:")
        for a in informe["advertencias"][:10]:
            lineas.append("  ! " + a)
    return "\n".join(lineas)


# ==============================================================
# FUNCIÓN DE SCRAPING EN VIVO PARA CVLAC (INTEGRADA)
# ==============================================================
def hacer_scraping_cvlac(cod_rh):
    """Realiza el scraping web en tiempo real del CvLAC de Minciencias usando cod_rh."""
    if not cod_rh:
        return "El investigador no tiene registrado un código CvLAC (cod_rh)."
    
    url = f"https://scienti.minciencias.gov.co/cvlac/visualizador/generarCurriculoCv.do?cod_rh={cod_rh}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=25)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        return f"Error al conectar con el CvLAC: {e}"

    lineas = []

    # 1. Datos Generales - Identificación
    anchor_datos = soup.find('a', {'name': 'datos_generales'})
    if anchor_datos:
        tabla = anchor_datos.find_next('table')
        if tabla:
            lineas.append(("h", "Datos Generales: Identificación"))
            for fila in tabla.find_all('tr'):
                cols = fila.find_all('td')
                if len(cols) == 2:
                    titulo = limpiar(cols[0].get_text(strip=True))
                    valor = limpiar(cols[1].get_text(strip=True))
                    if titulo and valor:
                        lineas.append(("i", f"   • {titulo}: {valor}"))

    # 2. Redes Sociales Académicas
    anchor_redes = soup.find('a', {'name': 'redes_identificadores'})
    if anchor_redes:
        tabla_redes = anchor_redes.find_next('table')
        if tabla_redes:
            lineas.append(("h", "Redes Sociales Académicas"))
            for a in tabla_redes.find_all('a'):
                txt = limpiar(a.get_text(strip=True))
                href = limpiar(a.get('href', ''))
                if txt and href:
                    lineas.append(("i", f"   • {txt}: {href}"))

    # 3. Identificadores de Autor
    anchor_idents = soup.find('a', {'name': 'red_identificadores'})
    if anchor_idents:
        tabla_idents = anchor_idents.find_next('table')
        if tabla_idents:
            lineas.append(("h", "Identificadores de Autor"))
            for a in tabla_idents.find_all('a'):
                txt = limpiar(a.get_text(strip=True))
                href = limpiar(a.get('href', ''))
                if txt and href:
                    lineas.append(("i", f"   • {txt}: {href}"))

    # 4. Formación Académica
    anchor_form = soup.find('a', {'name': 'formacion_acad'})
    if anchor_form:
        tabla_form = anchor_form.find_next('table')
        if tabla_form:
            lineas.append(("h", "Formación Académica"))
            for fila in tabla_form.find_all('tr'):
                tds = fila.find_all('td')
                if len(tds) >= 2:
                    texto = limpiar(tds[1].get_text(separator=" | ", strip=True))
                    if texto and "Formación Académica" not in texto:
                        lineas.append(("i", f"   • {texto}"))

    # 5. Formación Complementaria
    anchor_comp = soup.find('a', {'name': 'formacion_comp'})
    if anchor_comp:
        tabla_comp = anchor_comp.find_next('table')
        if tabla_comp:
            lineas.append(("h", "Formación Complementaria"))
            for fila in tabla_comp.find_all('tr'):
                tds = fila.find_all('td')
                if len(tds) >= 2:
                    texto = limpiar(tds[1].get_text(separator=" | ", strip=True))
                    if texto and "Formación Complementaria" not in texto:
                        lineas.append(("i", f"   • {texto}"))

    # 6. Experiencia Profesional
    anchor_exp = soup.find('a', {'name': 'experiencia'})
    if anchor_exp:
        tabla_exp = anchor_exp.find_next('table')
        if tabla_exp:
            lineas.append(("h", "Experiencia Profesional"))
            for fila in tabla_exp.find_all('tr'):
                tds = fila.find_all('td')
                if len(tds) >= 2:
                    texto = limpiar(tds[1].get_text(separator=" | ", strip=True))
                    if texto and "Experiencia profesional" not in texto:
                        lineas.append(("i", f"   • {texto}"))

    # 7. Producción Bibliográfica
    anchor_art = soup.find('a', {'name': 'articulos'})
    if anchor_art:
        tabla_art = anchor_art.find_next('table')
        if tabla_art:
            lineas.append(("h", "Producción Bibliográfica - Artículos"))
            for block in tabla_art.find_all('blockquote'):
                texto_block = limpiar(block.get_text(separator=' ', strip=True))
                if texto_block:
                    lineas.append(("i", f"   • {texto_block}"))

    anchor_cap = soup.find('a', {'name': 'capitulos'})
    if anchor_cap:
        tabla_cap = anchor_cap.find_next('table')
        if tabla_cap:
            lineas.append(("h", "Producción Bibliográfica - Capítulos de libro"))
            for block in tabla_cap.find_all('blockquote'):
                texto_block = limpiar(block.get_text(separator=' ', strip=True))
                if texto_block:
                    lineas.append(("i", f"   • {texto_block}"))

    return lineas


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

COLOR_PRIMARIO = "#14532D"
COLOR_ACENTO = "#16A34A"
COLOR_FONDO = "#F3F4F6"
COLOR_MENU = "#0F3D22"
COLORES_GRAFICA = ["#16A34A", "#2563EB", "#D97706", "#9333EA", "#DC2626", "#0891B2"]
ARCHIVO_LOGO = "logo_upc.png"

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

APP = {"sis": None, "ruta": "pea_i_datos.json", "sucio": False,
       "ventana_n": 0, "mensaje": ""}


def anio_actual():
    return datetime.now().year


def clave_de(texto):
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
    cambios = {}
    for k, v in nuevos.items():
        if isinstance(v, list):
            if sorted(v) != sorted(actual[k]):
                cambios[k] = v
        elif v != actual[k]:
            cambios[k] = v
    return cambios


def resolver(error, mensaje=""):
    if error:
        messagebox.showerror("No se pudo completar la operación", error,
                             parent=APP["raiz"])
        return False
    APP["mensaje"] = mensaje
    APP["sucio"] = True
    refrescar_todo()
    return True


def crear_tabla(padre, columnas):
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
    barra = ttk.Frame(padre)
    for texto, comando, destacado in botones:
        estilo = "Accent.TButton" if destacado else "TButton"
        ttk.Button(barra, text=texto, command=comando, style=estilo).pack(
            side="left", padx=(0, 6))
    return barra


def dialogo_formulario(titulo, campos, valores=None):
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
    n = grupo_consultar(APP["sis"], codigo)["productos"]["tam"]
    if n == 0:
        if not messagebox.askyesno("Eliminar grupo",
                                   "¿Eliminar definitivamente el grupo %s?" % codigo,
                                   parent=APP["raiz"]):
            return
        _, error = grupo_eliminar(APP["sis"], codigo)
        resolver(error, "Grupo %s eliminado" % codigo)
        return
    texto = ("El grupo %s tiene %d productos asociados.\n\n"
             "• SÍ: elimina el grupo junto con sus %d productos y sus integrantes.\n"
             "• NO: cancela.\n\n¿Eliminar el grupo y sus productos?" % (codigo, n, n))
    if not messagebox.askyesno("Eliminar grupo con productos", texto, parent=APP["raiz"]):
        return
    _, error = grupo_eliminar_cascada(APP["sis"], codigo)
    resolver(error, "Grupo %s y sus %d productos eliminados" % (codigo, n))


def refrescar_grupos():
    filas = []
    ver_todo = APP["ver_inactivos"].get()
    for g in lista_recorrer(APP["sis"]["grupos"], solo_activos=not ver_todo):
        valores = (g["codigo"], g["nombre"], g["lider"], g["categoria"],
                   ficha_valor(g, "Listado", "Clasificado en"),
                   g["integrantes"]["tam"], g["productos"]["tam"], si_no(g["activo"]))
        filas.append((g["codigo"], valores, not g["activo"]))
    llenar_tabla(APP["tabla_grupos"], filas)


def abrir_integrantes():
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
    resolver(error, "Investigador %s eliminado" % id_inv)


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
        valores = (i["id"], i["nombre"], ficha_valor(i, "Identificación", "Nacionalidad"),
                   i["cod_rh"], i["email"], i["formacion"],
                   i["categoria"], i["productos"]["tam"], si_no(i["activo"]))
        filas.append((i["id"], valores, not i["activo"]))
    llenar_tabla(APP["tabla_inv"], filas)


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
    resolver(error, "Producto %s eliminado" % id_prod)


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


def mostrar_texto(titulo, texto):
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


def importar_origen(tipo, origen, item=None, confirmar=True):
    raiz = APP["raiz"]
    raiz.config(cursor="watch")
    raiz.update_idletasks()
    datos, error = leer_origen(tipo, origen, "auto", item)
    raiz.config(cursor="")
    if error:
        if confirmar:
            messagebox.showerror("Error", error, parent=raiz)
        return "error: " + error.splitlines()[0]
    informe, error = importar_datos(APP["sis"], datos, None, None)
    if error:
        if confirmar:
            messagebox.showerror("Error", error, parent=raiz)
        return "error: " + error.splitlines()[0]
    return "ok"


def accion_importar_url():
    url = simpledialog.askstring("Importar", "Pegue la URL:", parent=APP["raiz"])
    if url and url.strip():
        importar_origen("url", url.strip())
        resolver(None, "Importación completada")


def accion_importar_archivo():
    ruta = filedialog.askopenfilename(filetypes=[("HTML, PDF o CSV", "*.html *.htm *.pdf *.csv")])
    if ruta:
        importar_origen("html" if ruta.endswith(".html") else "csv", ruta)
        resolver(None, "Importación completada")


def confirmar_perdida():
    if not APP["sucio"]:
        return True
    return messagebox.askyesno("Cambios sin guardar", "¿Continuar?", parent=APP["raiz"])


def nuevo_vacio():
    if not confirmar_perdida():
        return
    APP["sis"] = sistema_crear()
    APP["sucio"] = False
    resolver(None, "Sistema iniciado sin datos")


def abrir_archivo():
    if not confirmar_perdida():
        return
    ruta = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
    if not ruta:
        return
    sis, avisos, error = cargar_json(ruta)
    if error:
        messagebox.showerror("Error", error, parent=APP["raiz"])
        return
    APP["sis"] = sis
    APP["ruta"] = ruta
    resolver(None, "Datos cargados")


def guardar():
    error = guardar_json(APP["sis"], APP["ruta"])
    if error:
        messagebox.showerror("Error", error, parent=APP["raiz"])
        return False
    APP["sucio"] = False
    resolver(None, "Guardado")
    return True


def guardar_como():
    ruta = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
    if ruta:
        APP["ruta"] = ruta
        guardar()


def cargar_ejemplo():
    APP["sis"] = sistema_crear()
    resolver(None, "Ejemplo cargado")


def cerrar_app():
    if APP["sucio"]:
        if messagebox.askyesno("Salir", "¿Guardar cambios?", parent=APP["raiz"]):
            guardar()
    APP["raiz"].destroy()


def preguntar_inicio():
    if messagebox.askyesno("PEA-i", "¿Cargar datos desde un archivo?", parent=APP["raiz"]):
        abrir_archivo()


def accion_exportar_txt():
    ruta = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Texto", "*.txt")])
    if ruta:
        exportar_txt(APP["sis"], ruta)
        messagebox.showinfo("Exportar", "Exportado correctamente", parent=APP["raiz"])


def accion_abrir_txt():
    if not confirmar_perdida():
        return
    ruta = filedialog.askopenfilename(filetypes=[("Texto", "*.txt")])
    if ruta:
        sis, _, error = importar_txt(ruta)
        if error:
            messagebox.showerror("Error", error, parent=APP["raiz"])
            return
        APP["sis"] = sis
        resolver(None, "Cargado desde TXT")


# ==========================================================
# VENTANA EMERGENTE DE CONSULTA DE GRUPO
# ==========================================================
ORDEN_SECCIONES_GRUPO = ("Datos básicos", "Instituciones", "Plan Estratégico",
                         "Líneas de investigación declaradas por el grupo")


def lineas_ficha(entidad, nombres, vacias=True):
    por = dict(ficha_por_seccion(entidad))
    salida = []
    for sec in nombres:
        items = por.get(sec, [])
        if not items and not vacias:
            continue
        salida.append(("h", sec))
        if not items:
            salida.append(("m", "   (sin información)"))
        for f in items:
            texto = "   • %s: %s" % (f["campo"], f["valor"]) if f["campo"] else "   • " + f["valor"]
            salida.append(("i", texto))
    return salida


def secciones_restantes(entidad, canon):
    return [sec for sec, _ in ficha_por_seccion(entidad) if sec not in canon and sec != "Listado"]


def lineas_resumen_productos(productos):
    por_tipo = {}
    for p in productos:
        por_tipo[p["tipo"]] = por_tipo.get(p["tipo"], 0) + 1
    salida = [("h", "PRODUCTOS REGISTRADOS EN EL PROGRAMA (%d)" % len(productos))]
    if not por_tipo:
        salida.append(("m", "   (sin productos)"))
    for tipo, n in sorted(por_tipo.items(), key=lambda kv: (-kv[1], kv[0])):
        salida.append(("i", "   • %s: %d" % (tipo, n)))
    return salida


def lineas_consulta_grupo(g):
    L = [("t", "GRUPO DE INVESTIGACIÓN"), ("n", "%s  —  %s" % (g["codigo"], g["nombre"])),
         ("h", "Datos del listado"),
         ("i", "   • Cod grupo: " + g["codigo"]), ("i", "   • Nombre grupo: " + g["nombre"]),
         ("i", "   • Líder: " + g["lider"]),
         ("i", "   • Estado: " + (ficha_valor(g, "Listado", "Estado") or g["categoria"])),
         ("i", "   • Clasificado en: " + (ficha_valor(g, "Listado", "Clasificado en") or "N/D")),
         ("i", "   • Activo en el programa: " + si_no(g["activo"]))]
    L += lineas_ficha(g, ORDEN_SECCIONES_GRUPO)
    integrantes = lista_recorrer(g["integrantes"])
    L.append(("h", "Integrantes del grupo (%d)" % len(integrantes)))
    if not integrantes:
        L.append(("m", "   (sin integrantes)"))
    for m in integrantes:
        L.append(("i", "   • %s  |  %s  |  %s h  |  %s%s"
                  % (nombre_investigador(m["id_investigador"]), m["vinculacion"], m["horas"],
                     m["periodo"], "" if m["activo"] else "   [inactivo]")))
    L += lineas_ficha(g, secciones_restantes(g, ORDEN_SECCIONES_GRUPO), False)
    L += lineas_resumen_productos(lista_recorrer(g["productos"]))
    return L


def accion_consultar_grupo():
    codigo = exigir_seleccion(APP["tabla_grupos"])
    if codigo is None:
        return
    g = grupo_consultar(APP["sis"], codigo)
    if g is None:
        return

    ventana = tk.Toplevel(APP["raiz"])
    ventana.title("Consultar Grupo - %s" % g["nombre"])
    ventana.geometry("900x600")
    ventana.configure(bg=COLOR_FONDO)

    def copiar():
        ventana.clipboard_clear()
        ventana.clipboard_append(caja.get("1.0", "end"))
        messagebox.showinfo("Copiado", "Información copiada al portapapeles", parent=ventana)

    barra = ttk.Frame(ventana)
    barra.pack(fill="x", padx=12, pady=(12, 4))
    ttk.Button(barra, text="Copiar información", style="Accent.TButton", command=copiar).pack(side="left")
    ttk.Button(barra, text="Cerrar", command=ventana.destroy).pack(side="right")

    cuerpo = ttk.Frame(ventana)
    cuerpo.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    caja = tk.Text(cuerpo, wrap="word", font=("Segoe UI", 10), padx=14, pady=8,
                   bg="white", relief="flat")
    scroll = ttk.Scrollbar(cuerpo, orient="vertical", command=caja.yview)
    caja.configure(yscrollcommand=scroll.set)
    caja.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    caja.tag_configure("t", font=("Segoe UI", 16, "bold"), foreground=COLOR_PRIMARIO)
    caja.tag_configure("n", font=("Segoe UI", 12, "bold"), spacing3=4)
    caja.tag_configure("h", font=("Segoe UI", 11, "bold"), background="#DCFCE7",
                       foreground=COLOR_PRIMARIO, spacing1=12, spacing3=4)
    caja.tag_configure("i", font=("Segoe UI", 10))
    caja.tag_configure("m", font=("Segoe UI", 10, "italic"), foreground="#6B7280")

    lineas = lineas_consulta_grupo(g)
    for estilo, texto in lineas:
        caja.insert("end", texto + "\n", estilo)
    caja.configure(state="disabled")


# ==========================================================
# VENTANA EMERGENTE DE CONSULTA DE INVESTIGADOR (CON SCRAPING EN VIVO)
# ==========================================================
ORDEN_SECCIONES_INVESTIGADOR = ("Identificación", "Formación académica",
                                "Formación complementaria", "Experiencia profesional",
                                "Otra información personal")


def lineas_consulta_investigador(inv):
    productos = lista_recorrer(inv["productos"])
    L = [("t", "HOJA DE VIDA - INVESTIGADOR"), ("n", "%s  —  %s" % (inv["id"], inv["nombre"])),
         ("h", "Datos básicos"),
         ("i", "   • ID: " + inv["id"]), ("i", "   • Nombre completo: " + inv["nombre"]),
         ("i", "   • Código CvLAC (cod_rh): " + (inv["cod_rh"] or "N/D")),
         ("i", "   • Correo: " + (inv["email"] or "N/D")),
         ("i", "   • Formación: " + (inv["formacion"] or "N/D")),
         ("i", "   • Categoría: " + inv["categoria"]),
         ("i", "   • Activo en el programa: " + si_no(inv["activo"]))]
    L += lineas_ficha(inv, ORDEN_SECCIONES_INVESTIGADOR, False)
    L += lineas_ficha(inv, secciones_restantes(inv, ORDEN_SECCIONES_INVESTIGADOR), False)
    L += lineas_resumen_productos(productos)
    return L


def accion_consultar_investigador():
    id_inv = exigir_seleccion(APP["tabla_inv"])
    if id_inv is None:
        return
    inv = investigador_consultar(APP["sis"], id_inv)
    if inv is None:
        return

    ventana = tk.Toplevel(APP["raiz"])
    ventana.title("Consultar Investigador (CvLAC) - %s" % inv['nombre'])
    ventana.geometry("950x650")
    ventana.configure(bg=COLOR_FONDO)

    def copiar():
        ventana.clipboard_clear()
        ventana.clipboard_append(caja.get("1.0", "end"))
        messagebox.showinfo("Copiado", "Información copiada al portapapeles", parent=ventana)

    barra = ttk.Frame(ventana)
    barra.pack(fill="x", padx=12, pady=(12, 4))
    ttk.Button(barra, text="Copiar información", style="Accent.TButton", command=copiar).pack(side="left")
    ttk.Button(barra, text="Cerrar", command=ventana.destroy).pack(side="right")

    cuerpo = ttk.Frame(ventana)
    cuerpo.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    caja = tk.Text(cuerpo, wrap="word", font=("Segoe UI", 10), padx=14, pady=8,
                   bg="white", relief="flat")
    scroll = ttk.Scrollbar(cuerpo, orient="vertical", command=caja.yview)
    caja.configure(yscrollcommand=scroll.set)
    caja.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    caja.tag_configure("t", font=("Segoe UI", 16, "bold"), foreground=COLOR_PRIMARIO)
    caja.tag_configure("n", font=("Segoe UI", 12, "bold"), spacing3=4)
    caja.tag_configure("h", font=("Segoe UI", 11, "bold"), background="#DCFCE7",
                       foreground=COLOR_PRIMARIO, spacing1=12, spacing3=4)
    caja.tag_configure("i", font=("Segoe UI", 10))
    caja.tag_configure("m", font=("Segoe UI", 10, "italic"), foreground="#6B7280")

    # Mostrar datos base locales primero
    lineas_locales = lineas_consulta_investigador(inv)
    for estilo, texto in lineas_locales:
        caja.insert("end", texto + "\n", estilo)
    
    caja.insert("end", "\n" + "="*80 + "\n\n", "h")
    caja.insert("end", "⏳ Realizando scraping en tiempo real del CvLAC de Minciencias...\n", "m")
    ventana.update_idletasks()

    # Ejecutar el scraping en vivo usando el cod_rh del investigador
    if inv.get("cod_rh"):
        lineas_web = hacer_scraping_cvlac(inv["cod_rh"])
        caja.delete("1.0", "end")
        for estilo, texto in lineas_locales:
            caja.insert("end", texto + "\n", estilo)
        
        if isinstance(lineas_web, str):
            caja.insert("end", lineas_web + "\n", "m")
        else:
            for estilo, texto in lineas_web:
                caja.insert("end", texto + "\n", estilo)
    else:
        caja.insert("end", "⚠️ El investigador no tiene un 'cod_rh' (código CvLAC) registrado para realizar el scraping web automático.\n", "m")

    caja.configure(state="disabled")


def actualizar_estado():
    sis = APP["sis"]
    conteos = ("Grupos: %d  |  Investigadores: %d  |  Productos: %d"
               % (sis["grupos"]["tam"], sis["investigadores"]["tam"],
                  sis["productos"]["tam"]))
    prefijo = APP["mensaje"] + "      •      " if APP["mensaje"] else ""
    APP["estado"].set(prefijo + conteos)
    APP["raiz"].title("PEA-i - Universidad Popular del Cesar" + (" *" if APP["sucio"] else ""))


def refrescar_todo():
    refrescar_grupos()
    refrescar_investigadores()
    refrescar_filtros_productos()
    refrescar_productos()
    refrescar_dashboard()
    actualizar_estado()


def cambiar_ventana():
    texto = APP["ventana_txt"].get()
    if texto == "Histórico completo":
        n = 0
    elif texto == "Personalizado...":
        n = simpledialog.askinteger("Ventana", "¿Cuántos años hacia atrás?", parent=APP["raiz"])
        if n is None:
            return
        APP["ventana_txt"].set(texto_ventana(n))
    else:
        n = int(texto.split()[1])
    APP["ventana_n"] = n
    refrescar_todo()


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
    estilo.configure("TNotebook.Tab", padding=(16, 7), font=("Segoe UI", 10, "bold"))


def construir_menu():
    APP["raiz"].bind("<Control-s>", lambda e: guardar())


def definicion_menus():
    return [
        ("Archivo", [("Nuevo", nuevo_vacio), ("Abrir...", abrir_archivo),
                     ("Guardar      Ctrl+S", guardar), ("Guardar como...", guardar_como), None,
                     ("Ejemplo", cargar_ejemplo), None,
                     ("Exportar TXT...", accion_exportar_txt),
                     ("Abrir TXT...", accion_abrir_txt), None,
                     ("Salir", cerrar_app)]),
        ("Importar", [("Desde URL...", accion_importar_url),
                      ("Desde archivo...", accion_importar_archivo),
                      ("Crear plantilla CSV...", lambda: crear_plantilla_csv("plantilla.csv"))]),
    ]


def construir_barra_menus():
    barra = tk.Frame(APP["raiz"], bg=COLOR_MENU)
    barra.pack(fill="x")
    for titulo, opciones in definicion_menus():
        boton = tk.Menubutton(barra, text=titulo + "  ▾", bg=COLOR_MENU, fg="white",
                              activebackground=COLOR_ACENTO, activeforeground="white",
                              relief="flat", bd=0, padx=16, pady=7, cursor="hand2",
                              font=("Segoe UI", 10, "bold"))
        menu = tk.Menu(boton, tearoff=0, font=("Segoe UI", 10))
        for opcion in opciones:
            if opcion is None:
                menu.add_separator()
            else:
                menu.add_command(label=opcion[0], command=opcion[1])
        boton.configure(menu=menu)
        boton.pack(side="left")


def construir_encabezado():
    marco = tk.Frame(APP["raiz"], bg=COLOR_PRIMARIO)
    marco.pack(fill="x")
    textos = tk.Frame(marco, bg=COLOR_PRIMARIO)
    textos.pack(side="left", padx=14, pady=8)
    tk.Label(textos, text="Universidad Popular del Cesar", bg=COLOR_PRIMARIO, fg="white",
             font=("Segoe UI", 15, "bold")).pack(anchor="w")
    tk.Label(textos, text="PEA-i · Programa Estadístico de Análisis de Investigación",
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
    ttk.Checkbutton(barra, text="Mostrar inactivos",
                    variable=APP["ver_inactivos"], command=refrescar_todo).pack(
        side="left", padx=16)
    ttk.Button(barra, text="💾 Guardar", command=guardar).pack(side="right", padx=6)


def construir_estado():
    APP["estado"] = tk.StringVar()
    tk.Label(APP["raiz"], textvariable=APP["estado"], anchor="w", bg="#E5E7EB",
             fg="#374151", font=("Segoe UI", 9), padx=10, pady=4).pack(side="bottom",
                                                                      fill="x")


def construir_tab_grupos(padre):
    botones = barra_botones(padre, [
        ("Nuevo", accion_grupo_nuevo, True), ("Consultar", accion_consultar_grupo, True),
        ("Editar", accion_grupo_editar, False), ("Integrantes", abrir_integrantes, False),
        ("Activar / Desactivar", accion_grupo_alternar, False),
        ("Eliminar", accion_grupo_eliminar, False)])
    botones.pack(fill="x", padx=10, pady=10)
    columnas = [("codigo", "Código", 90), ("nombre", "Nombre del grupo", 290),
                ("lider", "Líder", 180), ("categoria", "Estado", 80),
                ("clasificado", "Clasificado en", 170),
                ("integrantes", "Integrantes", 85), ("productos", "Productos", 75),
                ("activo", "Activo", 55)]
    marco, APP["tabla_grupos"] = crear_tabla(padre, columnas)
    marco.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    APP["tabla_grupos"].bind("<Double-1>", lambda e: abrir_integrantes())


def construir_tab_investigadores(padre):
    botones = barra_botones(padre, [
        ("Nuevo", accion_inv_nuevo, True), ("Consultar", accion_consultar_investigador, True),
        ("Editar", accion_inv_editar, False),
        ("Ver sus productos", accion_inv_ver_productos, False),
        ("Activar / Desactivar", accion_inv_alternar, False),
        ("Eliminar", accion_inv_eliminar, False)])
    botones.pack(fill="x", padx=10, pady=10)
    columnas = [("id", "ID", 80), ("nombre", "Nombre", 230),
                ("nacionalidad", "Nacionalidad", 100), ("cod_rh", "Cod. CvLAC", 100),
                ("email", "Correo", 170), ("formacion", "Formación", 110),
                ("categoria", "Categoría", 140), ("productos", "Productos", 75),
                ("activo", "Activo", 55)]
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
        ttk.Label(padre, text="Instale matplotlib para ver las gráficas.", font=("Segoe UI", 12)).pack(pady=40)


def construir_pestanas():
    cuaderno = ttk.Notebook(APP["raiz"])
    cuaderno.pack(fill="both", expand=True, padx=10, pady=8)
    APP["tabs"] = cuaderno
    
    constructores = [("  Grupos  ", construir_tab_grupos),
                     ("  Investigadores  ", construir_tab_investigadores),
                     ("  Productos  ", construir_tab_productos),
                     ("  Estadísticas  ", construir_tab_estadisticas)]
    for titulo, construir in constructores:
        marco = ttk.Frame(cuaderno)
        cuaderno.add(marco, text=titulo)
        construir(marco)
        if titulo.strip() == "Productos":
            APP["tab_productos"] = marco


def iniciar():
    if tk is None:
        print("Tkinter no está disponible.")
        return
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
    construir_barra_menus()
    construir_barra_herramientas()
    construir_estado()
    construir_pestanas()
    refrescar_todo()
    raiz.protocol("WM_DELETE_WINDOW", cerrar_app)
    raiz.after(300, preguntar_inicio)
    raiz.mainloop()


# ==========================================================
# MODO CONSOLA (lo usa el programa en C++ para delegar el scraping en Python)
#   python Taller2_PEAi.py --cli --datos datos.txt --importar url "https://..." [--modo auto]
#   python Taller2_PEAi.py --cli --datos datos.txt --importar html listado.html
#   python Taller2_PEAi.py --cli --datos datos.txt --importar html cv.html --modo investigador --grupo COL0218897
#   python Taller2_PEAi.py --cli --datos datos.txt --procesar-cola
# Lee --datos (.txt PEA-i o .json), importa, y vuelve a escribir el resultado en --salida
# (por defecto el mismo archivo). Código de salida 0 = correcto, 1 = error.
# ==========================================================
def cli_cargar(ruta):
    if not os.path.exists(ruta):
        return sistema_crear(), None
    if ruta.lower().endswith(".json"):
        sis, avisos, error = cargar_json(ruta)
    else:
        sis, avisos, error = importar_txt(ruta)
    for a in avisos[:5]:
        print("  ! " + a)
    return sis, error


def cli_guardar(sis, ruta):
    if ruta.lower().endswith(".json"):
        return guardar_json(sis, ruta)
    return exportar_txt(sis, ruta)


def cli_procesar_cola(sis):
    cola = sis["importaciones"]
    if cola["tam"] == 0:
        print("La cola de importaciones está vacía.")
        return
    correctas = 0
    fallidas = []
    numero = 0
    while not cola_vacia(cola):          # incluye lo que se vaya encolando (CvLAC de integrantes)
        numero += 1
        item = cola_desencolar(cola)
        etiqueta = item.get("codigo") or item["origen"]
        print("[%d | quedan %d] %s %s" % (numero, cola["tam"], item.get("modo", ""), etiqueta))
        datos, error = leer_origen(item["tipo"], item["origen"], "auto", item)
        if error is None:
            informe, error = importar_datos(sis, datos, None, item.get("codigo"), True)
        if error:
            print("   ERROR: " + error.splitlines()[0])
            item["estado"] = ("error: " + error.splitlines()[0])[:60]
            fallidas.append(item)
        else:
            correctas += 1
            print("   OK: %d productos nuevos, %d integrantes nuevos"
                  % (informe["productos_nuevos"], informe["integrantes_nuevos"]))
        if not cola_vacia(cola):
            time.sleep(2)                 # pausa entre descargas
    for item in fallidas:
        cola_encolar(cola, item)
    print("\nCola procesada: %d correctas, %d con error (siguen en la cola)"
          % (correctas, len(fallidas)))


def main_cli(argv):
    ap = argparse.ArgumentParser(description="PEA-i sin interfaz gráfica")
    ap.add_argument("--datos", required=True, help="archivo de datos (.txt PEA-i o .json)")
    ap.add_argument("--salida", help="archivo de salida (por defecto, el mismo de --datos)")
    ap.add_argument("--importar", nargs=2, metavar=("TIPO", "ORIGEN"),
                    help="TIPO: url | html | pdf | csv")
    ap.add_argument("--modo", default="auto", choices=["auto", "grupo", "investigador"])
    ap.add_argument("--grupo", default="", help="código del grupo (para un CvLAC)")
    ap.add_argument("--procesar-cola", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sis, error = cli_cargar(args.datos)
    if error:
        print("ERROR: " + error)
        return 1
    salida = args.salida or args.datos
    try:
        if args.importar:
            tipo, origen = args.importar
            datos, error = leer_origen(tipo, origen, args.modo)
            if error == MODO_NO_DETECTADO:
                print("ERROR: no se pudo determinar si la fuente es un grupo o un investigador. "
                      "Indique el contenido.")
                return 1
            if error:
                print("ERROR: " + error)
                return 1
            if datos["modo"] == "investigador" and not args.grupo:
                print("ERROR: para importar un CvLAC indique el grupo al que se asocian "
                      "los productos.")
                return 1
            print(describir_datos(datos) + "\n")
            informe, error = importar_datos(sis, datos, None, args.grupo or None)
            if error:
                print("ERROR: " + error)
                return 1
            print(informe_texto(informe))
        if args.procesar_cola:
            cli_procesar_cola(sis)
    finally:
        error = cli_guardar(sis, salida)
        if error:
            print("ERROR al guardar: " + error)
    return 0


if __name__ == "__main__":
    if "--cli" in sys.argv:
        sys.exit(main_cli([a for a in sys.argv[1:] if a != "--cli"]))
    iniciar()
