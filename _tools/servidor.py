#!/usr/bin/env python3
"""Servidor estático local para desarrollo y verificación de CircuitoLab.

Uso:
    python3 _tools/servidor.py [puerto]

Por defecto sirve en 127.0.0.1:8766 (solo local, sin exposure en la red).
"""
import http.server
import os
import socketserver
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Manejador(http.server.SimpleHTTPRequestHandler):
    # HTTP/1.1 mantiene viva la conexión entre peticiones. Con el HTTP/1.0 por
    # defecto, Chromium reutiliza una conexión que el servidor ya cerró y salta
    # un ERR_CONNECTION_RESET en la primera imagen (el logo) al cargar.
    protocol_version = "HTTP/1.1"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=RAIZ, **kw)

    def end_headers(self):
        # sin caché, para que los cambios se vean al recargar
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def handle_one_request(self):
        # el cliente puede cortar la conexión (recarga durante la descarga de
        # una imagen): no debe matar el servidor ni ensuciar el log
        try:
            super().handle_one_request()
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            self.close_connection = True

    def log_message(self, formato, *args):
        # solo las peticiones con error
        if " 200 " not in formato % args:
            sys.stderr.write("%s - %s\n" % (self.address_string(), formato % args))


class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
    with Servidor(("127.0.0.1", puerto), Manejador) as httpd:
        print(f"CircuitoLab servido en http://127.0.0.1:{puerto}/")
        print("Ctrl+C para parar.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")


if __name__ == "__main__":
    main()
