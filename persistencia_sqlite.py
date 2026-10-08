# -*- coding: utf-8 -*-
"""
PEA-i - Persistencia en BASE DE DATOS (SQLite) - complemento 14.b del taller.

Usa solo la librería estándar (sqlite3). Es independiente de Tkinter y trabaja con
los mismos diccionarios que ya produce tu programa:

    sistema_a_dict(sis)      -> dict   --->  guardar_sqlite(dic, "pea_i.db")
    cargar_sqlite("pea_i.db") -> dict  --->  sistema_desde_dict(dic)

Así las LISTAS/PILAS/COLAS siguen siendo la estructura en memoria y la BD es
solo la capa de persistencia (la BD también sirve para interoperar con C/C++ o Rust,
que pueden leer el mismo archivo .db).
"""
import json
import sqlite3

ESQUEMA = """
CREATE TABLE IF NOT EXISTS meta (
    clave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE IF NOT EXISTS grupo (
    codigo TEXT PRIMARY KEY, nombre TEXT NOT NULL, lider TEXT,
    categoria TEXT, url TEXT, activo INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS investigador (
    id TEXT PRIMARY KEY, nombre TEXT NOT NULL, cod_rh TEXT, email TEXT,
    formacion TEXT, categoria TEXT, activo INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS integrante (
    codigo_grupo TEXT NOT NULL REFERENCES grupo(codigo) ON DELETE CASCADE,
    id_investigador TEXT NOT NULL REFERENCES investigador(id) ON DELETE CASCADE,
    vinculacion TEXT, horas TEXT, periodo TEXT,
    activo INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (codigo_grupo, id_investigador));
CREATE TABLE IF NOT EXISTS producto (
    id TEXT PRIMARY KEY, titulo TEXT NOT NULL, tipo TEXT, categoria TEXT,
    anio INTEGER, validado INTEGER NOT NULL DEFAULT 0,
    codigo_grupo TEXT REFERENCES grupo(codigo) ON DELETE CASCADE,
    activo INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS producto_autor (
    id_producto TEXT NOT NULL REFERENCES producto(id) ON DELETE CASCADE,
    id_investigador TEXT NOT NULL,
    PRIMARY KEY (id_producto, id_investigador));
CREATE TABLE IF NOT EXISTS importacion (
    orden INTEGER PRIMARY KEY AUTOINCREMENT, datos TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_prod_anio  ON producto(anio);
CREATE INDEX IF NOT EXISTS ix_prod_grupo ON producto(codigo_grupo);
CREATE INDEX IF NOT EXISTS ix_prod_tipo  ON producto(tipo);
"""


def _b(valor):
    return 1 if valor else 0


def guardar_sqlite(dic, ruta):
    """Guarda el diccionario del sistema. Devuelve None si OK o el mensaje de error.
    Se reescribe todo dentro de UNA transacción: o se guarda completo o no se toca."""
    try:
        con = sqlite3.connect(ruta)
        con.execute("PRAGMA foreign_keys = OFF")      # se borra y reinserta todo
        con.executescript(ESQUEMA)
        with con:                                       # transacción atómica
            for tabla in ("producto_autor", "producto", "integrante",
                          "investigador", "grupo", "importacion", "meta"):
                con.execute("DELETE FROM " + tabla)
            con.execute("INSERT INTO meta VALUES ('contador_prod', ?)",
                        (str(dic.get("contador_prod", 0)),))
            con.execute("INSERT INTO meta VALUES ('contador_inv', ?)",
                        (str(dic.get("contador_inv", 0)),))
            for g in dic.get("grupos", []):
                con.execute("INSERT INTO grupo VALUES (?,?,?,?,?,?)",
                            (g["codigo"], g["nombre"], g.get("lider"),
                             g.get("categoria"), g.get("url"), _b(g.get("activo", True))))
                for i in g.get("integrantes", []):
                    con.execute("INSERT OR REPLACE INTO integrante VALUES (?,?,?,?,?,?)",
                                (g["codigo"], i["id_investigador"], i.get("vinculacion"),
                                 str(i.get("horas", "")), i.get("periodo"),
                                 _b(i.get("activo", True))))
            for i in dic.get("investigadores", []):
                con.execute("INSERT INTO investigador VALUES (?,?,?,?,?,?,?)",
                            (i["id"], i["nombre"], i.get("cod_rh"), i.get("email"),
                             i.get("formacion"), i.get("categoria"),
                             _b(i.get("activo", True))))
            for p in dic.get("productos", []):
                con.execute("INSERT INTO producto VALUES (?,?,?,?,?,?,?,?)",
                            (p["id"], p["titulo"], p.get("tipo"), p.get("categoria"),
                             p.get("anio"), _b(p.get("validado")), p.get("grupo"),
                             _b(p.get("activo", True))))
                for a in p.get("investigadores", []):
                    con.execute("INSERT OR IGNORE INTO producto_autor VALUES (?,?)",
                                (p["id"], a))
            for imp in dic.get("importaciones", []):
                con.execute("INSERT INTO importacion (datos) VALUES (?)",
                            (json.dumps(imp, ensure_ascii=False),))
        con.close()
    except sqlite3.Error as e:
        return "No se pudo guardar en la base de datos: %s" % e
    return None


def cargar_sqlite(ruta):
    """Devuelve (diccionario, error). El diccionario tiene el mismo formato que
    sistema_a_dict(), listo para sistema_desde_dict()."""
    try:
        con = sqlite3.connect(ruta)
        con.row_factory = sqlite3.Row
        meta = {r["clave"]: r["valor"] for r in con.execute("SELECT * FROM meta")}
        dic = {"version": 1,
               "contador_prod": int(meta.get("contador_prod", 0)),
               "contador_inv": int(meta.get("contador_inv", 0)),
               "grupos": [], "investigadores": [], "productos": [], "importaciones": []}
        integrantes = {}
        for r in con.execute("SELECT * FROM integrante"):
            integrantes.setdefault(r["codigo_grupo"], []).append(
                {"id_investigador": r["id_investigador"], "vinculacion": r["vinculacion"],
                 "horas": r["horas"], "periodo": r["periodo"], "activo": bool(r["activo"])})
        for r in con.execute("SELECT * FROM grupo"):
            dic["grupos"].append({"codigo": r["codigo"], "nombre": r["nombre"],
                                  "lider": r["lider"], "categoria": r["categoria"],
                                  "url": r["url"], "activo": bool(r["activo"]),
                                  "integrantes": integrantes.get(r["codigo"], [])})
        for r in con.execute("SELECT * FROM investigador"):
            d = dict(r)
            d["activo"] = bool(d["activo"])
            dic["investigadores"].append(d)
        autores = {}
        for r in con.execute("SELECT * FROM producto_autor"):
            autores.setdefault(r["id_producto"], []).append(r["id_investigador"])
        for r in con.execute("SELECT * FROM producto"):
            dic["productos"].append({"id": r["id"], "titulo": r["titulo"], "tipo": r["tipo"],
                                     "categoria": r["categoria"], "anio": r["anio"],
                                     "validado": bool(r["validado"]), "grupo": r["codigo_grupo"],
                                     "investigadores": autores.get(r["id"], []),
                                     "activo": bool(r["activo"])})
        for r in con.execute("SELECT datos FROM importacion ORDER BY orden"):
            dic["importaciones"].append(json.loads(r["datos"]))
        con.close()
    except (sqlite3.Error, ValueError) as e:
        return None, "No se pudo leer la base de datos: %s" % e
    return dic, None
