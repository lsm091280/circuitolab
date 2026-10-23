/* Service worker del motor CircuitJS1.
   El motor (bundle GWT) intenta registrar 'service-worker.js' en su propio
   directorio. Si no existe, el navegador registra un error 404 en la consola.
   Este fichero hace que la petición devuelva 200 y no cachea nada: el motor
   sigue siendo la única fuente y la app funciona igual sin conexión.

   IMPORTANTE: no debe cachear nada. Si cacheara, el motor podría quedar
   congelado en una versión antigua y las actualizaciones no llegarían. */
self.addEventListener('install', function (evento) {
  evento.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', function (evento) {
  evento.waitUntil(self.clients.claim());
});

/* Sin estrategia de caché: se responde con la red y, si falla, con error. */
self.addEventListener('fetch', function (evento) {
  evento.respondWith(
    fetch(evento.request).catch(function () {
      return new Response('', { status: 503, statusText: 'Sin conexion' });
    })
  );
});
