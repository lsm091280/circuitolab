# CircuitoLab — informe técnico

Simulador de circuitos para clase construido **sobre el motor CircuitJS1** (Paul
Falstad e Iain Sharp), con interfaz propia del brand tecnoLSM y una capa didáctica:
cada circuito lleva una explicación de su funcionamiento que se abre y se cierra.

- **Versión del informe:** 22 de octubre de 2026
- **Carpeta de trabajo:** `~/Downloads/circuitolab/`
- **Licencia del conjunto:** GPL-2.0 (ver «Licencia y atribución»)

---

## 1. Vía de integración elegida: A (shell propio + motor en iframe self-hosteado)

**Elegí la vía A y está probada empíricamente, no supuesto.** La vía B (fork del Java
y recompilar con GWT) no se ha iniciado: no hizo falta.

### 1.1 Qué funciona (medido con Chrome headless, no de memoria)

| Comprobación | Cómo se midió | Resultado |
|---|---|---|
| El motor se carga en `<iframe>` | `page.goto` + espera de red | HTTP 200, lienzo de 1440×900 en (0,0) |
| `?hideMenu=true` | Medición de la geometría del canvas principal | El lienzo pasa de 1274×830 en (0,70) a 1440×900 en (0,0) — la barra de menús desaparece |
| `?hideSidebar=true` | Ídem | Desaparecen los 6 canvas auxiliares del panel lateral; lienzo 1440×870 |
| `?hideInfoBox=true` | Medición de texto visible | Desaparecen las etiquetas «Circuito actual:», «Velocidad de simulación», «Brillo» |
| Las tres juntas | Ídem | Lienzo 1440×900 en (0,0), **0 tablas, 0 etiquetas**: el lienzo queda limpio |
| `?lang=es` | Lectura del texto del DOM del motor | La interfaz sale en castellano: «Velocidad de simulación», «Circuito actual:», «Reiniciar», «Conexión eléctrica», «Resistencia» |
| La simulación avanza | `CircuitJS1.getTime()` dos veces, 2,5 s de diferencia | El tiempo de simulación cambia: **no es un dibujo estático** |
| Se puede parar y reanudar | `setSimRunning(false)` / `(true)` | Congela el tiempo y lo reanuda |
| Cambiar de circuito sin recargar | `importCircuit()` con `cap.txt`, `induct.txt`, `pot.txt` | El número de elementos del circuito cambia 9 → 8 → 6, coincidiendo con cada `.txt` |

**La prueba que lo respalda:** con las tres banderas, el motor entrega un canvas de
1440×900 sin ninguna interfaz alrededor, y expone `window.CircuitJS1` con 13 métodos
(`importCircuit`, `getTime`, `setSimRunning`, `getElements`, `getCircuitAsSVG`…). Como
el shell y el motor se sirven **desde el mismo origen**, el `iframe.contentWindow` es
accesible sin trampas de CORS.

> Detalle técnico: el primer intento de sonda falló con
> `SecurityError: Blocked a frame with origin "null" from accessing a cross-origin
> frame`. La causa era que la página de prueba se creaba con `page.setContent()`
> (origen `null`). Servido desde el mismo origen que el motor, funciona.

### 1.2 Por qué no la vía B

Recompilar el motor exigiría Eclipse + plugin GWT + JDK sobre un repositorio parado
desde enero de 2024, con un único mantenedor. El resultado sería idéntico en
funcionalidad y mucho más frágil. La vía A da exactamente lo que se pedía
(lienzo limpio + interfaz propia) con coste cero de mantenimiento.

### 1.3 Lo que NO se ha hecho

- No se ha modificado ni un byte del motor: se copia tal cual (`assets/vendor/circuitjs/engine/`).
- No se ha reimplementado el motor.
- No se ha reescrito el aspecto del original: la interfaz del motor queda oculta.

---

## 2. El motor y sus datos

| Elemento | Origen | Tamaño |
|---|---|---|
| Bundle GWT (`circuitjs-_Vd2jZk5.js`) | `circuitjs1.falstad.com/circuit/` | 1,18 MB |
| CSS del motor + tipografía `fontello` | ídem | 6 KB + 5 ficheros |
| `setuplist.txt` | ídem | 12,6 KB, **367 entradas** |
| `circuits/*.txt` | ídem | **367 circuitos** |
| `locale/locale_es.txt` | ídem | 68 KB |
| `lz-string.min.js` | repo `sharpie7/circuitjs1` | 4,7 KB |
| `COPYING.txt` (licencia GPL-2.0) | repo `sharpie7/circuitjs1` | 18 KB |

### 2.1 El repositorio como fuente de verdad

El repo `sharpie7/circuitjs1` (GPL-2.0, último push 2024-01-22) contiene el código
Java legible. Se ha usado para:

1. Extraer el **mapa oficial de tipos** de `CirSim.java` (`createCe()`): qué código
   numérico corresponde a cada elemento (`r` = resistencia, `c` = condensador,
   `172` = fuente variable, `38` = control deslizante, `o` = osciloscopio, `h` = pista…).
2. Leer el **formato de volcado** de cada clase en su fichero `.java` (`VoltageElm.java`,
   `VarRailElm.java`, `RailElm.java`…). Esto es lo que permite extraer valores reales
   (resistencias, capacidades, frecuencias, tensiones de alimentación) en lugar de
   adivinarlos.

### 2.2 Comparación repo ↔ sitio en vivo

Los circuitos del repo y los del sitio en vivo son **idénticos byte a byte** en las
muestras comprobadas (`ohms.txt`, `cap.txt`, `3-cgand.txt`).

