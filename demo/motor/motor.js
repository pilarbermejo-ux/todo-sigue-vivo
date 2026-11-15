/* Todo Sigue Vivo · motor de la demo de portfolio.
 *
 * Ejecuta el mismo servidor en Python de la POC (servidor.py) dentro del navegador con Pyodide.
 * - Intercepta fetch("/api/...") y EventSource("/api/stream...") de la web, sin tocar su lógica.
 * - Los datos (SQLite y fotos) se guardan en IndexedDB, solo en el navegador de quien la visita.
 * - Si la página está dentro de la sala de test, usa el motor de la sala: así los dos móviles
 *   comparten los mismos datos y se avisan en tiempo real.
 */
(function () {
  "use strict";
  const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
  const BASE = document.currentScript.src.replace(/[^/]*$/, "");

  function motorDelPadre() {
    try { if (window.parent !== window && window.parent.TSV_MOTOR) return window.parent.TSV_MOTOR; } catch (e) {}
    return null;
  }

  function cargarScript(src) {
    return new Promise((ok, ko) => {
      const s = document.createElement("script");
      s.src = src; s.onload = ok; s.onerror = () => ko(new Error("No se ha podido cargar " + src));
      document.head.appendChild(s);
    });
  }

  function crearMotor() {
    const oyentes = new Set();
    const fotos = new Map();
    let py, manejar, uidDe, desfasado = false, cola = Promise.resolve(), pendientes = [];
    // Varias pestañas abiertas a la vez: se avisan de los cambios y comparten los avisos en tiempo real.
    const canal = "BroadcastChannel" in window ? new BroadcastChannel("tsv-demo") : null;

    function repartir(clave, txt) {
      for (const o of [...oyentes]) {
        if (clave !== "todos" && o.clave !== clave) continue;
        try { o.cb(txt); } catch (e) { oyentes.delete(o); }
      }
    }
    // Los avisos llegan al momento en esta pestaña; a las demás, en cuanto los datos están guardados.
    window.tsvEmit = (clave, txt) => {
      repartir(clave, txt);
      pendientes.push({ t: "emit", clave, txt });
    };
    // Guarda en IndexedDB (en fila, sin solapar) y después avisa a las demás pestañas.
    function guardar() {
      cola = cola.then(() => new Promise(ok => {
        const avisos = pendientes; pendientes = [];
        try {
          py.FS.syncfs(false, () => {
            if (canal) { canal.postMessage({ t: "guardado" }); avisos.forEach(a => canal.postMessage(a)); }
            ok();
          });
        } catch (e) { ok(); }
      }));
      return cola;
    }
    window.tsvPersist = () => { guardar(); };
    if (canal) canal.onmessage = e => {
      const m = e.data || {};
      if (m.t === "guardado") desfasado = true;
      if (m.t === "emit") { desfasado = true; repartir(m.clave, m.txt); }
    };
    async function alDia() {
      await cola;
      if (!desfasado) return;
      desfasado = false;
      await new Promise(ok => py.FS.syncfs(true, () => ok()));
      fotos.clear();
    }

    const texto = u => fetch(u).then(r => { if (!r.ok) throw new Error(u); return r.text(); });
    const bytes = u => fetch(u).then(r => { if (!r.ok) throw new Error(u); return r.arrayBuffer(); }).then(b => new Uint8Array(b));

    const ready = (async () => {
      if (typeof loadPyodide === "undefined") await cargarScript(PYODIDE + "pyodide.js");
      const [srv, nav, gata, riego] = await Promise.all([
        texto(BASE + "servidor.py"), texto(BASE + "navegador.py"),
        bytes(BASE + "../img/visita-gata.jpg"), bytes(BASE + "../img/visita-riego.jpg")]);
      py = await loadPyodide({ indexURL: PYODIDE });
      await py.loadPackage("sqlite3");
      const FS = py.FS;
      FS.mkdir("/datos");
      FS.mount(FS.filesystems.IDBFS, {}, "/datos");
      await new Promise(ok => FS.syncfs(true, () => ok()));
      ["/app", "/public", "/public/img"].forEach(d => { try { FS.mkdir(d); } catch (e) {} });
      FS.writeFile("/app/servidor.py", srv);
      FS.writeFile("/app/navegador.py", nav);
      FS.writeFile("/public/img/visita-gata.jpg", gata);
      FS.writeFile("/public/img/visita-riego.jpg", riego);
      py.runPython("import sys\nsys.path.insert(0, '/app')\nfrom navegador import manejar, uid_de, iniciar");
      manejar = py.globals.get("manejar");
      uidDe = py.globals.get("uid_de");
      py.globals.get("iniciar")();
      pendientes = [];
      await guardar();
    })();

    return {
      ready,
      async peticion(metodo, url, body, tok) {
        await ready;
        await alDia();
        const path = url.split("?")[0];
        const r = manejar(metodo, path, body || "", tok || "");
        const out = r.toJs();
        r.destroy();
        if (metodo !== "GET") await guardar(); else { const avisos = pendientes; pendientes = []; if (canal) avisos.forEach(a => canal.postMessage(a)); }
        return out;
      },
      async suscribir(tok, cb) {
        await ready;
        await alDia();
        let clave = "mod";
        if (tok !== null) {
          const uid = uidDe(tok);
          if (uid === undefined || uid === null) return () => {};
          clave = String(uid);
        }
        const o = { clave, cb };
        oyentes.add(o);
        return () => oyentes.delete(o);
      },
      foto(archivo) {
        if (fotos.has(archivo)) return fotos.get(archivo);
        let url = "";
        try {
          const data = py.FS.readFile("/datos/fotos/" + archivo);
          url = URL.createObjectURL(new Blob([data], { type: "image/jpeg" }));
        } catch (e) { url = ""; }
        if (url) fotos.set(archivo, url);
        return url;
      },
    };
  }

  const M = motorDelPadre() || (window.TSV_MOTOR = crearMotor());
  window.TSV = M;

  /* ---------- fetch("/api/...") ---------- */
  const fetchReal = window.fetch.bind(window);
  window.fetch = function (input, init) {
    const url = typeof input === "string" ? input : (input && input.url) || "";
    if (!url.startsWith("/api/")) return fetchReal(input, init);
    init = init || {};
    const h = init.headers || {};
    const tok = String(h.Authorization || h.authorization || "").replace("Bearer ", "");
    return M.peticion(String(init.method || "GET").toUpperCase(), url, init.body || "", tok)
      .then(([st, txt, ct]) => new Response(txt, { status: st, headers: { "Content-Type": ct } }));
  };

  /* ---------- EventSource("/api/stream...") ---------- */
  const ESReal = window.EventSource;
  function ESDemo(url) {
    url = String(url);
    if (!url.startsWith("/api/stream")) return new ESReal(url);
    const q = new URLSearchParams(url.split("?")[1] || "");
    let off = null, cerrado = false;
    this.readyState = 1;
    this.onmessage = null;
    this.onerror = null;
    M.suscribir(q.get("mod") === "1" ? null : (q.get("token") || ""), txt => {
      if (!cerrado && this.onmessage) this.onmessage({ data: txt });
    }).then(f => { if (cerrado) f(); else off = f; });
    this.close = () => { cerrado = true; this.readyState = 2; if (off) off(); };
    addEventListener("pagehide", () => this.close());
  }
  window.EventSource = ESDemo;

  /* ---------- fotos guardadas en el navegador ---------- */
  window.fotoURL = archivo => M.foto(archivo);

  /* ---------- descargas CSV de la sala ---------- */
  document.addEventListener("click", async e => {
    const a = e.target.closest && e.target.closest('a[href^="/api/"]');
    if (!a) return;
    e.preventDefault();
    const r = await fetch(a.getAttribute("href"));
    const blob = new Blob([await r.text()], { type: "text/csv;charset=utf-8" });
    const u = URL.createObjectURL(blob);
    const d = document.createElement("a");
    d.href = u; d.download = a.getAttribute("href").split("/").pop().replace(".csv", "-test.csv");
    document.body.appendChild(d); d.click(); d.remove();
    setTimeout(() => URL.revokeObjectURL(u), 2000);
  });

  /* ---------- pantalla de carga ---------- */
  let capa = null;
  const t = setTimeout(() => {
    capa = document.createElement("div");
    capa.className = "tsv-cargando";
    capa.setAttribute("role", "status");
    capa.innerHTML = '<div><span class="tsv-spin" aria-hidden="true"></span><b>Preparando la demo…</b><small>La primera vez tarda unos segundos: todo funciona dentro de tu navegador.</small></div>';
    const st = document.createElement("style");
    st.textContent = '.tsv-cargando{position:fixed;inset:0;z-index:9999;display:grid;place-items:center;background:var(--canvas,#F7F7FB);color:var(--ink,#1B1A24);font:400 15px/1.5 "Instrument Sans",system-ui,sans-serif;text-align:center;padding:24px}.tsv-cargando div{display:grid;gap:8px;justify-items:center;max-width:320px}.tsv-cargando b{font:700 20px/1.2 "Bricolage Grotesque",system-ui,sans-serif;letter-spacing:-.02em}.tsv-cargando small{color:var(--ink-muted,#6B6979);font-size:14px}.tsv-spin{width:36px;height:36px;border-radius:50%;border:3px solid #DADAFF;border-top-color:#5646B0;animation:tsvspin .9s linear infinite;margin-bottom:8px}@keyframes tsvspin{to{transform:rotate(360deg)}}@media (prefers-reduced-motion:reduce){.tsv-spin{animation:none}}';
    document.head.appendChild(st);
    (document.body || document.documentElement).appendChild(capa);
  }, 250);
  M.ready.then(() => { clearTimeout(t); if (capa) capa.remove(); }, err => {
    clearTimeout(t);
    console.error(err);
    if (!capa) { capa = document.createElement("div"); capa.className = "tsv-cargando"; document.body.appendChild(capa); }
    capa.innerHTML = '<div><b>No se ha podido preparar la demo</b><small>Comprueba tu conexión a internet y recarga la página.</small></div>';
  });
})();
