#!/usr/bin/env python3
"""Trae images/hborder.png del motor original (una sola imagen que el CSS de
GWT pide para el borde del menu). Si no se puede descargar, crea un PNG
transparente 1x1: el CSS del brand repinta ese borde, asi que la imagen no se ve,
pero el navegador la pide igual y deja un 404 en consola."""
import os
import ssl
import struct
import urllib.request
import zlib

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    CTX = ssl.create_default_context()

DEST = "/Users/luissolamantilla/Downloads/circuitolab/assets/vendor/circuitjs/engine/images"
URL = "https://circuitjs1.falstad.com/circuit/images/hborder.png"

os.makedirs(DEST, exist_ok=True)
destino = os.path.join(DEST, "hborder.png")

ok = False
try:
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
        datos = r.read()
    if datos[:8] == b"\x89PNG\r\n\x1a\n":
        with open(destino, "wb") as f:
            f.write(datos)
        print(f"descargado: {len(datos)} bytes -> {destino}")
        ok = True
    else:
        print("respuesta no es PNG, se genera uno transparente")
except Exception as e:
    print("no se pudo descargar:", e)


def png_transparente(ruta, w=1, h=1):
    """PNG RGBA de w x h totalmente transparente, sin dependencias."""
    def trozo(tipo, datos):
        return (struct.pack(">I", len(datos)) + tipo + datos +
                struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF))
    cabecera = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    fila = b"\x00" + b"\x00\x00\x00\x00" * w
    datos = zlib.compress(fila * h, 9)
    png = b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", cabecera) + trozo(b"IDAT", datos) + trozo(b"IEND", b"")
    with open(ruta, "wb") as f:
        f.write(png)
    return len(png)


if not ok:
    n = png_transparente(destino)
    print(f"generado PNG transparente: {n} bytes -> {destino}")

print("tamaño final:", os.path.getsize(destino), "bytes")