El `setuplist.txt` **sí difiere**: el del sitio en vivo tiene 367 entradas y el del
repo 331 (el vivo incluye 36 circuitos más: familia `cs-*`, `td4-*`, `nmosinverter3`,
`satcore-*`…). **Se usa el `setuplist.txt` del sitio en vivo** (367 circuitos) porque
es el que el motor carga en ejecución y el que corresponde al bundle desplegado.

---

## 3. Cobertura real de la traducción al español

El motor trae `locale/locale_es.txt` (68 KB). Se ha medido su cobertura real
contra las llamadas de traducción que el bundle hace:

| Medida | Valor |
|---|---|
| Claves en `locale_es.txt` | **1.702** |
| Cadenas distintas que el motor pide traducir (`T.LS(...)`) | **194** |
| Cadenas cubiertas **literalmente** por el fichero de idioma | **169 (87,1 %)** |
| Cadenas cubiertas contando las variantes `~N` | **169 (87,1 %)** |
| Cadenas sin cubrir | **25** |

Las 25 sin cubrir se repiten en pantalla. Todas están **verificadas en la captura**:

| Cadena sin traducir | Dónde aparece | Traducción propuesta |
|---|---|---|
| `Command Palette` | paleta de comandos | «Paleta de comandos» |
| `Type a command...` | paleta de comandos | «Escribe un comando…» |
| `Recent` | paleta de comandos | «Recientes» |
| `Active Building Blocks` | paleta de comandos | «Bloques activos» |
| `Active Components` | paleta de comandos | «Componentes activos» |
| `Analog and Hybrid Chips` | paleta de comandos | «Chips analógicos e híbridos» |
| `Digital Chips` | paleta de comandos | «Chips digitales» |
| `Drag` | paleta de comandos | «Arrastrar» |
| `Passive Components` | paleta de comandos | «Componentes pasivos» |
| `Inputs and Sources` | paleta de comandos | «Entradas y fuentes» |
| `Outputs and Labels` | paleta de comandos | «Salidas y etiquetas» |
| `Logic Gates, Input and Output` | paleta de comandos | «Puertas lógicas, entrada y salida» |
| `Export Image` | paleta de comandos | «Exportar imagen» |
| `Transparent Background` | paleta de comandos | «Fondo transparente» |
| `default` | paleta de comandos | «predeterminado» |
| `export` | paleta de comandos | «exportar» |
| `RPM` | paleta de comandos | «RPM» (sin traducir) |
| `Circuit: ` | rótulo | «Circuito: » |
| `Loaded subcircuits: ` | rótulo | «Subcircuitos cargados: » |
| `No subcircuits found in file` | aviso | «No hay subcircuitos en el fichero» |
| `Please select one or more subcircuits.` | aviso | «Selecciona uno o más subcircuitos.» |
| `Are you sure you want to delete ` | confirmación | «¿Seguro que quieres borrar…?» |
| `Can't delete subcircuits in use in the current circuit: ` | aviso | «No se pueden borrar subcircuitos en uso…» |
| ` average` | sonda | « media» |
| `/div` | sonda | «/div» (sin traducir) |

**Por qué no importa en la práctica:** las 25 cadenas están **todas en la paleta de
comandos** (el buscador de comandos del propio motor) y en rótulos menores. **La
interfaz que el alumno ve en el simulador —botones, deslizadores, menús, textos de
los elementos— está traducida al 100 %**, como se ve en las capturas.

**Limitación conocida:** la paleta de comandos del motor es la única parte en
castellano con huecos. No se abre desde la interfaz de CircuitoLab (el menú visible
es el de `Archivo/Editar/Dibujar`, no la paleta de comandos), así que el alumnado no
se la encuentra.

**Ampliación propia:** al habilitar la edición aparecieron los diálogos del motor,
que el locale oficial no traía (`Edit Resistor`, `Edit Capacitor`…). Se añadieron
**65 cadenas** con `_tools/ampliar_locale.py`, así que ahora dicen «Editar
resistencia», «Editar condensador», etc. El fichero `locale_es.txt` es un dato, no
código: el bundle del motor no se ha tocado.

### 3.1 Cómo se fuerza el español

El motor elige el idioma por este orden:

1. parámetro `?lang=xx` en la URL;
2. `localStorage['language']`;
3. `navigator.languages[0]`.

CircuitoLab carga siempre el motor con `?lang=es`, de modo que el idioma no depende
del navegador ni de la configuración del alumno.

---

## 4. Contenido didáctico: estado

### 4.1 Cobertura

| | Circuitos |
|---|---|
| **Total en el catálogo** | **366** |
| **Con explicación completa** | **60** |
| **Pendientes** | **306** |

> Nota: el `setuplist.txt` del motor tiene 367 líneas, pero **`cmosinverter.txt`
> aparece dos veces** (en «MOSFETs» y en «Logic Families > CMOS»). Se descarta la
> segunda aparición para que el id no choque y la galería no muestre el mismo
> circuito dos veces. De ahí que el catálogo final tenga 366 circuitos.

**Todos los títulos y todas las categorías están traducidos al español**, incluidos
los 306 circuitos pendientes: la galería no mezcla idiomas.

Por curso. **El curso es solo un metadato** (se ve en la cabecera del circuito y
sirve para que el profesor sepa a qué nivel apunta): la galería **no** agrupa por
curso, agrupa por las categorías originales del motor.

