#!/usr/bin/env python3
"""Genera circuitos/catalogo.json y circuitos/estructura.json a partir de:
  1) el setuplist.txt del motor (367 circuitos, con su jerarquía de categorías);
  2) el mapa real de tipos extraído del Java del motor (CirSim.java), para
     poder leer los valores de cada circuito y verificarlos;
  3) las fichas de explicación (circuitos/explicaciones/*.json).

Uso:
    python3 _tools/generar_catalogo.py

El motor NO se modifica: solo se leen sus ficheros.
"""
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(RAIZ, "assets", "vendor", "circuitjs", "engine")
SALIDA_CAT = os.path.join(RAIZ, "circuitos", "catalogo.json")
SALIDA_EST = os.path.join(RAIZ, "circuitos", "estructura.json")
DIR_FICHAS = os.path.join(RAIZ, "circuitos", "explicaciones")

ORDEN_CURSO = ["3º ESO", "4º ESO", "Bachillerato"]

# Asignación de curso por categoría (mapeo didáctico; se puede ajustar aquí).
CURSO_POR_CATEGORIA = {
    "Basics": "3º ESO",
    "A/C Circuits": "4º ESO",
    "Passive Filters": "4º ESO",
    "Other Passive Circuits": "4º ESO",
    "Diodes": "4º ESO",
    "Transistors": "4º ESO",
    "555 Timer Chip": "4º ESO",
    "Logic Families": "4º ESO",
    "Combinational Logic": "4º ESO",
    "Misc Devices": "Bachillerato",
    "Sequential Logic": "Bachillerato",
    "Op-Amps": "Bachillerato",
}

# Circuitos concretos con nivel introductorio aunque su categoría diga otra cosa.
CURSO_OVERRIDE = {
    "ohms.txt": "3º ESO", "resistors.txt": "3º ESO", "lightbulb.txt": "3º ESO",
    "pot.txt": "4º ESO", "voltdivide.txt": "4º ESO", "cap.txt": "4º ESO",
    "induct.txt": "4º ESO", "relay.txt": "4º ESO", "diodelimit.txt": "4º ESO",
    "rectify.txt": "4º ESO", "npn.txt": "4º ESO", "pnp.txt": "4º ESO",
    "555square.txt": "4º ESO", "555monostable.txt": "4º ESO", "sine.txt": "4º ESO",
    "traffic.txt": "4º ESO",
    # los op-amps y los secuenciales empiezan en Bachillerato: se quitan del
    # override para que mande la categoría
    "opamp.txt": "Bachillerato",
    "clockedsrff.txt": "Bachillerato",
}


def parsear_setuplist(texto):
    entradas = []
    pila = []
    for linea in texto.splitlines():
        if not linea or linea.startswith("#"):
            continue
        if linea.startswith("+"):
            pila.append(linea[1:].strip())
        elif linea.startswith("-"):
            if pila:
                pila.pop()
        else:
            i = linea.find(" ")
            if i > 0:
                f = linea[:i]
                anidado = f.startswith(">")
                if anidado:
                    f = f[1:]
                jerarquia = list(pila)
                entradas.append({
                    "archivo": f,
                    "titulo": linea[i + 1:].strip(),
                    "categoria": jerarquia[0] if jerarquia else "Otros",
                    "subcategoria": jerarquia[1] if len(jerarquia) > 1 else "",
                    "jerarquia": jerarquia,
                })
    return entradas


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def cargar_fichas():
    """Carga las fichas de explicación de circuitos/explicaciones/*.json."""
    fichas = {}
    if not os.path.isdir(DIR_FICHAS):
        return fichas
    for nombre in sorted(os.listdir(DIR_FICHAS)):
        if not nombre.endswith(".json"):
            continue
        with open(os.path.join(DIR_FICHAS, nombre), encoding="utf-8") as f:
            for cid, ficha in json.load(f).items():
                fichas[cid] = ficha
    return fichas


