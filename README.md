# CircuitoLab

Simulador de circuitos para clase, construido sobre **CircuitJS1** (Paul Falstad e
Iain Sharp), con interfaz propia del brand tecnoLSM y una capa didáctica: cada
circuito trae su explicación desplegable.

- **App:** `index.html` (estática pura, sin paso de build)
- **Motor:** `assets/vendor/circuitjs/` — CircuitJS1, **GPL-2.0**, sin modificar
- **Contenido:** `circuitos/catalogo.json` (366 circuitos, 60 con explicación)
- **Herramientas reproducibles:** `_tools/`
- **Informe técnico completo:** [`INFORME.md`](INFORME.md)

## Uso local

```bash
python3 _tools/servidor.py 8766
# http://127.0.0.1:8766
```

## Comprobar que todo sigue bien

```bash
python3 _tools/verificar.py            # 34 comprobaciones de la app
python3 _tools/verificar_edicion.py    # 11 comprobaciones de creación de circuitos
python3 _tools/verificar_explicaciones.py  # 0 valores inventados en las fichas
```

## Licencia

**GPL-2.0.** El motor CircuitJS1 es GPL-2.0, así que el conjunto se distribuye bajo
la misma licencia y el código fuente está disponible en este repositorio. Ver
[`LICENCIA-GPL-2.0.txt`](LICENCIA-GPL-2.0.txt).

Atribución: motor de simulación CircuitJS1, de **Paul Falstad** e **Iain Sharp**
(<https://github.com/sharpie7/circuitjs1>), GPL-2.0. Interfaz, explicaciones y
adaptación didáctica: **Luis Solá Mantilla**. Obra derivada.