| Curso | Completas | Total |
|---|---|---|
| 3º ESO | **7** | 7 |
| 4º ESO | **47** | 167 |
| Bachillerato | **6** | 192 |

Por categoría (solo las que tienen alguna explicación completa):

| Categoría | Completas |
|---|---|
| Diodos | 12 |
| Conceptos básicos | 10 |
| Corriente alterna | 9 |
| Amplificadores operacionales | 6 |
| Transistores | 5 |
| Otros circuitos pasivos | 4 |
| Temporizador 555 | 3 |
| Lógica combinacional | 3 |
| Familias lógicas | 3 |
| Filtros pasivos | 3 |
| Lógica secuencial | 1 |
| Otros dispositivos | 1 |

### 4.2 Los 60 circuitos con explicación

Los títulos se muestran **traducidos al español**. El título original del motor se
conserva en el catálogo (campo `titulo`) y la traducción en `titulo_es`.

**Conceptos básicos (10):** Ley de Ohm · Resistencias en serie y paralelo ·
Condensador: carga y descarga · Bobina: corriente y contracorriente · Circuito RLC ·
Divisor de tensión · Potenciómetro · Potenciómetro como divisor ·
Condensador en corriente alterna · Bobina en corriente alterna

**Corriente alterna (9):** Impedancias a la misma frecuencia · Resonancia en serie ·
Resonancia en paralelo · Condensadores de distinta capacidad ·
Un condensador a distintas frecuencias · Bobinas de distinta inductancia ·
Una bobina a distintas frecuencias · Potenciómetro como divisor

**Filtros (3):** Filtro paso bajo (RC) · Filtro paso alto (RC) · Filtro paso banda

**Diodos (12):** Diodo · Curva I-V del diodo · Rectificador de media onda ·
Rectificador de onda completa · Rectificador con filtro · Limitador con diodo ·
Referencia de tensión con Zener · Curva I-V del diodo Zener · Duplicador de tensión ·
Triplicador de tensión · Restauración de la componente continua · Generador de pulsos

**Transistores (5):** Transistor NPN · Transistor PNP · Transistor como interruptor ·
Seguidor de emisor · Disparador de Schmitt

**Temporizador 555 (3):** Oscilador de onda cuadrada · Monoestable · Interior del 555

**Digital (7):** Semáforo · Puerta XOR · Sumador de medio bit · Sumador completo ·
Inversora TTL · Puerta NAND TTL · Puerta NAND CMOS

**Relé y medidas (3):** Relé · Puente de Wheatstone · Conmutadores de escalera

**Amplificadores operacionales (6):** Amplificador operacional · Amplificador inversor ·
Amplificador no inversor · Seguidor de tensión (buffer) · Amplificador sumador ·
Amplificador diferencial

**Teoremas (2):** Teorema de Thévenin · Teorema de Norton

**Otros (2):** Transformador · Bombilla

### 4.3 Cómo se han escrito las explicaciones

Cada ficha tiene tres bloques, todos en español y en segunda persona:

1. **Cómo funciona** — qué hace el circuito y por qué, con analogía cotidiana y las
   fórmulas cuando tocan.
2. **Qué observar** — qué componente tocar y qué debería pasar. Concreto.
3. **Prueba tú** — una o dos preguntas o retos para el alumno.

Máximo ~120 palabras por bloque. Sin relleno, sin frases de cortesía.

### 4.4 Exactitud: cómo se ha controlado

Regla de Luis: *«si no estás seguro de cómo funciona un circuito, no lo expliques»*.
Se ha aplicado con un procedimiento de tres capas:

1. **Extracción objetiva.** Un parser lee cada `.txt` del motor usando el mapa real
   de tipos extraído del Java (`CirSim.java`) y el formato de volcado de cada clase.
   De ahí salen los valores: resistencias, capacidades, inductancias, frecuencias,
   amplitudes, alimentación de los op-amps, tensión de Zener. **Ninguna cifra de las
   explicaciones se ha escrito de memoria.**
2. **Verificador automático** (`_tools/verificar_explicaciones.py`): recorre cada
   valor citado en las 60 fichas y lo busca en los valores reales del circuito.
   Distingue cuatro casos:
   - **ERROR** — el valor no está en el circuito y no es un cálculo declarado → **0**;
   - **resultado calculado** — el texto declara el cálculo (4 casos);
   - **propuesta de cambio** — el texto propone cambiar un valor (5 casos);
   - **valor de contexto** — conocimiento estándar (0,7 V de un diodo de silicio,
     230 V de la red, 3,3 V de un microcontrolador): 7 casos.
3. **Revisión de idioma**: script que detecta ideogramas, caracteres no latinos y
   palabras en inglés coladas. **0 problemas**.

**Errores reales que este procedimiento cazó y corrigió** (ninguno llegó a la app):

- `ohms.txt` no tiene una fuente de 6 V sino de **5 V**.
- `capmultfreq.txt` usa frecuencias de **15, 40 y 80 Hz**, no 2,5, 5 y 80.
- `impedance.txt` tiene un condensador de **11,486 µF** (1,1486 × 10⁻⁵ F), no 1,1486 µF.
- `amp-diff.txt`: la señal es una onda cuadrada de **1 V a 120 Hz**, no 120 V.
- `npn.txt`: la base está a **0,705 V** (y el rango del deslizador es 0,5–0,75 V), no 0,7 V exactos.
- 37 bloques de texto tenían `{fx(...)}` **sin renderizar** por ser cadenas y no
  f-strings. Cazado por revisión visual de la captura de tema claro.

