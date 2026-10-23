/* ==========================================================================
   CircuitoLab — lógica de la aplicación
   - carga del catálogo (circuitos/catalogo.json)
   - galería agrupada por curso / categoría / subcategoría, con buscador
   - control del motor por iframe (window.CircuitJS1, mismo origen)
   - acordeón de explicaciones con estado persistente
   - tema claro / oscuro
   ========================================================================== */
'use strict';

/* ---------------------------------------------------------------- estado */
const ESTADO = {
  catalogo: [],
  porId: new Map(),
  circuitoActual: null,
  api: null,              // window.CircuitJS1 del iframe
  bloquesAbiertos: {},     // { bloqueId: true }
  cargando: false,
};

const CLAVE_TEMA = 'circuitolab-tema';
const CLAVE_BLOQUES = 'circuitolab-bloques';
const CLAVE_ULTIMO = 'circuitolab-ultimo';

const MOTOR = 'assets/vendor/circuitjs/engine/circuitjs.html';
// hideMenu SE DEJA EN FALSE: el menú del motor es lo que da "Dibujar" (paleta
// completa de componentes), "Archivo > Nuevo circuito en blanco", deshacer,
// copiar/pegar, zoom y opciones. Sin él, el alumnado no puede crear circuitos,
// que es la mitad de la app original. Ocupa 30 px y ya está en español.
const PARAMETROS_MOTOR = 'hideMenu=false&hideSidebar=false&hideInfoBox=true&lang=es';

// hideSidebar=FALSE: ese panel es el unico sitio donde estan los cursores que
// pide Luis (tension del circuito, velocidad de corriente, velocidad de
// simulacion, brillo). Sin el, la app se queda sin controles.
const BLOQUES = [
  { id: 'como', etiqueta: 'Cómo funciona', icono: 'mdi:information-outline' },
  { id: 'observar', etiqueta: 'Qué observar', icono: 'mdi:eye-outline' },
  { id: 'prueba', etiqueta: 'Prueba tú', icono: 'mdi:pencil-outline' },
];

/* ---------------------------------------------------------------- utilidades */
const $ = (sel) => document.querySelector(sel);
const crear = (tag, clase, texto) => {
  const e = document.createElement(tag);
  if (clase) e.className = clase;
  if (texto !== undefined) e.textContent = texto;
  return e;
};

/** Inserta un SVG de MDI (del set embebido) como elemento.
 *  El HTML viene de assets/icons/icons.js, un fichero local generado por
 *  _tools/generar_iconos.py a partir de @iconify-json/mdi. No hay entrada externa,
 *  así que el innerHTML es seguro aquí. */
function icono(nombre) {
  const svg = window.MDI && window.MDI[nombre];
  const span = crear('span', 'ic');
  if (svg) {
    span.innerHTML = svg;
    const s = span.querySelector('svg');
    if (s) { s.setAttribute('aria-hidden', 'true'); s.setAttribute('focusable', 'false'); }
  }
  return span;
}