def cargar_titulos():
    """Títulos traducidos al español (circuitos/titulos-es.json)."""
    ruta = os.path.join(RAIZ, "circuitos", "titulos-es.json")
    if not os.path.exists(ruta):
        return {}
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def cargar_categorias():
    """Categorías y subcategorías traducidas (circuitos/categorias-es.json)."""
    ruta = os.path.join(RAIZ, "circuitos", "categorias-es.json")
    if not os.path.exists(ruta):
        return {}
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def main():
    setuplist = os.path.join(ENGINE, "setuplist.txt")
    if not os.path.exists(setuplist):
        print("ERROR: no existe el setuplist del motor. Ejecuta antes _tools/descargar_motor.py")
        return 1

    texto = open(setuplist, encoding="utf-8", errors="replace").read()
    entradas = parsear_setuplist(texto)
    print(f"entradas parseadas: {len(entradas)}")

    fichas = cargar_fichas()
    print(f"fichas de explicación cargadas: {len(fichas)}")

    titulos = cargar_titulos()
    print(f"títulos traducidos: {len(titulos)}")

    cats = cargar_categorias()
    print(f"categorías traducidas: {len(cats)}")

    catalogo = []
    completas = 0
    sin_traducir = []
    vistos = {}
    duplicados = []
    for e in entradas:
        clave = ">".join(e["jerarquia"])
        curso = CURSO_OVERRIDE.get(e["archivo"]) or CURSO_POR_CATEGORIA.get(e["categoria"], "Bachillerato")
        ruta = os.path.join(ENGINE, "circuits", e["archivo"])
        cid = slug(e["archivo"].replace(".txt", ""))
        # el setuplist del motor repite algun circuito en dos categorias
        # (p. ej. cmosinverter.txt). Se queda la primera aparicion para que el
        # id no choque y la galeria no muestre el mismo circuito dos veces.
        if e["archivo"] in vistos:
            duplicados.append((e["archivo"], vistos[e["archivo"]], clave))
            continue
        vistos[e["archivo"]] = clave
        ficha = fichas.get(cid)
        if ficha:
            completas += 1
        titulo_es = titulos.get(cid, "")
        if ficha and not titulo_es:
            sin_traducir.append(cid)
        catalogo.append({
            "id": cid,
            "archivo": e["archivo"],
            "titulo": e["titulo"],
            "titulo_es": titulo_es,
            "categoria": cats.get(e["categoria"], e["categoria"]),
            "subcategoria": cats.get(e["subcategoria"], e["subcategoria"]),
            "categoria_original": e["categoria"],
            "subcategoria_original": e["subcategoria"],
            "curso": curso,
            "url_circuito": "assets/vendor/circuitjs/engine/circuits/" + e["archivo"],
            "disponible": os.path.exists(ruta),
            "bytes": os.path.getsize(ruta) if os.path.exists(ruta) else 0,
            "estado": "completa" if ficha else "pendiente",
            "explicacion_html": (ficha or {}).get("como", ""),
            "que_observar": (ficha or {}).get("observar", ""),
            "prueba_tu": (ficha or {}).get("prueba", ""),
        })
    if sin_traducir:
        print("  AVISO: fichas sin título en español:", sin_traducir)
    if duplicados:
        print("  circuitos repetidos en el setuplist (se deja la primera aparición):")
        for arch, prim, seg in duplicados:
            print(f"     {arch}: {prim}  ->  descartada {seg}")

    def clave_orden(c):
        return (
            ORDEN_CURSO.index(c["curso"]) if c["curso"] in ORDEN_CURSO else 99,
            c["categoria"], c["subcategoria"], c["titulo"].lower(),
        )

    catalogo.sort(key=clave_orden)

    os.makedirs(os.path.dirname(SALIDA_CAT), exist_ok=True)
    with open(SALIDA_CAT, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=1)

    estructura = {}
    for c in catalogo:
        nodo = estructura.setdefault(c["curso"], {})
        cat = nodo.setdefault(c["categoria"], {})
        sub = cat.setdefault(c["subcategoria"] or "", [])
        sub.append({"id": c["id"], "titulo": c["titulo"], "estado": c["estado"],
                    "categoria": c["categoria"], "subcategoria": c["subcategoria"]})
    with open(SALIDA_EST, "w", encoding="utf-8") as f:
        json.dump(estructura, f, ensure_ascii=False, indent=1)

    print(f"catálogo escrito: {len(catalogo)} circuitos")
    print(f"  con explicación completa: {completas}")
    print(f"  pendientes: {len(catalogo) - completas}")
    for curso in ORDEN_CURSO:
        items = [c for c in catalogo if c["curso"] == curso]
        comp = sum(1 for c in items if c["estado"] == "completa")
        print(f"  {curso:14s} {comp:3d} de {len(items):3d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
