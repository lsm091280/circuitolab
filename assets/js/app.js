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
  busqueda: '',
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
const PARAMETROS_MOTOR = 'hideMenu=false&hideSidebar=true&hideInfoBox=true&lang=es';

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
  if (ESTADO.api) estilizarMotor();
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

/* ---------------------------------------------------------------- galería */
/* Un icono por categoría, para que la galería tenga jerarquía visual sin
   depender de imágenes externas. Las categorías son exactamente las del
   setuplist del motor (agrupación original de la app de Falstad). */
const ICONO_CATEGORIA = {
  'Conceptos básicos': 'mdi:school-outline',
  'Corriente alterna': 'mdi:sine-wave',
  'Filtros pasivos': 'mdi:filter-variant',
  'Filtros activos': 'mdi:filter-variant',
  'Otros circuitos pasivos': 'mdi:resistor',
  'Diodos': 'mdi:flash',
  'Transistores': 'mdi:amplifier',
  'MOSFET': 'mdi:chip',
  'Temporizador 555': 'mdi:timer-outline',
  'Familias lógicas': 'mdi:logic-gate-and',
  'Lógica combinacional': 'mdi:logic-gate-and',
  'Lógica secuencial': 'mdi:sync',
  'Amplificadores operacionales': 'mdi:amplifier',
  'Líneas de transmisión': 'mdi:transmission-tower',
  'Analógico y digital': 'mdi:waveform',
  'Convertidores de potencia': 'mdi:current-dc',
  'Bucles de enganche de fase': 'mdi:sync',
  'Osciloscopio 2D': 'mdi:chart-bell-curve',
  'Subcircuitos': 'mdi:package-variant',
  'Fuentes controladas': 'mdi:current-dc',
};

/** Línea de recuento bajo el buscador. Sustituye a los antiguos filtros por
 *  curso, que agrupaban los ejemplos de una forma que no es la del motor. */
function actualizarRecuento(nVisibles) {
  const cont = $('#filtros');
  if (!cont) return;
  const total = ESTADO.catalogo.length;
  const completas = ESTADO.catalogo.filter((c) => c.estado === 'completa').length;
  cont.innerHTML = '';
  if (nVisibles === total) {
    cont.appendChild(crear('span', 'recuento', `${total} circuitos · ${completas} con explicación`));
  } else {
    cont.appendChild(crear('span', 'recuento', `${nVisibles} de ${total} circuitos`));
  }
}

function circuitosVisibles() {
  const q = normalizar(ESTADO.busqueda);
  return ESTADO.catalogo.filter((c) => {
    if (!q) return true;
    const heno = normalizar(
      (c.titulo || '') + ' ' + (c.titulo_es || '') + ' ' +
      c.categoria + ' ' + c.subcategoria + ' ' + c.archivo
    );
    return heno.includes(q);
  });
}

