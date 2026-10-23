#!/usr/bin/env python3
"""CircuitoLab — verificacion de que el simulador se puede EDITAR.

Demuestra, con clics de verdad sobre los menus del motor, que el alumnado puede
crear circuitos desde cero, igual que en la app original:

  1. El menu del motor esta visible y en castellano.
  2. Archivo > Nuevo circuito en blanco deja el lienzo vacio.
  3. Dibujar > Resistencia activa el modo dibujo (cursor en cruz).
  4. Arrastrar sobre el lienzo crea de verdad un ResistorElm.
  5. RUN / Stop congela y reanuda la simulacion.

Uso:  python3 _tools/verificar_edicion.py
"""
import json
import os
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUERTO = 8779
CAPTURAS = os.path.join(RAIZ, "_tools", "capturas")
NODE_MODULES = ("/Users/luissolamantilla/Mis aplicaciones/Aula_Virtual-main/"
                "cascaron-aula-virtual/node_modules")

PRUEBA = r"""
const fs = require('fs');
const puppeteer = require(process.env.PM + '/puppeteer');
const wait = ms => new Promise(r => setTimeout(r, ms));

const fallos = [];
const ok = (cond, texto) => { console.log((cond ? '  OK   ' : '  FALLO ') + texto); if (!cond) fallos.push(texto); };

(async () => {
  const browser = await puppeteer.launch({ headless: 'shell', args: ['--no-sandbox', '--window-size=1440,900'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  const errores = [];
  page.on('pageerror', e => errores.push(String(e).slice(0, 160)));

  await page.goto(process.env.BASE, { waitUntil: 'networkidle2', timeout: 45000 });
  await wait(9000);

  let frame = null;
  for (let i = 0; i < 60; i++) {
    frame = page.frames().find(f => f.url().includes('circuitjs.html'));
    if (frame && await frame.evaluate(() => !!window.CircuitJS1).catch(() => false)) break;
    frame = null; await wait(500);
  }
  if (!frame) { console.log('  FALLO no se encontro el motor'); process.exit(1); }

  const nElems = () => frame.evaluate(() => window.CircuitJS1.getElements().length);
  const tipos = () => frame.evaluate(() => window.CircuitJS1.getElements().map(e => e.getType()));
  const off = await page.evaluate(() => {
    const q = document.querySelector('#lienzo').getBoundingClientRect();
    return { x: q.x, y: q.y };
  });

  /* --- 1) el menu esta visible y en castellano --- */
  const barra = await frame.evaluate(() => Array.from(document.querySelectorAll('td.gwt-MenuItem'))
    .filter(e => { const q = e.getBoundingClientRect(); return q.height > 10 && q.height < 45 && q.width < 200 && q.y < 40; })
    .map(e => (e.textContent || '').trim().split('\n')[0].replace(/\s+[A-Z].*$/, '')));
  const etiquetas = ['Archivo', 'Editar', 'Dibujar', 'Opciones', 'Ejemplos de circuitos'];
  const visibles = etiquetas.filter(t => barra.some(b => b.startsWith(t)));
  ok(visibles.length === etiquetas.length, 'el menu del motor esta visible y en castellano (' + visibles.join(', ') + ')');

  /* --- 2) Archivo > Nuevo circuito en blanco --- */
  const antes = await nElems();
  const rectBarra = async (t) => {
    const rr = await frame.evaluate((et) => {
      const it = Array.from(document.querySelectorAll('td.gwt-MenuItem')).find(e => {
        const q = e.getBoundingClientRect();
        return (e.textContent || '').trim().startsWith(et) && q.height > 10 && q.height < 45 && q.width < 200 && q.y < 40;
      });
      if (!it) return null;
      const q = it.getBoundingClientRect();
      return { x: q.x + q.width / 2, y: q.y + q.height / 2 };
    }, t);
    return rr ? { x: rr.x + off.x, y: rr.y + off.y } : null;
  };
  const rectItem = async (t) => {
    const rr = await frame.evaluate((et) => {
      /* el texto del item lleva delante la marca del modo activo, y los items
         con submenu arrastran dentro el texto de todo el submenu */
      const it = Array.from(document.querySelectorAll('.menuDropdown .menuItem')).find(e => {
        const q = e.getBoundingClientRect();
        const limpio = (e.textContent || '').trim().toLowerCase().replace(/^[^a-z0-9]+/, '');
        const esMadre = (e.textContent || '').includes('\u25ba');
        return limpio.startsWith(et) && !esMadre && q.width > 20 && q.height > 5;
      });
      if (!it) return null;
      const q = it.getBoundingClientRect();
      return { x: q.x + q.width / 2, y: q.y + q.height / 2 };
    }, t);
    return rr ? { x: rr.x + off.x, y: rr.y + off.y } : null;
  };

  const pArchivo = await rectBarra('Archivo');
  if (pArchivo) { await page.mouse.click(pArchivo.x, pArchivo.y); await wait(900); }
  const pNuevo = await rectItem('nuevo circuito en blanco');
  ok(!!pNuevo, 'el desplegable Archivo ofrece "Nuevo circuito en blanco"');
  if (pNuevo) { await page.mouse.click(pNuevo.x, pNuevo.y); await wait(1800); }
  const trasNuevo = await nElems();
  ok(trasNuevo === 0, 'Nuevo circuito en blanco vacia el lienzo (' + antes + ' -> ' + trasNuevo + ' elementos)');

  /* --- 3) Dibujar > Resistencia --- */
  const pDibujar = await rectBarra('Dibujar');
  if (pDibujar) { await page.mouse.click(pDibujar.x, pDibujar.y); await wait(1400); }
  const abierto = await frame.evaluate(() =>
    Array.from(document.querySelectorAll('.menuDropdown')).some(u => u.getBoundingClientRect().height > 30));
  ok(abierto, 'el menu Dibujar despliega la paleta de componentes');
  const pRes = await rectItem('resistencia');
  ok(!!pRes, 'la paleta incluye "Resistencia"');

  const caja = await frame.evaluate(() => {
    let mayor = null;
    for (const c of document.querySelectorAll('canvas')) {
      if (!mayor || c.width * c.height > mayor.width * mayor.height) mayor = c;
    }
    const q = mayor.getBoundingClientRect();
    return { x: q.x, y: q.y, w: q.width, h: q.height };
  });

  if (pRes) { await page.mouse.click(pRes.x, pRes.y); await wait(1000); }
  const cursor = await frame.evaluate(() => {
    let mayor = null;
    for (const c of document.querySelectorAll('canvas')) {
      if (!mayor || c.width * c.height > mayor.width * mayor.height) mayor = c;
    }
    return getComputedStyle(mayor).cursor;
  });
  ok(cursor === 'crosshair', 'elegir Resistencia pone el lienzo en modo dibujo (cursor ' + cursor + ')');

  /* --- 4) arrastrar para dibujar la resistencia --- */
  const ax = off.x + caja.x + caja.w * 0.30;
  const ay = off.y + caja.y + caja.h * 0.35;
  await page.mouse.move(ax, ay); await wait(200);
  await page.mouse.down(); await wait(250);
  await page.mouse.move(ax + 64, ay, { steps: 6 }); await wait(200);
  await page.mouse.move(ax + 128, ay, { steps: 6 }); await wait(200);
  await page.mouse.up(); await wait(1500);

  const tras = await nElems();
  const tps = await tipos();
  ok(tras === 1, 'arrastrar en el lienzo crea el componente (' + tras + ')');
  ok(tps.includes('ResistorElm'), 'el componente creado es una resistencia (' + tps.join(', ') + ')');
  await page.screenshot({ path: process.env.CAP + '/05-crear-circuito.png' });

  /* --- 5) RUN / Stop congela y reanuda --- */
  await frame.evaluate(() => window.CircuitJS1.setSimRunning(false));
  await wait(600);
  const t1 = await frame.evaluate(() => window.CircuitJS1.getTime());
  await wait(900);
  const t2 = await frame.evaluate(() => window.CircuitJS1.getTime());
  await frame.evaluate(() => window.CircuitJS1.setSimRunning(true));
  await wait(900);
  const t3 = await frame.evaluate(() => window.CircuitJS1.getTime());
  ok(Math.abs(t2 - t1) < 1e-9, 'detener la simulacion congela el tiempo');
  ok(t3 > t2, 'reanudar la simulacion vuelve a avanzar');

  ok(errores.length === 0, 'consola sin errores' + (errores.length ? ': ' + JSON.stringify(errores.slice(0, 2)) : ''));

  await browser.close();
  console.log('\n===== ' + (fallos.length ? 'FALLOS: ' + fallos.length : 'EDICION OK: se puede crear circuitos') + ' =====');
  process.exit(fallos.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
"""


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=RAIZ, **kw)

    def log_message(self, *a):
        pass

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass


def main():
    os.makedirs(CAPTURAS, exist_ok=True)
    if not os.path.isdir(NODE_MODULES):
        print("No encuentro puppeteer en", NODE_MODULES)
        return 2
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    time.sleep(0.6)
    js = os.path.join(RAIZ, "_tools", "_verificar_edicion.cjs")
    with open(js, "w", encoding="utf-8") as f:
        f.write(PRUEBA)
    env = dict(os.environ)
    env["PM"] = NODE_MODULES
    env["CAP"] = CAPTURAS
    env["BASE"] = f"http://127.0.0.1:{PUERTO}/index.html"
    try:
        res = subprocess.run(["node", js], env=env, timeout=300)
        return res.returncode
    finally:
        servidor.shutdown()
        try:
            os.remove(js)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