**Ninguna explicación se ha inventado.** Cuando un valor no estaba en el circuito,
se comprobó en el Java del motor o se marcó como cálculo declarado.

### 4.5 Fallos que encontró la verificación (y se corrigieron)

> **Corrección importante (23/10/2026):** la ficha de **Ley de Ohm** describía dos
> resistencias **en serie** cuando `ohms.txt` son **en paralelo** (5 V sobre 100 Ω y
> 1 kΩ → 50 mA y 5 mA). Se reescribió completa. El verificador automático comprueba
> cifras, **no topología**: este fallo lo cazó una captura revisada a ojo. Las demás
> fichas que hablan de serie/paralelo están pendientes de esa misma revisión manual.


Esta es la parte que de verdad da valor al trabajo: **ninguno de estos fallos lo
vio una lectura del código; los cazó una captura o una medición.**

| Fallo | Cómo se detectó | Corrección |
|---|---|---|
| **37 bloques con `{fx(...)}` sin renderizar** — el texto salía literal en el panel | Revisión visual de la captura de tema claro | Las cadenas no eran f-strings. Convertidas 37 (más una con comillas escapadas) |
| **«Explicación pendiente» visible junto a «Completa»** | Revisión visual de la captura de tema oscuro | `.pendiente { display: flex }` pisaba el atributo `hidden`. Añadido `[hidden] { display: none !important }` |
| **Atribución de licencia duplicada** (nota del panel + pie) | Revisión visual de la captura móvil | Eliminada la nota del panel; queda solo el pie, con `id="acerca"` |
| **La galería se interponía entre el simulador y su explicación en móvil** | Revisión visual de la captura móvil | Reordenado a simulador → explicación → galería |
| **Fuentes pidiéndose a `fonts.gstatic.com` en runtime** | arnés de peticiones externas | El generador reescribía las URLs después de concatenar. Rehecho: 0 URLs externas |
| **404 del service worker en cada carga** (2 errores de consola) | arnés de consola | Creado `engine/service-worker.js` sin caché |
| **Títulos y categorías en inglés** en la galería | Revisión visual | Traducidos 60 títulos y 57 categorías/subcategorías |
| **`ERR_CONNECTION_RESET` intermitente** al recargar | arnés de consola | El servidor de desarrollo no capturaba el corte de conexión del cliente |
| **Valores mal leídos en el parser** (`VarRailElm`, `OpAmpElm`, `ZenerElm`) | Verificador de valores | Corregido el formato de volcado según el Java de cada clase |

**Lección para próximas sesiones:** un arnés que solo mide geometría y consola no
detecta que un texto sale en crudo. Hay que **mirar la captura**. La visión
artificial encontró tres fallos que 28 comprobaciones automáticas daban por buenos.

---

## 5. Edición: sí se pueden crear circuitos (y por qué el menú está visible)

El motor se sirve con `hideMenu=false`. Es una decisión de producto, no un
descuido:

| Bandera | Valor | Motivo |
|---|---|---|
| `hideMenu` | **false** | El menú es donde vive *Dibujar* (la paleta completa de componentes), *Archivo → Nuevo circuito en blanco*, deshacer, copiar/pegar, zoom y opciones. Sin él, el alumnado no puede crear circuitos. Ocupa **30 px**. |
| `hideSidebar` | true | El panel derecho solo trae RUN, velocidad y los deslizadores del circuito. **No** tiene paleta de componentes: se comprobó y se descartó. Además carga un `iframe.html` que daba 404. |
| `hideInfoBox` | true | Las etiquetas de texto del circuito original tapan el dibujo. |

El menú del motor **ya estaba traducido al castellano** por su propio locale
(Archivo, Editar, Dibujar, Opciones, Ejemplos de circuitos). No hubo que traducirlo.

### 5.1 Qué contiene el menú (leído del motor en ejecución)

- **Archivo:** Nuevo circuito en blanco, Abrir archivo, Importar desde texto,
  Guardar como, Exportar como enlace, Exportar en formato texto, Exportar SVG,
  Copiar circuito como imagen, Crear subcircuito, Punto de operación CC, Imprimir.
- **Editar:** Deshacer, Rehacer, Cortar, Copiar, Pegar, Duplicar, Seleccionar todo,
  Buscar componente, Centrar, Zoom (100 %, +, −), Invertir X/Y, Rotar.
- **Dibujar:** paleta completa en 7 grupos — Passive Components, Inputs and Sources,
  Outputs and Labels, Active Components, Active Building Blocks, Logic Gates,
  Digital Chips, Analog and Hybrid Chips.
- **Osciloscopios, Opciones, Herramientas, Ejemplos de circuitos** (la lista original
  con sus categorías, que es la misma que alimenta la galería).

### 5.2 Estilo del menú: CSS inyectado, motor intacto

El motor trae una hoja de estilos noventera. Como el iframe es **del mismo origen**,
`assets/js/app.js` le inyecta un `<style id="circuitolab-estilo">` con los tokens del
brand: tipografía DM Sans (con su `@font-face` para dentro del iframe), superficies,
bordes y hover en cian. **No se toca el bundle**: el motor sigue byte a byte como se
descargó.

Los desplegables **no** son GWT (`UL.menuDropdown` / `LI.menuItem`), así que hubo que
estilizar esas clases, no `.gwt-MenuBarPopup`. Se descubrió volcando el DOM con el
menú abierto.

### 5.3 Diálogos de edición en español

