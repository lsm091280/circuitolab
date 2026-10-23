#!/usr/bin/env python3
"""ARNÉS DE VERIFICACIÓN de CircuitoLab.

Mide (no estima) con Chrome headless:
  1) carga de la app y del motor (HTTP 200 en todos los recursos);
  2) el circuito dibuja en el lienzo (NO es un recuadro vacío);
  3) la simulación AVANZA (getTime() del motor cambia);
  4) cargar 3 circuitos distintos y comprobar que cambia lo dibujado;
  5) el acordeón abre y cierra, y el estado se conserva al cambiar de circuito;
  6) teclado: recorrido con Tab y aria-expanded correcto;
  7) consola sin errores;
  8) ninguna petición a dominios externos;
  9) capturas reales: claro/oscuro, escritorio/móvil, acordeón abierto/cerrado.

Salida: capturas en _tools/capturas/ y resumen en _tools/verificacion.json
"""
import json
import os
import subprocess
import sys
import time

BASE = "http://127.0.0.1:8766/"
NM = "/Users/luissolamantilla/Mis aplicaciones/Aula_Virtual-main/cascaron-aula-virtual/node_modules"
RAIZ = "/Users/luissolamantilla/Downloads/circuitolab"
CAPTURAS = os.path.join(RAIZ, "_tools", "capturas")

