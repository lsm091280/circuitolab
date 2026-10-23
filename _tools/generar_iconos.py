#!/usr/bin/env python3
"""Genera assets/icons/icons.js con los iconos MDI usados por la app.
Descarga una sola vez el set completo de @iconify-json/mdi y extrae los necesarios
(aliases incluidos). Resultado: un solo fichero local, cero CDN en runtime."""
import json
import os
import re
import sys

import os
import ssl
import urllib.request

try:
    import certifi
    _CA = certifi.where()
except Exception:
    _CA = None
_CTX = ssl.create_default_context(cafile=_CA) if _CA else ssl.create_default_context()


def fetch(url, timeout=180):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
        return r.read()

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(RAIZ, "assets", "icons")
CACHE = "/tmp/mdi_icons.json"

ICONOS = [
    "mdi:integrated-circuit", "mdi:magnify", "mdi:chevron-down", "mdi:chevron-up",
    "mdi:book-open-page-variant", "mdi:flask-outline", "mdi:school-outline",
    "mdi:theme-light-dark", "mdi:play", "mdi:pause", "mdi:information-outline",
    "mdi:check-circle-outline", "mdi:clock-outline", "mdi:lightbulb-on-outline",
    "mdi:pencil-outline", "mdi:download-outline", "mdi:open-in-new",
    "mdi:menu", "mdi:close", "mdi:chevron-left", "mdi:chevron-right",
    "mdi:alert-circle-outline", "mdi:school", "mdi:bookshelf",
    "mdi:electric-switch", "mdi:sine-wave", "mdi:resistor",
    "mdi:plus", "mdi:minus", "mdi:restore",
    "mdi:file-document-outline", "mdi:link-variant", "mdi:dots-horizontal",
    "mdi:playlist-check", "mdi:target", "mdi:eye-outline", "mdi:eye-off-outline",
    "mdi:refresh", "mdi:content-save-outline", "mdi:help-circle-outline",
    # iconos de las categorias de la galeria (agrupacion original del motor)
    "mdi:transmission-tower", "mdi:logic-gate-and", "mdi:timer-outline", "mdi:flash", "mdi:amplifier", "mdi:waveform", "mdi:sync", "mdi:package-variant", "mdi:filter-variant", "mdi:current-dc", "mdi:chart-bell-curve", "mdi:chip", "mdi:arrow-u-left-top", "mdi:pencil-ruler", "mdi:lock-outline",
]


def cargar_set():
    if os.path.exists(CACHE):
        return json.load(open(CACHE))
    url = "https://cdn.jsdelivr.net/npm/@iconify-json/mdi@latest/icons.json"
    print("descargando set MDI completo…")
    d = fetch(url, timeout=180)
    with open(CACHE, "wb") as f:
        f.write(d)
    print("set:", len(d), "bytes")
    return json.loads(d.decode("utf-8"))


def main():
    data = cargar_set()
    icons = data.get("icons", {})
    aliases = data.get("aliases", {})
    os.makedirs(OUT, exist_ok=True)

    svg_map = {}
    faltan = []
    for nombre in ICONOS:
        clave = nombre.split(":", 1)[1]
        cuerpo = None
        if clave in icons:
            cuerpo = icons[clave]["body"]
        elif clave in aliases:
            a = aliases[clave]
            padre = a["parent"]
            if padre in icons:
                cuerpo = icons[padre]["body"]
        if cuerpo is None:
            faltan.append(nombre)
            continue
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="1em" '
               'height="1em" fill="currentColor">' + cuerpo + "</svg>")
        svg = re.sub(r"\s+", " ", svg).strip()
        svg_map[nombre] = svg

    if faltan:
        print("NO ENCONTRADOS:", faltan)

    with open(os.path.join(OUT, "icons.js"), "w", encoding="utf-8") as f:
        f.write("/* Iconos MDI (Iconify) embebidos — familia obligatoria del brand tecnoLSM.\n")
        f.write("   Origen: @iconify-json/mdi (Material Design Icons, Apache-2.0 / MIT).\n")
        f.write("   Generado por _tools/generar_iconos.py — NO editar a mano. */\n")
        f.write("window.MDI = {\n")
        for k in ICONOS:
            if k in svg_map:
                f.write(f"  {json.dumps(k)}: {json.dumps(svg_map[k], ensure_ascii=False)},\n")
        f.write("};\n")

    # copia en HTML individual por si se quieren usar como <img>
    for k, v in svg_map.items():
        open(os.path.join(OUT, k.replace(":", "-") + ".svg"), "w", encoding="utf-8").write(v)

    print(f"{len(svg_map)}/{len(ICONOS)} iconos escritos en icons.js")
    if len(svg_map) != len(ICONOS):
        raise SystemExit("FALTAN iconos: " + ", ".join(faltan))


if __name__ == "__main__":
    main()
