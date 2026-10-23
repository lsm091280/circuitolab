#!/usr/bin/env python3
"""Descarga el motor CircuitJS1 y sus datos al proyecto, y genera el catálogo.

Es reproducible: se puede volver a ejecutar y deja lo mismo.

Uso:
    python3 _tools/descargar_motor.py

Fuentes:
  - motor:  https://circuitjs1.falstad.com/circuit/circuitjs111d/
  - repo:   https://github.com/sharpie7/circuitjs1 (GPL-2.0) — para la licencia
             y los docs del motor
"""
import os
import re
import ssl
import sys
import urllib.request

try:
    import certifi
    CA = certifi.where()
except Exception:
    CA = None

SSL_CTX = ssl.create_default_context(cafile=CA) if CA else ssl.create_default_context()
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(RAIZ, "assets", "vendor", "circuitjs")
ENGINE = os.path.join(VENDOR, "engine")

BASE_MOTOR = "https://circuitjs1.falstad.com/circuit/"
BASE_REPO = "https://raw.githubusercontent.com/sharpie7/circuitjs1/master/"

HTML_MOTOR = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Motor CircuitJS1</title>
<link rel="stylesheet" href="font/fontello.css">
<script type="module" crossorigin src="circuitjs-_Vd2jZk5.js"></script>
<link rel="stylesheet" crossorigin href="circuitjs-DDWVHsFC.css">
</head>
<body>
</body>
</html>
"""


def fetch(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
        return r.read()


def guardar(url, destino):
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    datos = fetch(url)
    with open(destino, "wb") as f:
        f.write(datos)
    return len(datos)


def main():
    # 1) el HTML de arranque propio (sin Dropbox, con rutas locales)
    os.makedirs(ENGINE, exist_ok=True)
    with open(os.path.join(ENGINE, "circuitjs.html"), "w", encoding="utf-8") as f:
        f.write(HTML_MOTOR)
    print("HTML de arranque del motor escrito")

    # 2) el bundle y su CSS se sacan de la pagina del sitio, que es la que
    #    declara los nombres reales de los ficheros (con hash)
    html = fetch(BASE_MOTOR + "circuitjs.html").decode("utf-8")
    js = re.search(r'src="\.?/?([^"]*circuitjs-[^"]*\.js)"', html)
    css = re.search(r'href="\.?/?([^"]*circuitjs-[^"]*\.css)"', html)
    if not js:
        print("ERROR: no se encuentra el bundle del motor en la pagina")
        return 1
    nombre_js = os.path.basename(js.group(1))
    nombre_css = os.path.basename(css.group(1)) if css else "circuitjs-DDWVHsFC.css"

    ficheros = [
        (BASE_MOTOR + js.group(1), os.path.join(ENGINE, nombre_js)),
        (BASE_MOTOR + (css.group(1) if css else "circuitjs111d/" + nombre_css),
         os.path.join(ENGINE, nombre_css)),
        (BASE_MOTOR + "circuitjs111d/setuplist.txt", os.path.join(ENGINE, "setuplist.txt")),
        (BASE_MOTOR + "circuitjs111d/locale/locale_es.txt",
         os.path.join(ENGINE, "locale", "locale_es.txt")),
        (BASE_MOTOR + "circuitjs111d/font/fontello.css", os.path.join(ENGINE, "font", "fontello.css")),
        (BASE_REPO + "war/lz-string.min.js", os.path.join(VENDOR, "lz-string.min.js")),
        (BASE_REPO + "COPYING.txt", os.path.join(VENDOR, "COPYING.txt")),
        (BASE_REPO + "COPYING.txt", os.path.join(RAIZ, "LICENCIA-GPL-2.0.txt")),
        (BASE_REPO + "README.md", os.path.join(VENDOR, "docs-motor", "README.md")),
        (BASE_REPO + "INTERNALS.md", os.path.join(VENDOR, "docs-motor", "INTERNALS.md")),
    ]
    for f in ["fontello.woff2", "fontello.woff", "fontello.ttf", "fontello.eot", "fontello.svg"]:
        ficheros.append((BASE_MOTOR + "circuitjs111d/font/" + f, os.path.join(ENGINE, "font", f)))

    for url, destino in ficheros:
        try:
            n = guardar(url, destino)
            print(f"OK   {os.path.relpath(destino, RAIZ):58s} {n:>9,} bytes")
        except Exception as e:
            print(f"FALLO {url}: {e}")

    # 3) los 367 circuitos, leidos del setuplist
    txt = open(os.path.join(ENGINE, "setuplist.txt"), encoding="utf-8", errors="replace").read()
    nombres = []
    for linea in txt.splitlines():
        if not linea or linea[0] in "#+-":
            continue
        i = linea.find(" ")
        if i > 0:
            f = linea[:i]
            nombres.append(f[1:] if f.startswith(">") else f)
    print(f"\ncircuitos en el setuplist: {len(nombres)}")
    fallos = 0
    for n in nombres:
        destino = os.path.join(ENGINE, "circuits", n)
        if os.path.exists(destino):
            continue
        try:
            guardar(BASE_MOTOR + "circuitjs111d/circuits/" + n, destino)
        except Exception as e:
            print(f"  FALLO {n}: {e}")
            fallos += 1
    total = len([f for f in os.listdir(os.path.join(ENGINE, "circuits")) if f.endswith(".txt")])
    print(f"circuitos en disco: {total} | fallos: {fallos}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