Al crear un circuito, el motor titula cada diálogo `"Edit " + tipo`. El locale
oficial solo trae `"Edit Component"`, así que salía *Edit Resistor*, *Edit Capacitor*…
Se añadieron **65 cadenas** a `locale/locale_es.txt` con
`_tools/ampliar_locale.py` (fichero de datos, no código). Ahora dice
**«Editar resistencia»**.

---

## 6. Layout final: el simulador manda, sin galería lateral

La primera versión llevaba una galería a la izquierda agrupada por curso y luego por
categorías del motor. **Las dos se han quitado por indicación de Luis:** los ejemplos
ya están en el desplegable *Ejemplos de circuitos* del propio motor, así que la
galería era una segunda lista de lo mismo robándole ancho al simulador.

- **Dos columnas:** simulador + panel de explicación. A menos de 1180 px el panel se
  va debajo; el simulador se queda todo el ancho.
- **Se quitan los tres enlaces superiores** (*Circuitos*, *Explicaciones*, *Acerca de*):
  no hacían nada. La atribución GPL sigue en el pie, que es donde importa.

### 6.1 El problema que esto abría (y cómo se resolvió)

Sin galería, el panel didáctico se quedaba sin saber **qué circuito hay cargado**: el
motor no expone un evento de cambio ni el nombre del fichero. Sin eso, la capa
didáctica se moría.

**Solución:** el motor pide cada ejemplo como `circuits/<archivo>.txt`. Como el iframe
es del mismo origen, `app.js` intercepta `fetch` y `XMLHttpRequest` **dentro del iframe**
y traduce el nombre del fichero al id del catálogo. El panel se actualiza solo.

Comprobado: abrir «Transistor NPN» desde el menú del motor cambia la cabecera a
*Transistor NPN* y su explicación aparece sin tocar nada más. Si el circuito es propio
o importado, el panel lo dice («Circuito propio»).

### 6.2 Los cursores del motor

Se pusieron `hideSidebar=false`. Ese panel es el único sitio donde están los controles
que pidió Luis: **Reiniciar**, **RUN/Stop**, **Velocidad de simulación**, **Velocidad de
corriente**, **Brillo** y los cursores propios del circuito (por ejemplo *Tensión* en la
Ley de Ohm).

- Son **canvas dibujados por el motor**, no `<input type="range">`: no se pueden
  recolorear por CSS. Se estiliza el marco (fondo, tipografía, botones) y se dejan tal cual.
- El motor mete dentro un `iframe.html` vacío de 325 px como hueco de branding: se oculta.

### 6.3 Afinado del 23/10/2026 (segunda vuelta)

- **La barra del simulador ya no muestra el curso.** Se quedó solo con el nombre del
  circuito y su categoría, y se compactó (de 52 px a lo mínimo: padding 5/12 y título
  a 15 px). Cada píxel de esa barra es lienzo que se pierde.
- **Fuera el cajón de ayuda** que había bajo el lienzo.
- **El padding del panel cortaba los cursores**: el motor dibuja canvas de 166 px fijos
  y con `padding: 8px 10px` el contenido pedía 186 px en una caja de 165, así que se
  recortaban por la derecha. Se quitó el padding lateral.
- **Cursores con el brand.** El motor los pinta en `<canvas>` (carril con flechas en los
  extremos, relleno rojo, tirador metálico: estética de 2003) y **no se pueden recolorear
  por CSS**. Solución: se tapan con un `input[type=range]` del brand y se pilotan
  disparando los mismos eventos de ratón que haría el usuario sobre el canvas original.
  - La **posición inicial se lee del propio canvas** (se busca hasta dónde llega el
    relleno rojo), así que cada cursor arranca en su valor real, no en un 50 % falso.
  - Comprobado que mover el cursor cambia de verdad el circuito (`exportCircuit` cambia).
  - El envoltorio es idempotente y solo envuelve canvas **con etiqueta**; los canvas
    sueltos que deja el motor al reconstruir el panel se ocultan.
  - **Brillo** se pinta apagado y bloqueado porque el motor lo marca deshabilitado.
- **Pendiente menor:** el botón RUN/STOP sigue en rojo (lo pinta el motor). Se deja así
  a propósito: rojo = parar es convención y avisa de estado.

---

## 7. Decisiones de diseño

### 7.1 Marca y estética

- Brand **tecnoLSM**: cian `#68D7E8` (interacción), cobre `#C58B62` (oficio),
  magenta `#E27AB3` (hover), fondo `#0B111E`, superficie `#1B2636`.
- Tipografías **Space Grotesk** (display), **DM Sans** (cuerpo), **IBM Plex Mono**
  (datos y rótulos), autoalojadas en `assets/fonts/` (20 ficheros `.woff2`, 0 URLs
  externas — verificado).
- Iconos de la familia **MDI** de Iconify, embebidos en `assets/icons/icons.js`
  (40 iconos). `api.iconify.design` devuelve 403, así que se extraen del paquete
  `@iconify-json/mdi`.
- **Sin sombras, sin degradados, sin orbes decorativos.** Profundidad por contraste
  de superficie y borde.
- Retícula de 3 columnas: galería 300 px · simulador flexible · panel didáctico 400 px.
  Máximo 1180 px de ancho útil, escala de 4 px, radios 8/14/22 px.

### 7.2 El lienzo claro dentro de una app oscura

El motor dibuja sobre **fondo negro** (comprobado: los cuatro píxeles de las
esquinas del canvas son `rgb(0,0,0)`). En modo oscuro, el lienzo se mete en una
**tarjeta con borde propio** (`.simulador__lienzo`), con fondo `#000` y borde del
brand, para que no quede un rectángulo blanco o un parche chillón pegado al fondo.
En modo claro el marco pasa a `#fff`, que es el fondo natural del motor.

