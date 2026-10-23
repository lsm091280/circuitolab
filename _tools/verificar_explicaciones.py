#!/usr/bin/env python3
"""Verifica la EXACTITUD de las explicaciones: cada valor numérico citado debe
existir en el circuito del motor, o ser un cálculo declarado, una propuesta de
cambio o un valor de contexto físico estándar.

Uso:
    python3 _tools/verificar_explicaciones.py

Necesita el mapa de tipos del motor. Lo extrae del propio bundle si no hay
un volcado previo: por eso lee los .txt y aplica el mapa de CirSim.java que
se descarga del repo (o usa la copia local si existe).

Salida: informe por pantalla. Código de salida 1 si hay algún ERROR.
"""
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(RAIZ, "assets", "vendor", "circuitjs", "engine")
CAT = os.path.join(RAIZ, "circuitos", "catalogo.json")
DIR_FICHAS = os.path.join(RAIZ, "circuitos", "explicaciones")

pat_num = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(V|mv|Ω|kΩ|MΩ|µF|uF|mF|pF|nF|H|mH|k|M|Hz|kHz|GHz|ms|µs|s)\b")
CALCULO = re.compile(r"calcula|resultado|sale |ser[aá] |=", re.I)
PROPUESTA = re.compile(r"sustituye|cambia|cambiar|pondr[ií]a|reemplaza", re.I)

# Valores de contexto físico estándar: no salen del .txt pero son conocimiento
# general, no invención. Se listan para que quede claro qué se admite.
GENERAL = {
    (0.7, "V"): "tensión de umbral de un diodo de silicio / unión base-emisor",
    (230.0, "V"): "tensión de la red eléctrica",
    (220.0, "V"): "tensión de la red eléctrica",
    (3.3, "V"): "tensión de un microcontrolador de 3,3 V",
}

CONV = {
    "kΩ": 1e3, "k": 1e3, "MΩ": 1e6, "M": 1e6, "mH": 1e-3,
    "µF": 1e-6, "uF": 1e-6, "mF": 1e-3, "nF": 1e-9, "pF": 1e-12,
    "kHz": 1e3, "GHz": 1e9, "ms": 1e-3, "µs": 1e-6, "mv": 1e-3,
}

# Mapa de códigos del formato .txt -> clase de elemento (de CirSim.java createCe).
MAPA = {
    ord('A'): "AntennaElm", ord('I'): "InverterElm", ord('L'): "LogicInputElm",
    ord('M'): "LogicOutputElm", ord('O'): "OutputElm", ord('R'): "RailElm",
    ord('S'): "Switch2Elm", ord('T'): "TransformerElm", ord('a'): "OpAmpElm",
    ord('b'): "BoxElm", ord('c'): "CapacitorElm", ord('d'): "DiodeElm",
    ord('f'): "MosfetElm", ord('g'): "GroundElm", ord('i'): "CurrentElm",
    ord('j'): "JfetElm", ord('l'): "InductorElm", ord('m'): "MemristorElm",
    ord('n'): "NoiseElm", ord('p'): "ProbeElm", ord('r'): "ResistorElm",
    ord('s'): "SwitchElm", ord('t'): "TransistorElm", ord('v'): "VoltageElm",
    ord('w'): "WireElm", ord('x'): "TextElm", ord('z'): "ZenerElm",
    150: "AndGateElm", 151: "NandGateElm", 152: "OrGateElm", 153: "NorGateElm",
    154: "XorGateElm", 155: "DFlipFlopElm", 156: "JKFlipFlopElm", 157: "SevenSegElm",
    162: "LEDElm", 163: "RingCounterElm", 164: "CounterElm", 165: "TimerElm",
    172: "VarRailElm", 174: "PotElm", 178: "RelayElm", 181: "LampElm",
    182: "SchmittElm", 370: "AmmeterElm", 419: "TestPointElm",
}


def num(t):
    try:
        return float(t)
    except Exception:
        return None


def valores_de_circuito(archivo):
    """Extrae los valores numéricos reales de un .txt del motor."""
    ruta = os.path.join(ENGINE, "circuits", archivo)
    if not os.path.exists(ruta):
        return set()
    vals = set()
    for linea in open(ruta, encoding="utf-8", errors="replace").read().splitlines():
        p = linea.split()
        if not p or p[0] == "$":
            continue
        cab = p[0]
        try:
            c = int(cab)
        except ValueError:
            c = ord(cab[0])
        if c in (34, 32, 38, 46) or c not in MAPA:
            continue
        tipo = MAPA[c]
        extra = p[6:] if len(p) > 6 else []
        if tipo in ("ResistorElm", "CapacitorElm", "InductorElm", "PotElm",
                    "CurrentElm", "TransformerElm") and extra:
            v = num(extra[0])
            if v is not None:
                vals.add(v)
        if tipo in ("VoltageElm", "RailElm", "VarRailElm") and len(extra) > 2:
            for tok in extra[:4]:
                v = num(tok)
                if v is not None:
                    vals.add(v)
        if tipo == "VarRailElm" and len(extra) > 1:
            v = num(extra[1])
            if v is not None:
                vals.add(v)
        if tipo == "OpAmpElm" and len(extra) >= 2:
            for tok in extra[:2]:
                v = num(tok)
                if v is not None:
                    vals.add(v)
        if tipo == "ZenerElm" and extra:
            v = num(extra[-1])
            if v is not None:
                vals.add(v)
        # los ajustables '38' y los textos también pueden citar valores
        for tok in extra:
            v = num(tok)
            if v is not None:
                vals.add(v)
    return vals


def main():
    if not os.path.exists(CAT):
        print("ERROR: no existe el catálogo. Ejecuta _tools/generar_catalogo.py")
        return 1
    catalogo = json.load(open(CAT, encoding="utf-8"))

    fichas = {}
    for nombre in sorted(os.listdir(DIR_FICHAS)):
        if nombre.endswith(".json"):
            fichas.update(json.load(open(os.path.join(DIR_FICHAS, nombre), encoding="utf-8")))

    valores = {c["id"]: valores_de_circuito(c["archivo"]) for c in catalogo}

    errores, calculos, propuestas, generales = [], [], [], []
    for cid, ficha in sorted(fichas.items()):
        vals = valores.get(cid, set())
        for campo in ("como", "observar", "prueba"):
            plano = re.sub(r"<[^>]+>", " ", ficha.get(campo, ""))
            for n_txt, uni in pat_num.findall(plano):
                n = float(n_txt.replace(",", "."))
                cand = {n * CONV.get(uni, 1.0), n}
                if any(abs(v - c) <= max(abs(c) * 0.02, 1e-9) for v in vals for c in cand):
                    continue
                item = f"{cid}.{campo}: {n_txt} {uni}"
                if (n, uni) in GENERAL:
                    generales.append(item + f"  [general: {GENERAL[(n, uni)]}]")
                elif PROPUESTA.search(plano):
                    propuestas.append(item + "  [propuesta de cambio]")
                elif CALCULO.search(plano):
                    calculos.append(item + "  [resultado calculado]")
                else:
                    errores.append(item + "  [ERROR]")

    print(f"fichas verificadas: {len(fichas)}")
    print(f"\nERRORES ({len(errores)}):")
    for e in errores:
        print("  -", e)
    print(f"\nresultados calculados ({len(calculos)}) / propuestas ({len(propuestas)}) / contexto ({len(generales)})")
    for c in calculos + propuestas + generales:
        print("  -", c)
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
