#!/usr/bin/env python3
"""Genera assets/fonts/fonts.css con las tipografías del brand AUTOALOJADAS.

Descarga el CSS de Google Fonts y cada .woff2, y reescribe las URLs para que
apunte a los ficheros locales. Nada de CDN en runtime: la app funciona sin red.

Uso: python3 _tools/generar_fuentes.py
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
DESTINO = os.path.join(RAIZ, "assets", "fonts")

FAMILIAS = [
    ("Space+Grotesk", "wght@400;500;600;700"),
    ("DM+Sans", "wght@400;500;600;700"),
    ("IBM+Plex+Mono", "wght@400;500;600"),
]


def fetch(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
        return r.read()


def main():
    os.makedirs(DESTINO, exist_ok=True)
    # borrar los woff2 viejos para no dejar huérfanos
    for f in os.listdir(DESTINO):
        if f.endswith(".woff2"):
            os.remove(os.path.join(DESTINO, f))

    css_final = ["/* Tipografías del brand tecnoLSM autoalojadas.",
                 "   Space Grotesk, DM Sans e IBM Plex Mono.",
                 "   SIL Open Font License 1.1. Generado por _tools/generar_fuentes.py. */", ""]
    n_desc = 0
    externas = 0

    for fam, ejes in FAMILIAS:
        url = f"https://fonts.googleapis.com/css2?family={fam}:{ejes}&display=swap"
        css = fetch(url).decode("utf-8")
        urls = []
        for u in re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)", css):
            if u not in urls:
                urls.append(u)
        css_final.append(f"/* ---- {fam.replace('+', ' ')} ---- */")
        for i, u in enumerate(urls):
            nombre = f"{fam.split('+')[0].lower()}-{i}.woff2"
            datos = fetch(u)
            with open(os.path.join(DESTINO, nombre), "wb") as f:
                f.write(datos)
            n_desc += 1
            css = css.replace(u, f"./{nombre}")
        # quitar el bloque de vietnamese (no hace falta) para reducir peso
        css = re.sub(r"/\* vietnamese \*/\s*@font-face \{[^}]*\}\s*", "", css)
        css_final.append(css.strip())
        css_final.append("")

    ruta_css = os.path.join(DESTINO, "fonts.css")
    with open(ruta_css, "w", encoding="utf-8") as f:
        f.write("\n".join(css_final))

    texto = open(ruta_css, encoding="utf-8").read()
    externas = len(re.findall(r"https?://(?!www\.w3\.org)", texto))
    print(f"descargados {n_desc} ficheros woff2")
    print(f"fonts.css: {len(texto)} bytes | referencias externas: {externas}")
    if externas:
        print("ERROR: quedan URLs externas en fonts.css")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