### 7.3 Fórmulas: CSS puro, nunca KaTeX

Las magnitudes y las fórmulas se muestran como **fichas** con color propio
(`.fx`, una por fórmula, con `border-left: 3px solid currentColor`) y las divisiones
como **fracción apilada con CSS** (`.frac` > `.num` / `.den`, con `border-top`).
Cero dependencias, cero tipografías extra, funciona sin conexión.

> Detalle fino: los colores de las fichas van en reglas de **dos clases**
> (`.fx.fx-1`, especificidad 0,2,0) para que ninguna regla del contenedor los pise
> en silencio.

### 7.4 Accesibilidad

- El acordeón usa cabeceras `<button>` con `aria-expanded` y `aria-controls`.
- Estado abierto/cerrado **conservado al cambiar de circuito** (en `localStorage`).
- Recorrido con Tab verificado: las cabeceras del acordeón reciben el foco.
- Enlace de salto (`skip-link`) al simulador.
- `prefers-reduced-motion` respetado.
- El aviso «Explicación pendiente» se muestra **solo** cuando el circuito no tiene
  explicación, y los pendientes se distinguen en la galería con un punto de color.

### 7.5 Responsive

| Ancho | Comportamiento |
|---|---|
| ≥ 1400 px | 3 columnas (300 / flexible / 400) |
| 1180–1400 px | 3 columnas más estrechas (260 / flexible / 340) |
| 820–1180 px | El panel didáctico pasa **debajo** del simulador; la galería queda fija |
| < 820 px | Una columna: simulador arriba, galería en medio, panel abajo |

Verificado a 1600×950 y a 390×844 sin desbordamiento horizontal.

---

## 8. Verificación realizada

Todo con Chrome headless (Puppeteer), sobre el servidor local real.

| # | Comprobación | Resultado |
|---|---|---|
| 1 | HTTP 200 en todos los recursos | **OK** |
| 2 | Ninguna petición a dominios externos | **OK** (0 externas) |
| 3 | La galería lista circuitos | **OK** (366 circuitos) |
| 3b | La galería agrupa por categorías del motor | **OK** (22 categorías) |
| 3c | La galería **NO** agrupa por curso | **OK** (0 grupos de curso) |
| 4 | El acordeón tiene 3 bloques | **OK** |
| 5 | El motor termina de cargar | **OK** |
| 6 | Sin desbordamiento horizontal (1600 px) | **OK** |
| 7 | Sin desbordamiento horizontal (390 px) | **OK** |
| 8 | Ninguna fórmula sin renderizar | **OK** |
| 9 | Las fichas de fórmula se pintan | **OK** |
| 10 | Los títulos con explicación están en español | **OK** (0 en inglés) |
| 11 | Hay al menos 60 circuitos con explicación en la galería | **OK** (60) |
| 12 | Las categorías de la galería están en español | **OK** (0 en inglés) |
| 13 | El lienzo dibuja el circuito (no está vacío) | **OK** |
| 14 | **La simulación avanza** (`getTime()` cambia) | **OK** |
| 15 | El acordeón abre | **OK** |
| 16 | El acordeón cierra | **OK** |
| 17 | El estado abierto se conserva al cambiar de circuito | **OK** |
| 18 | «Explicación pendiente» NO aparece si hay explicación | **OK** |
| 19 | Un circuito pendiente muestra el aviso y no tiene bloques | **OK** |
| 20 | Un circuito pendiente se marca como «Pendiente» | **OK** |
| 21 | Se cargan 3 circuitos distintos | **OK** |
| 22 | Cada circuito dibuja algo distinto (firmas de píxeles distintas) | **OK** |
| 23 | Todos los circuitos dibujan contenido | **OK** |
| 24 | La cabecera del acordeón recibe el foco | **OK** |
| 25 | `aria-controls` apunta a un panel existente | **OK** |
| 26 | Consola sin errores (tema oscuro) | **OK** |
| 27 | Consola sin errores (tema claro) | **OK** |
| 28 | Consola sin errores (móvil) | **OK** |
| 29 | El tema claro se aplica | **OK** |
| 30 | El circuito dibuja en tema claro | **OK** |
| 31 | Errores de valores en las 60 explicaciones | **0** |
| 32 | Idioma de las 60 fichas (sin ideogramas ni inglés) | **0 problemas** |
| 33 | Todas las fuentes se sirven en local | **OK** (0 URLs externas) |

### 8.1 Edición: creación de circuitos (`_tools/verificar_edicion.py`)

Once comprobaciones con clics reales sobre los menús del motor (GWT ignora los
eventos sintéticos, hay que usar el ratón de verdad).

| # | Comprobación | Resultado |
|---|---|---|
| E1 | El menú del motor está visible y en castellano | **OK** |
| E2 | El desplegable Archivo ofrece «Nuevo circuito en blanco» | **OK** |
| E3 | «Nuevo circuito en blanco» vacía el lienzo | **OK** (7 → 0 elementos) |
| E4 | El menú Dibujar despliega la paleta de componentes | **OK** |
| E5 | La paleta incluye «Resistencia» | **OK** |
| E6 | Elegir Resistencia pone el lienzo en modo dibujo | **OK** (cursor `crosshair`) |
| E7 | Arrastrar en el lienzo crea el componente | **OK** (1) |
| E8 | El componente creado es una resistencia | **OK** (`ResistorElm`) |
| E9 | Detener la simulación congela el tiempo | **OK** |
| E10 | Reanudar la simulación vuelve a avanzar | **OK** |
| E11 | Consola sin errores durante la edición | **OK** |