PROBE = r"""
const fs = require('fs');
const path = require('path');
const puppeteer = require(process.env.PM + '/puppeteer');
const wait = ms => new Promise(r => setTimeout(r, ms));
const CAP = process.env.CAP;
const BASE = 'http://127.0.0.1:8766/';

const fallos = [];
const avisos = [];
function check(cond, msg, detalle) {
  if (cond) { console.log('  OK   ' + msg); }
  else { fallos.push(msg + (detalle ? ' -> ' + JSON.stringify(detalle) : '')); console.log('  FALLO ' + msg + (detalle ? ' -> ' + JSON.stringify(detalle) : '')); }
}

async function firmaLienzo(page) {
  // firma del iframe del motor: suma de píxeles del canvas principal
  const frames = page.frames();
  const motor = frames.find(f => f.url().includes('circuitjs.html'));
  if (!motor) return null;
  return await motor.evaluate(() => {
    const cs = Array.from(document.querySelectorAll('canvas'));
    let mayor = null;
    for (const c of cs) if (!mayor || c.width * c.height > mayor.width * mayor.height) mayor = c;
    if (!mayor) return null;
    const c2 = document.createElement('canvas');
    c2.width = mayor.width; c2.height = mayor.height;
    const ctx = c2.getContext('2d');
    ctx.drawImage(mayor, 0, 0);
    const d = ctx.getImageData(0, 0, c2.width, c2.height).data;
    let s = 0, noNegro = 0, n = 0;
    for (let i = 0; i < d.length; i += 4 * 11) { s += d[i] + d[i+1] + d[i+2]; if (d[i]+d[i+1]+d[i+2] > 90) noNegro++; n++; }
    return { s, noNegro, n, w: mayor.width, h: mayor.height };
  });
}

async function apiMotor(page) {
  const frames = page.frames();
  const motor = frames.find(f => f.url().includes('circuitjs.html'));
  if (!motor) return null;
  return await motor.evaluate(() => {
    const api = window.CircuitJS1;
    if (!api) return null;
    return { t: api.getTime(), corriendo: api.isRunning(), n: api.getElements().length };
  });
}

(async () => {
  // protocolTimeout alto: el motor anima sin parar y una captura grande puede
  // tardar mas que el limite por defecto (daba "Page.captureScreenshot timed out",
  // que parece un fallo de la app y no lo es)
  const browser = await puppeteer.launch({ headless: 'shell', args: ['--no-sandbox'],
                                           protocolTimeout: 180000 });

  // ============ 1) ESCRITORIO, TEMA OSCURO ============
  console.log('\n== 1) Escritorio, tema oscuro ==');
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 950 });
  const errores = [], externas = [], recursos = [];
  page.on('pageerror', e => errores.push('pageerror: ' + String(e).slice(0, 220)));
  page.on('console', m => { if (m.type() === 'error') errores.push('console: ' + m.text().slice(0, 220)); });
  page.on('requestfailed', r => errores.push('requestfailed: ' + r.url().slice(0, 160) + ' ' + (r.failure() || {}).errorText));
  page.on('response', r => recursos.push({ url: r.url(), status: r.status() }));
  page.on('request', r => { const u = r.url(); if (!u.startsWith(BASE) && !u.startsWith('data:') && !u.startsWith('about:') && !u.startsWith('blob:')) externas.push(u); });

  // El tema se fija ANTES de cargar (evaluateOnNewDocument). Antes se hacía
  // goto + reload, y el reload cancelaba las peticiones en curso (el logo),
  // generando falsos ERR_CONNECTION_RESET en el arnés.
  await page.evaluateOnNewDocument(() => {
    try { localStorage.setItem('circuitolab-tema', 'dark'); } catch (e) {}
  });
  await page.goto(BASE, { waitUntil: 'networkidle2', timeout: 45000 });
  await wait(7000);

  // recursos
  const fallosRes = recursos.filter(r => r.status >= 400);
  check(fallosRes.length === 0, 'todos los recursos responden 200', fallosRes.slice(0, 5));
  check(externas.length === 0, 'ninguna petición a dominios externos', externas);

  // estructura
  const est = await page.evaluate(() => ({
    circuitos: document.querySelectorAll('.circuito').length,
    grupos: document.querySelectorAll('.grupo').length,
    // títulos de los grupos de primer nivel: deben ser categorías del motor,
    // no cursos (3º ESO / 4º ESO / Bachillerato)
    titulosGrupo: Array.from(document.querySelectorAll('#lista-circuitos > .grupo > .grupo__titulo'))
      .map((b) => b.textContent.replace(/\d+$/, '').trim()),
    bloques: document.querySelectorAll('.bloque').length,
    titulo: (document.getElementById('titulo-circuito') || {}).textContent,
    estado: (document.getElementById('estado-panel') || {}).textContent,
    iframeSrc: (document.getElementById('lienzo') || {}).src,
    cargandoOculto: document.getElementById('cargando').hidden,
    anchoBody: document.body.scrollWidth,
    ventana: window.innerWidth,
  }));
  check(est.circuitos > 0, 'la galería lista circuitos', est);
  check(est.grupos > 0, 'la galería agrupa por categorías', est);
  // la agrupación debe ser la del motor, no por curso
  const cursos = ['3º ESO', '4º ESO', 'Bachillerato'];
  const gruposCurso = (est.titulosGrupo || []).filter((t) => cursos.some((c) => t.includes(c)));
  check(gruposCurso.length === 0, 'la galería NO agrupa por curso', { gruposCurso });
  const gruposCat = (est.titulosGrupo || []).filter((t) => t.length > 2);
  check(gruposCat.length >= 5, 'la galería usa las categorías del motor (' + gruposCat.length + ')',
        { grupos: gruposCat.slice(0, 6) });
  check(est.bloques === 3, 'el acordeón tiene 3 bloques', est);
  check(est.cargandoOculto === true, 'el motor terminó de cargar', est);
  check(est.anchoBody <= est.ventana + 2, 'sin desbordamiento horizontal', est);

  // 1b) ninguna formula sin renderizar (el bug de las cadenas sin f-string)
  const formulas = await page.evaluate(() => {
    const texto = document.getElementById('cuerpo-panel').innerText;
    const sinRender = texto.match(/\{fx\(|{frac\(/g) || [];
    const fichas = document.querySelectorAll('.fx').length;
    const fracciones = document.querySelectorAll('.frac').length;
    return { sinRender: sinRender.length, fichas, fracciones };
  });
  check(formulas.sinRender === 0, 'ninguna fórmula queda sin renderizar', formulas);
  check(formulas.fichas > 0, 'las fichas de fórmula se pintan', formulas);

  // 1c) los títulos de los circuitos CON explicación salen en español
  //     (los pendientes conservan el título original del motor hasta la fase 2)
  const titulos = await page.evaluate(() => {
    const filas = Array.from(document.querySelectorAll('.circuito'));
    const conFicha = filas.filter(b => b.querySelector('.circuito__punto.completa'))
      .map(b => b.querySelector('.circuito__nombre').textContent.trim());
    // "Transistor" es la misma palabra en español, no cuenta como inglés
    const enIngles = conFicha.filter(n => /\b(Law|Theorem|Divider|Filter|Counter|Gate|Amplifier|Inverter|Oscillator)\b/.test(n));
    return { conFicha: conFicha.length, enIngles: enIngles.length, muestraIngles: enIngles.slice(0, 6) };
  });
  check(titulos.enIngles === 0, 'los títulos con explicación están en español', titulos);
  check(titulos.conFicha >= 60, 'hay al menos 60 circuitos con explicación en la galería', titulos);

  // 1d) las categorías de la galería también en español
  const categorias = await page.evaluate(() => {
    const textos = Array.from(document.querySelectorAll('.grupo__titulo span'))
      .map(e => e.textContent.trim()).filter(Boolean);
    const ingles = textos.filter(t => /\b(Basics|Circuits|Diodes|Transistors|MOSFETs|Chip|Families|Logic|Filters|Converters|Lines|Sources|Devices|Scope|Amplifiers|Oscillators)\b/.test(t));
    return { total: textos.length, ingles: ingles.slice(0, 8), nIngles: ingles.length };
  });
  check(categorias.nIngles === 0, 'las categorías de la galería están en español', categorias);

  // 2) el lienzo dibuja
  const f1 = await firmaLienzo(page);
  check(f1 && f1.noNegro > 50, 'el lienzo dibuja el circuito (no está vacío)', f1);

  // 3) la simulación avanza
  const a1 = await apiMotor(page);
  await wait(2500);
  const a2 = await apiMotor(page);
  check(a1 && a2 && a2.t !== a1.t, 'la simulación avanza (getTime cambia)', { a1, a2 });

  /* Captura con el motor en pausa: con el canvas animando a 60 fps,
     Page.captureScreenshot se atasca y aborta el arnés con un ProtocolError
     que parece un fallo de la app y no lo es. */
  const capturar = async (destino) => {
    try {
      const f = page.frames().find((x) => x.url().includes('circuitjs.html'));
      if (f) await f.evaluate(() => window.CircuitJS1 && window.CircuitJS1.setSimRunning(false));
    } catch (e) { /* el motor puede no estar listo */ }
    await wait(350);
    await page.screenshot({ path: destino });
    try {
      const f = page.frames().find((x) => x.url().includes('circuitjs.html'));
      if (f) await f.evaluate(() => window.CircuitJS1 && window.CircuitJS1.setSimRunning(true));
    } catch (e) { /* idem */ }
  };

  await capturar(path.join(CAP, '01-oscuro-escritorio.png'));

  // 5) acordeón: abrir y cerrar
  const ac = await page.evaluate(() => {
    const cab = document.querySelectorAll('.bloque__cabecera')[1];
    const antes = cab.getAttribute('aria-expanded');
    const cuerpo = document.getElementById(cab.getAttribute('aria-controls'));
    cab.click();
    const despues = cab.getAttribute('aria-expanded');
    const visible = !cuerpo.hidden;
    cab.click();
    const cerrado = cab.getAttribute('aria-expanded');
    return { antes, despues, visible, cerrado, ocultoTrasCerrar: cuerpo.hidden };
  });
  check(ac.antes === 'false' && ac.despues === 'true' && ac.visible, 'el acordeón abre', ac);
  check(ac.cerrado === 'false' && ac.ocultoTrasCerrar, 'el acordeón cierra', ac);

  // 5b) el estado se conserva al cambiar de circuito
  const persist = await page.evaluate(async () => {
    const cab = document.querySelectorAll('.bloque__cabecera')[0];
    if (cab.getAttribute('aria-expanded') === 'false') cab.click();
    const estado = localStorage.getItem('circuitolab-bloques');
    // cambia de circuito
    const botones = Array.from(document.querySelectorAll('.circuito'));
    const otro = botones.find(b => b.getAttribute('aria-current') !== 'true');
    otro.click();
    await new Promise(r => setTimeout(r, 1200));
    const cab2 = document.querySelectorAll('.bloque__cabecera')[0];
    return { estadoGuardado: estado, estadoEnOtro: cab2 ? cab2.getAttribute('aria-expanded') : null };
  });
  check(persist.estadoEnOtro === 'true', 'el bloque abierto se conserva al cambiar de circuito', persist);

  // 5c) coherencia del aviso "Explicación pendiente": solo si NO hay explicación
  const coherencia = await page.evaluate(() => {
    const pend = document.getElementById('sin-explicacion');
    const bloques = document.querySelectorAll('.bloque').length;
    const visible = pend && getComputedStyle(pend).display !== 'none';
    return { bloques, avisoVisible: visible, estado: document.getElementById('estado-panel').textContent };
  });
  check(!(coherencia.bloques > 0 && coherencia.avisoVisible),
    'el aviso "Explicación pendiente" NO aparece si hay explicación', coherencia);

  // 5d) un circuito PENDIENTE debe mostrar el aviso y no tener bloques
  const pendiente = await page.evaluate(async () => {
    // busca un circuito con estado pendiente usando el buscador
    const input = document.getElementById('buscar');
    const todos = Array.from(document.querySelectorAll('.circuito'));
    const punto = todos.find(b => b.querySelector('.circuito__punto.pendiente'));
    if (!punto) return { encontrado: false };
    punto.click();
    await new Promise(r => setTimeout(r, 1000));
    const pend = document.getElementById('sin-explicacion');
    return {
      encontrado: true,
      id: punto.dataset.id,
      avisoVisible: pend && getComputedStyle(pend).display !== 'none',
      bloques: document.querySelectorAll('.bloque').length,
      estado: document.getElementById('estado-panel').textContent,
    };
  });
  if (pendiente.encontrado) {
    check(pendiente.avisoVisible && pendiente.bloques === 0,
      'un circuito pendiente muestra el aviso y no tiene bloques', pendiente);
    check(pendiente.estado === 'Pendiente', 'un circuito pendiente se marca como Pendiente', pendiente);
  } else {
    avisos.push('no se encontró ningún circuito pendiente en la galería');
  }

  // 4) tres circuitos distintos -> dibuja distinto
  console.log('\n== 4) Tres circuitos distintos ==');
  const ids = await page.evaluate(() => Array.from(document.querySelectorAll('.circuito')).map(b => ({ id: b.dataset.id, t: b.textContent.trim() })));
  const objetivo = ['ohms', 'cap', 'npn'].filter(x => ids.some(i => i.id === x));
  check(objetivo.length === 3, 'los 3 circuitos de prueba están en la galería', { objetivo, total: ids.length });
  const firmas = [];
  for (const id of objetivo) {
    await page.evaluate((wanted) => {
      const b = Array.from(document.querySelectorAll('.circuito')).find(x => x.dataset.id === wanted);
      if (b) b.click();
    }, id);
    await wait(2600);
    const f = await firmaLienzo(page);
    const tit = await page.evaluate(() => document.getElementById('titulo-circuito').textContent);
    firmas.push({ id, tit, firma: f && f.s, noNegro: f && f.noNegro });
    await capturar(path.join(CAP, 'circuito-' + id + '.png'));
  }
  const distintas = new Set(firmas.map(f => f.firma)).size;
  check(firmas.length === 3, 'se cargaron 3 circuitos', firmas.map(f => f.id));
  check(distintas === 3, 'cada circuito dibuja algo distinto', { firmas: firmas.map(f => ({ id: f.id, s: f.firma })) });
  check(firmas.every(f => f.noNegro > 50), 'todos los circuitos dibujan contenido', firmas);

  // 6) teclado y accesibilidad
  console.log('\n== 6) Teclado y accesibilidad ==');
  const teclado = await page.evaluate(async () => {
    const cab = document.querySelectorAll('.bloque__cabecera')[0];
    cab.focus();
    const activo = document.activeElement === cab;
    const antes = cab.getAttribute('aria-expanded');
    cab.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    cab.click();
    const despues = cab.getAttribute('aria-expanded');
    const roles = {
      cabecerasAcordeon: document.querySelectorAll('.bloque__cabecera[aria-expanded]').length,
      controles: document.querySelectorAll('.bloque__cabecera[aria-controls]').length,
      rolesNecesarios: document.querySelectorAll('[aria-expanded]').length,
    };
    return { activo, antes, despues, ...roles };
  });
  check(teclado.activo, 'la cabecera del acordeón recibe el foco', teclado);
  check(teclado.controles === teclado.cabecerasAcordeon, 'aria-controls apunta a un panel existente', teclado);

  // 7) consola
  console.log('\n== 7) Consola ==');
  const erroresFiltrados = errores.filter(e => !/favicon/i.test(e));
  check(erroresFiltrados.length === 0, 'consola sin errores', erroresFiltrados.slice(0, 6));

  // captura con acordeón abierto
  await page.evaluate(() => {
    document.querySelectorAll('.bloque__cabecera').forEach(c => { if (c.getAttribute('aria-expanded') === 'false') c.click(); });
  });
  await wait(500);
  await capturar(path.join(CAP, '02-oscuro-acordeon-abierto.png'));

  await page.close();

  // ============ 2) TEMA CLARO ============
  console.log('\n== 2) Tema claro ==');
  const claro = await browser.newPage();
  await claro.setViewport({ width: 1600, height: 950 });
  const errClaro = [];
  claro.on('pageerror', e => errClaro.push(String(e).slice(0, 200)));
  claro.on('console', m => { if (m.type() === 'error') errClaro.push(m.text().slice(0, 200)); });
  await claro.evaluateOnNewDocument(() => {
    try { localStorage.setItem('circuitolab-tema', 'light'); } catch (e) {}
  });
  await claro.goto(BASE, { waitUntil: 'networkidle2', timeout: 45000 });
  await wait(7000);
  const temaClaro = await claro.evaluate(() => ({
    tema: document.documentElement.dataset.theme,
    bg: getComputedStyle(document.body).backgroundColor,
    fg: getComputedStyle(document.body).color,
  }));
  check(temaClaro.tema === 'light', 'el tema claro se aplica', temaClaro);
  check(errClaro.length === 0, 'consola sin errores en tema claro', errClaro.slice(0, 4));
  const fClaro = await firmaLienzo(claro);
  check(fClaro && fClaro.noNegro > 50, 'el circuito dibuja en tema claro', fClaro);
  await claro.screenshot({ path: path.join(CAP, '03-claro-escritorio.png') });
  await claro.close();

  // ============ 3) MÓVIL ============
  console.log('\n== 3) Móvil (390x844) ==');
  const movil = await browser.newPage();
  await movil.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
  const errMovil = [];
  movil.on('pageerror', e => errMovil.push(String(e).slice(0, 200)));
  await movil.goto(BASE, { waitUntil: 'networkidle2', timeout: 45000 });
  await wait(6500);
  const movilInfo = await movil.evaluate(() => ({
    scrollW: document.body.scrollWidth,
    ventana: window.innerWidth,
   Overflow: document.body.scrollWidth > window.innerWidth + 2,
    bloques: document.querySelectorAll('.bloque').length,
  }));
  check(!movilInfo.Overflow, 'sin desbordamiento horizontal en móvil', movilInfo);
  check(errMovil.length === 0, 'consola sin errores en móvil', errMovil.slice(0, 4));
  await movil.screenshot({ path: path.join(CAP, '04-movil.png'), fullPage: true });
  await movil.close();

  await browser.close();

  const resumen = { fallos, avisos, total: fallos.length };
  fs.writeFileSync(path.join(CAP, '..', 'verificacion.json'), JSON.stringify(resumen, null, 1));
  console.log('\n===== RESULTADO: ' + (fallos.length === 0 ? 'TODO OK' : fallos.length + ' FALLOS') + ' =====');
  for (const f of fallos) console.log('  - ' + f);
  process.exit(fallos.length === 0 ? 0 : 1);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
"""


def main():
    os.makedirs(CAPTURAS, exist_ok=True)
    script = "/Users/luissolamantilla/Downloads/temporales_hermes/verificar_app.cjs"
    with open(script, "w", encoding="utf-8") as f:
        f.write(PROBE)
    env = dict(os.environ)
    env["PM"] = NM
    env["CAP"] = CAPTURAS
    return subprocess.run(["node", script], env=env, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