function normalizar(txt) {
  return (txt || '').toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

/** Título para mostrar: el traducido si existe, si no el original del motor. */
function nombreCircuito(c) {
  return (c && (c.titulo_es || c.titulo)) || '';
}

function leerJSON(clave, porDefecto) {
  try {
    const v = localStorage.getItem(clave);
    return v ? JSON.parse(v) : porDefecto;
  } catch (e) { return porDefecto; }
}

function guardarJSON(clave, valor) {
  try { localStorage.setItem(clave, JSON.stringify(valor)); } catch (e) { /* modo privado */ }
}

/* ---------------------------------------------------------------- tema */
function aplicarTema(tema) {
  const root = document.documentElement;
  root.dataset.theme = tema;
  const boton = $('#btn-tema');
  const cont = $('#icono-tema');
  if (cont) {
    cont.innerHTML = '';
    cont.appendChild(icono(tema === 'light' ? 'mdi:theme-light-dark' : 'mdi:theme-light-dark'));
  }
  if (boton) {
    boton.setAttribute('aria-label', tema === 'light' ? 'Cambiar a modo oscuro' : 'Cambiar a modo claro');
  }
  // el menú del motor se tiñe con el tema del shell (mismo origen)
  if (ESTADO.api) { estilizarMotor(); modernizarCursores(); }
}

function initTema() {
  let tema = 'dark';
  try { tema = localStorage.getItem(CLAVE_TEMA) || 'dark'; } catch (e) { /* ignora */ }
  aplicarTema(tema);
  const boton = $('#btn-tema');
  if (boton) {
    boton.addEventListener('click', () => {
      const nuevo = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
      aplicarTema(nuevo);
      try { localStorage.setItem(CLAVE_TEMA, nuevo); } catch (e) { /* ignora */ }
    });
  }
}

/* ---------------------------------------------------------------- carga */
async function cargarCatalogo() {
  const resp = await fetch('circuitos/catalogo.json', { cache: 'no-cache' });
  if (!resp.ok) throw new Error('No se pudo cargar el catálogo: HTTP ' + resp.status);
  ESTADO.catalogo = await resp.json();
  ESTADO.porId = new Map(ESTADO.catalogo.map((c) => [c.id, c]));
}

/* ------------------------------------------------- identificación del circuito */
/* La galería lateral se quitó por indicación de Luis: los ejemplos ya están en
   el menú «Ejemplos de circuitos» del motor. Pero el panel didáctico necesita
   saber QUÉ circuito hay cargado, y el motor no avisa por API.

   Solución: el motor pide cada circuito como `circuits/<archivo>.txt`. Como el
   iframe es del mismo origen, se interceptan `fetch` y `XMLHttpRequest` dentro
   del iframe y se traduce el nombre del fichero al id del catálogo. Así el panel
   sigue al circuito se elija como se elija: menú del motor o importación. */
const POR_ARCHIVO = new Map();      // 'ohms.txt' -> registro del catálogo

function indexarArchivos() {
  POR_ARCHIVO.clear();
  for (const c of ESTADO.catalogo) {
    if (c.archivo) POR_ARCHIVO.set(c.archivo, c);
  }
}

/** El motor ha cargado un fichero de circuito: se sincroniza el panel. */
function alCargarArchivo(archivo) {
  const c = POR_ARCHIVO.get(archivo);
  if (!c) {
    // circuito propio, subcircuito o fichero importado: no está en el catálogo
    ESTADO.circuitoActual = null;
    const titulo = $('#titulo-circuito');
    const sub = $('#subtitulo-circuito');
    if (titulo) titulo.textContent = 'Circuito propio';
    if (sub) sub.textContent = 'Creado o importado. No está en el catálogo.';
    actualizarPanel();
    return;
  }
  if (ESTADO.circuitoActual === c.id) return;
  ESTADO.circuitoActual = c.id;
  try { localStorage.setItem(CLAVE_ULTIMO, c.id); } catch (e) { /* modo privado */ }
  pintarCabecera(c);
  actualizarPanel();
}

/** Engancha los cargadores del motor para enterarse de cada circuito. */
function vigilarCargasDelMotor() {
  const iframe = $('#lienzo');
  let w;
  try { w = iframe.contentWindow; } catch (e) { return; }
  if (!w || w.__circuitolabEnganchado) return;
  w.__circuitolabEnganchado = true;

  const revisar = (url) => {
    const m = String(url || '').match(/circuits\/([^/?#]+\.txt)/);
    if (m) alCargarArchivo(m[1]);
  };

  const fetchOriginal = w.fetch;
  if (typeof fetchOriginal === 'function') {
    w.fetch = function (...args) {
      try {
        const u = args[0];
        revisar(typeof u === 'string' ? u : (u && u.url));
      } catch (e) { /* no romper la carga por un fallo del gancho */ }
      return fetchOriginal.apply(this, args);
    };
  }

  const proto = w.XMLHttpRequest && w.XMLHttpRequest.prototype;
  if (proto && proto.open) {
    const abrirOriginal = proto.open;
    proto.open = function (metodo, url, ...resto) {
      try { revisar(url); } catch (e) { /* idem */ }
      return abrirOriginal.call(this, metodo, url, ...resto);
    };
  }
}

/** Cabecera del simulador: nombre, curso y categoría del circuito. */
function pintarCabecera(c) {
  const titulo = $('#titulo-circuito');
  const subtitulo = $('#subtitulo-circuito');
  if (titulo) titulo.textContent = nombreCircuito(c);
  if (subtitulo) {
    // el curso (3º ESO, 4º ESO...) fuera: Luis no lo quiere en la barra
    const partes = [c.categoria];
    if (c.subcategoria) partes.push(c.subcategoria);
    subtitulo.textContent = partes.join(' · ');
  }
}

/* ---------------------------------------------------------------- motor */
function urlMotor(circuito) {
  // El motor se carga una sola vez con las banderas; el circuito se cambia
  // después vía la API importCircuit (sin recargar el iframe).
  return MOTOR + '?' + PARAMETROS_MOTOR;
}

function iniciarMotor() {
  const iframe = $('#lienzo');
  const cargando = $('#cargando');
  iframe.addEventListener('load', () => {
    if (cargando) cargando.hidden = true;
    conectarAPI();
  });
  iframe.src = urlMotor();
}

function conectarAPI() {
  const iframe = $('#lienzo');
  let intentos = 0;
  const probar = () => {
    intentos += 1;
    try {
      const w = iframe.contentWindow;
      if (w && w.CircuitJS1) {
        ESTADO.api = w.CircuitJS1;
        estilizarMotor();
        modernizarCursores();
        vigilarPanel();
        vigilarCargasDelMotor();
        if (ESTADO.circuitoActual) cargarCircuitoEnMotor(ESTADO.circuitoActual);
        return;
      }
    } catch (e) { /* aún no listo */ }
    if (intentos < 60) setTimeout(probar, 250);
  };
  setTimeout(probar, 300);
}

/* ------------------------------------------------------- estilo del motor */
/** El motor trae su propia hoja de estilos (noventera). Como el iframe es del
 *  mismo origen, se le inyecta un <style> con los tokens del brand: tipografía,
 *  superficies y hover. NO se toca el bundle: el motor sigue siendo el original.
 *  Se llama al conectar y cada vez que cambia el tema. */
function estilizarMotor() {
  const iframe = $('#lienzo');
  let doc;
  try { doc = iframe.contentDocument; } catch (e) { return; }
  if (!doc || !doc.head) return;

  const raiz = getComputedStyle(document.documentElement);
  const v = (n) => raiz.getPropertyValue(n).trim();
  const fondo = v('--surface-rgb') || '27 38 54';
  const fg = v('--fg-rgb') || '221 234 240';
  const borde = v('--border-rgb') || '83 103 125';
  const acento = v('--accent-rgb') || '104 215 232';
  const tenue = v('--muted-rgb') || '148 169 184';
  const realce = v('--surface2-rgb') || '44 58 77';

  let st = doc.getElementById('circuitolab-estilo');
  if (!st) {
    st = doc.createElement('style');
    st.id = 'circuitolab-estilo';
    doc.head.appendChild(st);
  }

  st.textContent = `
    /* --- cursores propios (el motor los dibuja en canvas, estilo 2003) --- */
    .cl-cursor-caja { position: relative; width: 166px; height: 22px; margin: 2px 0 0 0; }
    .cl-cursor-caja > canvas { position: absolute; inset: 0; opacity: 0; pointer-events: none; }
    .cl-cursor {
      -webkit-appearance: none; appearance: none;
      position: absolute; inset: 0; width: 100%; height: 22px;
      margin: 0; padding: 0; background: transparent; cursor: pointer;
      --p: 50%;
    }
    .cl-cursor::-webkit-slider-runnable-track {
      height: 4px; border-radius: 2px;
      background: linear-gradient(to right,
        rgb(${acento}) 0%, rgb(${acento}) var(--p),
        rgb(${realce}) var(--p), rgb(${realce}) 100%);
    }
    .cl-cursor::-webkit-slider-thumb {
      -webkit-appearance: none; appearance: none;
      width: 13px; height: 13px; margin-top: -4.5px;
      border-radius: 50%; background: rgb(${acento});
      border: 2px solid rgb(${fondo});
      box-shadow: none;
    }
    .cl-cursor--off { opacity: .45; cursor: default; }
    .cl-cursor--off::-webkit-slider-runnable-track { background: rgb(${realce}); }
    .cl-cursor--off::-webkit-slider-thumb { background: rgb(${tenue}); }
    .cl-cursor:focus-visible { outline: none; }
    .cl-cursor:focus-visible::-webkit-slider-thumb {
      box-shadow: 0 0 0 3px rgb(${acento} / .35);
    }
    /* la fuente del brand, cargada también dentro del iframe */
    @font-face {
      font-family: 'DM Sans';
      src: url('../../../fonts/dm-0.woff2') format('woff2');
      font-weight: 400; font-style: normal; font-display: swap;
    }
    @font-face {
      font-family: 'DM Sans';
      src: url('../../../fonts/dm-1.woff2') format('woff2');
      font-weight: 500; font-style: normal; font-display: swap;
    }
    /* barra de menús del motor */
    .gwt-MenuBar, .gwt-MenuBar-horizontal {
      background: rgb(${fondo}) !important;
      border-bottom: 1px solid rgb(${borde}) !important;
      padding: 0 4px !important;
      /* la barra de iconos del motor mide 33 px y la franja 30: se recortaban
         por abajo en cualquier ancho. Se deja crecer a lo que necesite. */
      height: auto !important;
      min-height: 0 !important;
      overflow: visible !important;
    }
    .gwt-MenuBar td.gwt-MenuItem {
      font: 500 12.5px/1 'DM Sans', system-ui, sans-serif !important;
      color: rgb(${tenue}) !important;
      /* 6 px arriba y abajo: con 8 la fila medía 33 px en una franja de 30 y
         los iconos de la barra de herramientas se recortaban por abajo */
      padding: 6px 10px !important;
      border-radius: 6px !important;
      transition: color .12s, background .12s;
    }
    .gwt-MenuBar td.gwt-MenuItem:hover,
    .gwt-MenuBar td.gwt-MenuItem-selected {
      color: rgb(${fg}) !important;
      background: rgb(${realce}) !important;
    }
    /* desplegables: el motor NO usa GWT para esto, usa UL.menuDropdown */
    .menuDropdown {
      background: rgb(${fondo}) !important;
      border: 1px solid rgb(${borde}) !important;
      border-radius: 10px !important;
      padding: 5px !important;
      box-shadow: none !important;
      z-index: 100 !important;
    }
    .menuItem {
      font: 400 13px/1.45 'DM Sans', system-ui, sans-serif !important;
      color: rgb(${fg}) !important;
      padding: 6px 9px !important;
      border-radius: 6px !important;
      gap: 8px;
    }
    .menuItem:hover { background: rgb(${realce}) !important; color: rgb(${acento}) !important; }
    .menuItem.menuItemDisabled, .menuItem.menuItemDisabled:hover {
      color: rgb(${tenue}) !important;
      background: none !important;
      opacity: .55;
    }
    .menuSeparator { border-top: 1px solid rgb(${borde}) !important; margin: 4px 2px !important; }
    .shortcutHint {
      font: 400 11px 'IBM Plex Mono', ui-monospace, monospace !important;
      color: rgb(${tenue}) !important;
      opacity: .8;
    }
    .submenuArrow { color: rgb(${tenue}) !important; }
    .menuItem i { color: rgb(${tenue}) !important; }
    .menuItem:hover i { color: rgb(${acento}) !important; }
    /* desplegables GWT (por si alguna parte los usa) */
    .gwt-MenuBarPopup, .gwt-MenuBar-vertical {
      background: rgb(${fondo}) !important;
      border: 1px solid rgb(${borde}) !important;
      border-radius: 10px !important;
      padding: 4px !important;
      box-shadow: none !important;
    }
    .gwt-MenuBarPopup td.gwt-MenuItem, .gwt-MenuBar-vertical td.gwt-MenuItem {
      font: 400 13px/1.5 'DM Sans', system-ui, sans-serif !important;
      color: rgb(${fg}) !important;
      padding: 6px 12px !important;
      border-radius: 6px !important;
    }
    .gwt-MenuBarPopup td.gwt-MenuItem:hover,
    .gwt-MenuBarPopup td.gwt-MenuItem-selected {
      background: rgb(${realce}) !important;
      color: rgb(${acento}) !important;
    }
    /* separadores y casillas del menu */
    .gwt-MenuBarPopup .gwt-MenuItem-separator {
      border-top: 1px solid rgb(${borde}) !important;
      margin: 4px 0 !important;
    }
    .gwt-MenuBarPopup img { filter: none !important; }
    /* panel lateral del motor: aqui viven los cursores (tension, velocidad de
       corriente, velocidad de simulacion, brillo). Los cursores son canvas
       dibujados por el motor: no se pueden recolorear por CSS, solo el marco. */
    #painel {
      background: rgb(${fondo}) !important;
      border-left: 1px solid rgb(${borde}) !important;
      /* sin padding lateral: los cursores del motor miden 166 px fijos y con
         padding se salian del panel (scrollWidth 186 > 165) y se cortaban */
      padding: 6px 0 0 0 !important;
      box-sizing: border-box !important;
      overflow: hidden !important;
    }
    #painel .topButton { width: 166px !important; }
    #painel .topButton {
      width: 100% !important;
      margin: 0 0 6px 0 !important;
      padding: 6px 8px !important;
      background: rgb(${realce}) !important;
      border: 1px solid rgb(${borde}) !important;
      border-radius: 6px !important;
      color: rgb(${fg}) !important;
      font: 600 10.5px/1.2 'IBM Plex Mono', ui-monospace, monospace !important;
      letter-spacing: .04em;
      cursor: pointer;
    }
    #painel .topButton:hover { border-color: rgb(${acento}) !important; color: rgb(${acento}) !important; }
    #painel .topSpace {
      font: 600 10.5px/1.25 'IBM Plex Mono', ui-monospace, monospace !important;
      letter-spacing: .05em;
      text-transform: uppercase;
      /* antes iban en color tenue a 9.5 px: no se leian en oscuro */
      color: rgb(${fg}) !important;
      margin: 12px 0 5px 0 !important;
      padding-left: 9px !important;
      white-space: normal !important;
      border-left: 2px solid rgb(${acento}) !important;
    }
    #painel .topSpace.disabled { opacity: .45; }
    /* El valor del circuito actual es un div sin clase que el motor pinta en
       NEGRO: sobre fondo oscuro no se lee. */
    #painel > div:not(.topSpace):not(.cl-cursor-caja) {
      color: rgb(${fg}) !important;
      font: 400 12.5px/1.35 'DM Sans', system-ui, sans-serif !important;
      padding: 0 9px 2px !important;
    }
    /* Barra de herramientas del motor: div fijo de ~836 px con fondo blanco
       (#f8f8f8). Se pinta con el brand y, si no cabe, se desplaza en vez de
       desbordar por la derecha. */
    .cl-barra-motor {
      background: rgb(${fondo}) !important;
      max-width: 100% !important;
      /* SIN overflow: recortaba los desplegables de las herramientas (salían
         cortados y desplazados). Los iconos ya caben sin scroll. */
      overflow: visible !important;
    }
    .cl-barra-motor * { color: rgb(${fg}) !important; }
    /* Iconos de la barra: el motor los dibuja a 36x35 y no caben (854 px de
       contenido en ~656 de hueco). Se reducen; los 10 primeros -edición y
       zoom, que no necesitan tanto- más que el resto. */
    .cl-barra-motor > span {
      width: 27px !important;
      height: 27px !important;
      font-size: 19px !important;
    }
    .cl-barra-motor > span:nth-child(-n+10) {
      width: 22px !important;
      height: 22px !important;
      font-size: 15px !important;
    }
    /* Los desplegables de las herramientas llevan la MISMA clase que la barra
       y sus iconos son SVG con width/height=40 fijos en el HTML: salian al
       doble. NO se puede encoger el SVG: su dibujo interno queda pegado al
       borde y la salida de la puerta se corta. Se deja la caja como el motor
       la calcula (40x40, asi no hay recortes ni solapes) y se ESCALA el dibujo. */
    .palette-container > span:nth-child(n) {
      /* 40x40 = la caja que calcula el motor. Con menos, el SVG de 40 se sale
         y la puerta se corta por abajo. El tamano se baja escalando, no midiendo. */
      width: 40px !important;
      height: 40px !important;
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      vertical-align: top !important;
      overflow: visible !important;
      transform: scale(0.52) !important;
      transform-origin: center center !important;
    }
    .palette-container > span > svg {
      width: 40px !important;
      height: 40px !important;
    }

    /* OJO: aqui habia un zoom para hacer sitio. NO se puede usar: los
       desplegables de la paleta son hijos absolutos de esta barra y el zoom
       desplaza su posicion (salian a la izquierda y no se podian pulsar).
       El hueco se gana reduciendo los iconos, no escalando la barra. */
    /* El rotulo "Modo: ..." que el motor escribe a la derecha de los iconos va
       con el mismo tamano que el resto y empuja la barra. Se reduce y se le
       limita el ancho para que nunca desborde. */
    .cl-barra-motor { font-size: 9.5px !important; }
    .cl-barra-motor > *:not([class*="cirjsicon"]) {
      font: 400 9.5px/1.2 'DM Sans', system-ui, sans-serif !important;
      /* el flex lo aplastaba a 35 px: se le da su ancho y el hueco se gana
         bajando el zoom de la barra */
      flex: 0 0 auto;
      max-width: none;
      /* el motor le fija un ancho pequeno (38 px) y el texto se derramaba:
         se le obliga a crecer con su contenido */
      width: max-content !important;
      min-width: 0 !important;
      white-space: nowrap;
      color: rgb(${tenue}) !important;
      padding-left: 8px;
    }
    .cl-barra-motor::-webkit-scrollbar { height: 6px; }
    .cl-barra-motor::-webkit-scrollbar-thumb { background: rgb(${borde}); border-radius: 3px; }
    #painel label.topSpace { display: block; }
    /* el motor mete un iframe.html vacio de 325 px como hueco de branding:
       aqui no hay branding que poner, asi que se oculta */
    #painel > iframe { display: none !important; }
    /* el lienzo sigue negro: es el color propio del simulador */
    body { margin: 0 !important; }
  `;

  // marca las barras claras del motor (fondo #f8f8f8 / blanco) para darles el
  // tratamiento del brand; se hace por color computado porque no tienen clase
  try {
    const vista = doc.defaultView;
    for (const el of doc.querySelectorAll('div')) {
      if (el.classList.contains('cl-barra-motor')) continue;
      const fondo = vista.getComputedStyle(el).backgroundColor;
      if (fondo === 'rgb(248, 248, 248)' || fondo === 'rgb(255, 255, 255)') {
        el.classList.add('cl-barra-motor');
      }
    }
  } catch (e) { /* si el DOM del motor no está listo, se reintenta al reconectar */ }
}

/* ------------------------------------------------- cursores del motor */
/** El motor dibuja sus cursores en <canvas>: carril con flechas en los extremos,
 *  relleno rojo y tirador metálico. Es estética de 2003 y NO se puede recolorear
 *  por CSS (los píxeles los pinta el propio motor).
 *
 *  Solución: se tapan con un input range del brand y se pilotan disparando los
 *  mismos eventos de ratón que produciría el usuario sobre el canvas original.
 *  El motor sigue siendo el dueño del valor; solo cambia la piel. */
function modernizarCursores() {
  const iframe = $('#lienzo');
  let doc;
  try { doc = iframe.contentDocument; } catch (e) { return; }
  if (!doc) return;
  const panel = doc.getElementById('painel');
  if (!panel) return;

  // idempotente: se deshace el envoltorio anterior antes de volver a envolver.
  // Sin esto, cada reconstruccion del panel dejaba cursores viejos sin etiqueta.
  for (const caja of panel.querySelectorAll('.cl-cursor-caja')) {
    const lienzo = caja.querySelector('canvas');
    if (lienzo) {
      delete lienzo.dataset.clCursor;
      caja.parentNode.insertBefore(lienzo, caja);
    }
    caja.remove();
  }

  for (const c of panel.querySelectorAll('canvas')) {
    if (c.dataset.clCursor) continue;
    // solo los cursores que llevan etiqueta del motor; los canvas sueltos son
    // restos de una reconstruccion a medias y no deben mostrarse
    const etiquetaEl = c.previousElementSibling;
    const tieneEtiqueta = etiquetaEl && etiquetaEl.classList &&
                          etiquetaEl.classList.contains('topSpace');
    if (!tieneEtiqueta) { c.style.display = 'none'; continue; }

    // posición de partida: hasta dónde llega el relleno rojo del motor
    const etiqueta = (etiquetaEl && etiquetaEl.textContent || '').trim();
    let frac = 0.5;
    try {
      const datos = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      const fila = Math.floor(c.height / 2);
      let ultimo = -1;
      for (let x = 0; x < c.width; x++) {
        const i = (fila * c.width + x) * 4;
        if (datos[i] > 110 && datos[i + 1] < 100 && datos[i + 2] < 100) ultimo = x;
      }
      if (ultimo > 0) frac = ultimo / c.width;
    } catch (e) { /* canvas opaco: se queda en el centro */ }

    const caja = doc.createElement('div');
    caja.className = 'cl-cursor-caja';
    c.parentNode.insertBefore(caja, c);
    caja.appendChild(c);

    const entrada = doc.createElement('input');
    entrada.type = 'range';
    entrada.min = '0';
    entrada.max = '1000';
    entrada.value = String(Math.round(frac * 1000));
    entrada.className = 'cl-cursor';
    entrada.setAttribute('aria-label', etiqueta || 'Cursor de simulación');
    entrada.style.setProperty('--p', (frac * 100).toFixed(1) + '%');
    // Brillo viene deshabilitado en el motor: el cursor debe parecerlo
    if (etiquetaEl && etiquetaEl.classList.contains('disabled')) {
      entrada.classList.add('cl-cursor--off');
      entrada.disabled = true;
    }
    caja.appendChild(entrada);

    const mover = (valor) => {
      const r = c.getBoundingClientRect();
      if (!r.width) return;
      const x = r.x + (valor / 1000) * r.width;
      const y = r.y + r.height / 2;
      const enviar = (tipo) => c.dispatchEvent(new MouseEvent(tipo, {
        bubbles: true, cancelable: true, view: doc.defaultView,
        clientX: x, clientY: y, button: 0, buttons: 1,
      }));
      enviar('mousedown');
      enviar('mousemove');
      enviar('mouseup');
    };

    entrada.addEventListener('input', () => {
      entrada.style.setProperty('--p', (entrada.value / 10).toFixed(1) + '%');
      mover(Number(entrada.value));
    });

    c.dataset.clCursor = '1';
  }
}

/** El motor reconstruye el panel al cambiar de circuito: hay que reponer los
 *  cursores cada vez. */
function vigilarPanel() {
  const iframe = $('#lienzo');
  let doc;
  try { doc = iframe.contentDocument; } catch (e) { return; }
  const panel = doc && doc.getElementById('painel');
  if (!panel || panel.__clVigilado) return;
  panel.__clVigilado = true;
  const Observador = doc.defaultView.MutationObserver;
  if (!Observador) return;
  const obs = new Observador(() => {
    if (panel.__clPendiente) return;
    panel.__clPendiente = true;
    setTimeout(() => { panel.__clPendiente = false; modernizarCursores(); }, 160);
  });
  obs.observe(panel, { childList: true, subtree: true });
}

/** Carga un circuito en el motor por la API (mismo origen). */
async function cargarCircuitoEnMotor(id) {
  const c = ESTADO.porId.get(id);
  if (!c || !ESTADO.api) return;
  try {
    const resp = await fetch(c.url_circuito, { cache: 'no-cache' });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const texto = await resp.text();
    ESTADO.api.importCircuit(texto, false);
    ESTADO.api.setSimRunning(true);
  } catch (e) {
    console.error('No se pudo cargar el circuito', id, e);
  }
}

/* ---------------------------------------------------------------- panel */
function estadoAcordeon() {
  return ESTADO.bloquesAbiertos;
}

function construirAcordeon() {
  const cont = $('#acordeon');
  cont.innerHTML = '';
  const c = ESTADO.circuitoActual ? ESTADO.porId.get(ESTADO.circuitoActual) : null;
  const pendientes = $('#sin-explicacion');

  if (!c || c.estado !== 'completa') {
    if (pendientes) pendientes.hidden = false;
    return;
  }
  if (pendientes) pendientes.hidden = true;

  const abiertos = estadoAcordeon();
  const campos = { como: 'explicacion_html', observar: 'que_observar', prueba: 'prueba_tu' };

  for (const b of BLOQUES) {
    const contenido = c[campos[b.id]] || '';
    if (!contenido) continue;

    const div = crear('div', 'bloque');
    const cab = crear('button', 'bloque__cabecera');
    cab.type = 'button';
    const abierto = !!abiertos[b.id];
    cab.setAttribute('aria-expanded', String(abierto));
    cab.setAttribute('aria-controls', 'bloque-' + b.id);
    cab.appendChild(icono(b.icono));
    cab.appendChild(crear('span', null, b.etiqueta));
    cab.appendChild(icono('mdi:chevron-down'));

    const cuerpo = crear('div', 'bloque__contenido');
    cuerpo.id = 'bloque-' + b.id;
    // El HTML viene de circuitos/catalogo.json, un fichero local escrito y
    // revisado por el autor (solo p, span con clase fx, ul y li). No hay
    // entrada de usuario ni contenido remoto, asi que el innerHTML es seguro.
    cuerpo.innerHTML = contenido;
    if (!abierto) cuerpo.hidden = true;

    cab.addEventListener('click', () => {
      const ahoraAbierto = cab.getAttribute('aria-expanded') === 'true';
      cab.setAttribute('aria-expanded', String(!ahoraAbierto));
      cuerpo.hidden = ahoraAbierto;
      ESTADO.bloquesAbiertos[b.id] = !ahoraAbierto;
      guardarJSON(CLAVE_BLOQUES, ESTADO.bloquesAbiertos);
    });

    div.appendChild(cab);
    div.appendChild(cuerpo);
    cont.appendChild(div);
  }
}

function actualizarPanel() {
  const c = ESTADO.circuitoActual ? ESTADO.porId.get(ESTADO.circuitoActual) : null;
  const estado = $('#estado-panel');
  if (estado) {
    estado.textContent = c ? (c.estado === 'completa' ? 'Completa' : 'Pendiente') : '—';
    estado.classList.toggle('completa', !!c && c.estado === 'completa');
  }
  construirAcordeon();
}

/* ---------------------------------------------------------------- selección */
function seleccionarCircuito(id) {
  const c = ESTADO.porId.get(id);
  if (!c) return;
  ESTADO.circuitoActual = id;
  try { localStorage.setItem(CLAVE_ULTIMO, id); } catch (e) { /* ignora */ }

  pintarCabecera(c);
  actualizarPanel();

  if (ESTADO.api) {
    cargarCircuitoEnMotor(id);
  } else {
    const cargando = $('#cargando');
    if (cargando) cargando.hidden = false;
  }
}

/* ---------------------------------------------------------------- botones */
function initBotones() {
  const reiniciar = $('#btn-reiniciar');
  if (reiniciar) {
    reiniciar.addEventListener('click', () => {
      if (ESTADO.circuitoActual) cargarCircuitoEnMotor(ESTADO.circuitoActual);
    });
  }

  const descargar = $('#btn-descargar');
  if (descargar) {
    descargar.addEventListener('click', async () => {
      const c = ESTADO.circuitoActual ? ESTADO.porId.get(ESTADO.circuitoActual) : null;
      if (!c) return;
      try {
        const resp = await fetch(c.url_circuito, { cache: 'no-cache' });
        const texto = await resp.text();
        const blob = new Blob([texto], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = crear('a');
        a.href = url;
        a.download = c.archivo;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      } catch (e) {
        console.error('No se pudo descargar el esquema', e);
      }
    });
  }
}

/* ---------------------------------------------------------------- ayuda */
function initAyuda() {
  const panel = $('#ayuda-panel');
  const abrir = $('#btn-ayuda');
  const cerrar = $('#btn-ayuda-cerrar');
  if (!panel || !abrir) return;

  const poner = (visible) => {
    panel.hidden = !visible;
    abrir.setAttribute('aria-expanded', String(visible));
  };

  abrir.addEventListener('click', () => poner(panel.hidden));
  if (cerrar) cerrar.addEventListener('click', () => poner(false));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !panel.hidden) poner(false);
  });
}

/* ---------------------------------------------------------------- iconos */
function initIconos() {
  const mapa = {
    '#icono-reiniciar': 'mdi:restore',
    '#icono-descargar': 'mdi:download-outline',
    '#icono-cargando': 'mdi:electric-switch',
    '#icono-panel': 'mdi:book-open-page-variant',
    '#icono-pendiente': 'mdi:clock-outline',
    '#icono-ayuda': 'mdi:help-circle-outline',
    '#icono-ayuda-cerrar': 'mdi:close',
  };
  for (const [sel, nombre] of Object.entries(mapa)) {
    const cont = document.querySelector(sel);
    if (cont) {
      cont.innerHTML = '';
      cont.appendChild(icono(nombre));
    }
  }
}

/* ---------------------------------------------------------------- arranque */
async function main() {
  initTema();
  initIconos();
  initBotones();
  initAyuda();

  try {
    await cargarCatalogo();
  } catch (e) {
    console.error(e);
    const titulo = $('#titulo-circuito');
    if (titulo) titulo.textContent = 'No se pudo cargar el catálogo';
    return;
  }

  ESTADO.bloquesAbiertos = leerJSON(CLAVE_BLOQUES, { como: true, observar: false, prueba: false });
  indexarArchivos();
  actualizarPanel();

  iniciarMotor();

  // último circuito visto
  let ultimo = null;
  try { ultimo = localStorage.getItem(CLAVE_ULTIMO); } catch (e) { /* ignora */ }
  if (ultimo && ESTADO.porId.has(ultimo)) {
    seleccionarCircuito(ultimo);
  } else {
    // por defecto, el primero con explicación completa
    const primero = ESTADO.catalogo.find((c) => c.estado === 'completa');
    if (primero) seleccionarCircuito(primero.id);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', main);
} else {
  main();
}