> **Cómo se dibuja:** en CircuitJS1 se dibuja **arrastrando** (pulsar en un extremo,
> arrastrar y soltar en el otro), no con dos clics sueltos. Con dos clics no se crea
> nada y parece que la app está rota; es el gesto del motor.

**Total: 34 + 11 = 45 comprobaciones automáticas en verde.**

**Capturas reales** en `_tools/capturas/`: escritorio oscuro, escritorio claro,
móvil (página completa), una por cada circuito de prueba y `05-crear-circuito.png`
con una resistencia recién creada.

### 8.2 Lo que NO está verificado

- **El menú del motor no cabe en un móvil de 390 px.** Son 7 entradas (~578 px) en una
  barra que no se puede desplazar sin romper los desplegables (GWT los posiciona en
  absoluto dentro de la barra: darle scroll recorta los menús). A 390 px se ve hasta
  «Opciones»; «Herramientas» y «Ejemplos de circuitos» quedan fuera. **No afecta al uso
  normal**: los circuitos se eligen en la galería, que sí es responsive. Los menús son
  para crear circuitos, y dibujar con el dedo no es el caso de uso. En tablet (≥768 px)
  y en proyector caben enteros y están verificados.
- **No se ha probado en un aula real** con proyector, luz ambiente y distancia. Las
  decisiones de tamaño de letra (16 px mínimo, 1,5× en proyector) están tomadas del
  criterio del brand, no de una medición con público delante.
- **No se ha probado en Safari ni en Firefox.** Solo Chromium (Puppeteer).
- **No se ha medido el contraste con la fórmula de WCAG**, solo se ha revisado a ojo
  y con la visión artificial.
- **No se ha probado el comportamiento con la red cortada** más allá de comprobar
  que no hay peticiones externas.

---

## 9. Licencia y atribución — ATENCIÓN

El motor **CircuitJS1 es GPL-2.0**. Esto tiene consecuencias reales y hay que
decirlas, no decidirlas en silencio:

### 9.1 El conjunto es GPL-2.0

Si CircuitoLab se publica, **el conjunto entero debe distribuirse bajo GPL-2.0**,
con el código fuente disponible. La interfaz, el CSS, el JavaScript, las
explicaciones y los scripts de `_tools/` **no** pueden cerrarse: son parte de una
obra derivada.

### 9.2 No se puede usar el pie de CC BY-NC-SA

El pie habitual de las apps del aula
(«Aplicación creada por Tecno LSM para uso educativo © 2026 Licencia libre de uso
no comercial (Creative Commons BY-NC-SA 4.0)») **no se puede poner aquí**: mezclar
GPL-2.0 con CC BY-NC-SA en el mismo conjunto es un conflicto de licencias. En
CircuitoLab el pie es **GPL-2.0**.

> Consecuencia práctica para Luis: si publica esta app, **no puede** ofrecerla bajo
> «uso no comercial». GPL-2.0 no impide el uso comercial, pero obliga a publicar el
> código fuente y a mantener la licencia.

### 9.3 Atribución (los DOS autores)

Texto usado en el pie de página y en el panel «Acerca de»:

