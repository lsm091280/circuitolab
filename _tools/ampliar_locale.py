#!/usr/bin/env python3
"""Amplia locale_es.txt con las cadenas de los dialogos de edicion.

El motor titula cada dialogo como "Edit " + tipo de componente y lo pasa por su
traductor. El locale oficial solo trae "Edit Component", asi que al crear un
circuito aparece "Edit Resistor", "Edit Capacitor"… en ingles. Se añaden esas
cadenas al fichero del locale (dato, no codigo: el bundle no se toca).

Uso: python3 _tools/ampliar_locale.py
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALE = os.path.join(RAIZ, "assets", "vendor", "circuitjs", "engine", "locale", "locale_es.txt")
MARCA = "# --- CircuitoLab: dialogos de edicion ---"

# tipo tal y como lo compone el motor -> español
TIPOS = {
    "Resistor": "Editar resistencia",
    "Capacitor": "Editar condensador",
    "Inductor": "Editar bobina",
    "Voltage": "Editar fuente de tensión",
    "Current": "Editar fuente de corriente",
    "Rail": "Editar tensión de alimentación",
    "VarRail": "Editar tensión variable",
    "Wire": "Editar cable",
    "Switch": "Editar interruptor",
    "Switch (SPST)": "Editar interruptor",
    "Switch (SPDT)": "Editar conmutador",
    "Switch (DPDT)": "Editar conmutador doble",
    "Switch (SPDT, MBB)": "Editar conmutador make-before-break",
    "Diode": "Editar diodo",
    "Zener diode": "Editar diodo Zener",
    "LED": "Editar LED",
    "Transistor": "Editar transistor",
    "MOSFET": "Editar MOSFET",
    "JFET": "Editar JFET",
    "Op-amp": "Editar amplificador operacional",
    "Relay": "Editar relé",
    "Pot": "Editar potenciómetro",
    "VarResistor": "Editar resistencia variable",
    "Thermistor": "Editar termistor",
    "Photoresistor": "Editar fotorresistencia",
    "Memo resistor": "Editar memristor",
    "Memristor": "Editar memristor",
    "Fuse": "Editar fusible",
    "Crystal": "Editar cristal de cuarzo",
    "Motor": "Editar motor",
    "Lamp": "Editar lámpara",
    "Box": "Editar recuadro",
    "Text": "Editar texto",
    "Labeled Node": "Editar etiqueta",
    "Scope": "Editar osciloscopio",
    "Probe": "Editar sonda",
    "Ammeter": "Editar amperímetro",
    "Voltmeter": "Editar voltímetro",
    "Ohmmeter": "Editar óhmetro",
    "Wattmeter": "Editar vatímetro",
    "Test Point": "Editar punto de test",
    "Data Recorder": "Editar exportación de datos",
    "Audio Output": "Editar salida de audio",
    "Triode": "Editar tríodo",
    "SCR": "Editar SCR",
    "DIAC": "Editar DIAC",
    "TRIAC": "Editar TRIAC",
    "Varactor": "Editar varactor",
    "Darlington pair": "Editar par Darlington",
    "UJT": "Editar transistor uniunión",
    "CCII": "Editar transportador de corriente",
    "CC2": "Editar transportador de corriente",
    "OTA": "Editar amplificador OTA",
    "Controlled Voltage Source": "Editar fuente de tensión controlada",
    "Controlled Current Source": "Editar fuente de corriente controlada",
    "Cross switch": "Editar conmutador cruzado",
    "cross switch": "Editar conmutador cruzado",
    "subcircuit": "Editar subcircuito",
    "ext. voltage": "Editar tensión externa",
    "logic input": "Editar entrada lógica",
    "custom logic": "Editar lógica personalizada",
    "sweep": "Editar barrido",
    "diode": "Editar diodo",
    "relay": "Editar relé",
    "transistor": "Editar transistor",
}

# otras cadenas de interfaz que salen al editar y no venian traducidas
SUELTAS = {
    "Edit Component": "Editar componente",
}


def main():
    if not os.path.exists(LOCALE):
        print("No encuentro", LOCALE)
        return 2

    with open(LOCALE, encoding="utf-8") as f:
        texto = f.read()

    if MARCA in texto:
        print("El locale ya tiene el bloque de CircuitoLab; no se toca.")
        return 0

    entradas = []
    for tipo, trad in sorted(TIPOS.items()):
        clave = "Edit " + tipo
        if f'"{clave}"=' not in texto:
            entradas.append(f'"{clave}"="{trad}"')
    for orig, trad in sorted(SUELTAS.items()):
        if f'"{orig}"=' not in texto:
            entradas.append(f'"{orig}"="{trad}"')

    if not entradas:
        print("Nada que añadir.")
        return 0

    bloque = "\n" + MARCA + "\n" + "\n".join(entradas) + "\n"
    if not texto.endswith("\n"):
        texto += "\n"
    with open(LOCALE, "w", encoding="utf-8") as f:
        f.write(texto + bloque)

    print(f"añadidas {len(entradas)} cadenas al locale_es.txt")
    for e in entradas[:6]:
        print("  ", e)
    if len(entradas) > 6:
        print(f"   … y {len(entradas) - 6} más")
    return 0


if __name__ == "__main__":
    sys.exit(main())
