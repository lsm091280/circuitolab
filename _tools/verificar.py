#!/usr/bin/env python3
"""CircuitoLab — verificación de la app (sin galería lateral).

Comprueba, contra el servidor local y con Chrome headless:
  - recursos y cero peticiones externas
  - el panel lateral del motor con sus cursores (lo que pidió Luis)
  - que NO queda galería ni navegación superior
  - que el panel didáctico SIGUE al circuito elegido en «Ejemplos de circuitos»
  - simulación viva, acordeón, temas, móvil y consola limpia

Uso:  python3 _tools/verificar.py
"""
import json
import os
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUERTO = 8766
CAPTURAS = os.path.join(RAIZ, "_tools", "capturas")
NODE_MODULES = ("/Users/luissolamantilla/Mis aplicaciones/Aula_Virtual-main/"
                "cascaron-aula-virtual/node_modules")

# circuitos de prueba: id del catálogo + título tal y como sale en el menú del motor
PRUEBA = [
    ("ohms", "Ley de Ohm"),
    ("npn", "Transistor NPN"),
    ("norton", "Teorema de Norton"),
]

JS = r"""
const fs = require('fs');
const path = require('path');
const puppeteer = require(process.env.PM + '/puppeteer');
const wait = ms => new Promise(r => setTimeout(r, ms));

const fallos = [];
const check = (cond, texto, datos) => {
  console.log((cond ? '  OK   ' : '  FALLO ') + texto);
  if (!cond) { fallos.push(texto); if (datos) console.log('        ', JSON.stringify(datos).slice(0, 300)); }
};
const CAP = process.env.CAP;
const BASE = process.env.BASE;

/* captura con el motor en pausa: con el canvas animando, CDP se atasca */
const capturar = async (page, destino) => {
  try {
    const f = page.frames().find(x => x.url().includes('/engine/circuitjs'));
    if (f) await f.evaluate(() => window.CircuitJS1 && window.CircuitJS1.setSimRunning(false));
  } catch (e) {}
  await wait(350);
  await page.screenshot({ path: destino });
  try {
    const f = page.frames().find(x => x.url().includes('/engine/circuitjs'));
    if (f) await f.evaluate(() => window.CircuitJS1 && window.CircuitJS1.setSimRunning(true));
  } catch (e) {}
};

const frameMotor = async (page) => {
  for (let i = 0; i < 80; i++) {
    const f = page.frames().find(x => x.url().includes('/engine/circuitjs') || x.url().includes('circuitjs.html'));
    if (f && await f.evaluate(() => !!window.CircuitJS1).catch(() => false)) return f;
    await wait(400);
  }
  return null;
};

/* abre un ejemplo del menu del motor pulsando el <li>: es lo que hace un alumno */
const abrirEjemplo = async (page, f, titulo) => {
  const ok = await f.evaluate((t) => {
    const li = Array.from(document.querySelectorAll('.menuItem')).find(e => {
      const txt = (e.textContent || '').trim();
      return txt === t && e.querySelectorAll('.menuItem').length === 0;
    });
    if (!li) return false;
    li.click();
    return true;
  }, titulo);
  await wait(3200);
  return ok;
};

const firmaLienzo = async (page, f) => f.evaluate(() => {
  let mayor = null;
  for (const c of document.querySelectorAll('canvas')) {
    if (!mayor || c.width * c.height > mayor.width * mayor.height) mayor = c;
  }
  if (!mayor) return null;
  const d = mayor.getContext('2d').getImageData(0, 0, mayor.width, mayor.height).data;
  let pintados = 0, suma = 0;
  for (let i = 0; i < d.length; i += 4 * 37) {
    if (d[i] > 30 || d[i + 1] > 30 || d[i + 2] > 30) pintados++;
    suma += d[i] + d[i + 2];
  }
  return { pintados, firma: suma % 100000 };
});

(async () => {
  const browser = await puppeteer.launch({ headless: 'shell', args: ['--no-sandbox'],
                                           protocolTimeout: 180000 });
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 950 });

  const errores = [], externas = [];
  const origen = new URL(BASE).origin;
  page.on('pageerror', e => errores.push(String(e).slice(0, 160)));
  page.on('console', m => { if (m.type() === 'error') errores.push(m.text().slice(0, 160)); });
  page.on('request', r => {
    const u = r.url();
    if (!u.startsWith(origen) && !u.startsWith('data:') && !u.startsWith('blob:')) externas.push(u.slice(0, 90));
  });

  await page.evaluateOnNewDocument(() => {
    try { localStorage.removeItem('circuitolab-ultimo'); } catch (e) {}
  });
  const resp = await page.goto(BASE, { waitUntil: 'networkidle2', timeout: 60000 });
  check(resp.status() === 200, 'la página responde 200 (' + resp.status() + ')');
  await wait(10000);

  const f = await frameMotor(page);
  check(!!f, 'el motor CircuitJS1 carga');

  /* ---------- 1) recursos ---------- */
  const recursos = await page.evaluate(async () => {
    const rutas = ['assets/css/app.css', 'assets/js/app.js', 'circuitos/catalogo.json',
                   'assets/vendor/circuitjs/engine/locale/locale_es.txt'];
    const out = [];
    for (const r of rutas) {
      try { const x = await fetch(r, { cache: 'no-store' }); out.push({ r, s: x.status }); }
      catch (e) { out.push({ r, s: 0 }); }
    }
    return out;
  });
  check(recursos.every(x => x.s === 200), 'los recursos clave responden 200', recursos);

  /* ---------- 2) sin galería ni navegación ---------- */
  const sin = await page.evaluate(() => ({
    galeria: document.querySelectorAll('#galeria, .galeria').length,
    nav: document.querySelectorAll('.cabecera__nav a').length,
  }));
  check(sin.galeria === 0, 'no queda la galería lateral', sin);
  check(sin.nav === 0, 'no quedan los enlaces superiores', sin);

  /* ---------- 3) el panel del motor con cursores ---------- */
  const panel = await f.evaluate(() => {
    const pa = document.getElementById('painel');
    if (!pa) return null;
    return {
      ancho: Math.round(pa.getBoundingClientRect().width),
      cursores: pa.querySelectorAll('canvas').length,
      botones: Array.from(pa.querySelectorAll('.topButton')).map(b => (b.textContent || '').trim()),
      etiquetas: Array.from(pa.querySelectorAll('.topSpace')).map(e => (e.textContent || '').trim()),
    };
  });
  check(!!panel, 'el panel lateral del motor está visible');
  check(panel && panel.cursores >= 3, 'el panel trae los cursores (' + (panel ? panel.cursores : 0) + ')', panel);
  check(panel && panel.etiquetas.some(t => /Velocidad de simulaci/i.test(t)),
        'está el cursor de velocidad de simulación', panel && panel.etiquetas);
  check(panel && panel.etiquetas.some(t => /Velocidad de corriente/i.test(t)),
        'está el cursor de velocidad de corriente', panel && panel.etiquetas);
  check(panel && panel.botones.some(b => /RUN/i.test(b)), 'están Reiniciar y RUN/Stop', panel && panel.botones);

  /* ---------- 4) abre con un circuito con explicación ---------- */
  const ini = await page.evaluate(() => ({
    titulo: (document.getElementById('titulo-circuito') || {}).textContent,
    bloques: document.querySelectorAll('.bloque').length,
  }));
  check(ini.bloques === 3, 'abre con un circuito que tiene explicación (' + ini.titulo + ')', ini);

  /* ---------- 5) el panel SIGUE al circuito del menú ---------- */
  const resultados = [];
  for (const [id, titulo] of JSON.parse(process.env.PRUEBA)) {
    const pulsado = await abrirEjemplo(page, f, titulo);
    const est = await page.evaluate(() => ({
      titulo: (document.getElementById('titulo-circuito') || {}).textContent,
      bloques: document.querySelectorAll('.bloque').length,
      estado: (document.getElementById('estado-panel') || {}).textContent,
      sub: (document.getElementById('subtitulo-circuito') || {}).textContent,
    }));
    const firma = await firmaLienzo(page, f);
    resultados.push({ id, esperado: titulo, pulsado, ...est, firma });
    await capturar(page, path.join(CAP, 'circuito-' + id + '.png'));
  }
  check(resultados.every(r => r.pulsado), 'se pueden abrir ejemplos desde el menú del motor',
        resultados.map(r => r.pulsado));
  check(resultados.every(r => r.titulo && r.titulo !== 'Circuito'),
        'la cabecera muestra el circuito cargado', resultados.map(r => r.titulo));
  check(resultados.every(r => r.bloques === 3),
        'el panel de explicación se actualiza solo al cambiar de circuito',
        resultados.map(r => ({ id: r.id, bloques: r.bloques })));
  check(new Set(resultados.map(r => r.firma && r.firma.firma)).size === resultados.length,
        'cada circuito dibuja algo distinto', resultados.map(r => r.firma && r.firma.firma));

  /* ---------- 6) simulación viva ---------- */
  const t1 = await f.evaluate(() => window.CircuitJS1.getTime());
  await wait(2500);
  const t2 = await f.evaluate(() => window.CircuitJS1.getTime());
  check(t2 !== t1, 'la simulación avanza (getTime cambia)');

  /* ---------- 7) acordeón ---------- */
  const ac = await page.evaluate(() => {
    const cab = document.querySelectorAll('.bloque__cabecera')[1];
    if (!cab) return null;
    const antes = cab.getAttribute('aria-expanded');
    cab.click();
    const medio = cab.getAttribute('aria-expanded');
    cab.click();
    return { antes, medio, despues: cab.getAttribute('aria-expanded'),
             existePanel: !!document.getElementById(cab.getAttribute('aria-controls')) };
  });
  check(ac && ac.antes === 'false' && ac.medio === 'true' && ac.despues === 'false',
        'el acordeón abre y cierra', ac);
  check(ac && ac.existePanel, 'aria-controls apunta a un panel existente', ac);

  await page.evaluate(() => {
    const cab = document.querySelectorAll('.bloque__cabecera')[0];
    // el primer bloque viene abierto por defecto: solo se abre si esta cerrado
    if (cab && cab.getAttribute('aria-expanded') === 'false') cab.click();
  });
  await abrirEjemplo(page, f, JSON.parse(process.env.PRUEBA)[0][1]);
  const persist = await page.evaluate(() => ({
    estado: document.querySelectorAll('.bloque__cabecera')[0].getAttribute('aria-expanded'),
  }));
  check(persist.estado === 'true', 'el bloque abierto se conserva al cambiar de circuito', persist);

  /* ---------- 8) fórmulas ---------- */
  const formulas = await page.evaluate(() => {
    const t = (document.getElementById('cuerpo-panel') || {}).innerText || '';
    return { crudas: (t.match(/\{fx\(|\{frac\(/g) || []).length,
             fichas: document.querySelectorAll('.fx, .frac').length };
  });
  check(formulas.crudas === 0, 'ninguna fórmula queda sin renderizar', formulas);
  check(formulas.fichas > 0, 'las fichas de fórmula se pintan', formulas);

  await capturar(page, path.join(CAP, '01-oscuro-escritorio.png'));

  /* ---------- 9) tema claro ---------- */
  await page.click('#btn-tema');
  await wait(2500);
  const claro = await page.evaluate(() => document.documentElement.dataset.theme);
  check(claro === 'light', 'el tema claro se aplica (' + claro + ')');
  await capturar(page, path.join(CAP, '03-claro-escritorio.png'));
  await page.click('#btn-tema');
  await wait(1500);

  /* ---------- 10) móvil ---------- */
  await page.setViewport({ width: 390, height: 844 });
  await wait(3000);
  const movil = await page.evaluate(() => ({
    ancho: document.documentElement.scrollWidth,
    ventana: window.innerWidth,
  }));
  check(movil.ancho <= movil.ventana + 2, 'sin desbordamiento horizontal en móvil', movil);
  await capturar(page, path.join(CAP, '04-movil.png'));

  /* ---------- 11) consola y red ---------- */
  check(externas.length === 0, 'cero peticiones a dominios externos' +
        (externas.length ? ': ' + JSON.stringify(externas.slice(0, 3)) : ''));
  check(errores.length === 0, 'consola sin errores' +
        (errores.length ? ': ' + JSON.stringify(errores.slice(0, 2)) : ''));

  await browser.close();
  fs.writeFileSync(path.join(CAP, '..', 'verificacion.json'),
                   JSON.stringify({ fallos, resultados }, null, 1));
  console.log('\n===== ' + (fallos.length ? 'FALLOS: ' + fallos.length : 'TODO OK') + ' =====');
  process.exit(fallos.length ? 1 : 0);
})().catch(e => { console.error('FATAL', String(e).slice(0, 400)); process.exit(1); });
"""