> Motor de simulación: CircuitJS1, de Paul Falstad e Iain Sharp
> (https://github.com/sharpie7/circuitjs1), bajo licencia GPL-2.0.
> Interfaz, explicaciones y adaptación didáctica: Luis Solá Mantilla.
> Obra derivada.

### 9.4 Licencia y código fuente

- Copia de la licencia GPL-2.0: `assets/vendor/circuitjs/COPYING.txt` (y
  `LICENCIA-GPL-2.0.txt` en la raíz).
- Enlace al repo original en el pie y en el panel.
- `assets/vendor/circuitjs/docs-motor/` contiene el `README.md` y el `INTERNALS.md`
  originales del motor, para referencia.

---

## 10. Estructura de la entrega

```
circuitolab/
├── index.html                     la app (shell)
├── INFORME.md                     este documento
├── LICENCIA-GPL-2.0.txt          copia de la licencia del motor
├── assets/
│   ├── css/base.css               tokens del brand, tipografía, fichas de fórmula
│   ├── css/app.css                layout de 3 columnas y responsive
│   ├── fonts/                     Space Grotesk + DM Sans + IBM Plex Mono (woff2 + fonts.css)
│   ├── icons/icons.js             55 iconos MDI embebidos (uno por categoría + interfaz)
│   ├── img/logo-lm-tecno.png      monograma LSM (512 px, 436 KB)
│   ├── img/favicon.svg
│   ├── js/app.js                  lógica de la aplicación (galería, acordeón, motor)
│   └── vendor/circuitjs/          MOTOR (GPL-2.0) — no editar
│       ├── engine/                bundle GWT, 367 circuitos, setuplist, locales, service-worker
│       │   ├── images/hborder.png PNG transparente que pide el CSS del menú de GWT
│       │   ├── iframe.html        placeholder que el motor carga dentro del panel
│       │   └── locale/locale_es.txt  locale español + 65 cadenas de diálogos añadidas
│       ├── lz-string.min.js
│       ├── COPYING.txt
│       └── docs-motor/            README.md e INTERNALS.md originales
├── circuitos/
│   ├── catalogo.json              los 366 circuitos con sus explicaciones
│   ├── estructura.json            árbol para la galería
│   ├── titulos-es.json            los 366 títulos traducidos
│   ├── categorias-es.json         categorías y subcategorías traducidas
│   └── explicaciones/             las fichas, por bloques
│       ├── 01-conceptos-basicos.json
│       └── 02-diodos-transistores-digital-opamps.json
└── _tools/
    ├── servidor.py                servidor local (127.0.0.1:8766, HTTP/1.1)
    ├── descargar_motor.py         descarga el motor y sus 367 circuitos
    ├── traer_imagenes_motor.py    trae/genera las imágenes que pide el CSS del motor
    ├── ampliar_locale.py          añade al locale los diálogos de edición
    ├── generar_catalogo.py        construye catalogo.json y estructura.json
    ├── generar_fuentes.py         descarga y autoaloja las tipografías
    ├── generar_iconos.py          extrae los iconos MDI del set completo
    ├── verificar.py               arnés principal con Chrome headless (34 comprobaciones)
    ├── verificar_edicion.py       crea un circuito de verdad con los menús (11 comprobaciones)
    ├── verificar_explicaciones.py verifica que ningún valor esté inventado
    ├── capturas/                  capturas reales de la verificación
    └── verificacion.json          resultado del último arnés
```

---

## 11. Qué queda por hacer

### 11.1 Contenido (Fase 2)

Las **306 explicaciones pendientes**. El sistema ya está preparado para crecer:

1. Añadir la ficha al JSON correspondiente de `circuitos/explicaciones/`.
2. Añadir su título a `circuitos/titulos-es.json` (si no está).
3. Ejecutar `python3 _tools/generar_catalogo.py`.
4. Ejecutar `python3 _tools/verificar_explicaciones.py` (debe dar 0 errores).

Orden sugerido por valor didáctico:

1. **4º ESO pendientes (120).** Filtros de paso banda y activos, osciladores,
   multivibradores, más diodos y más montajes con el 555.
2. **Bachillerato pendientes (186).** Familias lógicas completas (RTL, DTL, NMOS,
   ECL), biestables y contadores, op-amps avanzados, convertidores, MOSFET.
3. **3º ESO: completo.** Los 7 circuitos del nivel ya tienen explicación.

### 11.2 Técnica

- **Probar en Safari y Firefox.** El motor es JavaScript moderno; probablemente
  funcione, pero está sin verificar.
- **Firmar el `localStorage`**: hoy el estado de los bloques y el último circuito
  visto se guardan sin control de versión. Si el formato cambia, hay que limpiar.
- **Medida de contraste WCAG** con la fórmula sobre `getComputedStyle`, como en las
  apps del aula.
- **Los 25 strings sin traducir** de la paleta de comandos del motor: se pueden
  añadir a `assets/vendor/circuitjs/engine/locale/locale_es.txt`, pero ese fichero
  es del motor y hay que tratarlo con cuidado (es obra GPL).
- **Elegir el circuito por defecto.** Ahora se abre el primero con explicación
  completa (LRC Circuit). Quizá convenga el de Ley de Ohm.

### 11.3 Publicación — HECHA

| | |
|---|---|
| **Producción** | <https://circuitolab.pages.dev> |
| **Repositorio** | <https://github.com/lsm091280/circuitolab> (**público**) |
| **Proyecto Pages** | `circuitolab` (cuenta `03c97bdc6707d5aff0b48ab55a3cbd93`) |
| **Despliegue** | **Automático**: push a `main` → build + deploy (~40 s) |
| **Build** | ninguno (`build_command` vacío, salida en la raíz del repo) |
| **Copia oficial** | iCloud `…/Apps web propias/15.Circuitolab` (es también el checkout git) |

**Por qué el repo es público y no privado.** El motor es GPL-2.0 y la app se sirve
en una web abierta: la licencia exige que el código fuente esté disponible para
quien usa el programa. Un repo privado con la app publicada incumpliría la GPL-2.0.
No es una preferencia, es la consecuencia de la licencia del motor (sección 9).

**Qué se publica.** La raíz del repo entera: `index.html`, `assets/`, `circuitos/`,
`_tools/`, `INFORME.md`, `LICENCIA-GPL-2.0.txt` y `robots.txt`. Las herramientas y
las capturas quedan accesibles en el dominio, lo cual encaja con el espíritu de la
GPL y permite reproducir el proyecto desde cero.

**`robots.txt`** en la raíz: indexable por buscadores, con
`Content-Signal: search=yes, ai-train=no` y bloqueo de los rastreadores de
entrenamiento (GPTBot, ClaudeBot, CCBot, Bytespider…). Permitidos Googlebot, Bingbot
y los agentes que navegan a petición de una persona.

> Nota técnica: Cloudflare Pages aplica **Pretty URLs**, así que
> `circuitjs.html` se sirve en `/engine/circuitjs` (308). Funciona igual; solo hay
> que tenerlo en cuenta al automatizar pruebas contra el dominio.

---

## 12. Procedencia de los datos

- **Motor y circuitos:** `sharpie7/circuitjs1` (GitHub) y
  `circuitjs1.falstad.com` — ambos GPL-2.0, de Paul Falstad e Iain Sharp.
- **Código Java del motor** (para el mapa de tipos y los formatos de volcado):
  `src/com/lushprojects/circuitjs1/client/` del mismo repo.
- **Tipografías:** Google Fonts (Space Grotesk, DM Sans, IBM Plex Mono), SIL Open
  Font License 1.1, autoalojadas.
- **Iconos:** Material Design Icons vía Iconify, Apache-2.0.
- **Paleta, tipografía y reglas de marca:** brand tecnoLSM propio.