function construirGaleria() {
  const cont = $('#lista-circuitos');
  cont.innerHTML = '';
  const visibles = circuitosVisibles();
  actualizarRecuento(visibles.length);

  if (!visibles.length) {
    cont.appendChild(crear('p', 'galeria__vacio', 'Ningún circuito coincide con la búsqueda.'));
    return;
  }

  // Agrupación ORIGINAL del motor: categoría > subcategoría. Así el alumnado
  // encuentra los ejemplos donde los busca su profesor, no repartidos por curso.
  const arbol = new Map();
  for (const c of visibles) {
    if (!arbol.has(c.categoria)) arbol.set(c.categoria, new Map());
    const subs = arbol.get(c.categoria);
    const clave = c.subcategoria || '';
    if (!subs.has(clave)) subs.set(clave, []);
    subs.get(clave).push(c);
  }

  for (const [cat, subs] of arbol) {
    const grupoCat = crear('div', 'grupo');
    const cabCat = crear('button', 'grupo__titulo');
    cabCat.type = 'button';
    cabCat.setAttribute('aria-expanded', 'true');
    cabCat.appendChild(icono(ICONO_CATEGORIA[cat] || 'mdi:bookshelf'));
    cabCat.appendChild(crear('span', null, cat));
    let nCat = 0;
    for (const lista of subs.values()) nCat += lista.length;
    cabCat.appendChild(crear('span', 'grupo__cuenta', String(nCat)));
    const cuerpoCat = crear('div', 'grupo__hijos');
    grupoCat.appendChild(cabCat);
    grupoCat.appendChild(cuerpoCat);

    for (const [sub, lista] of subs) {
      if (sub) {
        const et = crear('div', 'kicker');
        et.style.padding = '8px 6px 4px';
        et.textContent = sub;
        cuerpoCat.appendChild(et);
      }
      for (const c of lista) {
        const b = crear('button', 'circuito');
        b.type = 'button';
        b.dataset.id = c.id;
        b.setAttribute('aria-current', String(ESTADO.circuitoActual === c.id));
        const punto = crear('span', 'circuito__punto ' + c.estado);
        punto.title = c.estado === 'completa' ? 'Explicación completa' : 'Explicación pendiente';
        b.appendChild(punto);
        b.appendChild(crear('span', 'circuito__nombre', nombreCircuito(c)));
        b.addEventListener('click', () => seleccionarCircuito(c.id));
        cuerpoCat.appendChild(b);
      }
    }

    cabCat.addEventListener('click', () => {
      const abierto = cabCat.getAttribute('aria-expanded') === 'true';
      cabCat.setAttribute('aria-expanded', String(!abierto));
      cuerpoCat.hidden = abierto;
    });

    cont.appendChild(grupoCat);
  }
}

function marcarCircuitoActivo() {
  for (const b of document.querySelectorAll('.circuito')) {
    b.setAttribute('aria-current', String(b.dataset.id === ESTADO.circuitoActual));
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
    }
    .gwt-MenuBar td.gwt-MenuItem {
      font: 500 12.5px/1 'DM Sans', system-ui, sans-serif !important;
      color: rgb(${tenue}) !important;
      padding: 8px 10px !important;
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
    /* el lienzo sigue negro: es el color propio del simulador */
    body { margin: 0 !important; }
  `;
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

  const titulo = $('#titulo-circuito');
  const subtitulo = $('#subtitulo-circuito');
  if (titulo) titulo.textContent = nombreCircuito(c);
  if (subtitulo) {
    const partes = [c.curso, c.categoria];
    if (c.subcategoria) partes.push(c.subcategoria);
    subtitulo.textContent = partes.join(' · ');
  }

  marcarCircuitoActivo();
  actualizarPanel();

  if (ESTADO.api) {
    cargarCircuitoEnMotor(id);
  } else {
    const cargando = $('#cargando');
    if (cargando) cargando.hidden = false;
  }
}

/* ---------------------------------------------------------------- buscador */
function initBuscador() {
  const input = $('#buscar');
  if (!input) return;
  let t = null;
  input.addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(() => {
      ESTADO.busqueda = input.value.trim();
      construirGaleria();
    }, 140);
  });
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

/* ---------------------------------------------------------------- iconos */
function initIconos() {
  const mapa = {
    '#icono-buscar': 'mdi:magnify',
    '#icono-reiniciar': 'mdi:restore',
    '#icono-descargar': 'mdi:download-outline',
    '#icono-cargando': 'mdi:electric-switch',
    '#icono-panel': 'mdi:book-open-page-variant',
    '#icono-pendiente': 'mdi:clock-outline',
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
  initBuscador();
  initBotones();

  try {
    await cargarCatalogo();
  } catch (e) {
    console.error(e);
    const cont = $('#lista-circuitos');
    if (cont) cont.innerHTML = '<p class="galeria__vacio">No se pudo cargar el catálogo de circuitos.</p>';
    return;
  }

  ESTADO.bloquesAbiertos = leerJSON(CLAVE_BLOQUES, { como: true, observar: false, prueba: false });
  construirGaleria();
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