class Handler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=RAIZ, **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, *a):
        pass

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            self.close_connection = True


def main():
    os.makedirs(CAPTURAS, exist_ok=True)
    if not os.path.isdir(NODE_MODULES):
        print("No encuentro puppeteer en", NODE_MODULES)
        return 2

    with open(os.path.join(RAIZ, "circuitos", "catalogo.json"), encoding="utf-8") as fh:
        catalogo = {c["id"]: c for c in json.load(fh)}
    prueba = []
    for cid, titulo in PRUEBA:
        c = catalogo.get(cid)
        if not c:
            print("AVISO: el circuito", cid, "no está en el catálogo")
            continue
        if c.get("estado") != "completa":
            print("AVISO:", cid, "no tiene explicación completa")
        prueba.append([cid, titulo])

    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    time.sleep(0.6)

    ruta = os.path.join(RAIZ, "_tools", "_verificar_app.cjs")
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(JS)
    env = dict(os.environ)
    env["PM"] = NODE_MODULES
    env["CAP"] = CAPTURAS
    env["BASE"] = f"http://127.0.0.1:{PUERTO}/index.html"
    env["PRUEBA"] = json.dumps(prueba)
    try:
        return subprocess.run(["node", ruta], env=env, timeout=420).returncode
    finally:
        servidor.shutdown()
        try:
            os.remove(ruta)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
