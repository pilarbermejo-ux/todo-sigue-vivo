#!/usr/bin/env python3
"""Todo Sigue Vivo · servidor de la POC para test con usuarios.

Solo usa la biblioteca estándar de Python 3 (sin instalar nada):
- SQLite como base de datos (datos/tsv.db)
- API JSON en /api/...
- Tiempo real con Server-Sent Events (/api/stream)
- Cuidadores «robot» que se presentan y responden en el chat
- Endpoints de moderación para la sala de test (/api/test/...)

Arranque:  python3 servidor.py    →  http://localhost:8080
"""
import base64, csv, hashlib, io, json, math, mimetypes, os, queue, re, secrets, sqlite3, threading, time
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(BASE, "public")
DATOS = os.path.join(BASE, "datos")
FOTOS = os.path.join(DATOS, "fotos")
DB_PATH = os.path.join(DATOS, "tsv.db")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8080"))
CLAVE_PRUEBA = "prueba-2026"   # contraseña de todas las cuentas de prueba (ver LEEME.md)
COMISION = 0.15

# ---------------------------------------------------------------- catálogo (PRD, anexo A)
ESPECIES = [
    # nombre, categoría (an|ex|pl), grupo, dificultad, cada (días), requiere formación, multiplicador, sensibilidad al calor, activa
    ("Gato", "an", "", 1, 1, 0, 1.00, 0.2, 1),
    ("Conejo", "an", "roedor", 2, 1, 0, 1.00, 0.5, 1),
    ("Hámster", "an", "roedor", 1, 1, 0, 0.90, 0.3, 1),
    ("Periquito", "an", "ave", 2, 1, 0, 1.00, 0.3, 1),
    ("Loro", "ex", "ave", 4, 1, 1, 1.40, 0.3, 1),
    ("Peces de acuario", "an", "", 2, 2, 0, 0.90, 0.2, 1),
    ("Tortuga", "ex", "reptil", 3, 2, 1, 1.30, 0.3, 1),
    ("Gecko leopardo", "ex", "reptil", 4, 2, 1, 1.40, 0.3, 1),
    ("Pogona", "ex", "reptil", 4, 1, 1, 1.50, 0.3, 1),
    ("Serpiente", "ex", "reptil", 5, 5, 1, 1.60, 0.3, 1),
    ("Potus", "pl", "interior", 1, 7, 0, 1.00, 0.4, 1),
    ("Sansevieria", "pl", "interior", 1, 14, 0, 1.00, 0.2, 1),
    ("Suculentas y cactus", "pl", "interior", 1, 14, 0, 1.00, 0.1, 1),
    ("Monstera", "pl", "interior", 2, 7, 0, 1.00, 0.5, 1),
    ("Ficus", "pl", "interior", 2, 6, 0, 1.05, 0.5, 1),
    ("Helecho", "pl", "interior", 3, 3, 0, 1.10, 0.9, 1),
    ("Calathea", "pl", "interior", 4, 4, 0, 1.20, 0.8, 1),
    ("Orquídea", "pl", "interior", 4, 7, 0, 1.20, 0.6, 1),
    ("Bonsái", "pl", "interior", 5, 2, 1, 1.40, 0.9, 1),
    ("Geranios de balcón", "pl", "exterior", 2, 2, 0, 1.00, 0.9, 1),
    ("Plantas aromáticas", "pl", "exterior", 2, 3, 0, 1.05, 0.8, 1),
    ("Huerto de terraza", "pl", "exterior", 3, 1, 0, 1.20, 1.0, 1),
    ("Perro", "an", "", 2, 1, 0, 1.00, 0.5, 0),  # no admitido en la v1 (CASA-05)
]
ZONAS = {"28004": "Malasaña-Universidad", "28015": "Malasaña-Universidad", "28010": "Chamberí",
         "28012": "Lavapiés-Embajadores", "28005": "Arganzuela", "28045": "Arganzuela",
         "28009": "Retiro", "28007": "Retiro", "28035": "Fuencarral-El Pardo"}
# POC: todo Madrid cuenta como zona piloto. Nadie va a lista de espera y los cuidadores
# reciben anuncios de cualquier código postal. Poner a False para volver a las zonas reales.
ZONA_UNICA = True

def zona_activa(cp):
    return ZONA_UNICA or cp in ZONAS

BARRIOS_FUERA = {"28033": "Hortaleza", "28039": "Tetuán", "28028": "Guindalera"}
OPCIONALES = {"del": "Insignia «Plantas delicadas»", "esp": "Ya ha cuidado tus especies delicadas",
              "rat": "Valoración de 4,5 o más", "serv": "Al menos 5 servicios completados", "fr": "Franja horaria estricta"}

SCHEMA = """
CREATE TABLE usuarios(id INTEGER PRIMARY KEY, nombre TEXT, apellido TEXT, correo TEXT UNIQUE, hash TEXT, sal TEXT,
  cp TEXT, barrio TEXT, rol TEXT, es_bot INTEGER DEFAULT 0, clave_bot TEXT, creado INTEGER);
CREATE TABLE sesiones(token TEXT PRIMARY KEY, usuario_id INTEGER, creado INTEGER);
CREATE TABLE especies(id INTEGER PRIMARY KEY, nombre TEXT, cat TEXT, grupo TEXT, dif INTEGER, cada INTEGER,
  formacion INTEGER, mult REAL, calor REAL, activa INTEGER);
CREATE TABLE casas(usuario_id INTEGER PRIMARY KEY, direccion TEXT, acceso TEXT, instr_acceso TEXT, veterinario TEXT, emergencia TEXT);
CREATE TABLE seres(id INTEGER PRIMARY KEY, usuario_id INTEGER, especie_id INTEGER, nombre TEXT, cantidad INTEGER,
  instr TEXT, alarma TEXT, medicacion INTEGER DEFAULT 0);
CREATE TABLE perfiles(usuario_id INTEGER PRIMARY KEY, bio TEXT, edad INTEGER, km REAL, acepta_an INTEGER, acepta_pl INTEGER,
  acepta_ex INTEGER, ex_grupos TEXT, medicacion INTEGER, verificado INTEGER, del INTEGER, rating REAL, n_res INTEGER,
  n_serv INTEGER, franjas TEXT, tarifa REAL, activo INTEGER);
CREATE TABLE zonas_cuidador(cuidador_id INTEGER, cp TEXT);
CREATE TABLE especies_cuidador(cuidador_id INTEGER, especie TEXT);
CREATE TABLE disponibilidad(id INTEGER PRIMARY KEY, cuidador_id INTEGER, inicio TEXT, fin TEXT);
CREATE TABLE anuncios(id INTEGER PRIMARY KEY, dueno_id INTEGER, inicio TEXT, fin TEXT, franja TEXT, habitada INTEGER,
  opt TEXT, nota TEXT, cp TEXT, plan TEXT, estado TEXT, elegido_id INTEGER, avisados INTEGER, urgente INTEGER,
  sin_respuesta INTEGER DEFAULT 0, creado INTEGER);
CREATE TABLE anuncio_seres(anuncio_id INTEGER, ser_id INTEGER);
CREATE TABLE avisos(anuncio_id INTEGER, cuidador_id INTEGER, enviado INTEGER, visto INTEGER DEFAULT 0);
CREATE TABLE candidaturas(id INTEGER PRIMARY KEY, anuncio_id INTEGER, cuidador_id INTEGER, mensaje TEXT, estado TEXT, creado INTEGER);
CREATE TABLE mensajes(id INTEGER PRIMARY KEY, candidatura_id INTEGER, autor_id INTEGER, texto TEXT, oculto INTEGER DEFAULT 0,
  sistema INTEGER DEFAULT 0, creado INTEGER, leido INTEGER DEFAULT 0);
CREATE TABLE encuentros(anuncio_id INTEGER PRIMARY KEY, huecos TEXT, elegido INTEGER, si_dueno INTEGER, si_cuidador INTEGER);
CREATE TABLE visitas(id INTEGER PRIMARY KEY, anuncio_id INTEGER, dia INTEGER, llegada INTEGER, salida INTEGER, tareas TEXT,
  nota TEXT, extra INTEGER DEFAULT 0, ejemplo INTEGER DEFAULT 0);
CREATE TABLE fotos(id INTEGER PRIMARY KEY, visita_id INTEGER, archivo TEXT, ejemplo INTEGER DEFAULT 0);
CREATE TABLE extras(id INTEGER PRIMARY KEY, anuncio_id INTEGER, estado TEXT, creado INTEGER);
CREATE TABLE notificaciones(id INTEGER PRIMARY KEY, usuario_id INTEGER, tipo TEXT, texto TEXT, sub TEXT, enlace TEXT,
  actor_id INTEGER, leida INTEGER DEFAULT 0, creada INTEGER);
CREATE TABLE resenas(id INTEGER PRIMARY KEY, anuncio_id INTEGER, autor_id INTEGER, destino_id INTEGER, puntos INTEGER,
  texto TEXT, aspecto TEXT, creada INTEGER);
CREATE TABLE confianza(dueno_id INTEGER, cuidador_id INTEGER);
CREATE TABLE config(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE eventos(id INTEGER PRIMARY KEY, ts INTEGER, sesion TEXT, usuario_id INTEGER, rol TEXT, nombre TEXT, datos TEXT);
CREATE TABLE respuestas(id INTEGER PRIMARY KEY, ts INTEGER, sesion TEXT, participante TEXT, usuario_id INTEGER, tarea TEXT,
  seq INTEGER, esperaba TEXT);
"""

# ---------------------------------------------------------------- utilidades
def ahora():
    return int(time.time() * 1000)

def hoy():
    return date.today()

def pd(s):
    return datetime.strptime(s, "%Y-%m-%d").date()

MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"]
DIA = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]

def fmt_d(s):
    d = pd(s) if isinstance(s, str) else s
    return "%d %s" % (d.day, MES[d.month - 1])

def fmt_dl(d):
    return "%s %d %s" % (DIA[d.weekday()], d.day, MES[d.month - 1])

def hhmm(ms):
    return datetime.fromtimestamp(ms / 1000).strftime("%H:%M")

def eur(n):
    s = ("%.2f" % n).replace(".", ",")
    return (s[:-3] if s.endswith(",00") else s) + " €"

def conectar():
    c = sqlite3.connect(DB_PATH, timeout=15, isolation_level=None, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c

def filas(c, sql, *a):
    return [dict(r) for r in c.execute(sql, a).fetchall()]

def fila(c, sql, *a):
    r = c.execute(sql, a).fetchone()
    return dict(r) if r else None

def hash_clave(clave, sal):
    return hashlib.pbkdf2_hmac("sha256", clave.encode(), sal.encode(), 60000).hex()

def cfg(c, k, defecto=None):
    r = fila(c, "SELECT v FROM config WHERE k=?", k)
    return r["v"] if r else defecto

def set_cfg(c, k, v):
    c.execute("INSERT OR REPLACE INTO config(k,v) VALUES(?,?)", (k, str(v)))

CONTACTO = re.compile(r"(\+?\d[\d\s.\-]{7,}\d)|([\w.+-]+@[\w-]+\.[\w.]+)|((https?://|www\.)\S+)|\b(bizum|whats?app|paypal|telegram)\b", re.I)

def filtrar(texto):
    nuevo, n = CONTACTO.subn("[dato oculto]", texto)
    return nuevo, n > 0

class ApiError(Exception):
    def __init__(self, msg, code=400):
        super().__init__(msg)
        self.msg, self.code = msg, code

# ---------------------------------------------------------------- tiempo real
class Hub:
    def __init__(self):
        self.lock = threading.Lock()
        self.subs = {}

    def sub(self, clave):
        q = queue.Queue()
        with self.lock:
            self.subs.setdefault(clave, []).append(q)
        return q

    def unsub(self, clave, q):
        with self.lock:
            if q in self.subs.get(clave, []):
                self.subs[clave].remove(q)

    def send(self, clave, msg):
        with self.lock:
            qs = list(self.subs.get(clave, []))
        for q in qs:
            q.put(msg)

HUB = Hub()

def notificar(c, uid, tipo, texto, sub="", enlace="", actor=None):
    cur = c.execute("INSERT INTO notificaciones(usuario_id,tipo,texto,sub,enlace,actor_id,creada) VALUES(?,?,?,?,?,?,?)",
                    (uid, tipo, texto, sub, enlace, actor, ahora()))
    n = fila(c, "SELECT * FROM notificaciones WHERE id=?", cur.lastrowid)
    HUB.send(uid, {"type": "notif", "notif": n})
    return n

def avisar_cambio(uid, que="datos"):
    HUB.send(uid, {"type": "refresh", "what": que})

def evento(c, uid, nombre, datos=None):
    rol = None
    if uid:
        u = fila(c, "SELECT rol, es_bot FROM usuarios WHERE id=?", uid)
        rol = ("bot-" if u and u["es_bot"] else "") + (u["rol"] if u else "")
    e = {"ts": ahora(), "sesion": cfg(c, "sesion", ""), "usuario_id": uid, "rol": rol, "nombre": nombre,
         "datos": json.dumps(datos or {}, ensure_ascii=False)}
    c.execute("INSERT INTO eventos(ts,sesion,usuario_id,rol,nombre,datos) VALUES(:ts,:sesion,:usuario_id,:rol,:nombre,:datos)", e)
    HUB.send("mod", {"type": "evento", "evento": e})

# Temporizadores de los robots (se cancelan al cargar un escenario)
TIMERS = []
GENERACION = [0]

def luego(seg, fn, *args):
    gen = GENERACION[0]

    def run():
        if gen != GENERACION[0]:
            return
        c = conectar()
        try:
            fn(c, *args)
        except Exception as e:  # un robot no debe tumbar el servidor
            print("robot:", e)
        finally:
            c.close()

    t = threading.Timer(seg, run)
    t.daemon = True
    TIMERS.append(t)
    t.start()

def cancelar_timers():
    GENERACION[0] += 1
    for t in TIMERS:
        t.cancel()
    TIMERS.clear()

# ---------------------------------------------------------------- reglas de negocio
def seres_por_ids(c, ids):
    if not ids:
        return []
    q = ",".join("?" * len(ids))
    return filas(c, """SELECT s.*, e.nombre AS especie, e.cat, e.grupo, e.dif, e.cada, e.formacion, e.mult, e.calor
                       FROM seres s JOIN especies e ON e.id=s.especie_id WHERE s.id IN (%s) ORDER BY s.id""" % q, *ids)

def seres_de_usuario(c, uid):
    return filas(c, """SELECT s.*, e.nombre AS especie, e.cat, e.grupo, e.dif, e.cada, e.formacion, e.mult, e.calor
                       FROM seres s JOIN especies e ON e.id=s.especie_id WHERE s.usuario_id=? ORDER BY s.id""", uid)

def calcular_plan(seres, inicio, fin, habitada):
    dias = (pd(fin) - pd(inicio)).days
    has_an = any(s["cat"] in ("an", "ex") for s in seres)
    has_ex = any(s["cat"] == "ex" for s in seres)
    has_pl = any(s["cat"] == "pl" for s in seres)
    min_cada = min([s["cada"] for s in seres] or [1])
    paso = 1 if has_an else min_cada
    dias_visita = list(range(0, max(dias, 1), paso)) or [0]
    delicadas = any(s["cat"] == "pl" and s["dif"] >= 4 for s in seres)
    mult = max([s["mult"] for s in seres] or [1])
    if has_ex:
        servicio, base, unidad = "Cuidado de exóticos certificado", 26, "visita"
    elif has_an and has_pl:
        servicio, base, unidad = "Cuidado combinado", 21 + (2 if delicadas else 0), "día"
    elif has_an:
        servicio, base, unidad = "Visita a domicilio", 16, "día"
    else:
        servicio, base, unidad = "Riego experto", 14 if delicadas else 12, "visita"
    por = round(base * mult, 2)
    extra = 3 if habitada else 0
    total = round((por + extra) * len(dias_visita), 2)
    return {"dias": dias, "visitas": len(dias_visita), "dias_visita": dias_visita, "servicio": servicio, "base": base,
            "mult": mult, "por_visita": por, "unidad": unidad, "extra": extra, "total": total, "delicadas": delicadas,
            "has_an": has_an, "has_pl": has_pl, "has_ex": has_ex}

def especies_clave(seres):
    return sorted({s["especie"] for s in seres if s["cat"] in ("an", "ex") or s["dif"] >= 3})

def idoneos(c, cp, inicio, fin, seres, franja, opt, dueno_id, excluir=()):
    """Cuidadores que cumplen TODOS los requisitos obligatorios (SOL-02) y los opcionales activos (SOL-03)."""
    cats = {s["cat"] for s in seres}
    ex_grupos = {s["grupo"] for s in seres if s["cat"] == "ex"}
    formacion_pl = any(s["cat"] == "pl" and s["formacion"] for s in seres)
    medic = any(s["medicacion"] for s in seres)
    claves = especies_clave(seres)
    confianza = {r["cuidador_id"] for r in filas(c, "SELECT cuidador_id FROM confianza WHERE dueno_id=?", dueno_id)}
    out = []
    for p in filas(c, """SELECT p.*, u.nombre, u.es_bot, u.barrio FROM perfiles p JOIN usuarios u ON u.id=p.usuario_id
                         WHERE p.activo=1 AND u.id<>?""", dueno_id):
        uid = p["usuario_id"]
        if uid in excluir or not p["verificado"]:
            continue
        if not ZONA_UNICA and not fila(c, "SELECT 1 FROM zonas_cuidador WHERE cuidador_id=? AND cp=?", uid, cp):
            continue
        if not fila(c, "SELECT 1 FROM disponibilidad WHERE cuidador_id=? AND inicio<=? AND fin>=?", uid, inicio, fin):
            continue
        if cats & {"an"} and not p["acepta_an"]:
            continue
        if "pl" in cats and not p["acepta_pl"]:
            continue
        if "ex" in cats and (not p["acepta_ex"] or not ex_grupos <= set((p["ex_grupos"] or "").split(","))):
            continue
        if formacion_pl and not p["del"]:
            continue
        if medic and not p["medicacion"]:
            continue
        esp = {r["especie"] for r in filas(c, "SELECT especie FROM especies_cuidador WHERE cuidador_id=?", uid)}
        if opt.get("del") and not p["del"]:
            continue
        if opt.get("esp") and not set(claves) <= esp:
            continue
        if opt.get("rat") and not (p["rating"] or 0) >= 4.5:
            continue
        if opt.get("serv") and (p["n_serv"] or 0) < 5:
            continue
        if opt.get("fr") and franja not in (p["franjas"] or ""):
            continue
        p["confianza"] = uid in confianza
        p["especies"] = sorted(esp)
        out.append(p)
    out.sort(key=lambda p: (not p["confianza"], not p["del"], p["km"] or 9, -(p["rating"] or 0)))
    return out

def sugerencia(c, cp, inicio, fin, seres, franja, opt, dueno_id):
    mejor, mejor_n = None, -1
    for k, v in opt.items():
        if not v:
            continue
        o2 = dict(opt)
        o2[k] = False
        n = len(idoneos(c, cp, inicio, fin, seres, franja, o2, dueno_id))
        if n > mejor_n:
            mejor, mejor_n = k, n
    return {"k": mejor, "texto": OPCIONALES.get(mejor), "n": mejor_n} if mejor else None

def anuncio_completo(c, aid):
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", aid)
    if not a:
        raise ApiError("Este anuncio no existe", 404)
    a["opt"] = json.loads(a["opt"] or "{}")
    a["plan"] = json.loads(a["plan"] or "{}")
    ids = [r["ser_id"] for r in filas(c, "SELECT ser_id FROM anuncio_seres WHERE anuncio_id=?", aid)]
    a["seres"] = seres_por_ids(c, ids)
    a["barrio"] = ZONAS.get(a["cp"], a["cp"])
    return a

def enviar_avisos(c, a, excluir=()):
    """EMP-01/02: aviso solo a idóneos, máximo 15 por tanda, con cupo para cuidadores nuevos."""
    ya = {r["cuidador_id"] for r in filas(c, "SELECT cuidador_id FROM avisos WHERE anuncio_id=?", a["id"])}
    lista = [p for p in idoneos(c, a["cp"], a["inicio"], a["fin"], a["seres"], a["franja"], a["opt"], a["dueno_id"], excluir)
             if p["usuario_id"] not in ya]
    tanda = lista[:15]
    nuevos = [p for p in lista if (p["n_serv"] or 0) <= 2]
    cupo = max(1, round(len(tanda) * 0.2)) if nuevos else 0
    if cupo and sum(1 for p in tanda if (p["n_serv"] or 0) <= 2) < cupo:
        for p in nuevos:
            if p not in tanda:
                if len(tanda) >= 15:
                    tanda.pop()
                tanda.append(p)
                if sum(1 for x in tanda if (x["n_serv"] or 0) <= 2) >= cupo:
                    break
    dueno = fila(c, "SELECT nombre FROM usuarios WHERE id=?", a["dueno_id"])
    for p in tanda:
        c.execute("INSERT INTO avisos(anuncio_id,cuidador_id,enviado) VALUES(?,?,?)", (a["id"], p["usuario_id"], ahora()))
        notificar(c, p["usuario_id"], "solicitud", "Nueva solicitud en %s" % a["barrio"],
                  "%s · %s – %s · %s" % (dueno["nombre"], fmt_d(a["inicio"]), fmt_d(a["fin"]), ", ".join(s["nombre"] for s in a["seres"])),
                  "#/solicitud/%d" % a["id"], a["dueno_id"])
    total = len(ya) + len(tanda)
    c.execute("UPDATE anuncios SET avisados=? WHERE id=?", (total, a["id"]))
    evento(c, a["dueno_id"], "aviso_enviado", {"anuncio": a["id"], "n": len(tanda), "nuevos_cupo": cupo})
    return tanda

def cand_info(c, cand_id):
    k = fila(c, "SELECT * FROM candidaturas WHERE id=?", cand_id)
    if not k:
        raise ApiError("Esta conversación no existe", 404)
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", k["anuncio_id"])
    return k, a

def puede_ver_chat(uid, k, a):
    return uid in (k["cuidador_id"], a["dueno_id"])

def contacto_visible(a):
    return a["estado"] in ("reservado", "en_curso", "completado")

def mensaje(c, cand_id, autor, texto, sistema=False):
    k, a = cand_info(c, cand_id)
    oculto = 0
    if not sistema and not contacto_visible(a):
        texto, hit = filtrar(texto)
        oculto = 1 if hit else 0
    cur = c.execute("INSERT INTO mensajes(candidatura_id,autor_id,texto,oculto,sistema,creado) VALUES(?,?,?,?,?,?)",
                    (cand_id, autor, texto, oculto, 1 if sistema else 0, ahora()))
    m = fila(c, "SELECT * FROM mensajes WHERE id=?", cur.lastrowid)
    for uid in (k["cuidador_id"], a["dueno_id"]):
        HUB.send(uid, {"type": "msg", "cand": cand_id, "msg": m})
    return m

def presentar(c, anuncio_id, cuidador_id, texto):
    a = anuncio_completo(c, anuncio_id)
    if a["dueno_id"] == cuidador_id:
        raise ApiError("No puedes presentarte a tu propio anuncio")
    if a["estado"] != "abierto":
        raise ApiError("Esta solicitud ya no está disponible")
    if fila(c, "SELECT 1 FROM candidaturas WHERE anuncio_id=? AND cuidador_id=?", anuncio_id, cuidador_id):
        raise ApiError("Ya te has presentado a esta solicitud")
    abiertas = fila(c, "SELECT COUNT(*) n FROM candidaturas WHERE cuidador_id=? AND estado='enviada'", cuidador_id)["n"]
    if abiertas >= 10:
        raise ApiError("Tienes 10 candidaturas abiertas. Espera a que se resuelva alguna.")
    if not fila(c, "SELECT 1 FROM disponibilidad WHERE cuidador_id=? AND inicio<=? AND fin>=?", cuidador_id, a["inicio"], a["fin"]):
        raise ApiError("Tu calendario ha cambiado y ya no estás libre en esas fechas.")
    cur = c.execute("INSERT INTO candidaturas(anuncio_id,cuidador_id,mensaje,estado,creado) VALUES(?,?,?,?,?)",
                    (anuncio_id, cuidador_id, texto, "enviada", ahora()))
    kid = cur.lastrowid
    u = fila(c, "SELECT * FROM usuarios WHERE id=?", cuidador_id)
    p = fila(c, "SELECT * FROM perfiles WHERE usuario_id=?", cuidador_id)
    mensaje(c, kid, cuidador_id, "%s se ha presentado a tu anuncio" % u["nombre"], sistema=True)
    if texto.strip():
        mensaje(c, kid, cuidador_id, texto.strip())
    notificar(c, a["dueno_id"], "candidatura", "%s se ha presentado a tu anuncio" % u["nombre"],
              "%s · a %s km" % (u["barrio"], str(p["km"]).replace(".", ",")), "#/anuncio/%d" % anuncio_id, cuidador_id)
    c.execute("UPDATE anuncios SET sin_respuesta=0 WHERE id=?", (anuncio_id,))
    avisar_cambio(cuidador_id)
    evento(c, cuidador_id, "candidatura_enviada", {"anuncio": anuncio_id, "con_mensaje": bool(texto.strip())})
    return kid

# ---------------------------------------------------------------- robots
GUION = {
    "javier": {"msg": "Hola, {d}. Llevo seis años cuidando casas con gatos y plantas entre Chamberí y Malasaña. Puedo pasar una vez al día, de mañana o de tarde, como mejor te venga.",
               "hora": "Suelo ir a primera hora, sobre las 9:00, pero me adapto a la franja que necesites.",
               "plantas": "Para las plantas delicadas uso agua sin cal y compruebo la humedad de la tierra antes de regar. Si hace calor, paso a pulverizar también.",
               "animal": "Con los gatos voy con calma: primero comida y agua, luego arenero, y me quedo un rato para que se acostumbren a mí.",
               "fotos": "Al salir te mando el parte con las tareas marcadas y fotos de cada uno.",
               "experiencia": "Unos 38 servicios en Todo Sigue Vivo y varios clientes que repiten cada verano.",
               "contacto": "Si te es más fácil, escríbeme al 612 345 678 y lo hablamos."},
    "sofia": {"msg": "Hola, {d}. Tengo dos gatos y un salón lleno de monsteras y ficus. Con las calatheas tengo menos experiencia, pero si me dejas las instrucciones las sigo al pie de la letra.",
              "hora": "Por las tardes, a partir de las 19:00. Si prefieres otra hora, dímelo y lo miramos.",
              "plantas": "He leído las instrucciones de tu ficha. Lo tengo claro y, si dudo, te pregunto antes de regar.",
              "animal": "Tengo dos gatos, así que sé leer cuándo están estresados. Le dejaría su espacio.",
              "fotos": "Sí, fotos en cada visita y una nota si veo algo raro.",
              "experiencia": "15 servicios hasta ahora, sobre todo gatos y plantas de interior."},
    "nerea": {"msg": "Hola, {d}. Soy Nerea, de Argüelles. Trabajo en un vivero y me encantan las plantas difíciles.",
              "hora": "Me viene mejor por la mañana, antes de ir al vivero.",
              "plantas": "Con las calatheas, agua sin cal y nada de sol directo. Te lo cuento todo en el parte."},
    "marisa": {"msg": "Hola, {d}. Vivo en Mirasierra, muy cerca. He tenido gatos toda la vida y ahora cuido los de mis vecinos cuando se van de viaje.",
               "hora": "Me viene bien por la mañana, sobre las 10:00, aunque puedo pasar por la tarde si lo prefieres.",
               "animal": "Primero agua y comida, luego el arenero, y me quedo un ratito con él para que no esté solo. Si es tímido, le dejo su espacio.",
               "fotos": "Te mando fotos en cada visita, y un vídeo si se deja.",
               "experiencia": "Unos 22 servicios ya, casi todos con gatos del barrio."},
    "ruben": {"msg": "Hola, {d}. Soy Rubén, de Peñagrande. Trabajo desde casa y tengo las tardes libres. Convivo con dos gatas rescatadas, así que estoy acostumbrado.",
              "hora": "Por las tardes, entre las 17:00 y las 20:00. Me adapto a la hora que le venga bien a tu gato.",
              "animal": "Reviso que coma y beba, limpio el arenero y juego un rato con él. Con las mías hago lo mismo.",
              "fotos": "Claro, foto en cada visita y te cuento cómo le veo."},
    "noa": {"msg": "Hola, {d}. Soy Noa, estudio Veterinaria y vivo en Mirasierra. Estoy empezando en Todo Sigue Vivo y me encantaría cuidar de tu gato.",
            "hora": "Tengo clases por la mañana, así que me viene mejor por la tarde o a última hora.",
            "animal": "En la facultad hago prácticas con gatos. Me fijo en si come, en el arenero y en cómo se mueve, y te aviso si veo algo raro.",
            "experiencia": "Llevo un servicio en la plataforma, pero tengo mucha experiencia con gatos en casa y en las prácticas."},
    "elena": {"msg": "Hola, {d}. Cuido reptiles y aves desde hace diez años y doy formación a otros cuidadores. Reviso temperatura y humedad del terrario en cada visita.",
              "animal": "Mido la temperatura de la zona caliente y la fría y te la apunto en el parte.",
              "hora": "Puedo pasar a la hora que necesite tu terrario; las luces UVB me las indicas en la ficha."},
}
TEMAS = [
    ("encuentro", r"encuentro|conoce|quedar|vernos|visita previa", "Me viene bien cualquier tarde de estos días. Proponme los huecos desde la web y elijo uno."),
    ("precio", r"precio|cu[aá]nto|€|cobr|pagar|pago", "El precio es el que ves en la web. El pago va por la plataforma al confirmar, así los dos estamos cubiertos."),
    ("hora", r"hora|horario|franja|mañana|tarde|noche|cu[aá]ndo (vendr|pasar|ir|vas)", "Me adapto a la franja que necesites. Dime qué te viene mejor."),
    ("fotos", r"foto|parte|me avisas|avisar", "Sí, al terminar cada visita te llega el parte con fotos."),
    ("animal", r"gat|lola|comida|arenero|terrario|gecko|pogona|reptil|p[aá]jar|ave|perr|animal", "Sigo las instrucciones de tu ficha y te cuento cómo está en cada parte."),
    ("plantas", r"riega|riego|regar|planta|calathea|helecho|orqu|bons|agua|monstera|suculent", "Riego según la ficha y compruebo la tierra antes, para no ahogarlas."),
    ("experiencia", r"experiencia|años|antes|has cuidado|servicios", "Llevo un tiempo cuidando casas en el barrio; en mi perfil ves los servicios y las reseñas."),
]
# Usuarios registrados que se presentan solos a los anuncios que les encajan (modo presentación).
# Se activa o desactiva desde la sala de test.
AUTO_PRESENTAR = ["javier", "sofia", "elena"]

GENERICO = ["¡Perfecto! Lo apunto.", "Sin problema, lo hablamos en el encuentro.", "Cuando quieras, proponme un hueco para conocernos."]

def robot_presentarse(c, anuncio_id, bot_id):
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", anuncio_id)
    if not a or a["estado"] != "abierto":
        return
    bot = fila(c, "SELECT * FROM usuarios WHERE id=?", bot_id)
    d = fila(c, "SELECT nombre FROM usuarios WHERE id=?", a["dueno_id"])["nombre"]
    g = GUION.get(bot["clave_bot"], {})
    texto = g.get("msg", "Hola, {d}. Soy %s, vivo en %s. Me encantaría cuidar de tu casa estos días." % (bot["nombre"], bot["barrio"])).format(d=d)
    try:
        presentar(c, anuncio_id, bot_id, texto)
    except ApiError:
        pass

def robot_responder(c, cand_id, texto_dueno):
    k, a = cand_info(c, cand_id)
    bot = fila(c, "SELECT * FROM usuarios WHERE id=?", k["cuidador_id"])
    g = GUION.get(bot["clave_bot"], {})
    dichos = {r["texto"] for r in filas(c, "SELECT texto FROM mensajes WHERE candidatura_id=? AND autor_id=?", cand_id, bot["id"])}
    r = None
    for tema, rx, defecto in TEMAS:
        if re.search(rx, texto_dueno, re.I):
            opcion = g.get(tema, defecto)
            if opcion not in dichos:
                r = opcion
                break
    if r is None and "contacto" in g and g["contacto"] not in dichos and len(dichos) >= 3:
        r = g["contacto"]  # una vez por conversación, para probar el filtro de datos de contacto
    if r is None:
        r = next((x for x in GENERICO if x not in dichos), GENERICO[-1])
    mensaje(c, cand_id, bot["id"], r)
    notificar(c, a["dueno_id"], "mensaje", "%s te ha escrito" % bot["nombre"], r[:60] + ("…" if len(r) > 60 else ""),
              "#/mensajes/%d" % cand_id, bot["id"])

def robot_elegir_hueco(c, anuncio_id):
    e = fila(c, "SELECT * FROM encuentros WHERE anuncio_id=?", anuncio_id)
    if e and not e["elegido"]:
        elegir_hueco(c, anuncio_id, json.loads(e["huecos"])[0])

def robot_seguir(c, anuncio_id):
    e = fila(c, "SELECT * FROM encuentros WHERE anuncio_id=?", anuncio_id)
    if e and e["si_cuidador"] is None:
        seguimos(c, anuncio_id, "cuidador", True)

def robot_extra(c, extra_id):
    aceptar_extra(c, extra_id)

# ---------------------------------------------------------------- acciones del journey
def elegir(c, dueno_id, cand_id, huecos):
    k, a = cand_info(c, cand_id)
    if a["dueno_id"] != dueno_id:
        raise ApiError("No puedes elegir en un anuncio que no es tuyo", 403)
    if a["estado"] != "abierto" or k["estado"] != "enviada":
        raise ApiError("Esta candidatura ya no se puede elegir")
    huecos = sorted({int(h) for h in huecos})
    if not 1 <= len(huecos) <= 3:
        raise ApiError("Propón entre 1 y 3 huecos")
    c.execute("UPDATE anuncios SET estado='asignado', elegido_id=? WHERE id=?", (k["cuidador_id"], a["id"]))
    c.execute("UPDATE candidaturas SET estado='elegida' WHERE id=?", (cand_id,))
    c.execute("INSERT OR REPLACE INTO encuentros(anuncio_id,huecos,elegido,si_dueno,si_cuidador) VALUES(?,?,NULL,NULL,NULL)",
              (a["id"], json.dumps(huecos)))
    dueno = fila(c, "SELECT nombre FROM usuarios WHERE id=?", dueno_id)["nombre"]
    elegido = fila(c, "SELECT * FROM usuarios WHERE id=?", k["cuidador_id"])
    for o in filas(c, "SELECT * FROM candidaturas WHERE anuncio_id=? AND id<>? AND estado='enviada'", a["id"], cand_id):
        c.execute("UPDATE candidaturas SET estado='descartada' WHERE id=?", (o["id"],))
        mensaje(c, o["id"], dueno_id, "%s ha elegido a otra persona. Gracias por presentarte." % dueno, sistema=True)
        notificar(c, o["cuidador_id"], "descartada", "%s ha elegido a otra persona" % dueno, "Gracias por presentarte",
                  "#/mensajes/%d" % o["id"], dueno_id)
    mensaje(c, cand_id, dueno_id, "%s te ha elegido y propone %d %s para conoceros" % (dueno, len(huecos), "hueco" if len(huecos) == 1 else "huecos"), sistema=True)
    notificar(c, k["cuidador_id"], "elegida", "%s te ha elegido" % dueno, "Elige cuándo conoceros en su casa",
              "#/reserva/%d" % a["id"], dueno_id)
    evento(c, dueno_id, "candidato_elegido", {"anuncio": a["id"], "cuidador": k["cuidador_id"], "huecos": len(huecos)})
    if elegido["es_bot"]:
        luego(6, robot_elegir_hueco, a["id"])

def elegir_hueco(c, anuncio_id, ts):
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", anuncio_id)
    e = fila(c, "SELECT * FROM encuentros WHERE anuncio_id=?", anuncio_id)
    if not e or int(ts) not in json.loads(e["huecos"]):
        raise ApiError("Ese hueco no está entre los propuestos")
    c.execute("UPDATE encuentros SET elegido=? WHERE anuncio_id=?", (int(ts), anuncio_id))
    k = fila(c, "SELECT * FROM candidaturas WHERE anuncio_id=? AND cuidador_id=?", anuncio_id, a["elegido_id"])
    cu = fila(c, "SELECT nombre FROM usuarios WHERE id=?", a["elegido_id"])["nombre"]
    d = datetime.fromtimestamp(int(ts) / 1000)
    mensaje(c, k["id"], a["elegido_id"], "Encuentro previo acordado · %s · %s" % (fmt_dl(d.date()), d.strftime("%H:%M")), sistema=True)
    notificar(c, a["dueno_id"], "encuentro", "%s ha elegido el %s · %s para conoceros" % (cu, fmt_dl(d.date()), d.strftime("%H:%M")),
              "Encuentro previo en tu casa", "#/anuncio/%d" % anuncio_id, a["elegido_id"])
    avisar_cambio(a["elegido_id"])
    evento(c, a["elegido_id"], "encuentro_confirmado", {"anuncio": anuncio_id})

def seguimos(c, anuncio_id, rol, si):
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", anuncio_id)
    e = fila(c, "SELECT * FROM encuentros WHERE anuncio_id=?", anuncio_id)
    if not e or not e["elegido"]:
        raise ApiError("Primero tenéis que acordar el encuentro")
    col = "si_dueno" if rol == "dueno" else "si_cuidador"
    c.execute("UPDATE encuentros SET %s=? WHERE anuncio_id=?" % col, (1 if si else 0, anuncio_id))
    e = fila(c, "SELECT * FROM encuentros WHERE anuncio_id=?", anuncio_id)
    k = fila(c, "SELECT * FROM candidaturas WHERE anuncio_id=? AND cuidador_id=?", anuncio_id, a["elegido_id"])
    yo, otro = (a["dueno_id"], a["elegido_id"]) if rol == "dueno" else (a["elegido_id"], a["dueno_id"])
    evento(c, yo, "seguimos_respuesta", {"anuncio": anuncio_id, "si": bool(si)})
    if not si:
        # ENC-01 CA3: vuelve a candidaturas abiertas, sin coste y sin mostrar el motivo
        c.execute("UPDATE anuncios SET estado='abierto', elegido_id=NULL WHERE id=?", (anuncio_id,))
        c.execute("UPDATE candidaturas SET estado='cerrada' WHERE id=?", (k["id"],))
        c.execute("UPDATE candidaturas SET estado='enviada' WHERE anuncio_id=? AND estado='descartada'", (anuncio_id,))
        c.execute("DELETE FROM encuentros WHERE anuncio_id=?", (anuncio_id,))
        mensaje(c, k["id"], yo, "No seguís adelante. El anuncio vuelve a estar abierto, sin coste.", sistema=True)
        notificar(c, a["dueno_id"], "reabierto", "Tu anuncio vuelve a estar abierto", "Sin coste. Puedes elegir a otra persona.", "#/anuncio/%d" % anuncio_id)
        notificar(c, a["elegido_id"], "reabierto", "No seguís adelante con esta reserva", "Sin coste ni penalización", "#/servicios")
        return
    if e["si_dueno"] == 1 and e["si_cuidador"] == 1:
        reservar(c, anuncio_id)
        return
    nombre = fila(c, "SELECT nombre FROM usuarios WHERE id=?", yo)["nombre"]
    notificar(c, otro, "seguimos", "%s quiere seguir adelante" % nombre, "Falta tu respuesta", "#/reserva/%d" % anuncio_id, yo)
    if rol == "dueno" and fila(c, "SELECT es_bot FROM usuarios WHERE id=?", a["elegido_id"])["es_bot"]:
        luego(4, robot_seguir, anuncio_id)

def reservar(c, anuncio_id):
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", anuncio_id)
    c.execute("UPDATE anuncios SET estado='reservado' WHERE id=?", (anuncio_id,))
    k = fila(c, "SELECT * FROM candidaturas WHERE anuncio_id=? AND cuidador_id=?", anuncio_id, a["elegido_id"])
    mensaje(c, k["id"], a["dueno_id"], "Reserva confirmada · pago simulado. Ya podéis compartir datos de contacto.", sistema=True)
    cu = fila(c, "SELECT nombre FROM usuarios WHERE id=?", a["elegido_id"])["nombre"]
    du = fila(c, "SELECT nombre FROM usuarios WHERE id=?", a["dueno_id"])["nombre"]
    notificar(c, a["dueno_id"], "reserva", "Reserva confirmada con %s" % cu, "Pago simulado en la prueba", "#/reserva/%d" % anuncio_id, a["elegido_id"])
    notificar(c, a["elegido_id"], "reserva", "Reserva confirmada con %s" % du, "Ya ves la dirección y el acceso", "#/reserva/%d" % anuncio_id, a["dueno_id"])
    evento(c, a["dueno_id"], "reserva_confirmada", {"anuncio": anuncio_id})

def tareas_del_dia(seres, dia):
    out = []
    for s in seres:
        toca = s["cat"] in ("an", "ex") or dia % max(1, s["cada"]) == 0
        out.append({"ser_id": s["id"], "nombre": s["nombre"], "especie": s["especie"], "cat": s["cat"], "cant": s["cantidad"],
                    "instr": s["instr"], "toca": toca, "estado": None if toca else "no_hoy",
                    "motivo": "" if toca else "No lo necesita hoy (cada %d días)" % s["cada"]})
    return out

def resumen_tareas(tareas):
    pl = [t for t in tareas if t["cat"] == "pl"]
    hechas_pl = sum(t["cant"] for t in pl if t["estado"] == "hecha")
    total_pl = sum(t["cant"] for t in pl)
    partes = []
    for t in tareas:
        if t["cat"] != "pl" and t["estado"] == "hecha":
            partes.append("%s, atendido" % t["nombre"] if t["cat"] == "an" else "%s, revisado" % t["nombre"])
    if total_pl:
        partes.append("%d de %d plantas regadas" % (hechas_pl, total_pl))
    return " · ".join(partes)

def llegada(c, cuidador_id, anuncio_id, dia, extra=False):
    a = anuncio_completo(c, anuncio_id)
    if a["elegido_id"] != cuidador_id or a["estado"] not in ("reservado", "en_curso"):
        raise ApiError("No tienes una reserva activa aquí", 403)
    if not extra and dia not in a["plan"]["dias_visita"]:
        raise ApiError("Ese día no hay visita prevista")
    if fila(c, "SELECT 1 FROM visitas WHERE anuncio_id=? AND dia=? AND extra=? ", anuncio_id, dia, 1 if extra else 0):
        raise ApiError("Esa visita ya está registrada")
    if fila(c, "SELECT 1 FROM visitas WHERE anuncio_id=? AND salida IS NULL", anuncio_id):
        raise ApiError("Termina primero la visita en curso")
    t = ahora()
    cur = c.execute("INSERT INTO visitas(anuncio_id,dia,llegada,tareas,extra) VALUES(?,?,?,?,?)",
                    (anuncio_id, dia, t, json.dumps(tareas_del_dia(a["seres"], dia), ensure_ascii=False), 1 if extra else 0))
    c.execute("UPDATE anuncios SET estado='en_curso' WHERE id=?", (anuncio_id,))
    cu = fila(c, "SELECT nombre FROM usuarios WHERE id=?", cuidador_id)["nombre"]
    notificar(c, a["dueno_id"], "llegada", "%s ha llegado · %s" % (cu, hhmm(t)), "Visita extra por calor" if extra else "Día %d de %d" % (a["plan"]["dias_visita"].index(dia) + 1, a["plan"]["visitas"]),
              "#/reserva/%d" % anuncio_id, cuidador_id)
    evento(c, cuidador_id, "visita_iniciada", {"anuncio": anuncio_id, "dia": dia, "extra": extra})
    return cur.lastrowid

def salida(c, cuidador_id, visita_id, nota, ejemplo=False):
    v = fila(c, "SELECT * FROM visitas WHERE id=?", visita_id)
    if not v:
        raise ApiError("Visita no encontrada", 404)
    a = anuncio_completo(c, v["anuncio_id"])
    if a["elegido_id"] != cuidador_id:
        raise ApiError("Esta visita no es tuya", 403)
    tareas = json.loads(v["tareas"])
    if any(t["estado"] is None for t in tareas):
        raise ApiError("Marca todas las tareas del día antes de terminar")
    if not fila(c, "SELECT 1 FROM fotos WHERE visita_id=?", visita_id):
        raise ApiError("Añade al menos una foto para el parte")
    t = ahora()
    c.execute("UPDATE visitas SET salida=?, nota=? WHERE id=?", (t, nota, visita_id))
    cu = fila(c, "SELECT nombre FROM usuarios WHERE id=?", cuidador_id)["nombre"]
    notificar(c, a["dueno_id"], "parte", "Parte del día · %s · %s" % (cu, hhmm(t)), resumen_tareas(tareas), "#/reserva/%d" % a["id"], cuidador_id)
    for t2 in tareas:
        if t2["estado"] == "no_pude" and t2["cat"] in ("an", "ex"):
            notificar(c, a["dueno_id"], "incidencia", "%s no ha podido atender a %s" % (cu, t2["nombre"]), t2.get("motivo") or "Revisa el parte", "#/reserva/%d" % a["id"], cuidador_id)
    evento(c, cuidador_id, "parte_enviado", {"anuncio": a["id"], "visita": visita_id, "ejemplo": ejemplo})
    hechas = {r["dia"] for r in filas(c, "SELECT dia FROM visitas WHERE anuncio_id=? AND extra=0 AND salida IS NOT NULL", a["id"])}
    if set(a["plan"]["dias_visita"]) <= hechas:
        completar(c, a["id"])

def completar(c, anuncio_id):
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", anuncio_id)
    if a["estado"] == "completado":
        return
    c.execute("UPDATE anuncios SET estado='completado' WHERE id=?", (anuncio_id,))
    c.execute("UPDATE perfiles SET n_serv=n_serv+1 WHERE usuario_id=?", (a["elegido_id"],))
    du = fila(c, "SELECT nombre FROM usuarios WHERE id=?", a["dueno_id"])["nombre"]
    cu = fila(c, "SELECT nombre FROM usuarios WHERE id=?", a["elegido_id"])["nombre"]
    notificar(c, a["dueno_id"], "fin", "Servicio terminado. ¿Qué tal con %s?" % cu, "Tienes 14 días para valorarlo", "#/reserva/%d" % anuncio_id, a["elegido_id"])
    notificar(c, a["elegido_id"], "fin", "Servicio terminado. ¿Qué tal con %s?" % du, "Tu pago se libera en 48 h (simulado)", "#/reserva/%d" % anuncio_id, a["dueno_id"])
    evento(c, a["dueno_id"], "reserva_completada", {"anuncio": anuncio_id})

def pedir_extra(c, dueno_id, anuncio_id):
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", anuncio_id)
    if not a or a["dueno_id"] != dueno_id or a["estado"] not in ("reservado", "en_curso"):
        raise ApiError("No hay una reserva activa para pedir la visita extra")
    if fila(c, "SELECT 1 FROM extras WHERE anuncio_id=? AND estado IN ('pedida','aceptada')", anuncio_id):
        raise ApiError("Ya has pedido una visita extra")
    cur = c.execute("INSERT INTO extras(anuncio_id,estado,creado) VALUES(?,?,?)", (anuncio_id, "pedida", ahora()))
    du = fila(c, "SELECT nombre FROM usuarios WHERE id=?", dueno_id)["nombre"]
    notificar(c, a["elegido_id"], "extra", "%s pide una visita extra por la ola de calor" % du, "Unos 12 € · orientativo. Tienes 4 h para aceptar", "#/reserva/%d" % anuncio_id, dueno_id)
    evento(c, dueno_id, "visita_extra_pedida", {"anuncio": anuncio_id})
    if fila(c, "SELECT es_bot FROM usuarios WHERE id=?", a["elegido_id"])["es_bot"]:
        luego(5, robot_extra, cur.lastrowid)

def aceptar_extra(c, extra_id, si=True):
    x = fila(c, "SELECT * FROM extras WHERE id=?", extra_id)
    if not x or x["estado"] != "pedida":
        raise ApiError("Esta petición ya no está pendiente")
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", x["anuncio_id"])
    c.execute("UPDATE extras SET estado=? WHERE id=?", ("aceptada" if si else "rechazada", extra_id))
    cu = fila(c, "SELECT nombre FROM usuarios WHERE id=?", a["elegido_id"])["nombre"]
    if si:
        notificar(c, a["dueno_id"], "extra", "%s hará la visita extra" % cu, "Te mandará el parte como siempre", "#/reserva/%d" % a["id"], a["elegido_id"])
    else:
        notificar(c, a["dueno_id"], "extra", "%s no puede hacer la visita extra" % cu, "Buscamos a otra persona disponible ese día. Si no la encontramos, no se te cobra.", "#/reserva/%d" % a["id"], a["elegido_id"])
    avisar_cambio(a["elegido_id"])
    evento(c, a["elegido_id"], "visita_extra_respuesta", {"anuncio": a["id"], "si": si})

def cancelar_cuidador(c, cuidador_id, anuncio_id):
    a = anuncio_completo(c, anuncio_id)
    if a["elegido_id"] != cuidador_id or a["estado"] not in ("asignado", "reservado"):
        raise ApiError("No puedes cancelar esta reserva")
    cu = fila(c, "SELECT nombre FROM usuarios WHERE id=?", cuidador_id)["nombre"]
    k = fila(c, "SELECT * FROM candidaturas WHERE anuncio_id=? AND cuidador_id=?", anuncio_id, cuidador_id)
    c.execute("UPDATE candidaturas SET estado='cerrada' WHERE id=?", (k["id"],))
    c.execute("UPDATE candidaturas SET estado='enviada' WHERE anuncio_id=? AND estado='descartada'", (anuncio_id,))
    c.execute("UPDATE anuncios SET estado='abierto', elegido_id=NULL WHERE id=?", (anuncio_id,))
    c.execute("DELETE FROM encuentros WHERE anuncio_id=?", (anuncio_id,))
    mensaje(c, k["id"], cuidador_id, "%s ha cancelado. Lo sentimos." % cu, sistema=True)
    # INC-03: «Te buscamos sustituto», nunca «garantizado»
    notificar(c, a["dueno_id"], "cancelacion", "%s no puede ir. Te buscamos sustituto." % cu,
              "Avisamos de nuevo a los cuidadores idóneos. Si no aparece nadie, recuperas el 100 %.", "#/anuncio/%d" % anuncio_id, cuidador_id)
    a = anuncio_completo(c, anuncio_id)
    enviar_avisos(c, a, excluir=(cuidador_id,))
    evento(c, cuidador_id, "reserva_cancelada", {"anuncio": anuncio_id, "quien": "cuidador"})

# ---------------------------------------------------------------- datos de prueba y escenarios
DUENOS = [
    # clave, nombre, apellido, cp, barrio, casa, seres [(especie, nombre, cantidad, instr, alarma, medicación)]
    ("marta", "Marta", "G.", "28004", "Malasaña-Universidad",
     ("Calle del Espíritu Santo, 18 · 3.º B", "Llaves en mano", "Portal con código 4521. La llave pequeña es del buzón.", "Clínica Veterinaria Dos de Mayo · 914 000 000", "Lucía (hermana) · 600 000 000"),
     [("Gato", "Lola", 1, "Media lata de húmeda por la mañana y pienso a voluntad. Agua limpia cada día. Arenero cada dos días.", "Si no come en 24 h, llamar a la veterinaria.", 0),
      ("Calathea", "Calatheas", 3, "200 ml de agua sin cal cada una. Pulverizar las hojas. Lejos del sol directo.", "Hojas enrolladas: le falta agua.", 0),
      ("Monstera", "Monstera", 1, "Medio litro si los tres primeros centímetros de tierra están secos.", "Hojas amarillas: exceso de riego.", 0),
      ("Suculentas y cactus", "Suculentas", 7, "No regar salvo que la ausencia supere dos semanas.", "Tallos blandos: exceso de riego.", 0)]),
    ("pablo", "Pablo", "R.", "28010", "Chamberí",
     ("Calle de Fuencarral, 140 · 5.º A", "Portero", "Las llaves las tiene el portero, Andrés.", "", "Ana · 600 000 001"),
     [("Helecho", "Helechos", 6, "Tierra siempre húmeda, nunca encharcada. Pulverizar a diario en verano.", "Puntas secas: falta humedad.", 0),
      ("Calathea", "Calatheas", 5, "Agua sin cal, 200 ml cada una.", "Hojas enrolladas: le falta agua.", 0),
      ("Bonsái", "Bonsái de olmo", 1, "Riego por inmersión 5 minutos. Sombra parcial.", "Hojas caídas en masa: avisar.", 0),
      ("Orquídea", "Orquídeas", 4, "Inmersión 10 minutos cada 7 días.", "Raíces grises: necesita agua.", 0),
      ("Potus", "Potus", 3, "Regar cuando la tierra esté seca.", "", 0)]),
    ("alex", "Álex", "M.", "28012", "Lavapiés-Embajadores",
     ("Calle del Ave María, 30 · 2.º", "Caja de llaves", "Caja de llaves en el portal, código 1987.", "Exóticos Madrid · 915 000 000", "Sam · 600 000 002"),
     [("Gecko leopardo", "Kiwi", 1, "Grillos vivos cada dos días (5-6). Zona caliente a 30-32 °C.", "Si no come dos tomas seguidas, avisar.", 0),
      ("Pogona", "Bruma", 1, "Verdura fresca cada día y 4 insectos. Luz UVB 12 h.", "Letargo fuera de temporada: avisar.", 0),
      ("Potus", "Potus", 2, "Regar cuando la tierra esté seca.", "", 0)]),
    ("lucas", "Lucas", "P.", "28033", "Hortaleza",
     ("Calle de Mar Caspio, 5", "Llaves en mano", "", "Veterinaria Hortaleza", ""),
     [("Gato", "Nube", 1, "Pienso dos veces al día.", "", 0)]),
]

CUIDADORES = [
    # clave, nombre, barrio, cp, km, edad, del, ha cuidado, rating, reseñas, servicios, franjas, tarifa, libre, zonas, extra
    ("irene", "Irene", "Malasaña", "28004", .4, 22, 1, ["Gato", "Calathea", "Monstera"], 5.0, 2, 2, "tn", .95, True, ["28004", "28015", "28010"], {"bot": 0, "bio": "Estudia Ingeniería Agrónoma. Tiene 30 plantas en casa y una gata, Mora."}),
    ("javier", "Javier", "Chamberí", "28010", 1.3, 40, 1, ["Gato", "Calathea", "Helecho", "Orquídea"], 4.9, 31, 38, "mt", 1.1, True, ["28004", "28010", "28015"], {"bio": "Cuida casas con animales y plantas desde hace seis años. Muchos clientes repiten cada verano."}),
    ("sofia", "Sofía", "Universidad", "28015", .8, 29, 1, ["Gato", "Monstera", "Ficus"], 4.7, 12, 15, "tn", 1.0, True, ["28004", "28015"], {"bio": "Tiene dos gatos y un salón lleno de monsteras y ficus."}),
    ("lucia", "Lucía", "Malasaña", "28004", .6, 31, 1, ["Gato", "Calathea", "Orquídea"], 4.8, 22, 27, "m", 1.0, False, ["28004"], {}),
    ("pedro", "Pedro", "Chueca", "28004", 1.1, 36, 0, ["Gato", "Monstera"], 4.6, 7, 9, "mt", 1.0, True, ["28004", "28010"], {}),
    ("ana", "Ana", "Conde Duque", "28015", .9, 27, 1, ["Gato", "Calathea"], 4.4, 5, 6, "t", 1.0, True, ["28004", "28015"], {}),
    ("marcos", "Marcos", "Malasaña", "28004", .5, 24, 0, ["Gato"], 4.2, 3, 3, "t", 1.0, True, ["28004"], {}),
    ("nerea", "Nerea", "Argüelles", "28015", 1.6, 33, 1, ["Calathea", "Monstera", "Ficus", "Helecho", "Bonsái"], 4.9, 10, 12, "m", 1.05, True, ["28004", "28015", "28010"], {"an": 0, "bio": "Trabaja en un vivero. Le gustan las plantas difíciles."}),
    ("hugo", "Hugo", "Malasaña", "28004", .7, 21, 0, ["Gato"], None, 0, 0, "tn", .9, True, ["28004"], {}),
    ("carla", "Carla", "Arganzuela", "28045", 4.2, 30, 1, ["Gato", "Calathea", "Helecho"], 4.6, 6, 8, "t", 1.0, True, ["28045", "28005"], {}),
    ("samuel", "Samuel", "Chamberí", "28010", 1.4, 45, 1, ["Calathea", "Bonsái", "Orquídea", "Helecho"], 4.8, 14, 16, "mt", 1.15, True, ["28004", "28010"], {"an": 0}),
    ("rosa", "Rosa", "Universidad", "28015", .6, 52, 1, ["Gato"], 4.5, 16, 19, "m", 1.0, True, ["28004", "28015"], {}),
    ("diego", "Diego", "Malasaña", "28004", .3, 26, 0, ["Gato"], None, 0, 0, "mt", 1.0, True, ["28004"], {"ver": 0}),
    ("alba", "Alba", "Chueca", "28004", 1.0, 23, 1, ["Gato", "Calathea"], None, 0, 1, "tn", .95, True, ["28004", "28010"], {}),
    ("tomas", "Tomás", "Chamberí", "28010", 1.5, 41, 0, ["Gato", "Monstera"], 4.8, 40, 44, "mt", 1.0, True, ["28004", "28010"], {}),
    ("marina", "Marina", "Conde Duque", "28015", 1.2, 28, 1, ["Gato", "Monstera", "Calathea"], 4.3, 4, 4, "mt", 1.0, True, ["28004", "28015"], {}),
    ("marisa", "Marisa", "Mirasierra", "28035", .6, 48, 0, ["Gato"], 4.8, 18, 22, "mt", 1.0, True, ["28035"], {"bot": 0, "bio": "Ha tenido gatos toda la vida. Ahora cuida los de sus vecinos cuando se van de viaje."}),
    ("ruben", "Rubén", "Peñagrande", "28035", 1.1, 31, 0, ["Gato", "Potus"], 4.6, 7, 9, "tn", .95, True, ["28035"], {"bot": 0, "bio": "Trabaja desde casa y tiene las tardes libres. Convive con dos gatas rescatadas."}),
    ("noa", "Noa", "Mirasierra", "28035", .9, 20, 0, ["Gato"], None, 0, 1, "mtn", .9, True, ["28035"], {"bot": 0, "bio": "Estudia Veterinaria. Busca sus primeros servicios en el barrio."}),
    ("elena", "Elena", "Lavapiés", "28012", .5, 35, 1, ["Gecko leopardo", "Pogona", "Tortuga", "Loro", "Gato"], 4.9, 26, 30, "mtn", 1.2, True, ["28012", "28005", "28004"], {"ex": 1, "medic": 1, "bio": "Cuida reptiles y aves desde hace diez años y forma a otros cuidadores."}),
]

def crear_usuario(c, correo, nombre, apellido, cp, rol, barrio=None, bot=0, clave_bot=None, clave=CLAVE_PRUEBA):
    sal = secrets.token_hex(8)
    cur = c.execute("INSERT INTO usuarios(nombre,apellido,correo,hash,sal,cp,barrio,rol,es_bot,clave_bot,creado) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (nombre, apellido, correo.lower(), hash_clave(clave, sal), sal, cp, barrio or ZONAS.get(cp) or BARRIOS_FUERA.get(cp) or ("Madrid · %s" % cp), rol, bot, clave_bot, ahora()))
    return cur.lastrowid

def sembrar(c):
    c.executescript(SCHEMA)
    for e in ESPECIES:
        c.execute("INSERT INTO especies(nombre,cat,grupo,dif,cada,formacion,mult,calor,activa) VALUES(?,?,?,?,?,?,?,?,?)", e)
    esp_id = {r["nombre"]: r["id"] for r in filas(c, "SELECT id,nombre FROM especies")}
    ids = {}
    for clave, nombre, ape, cp, barrio, casa, seres in DUENOS:
        uid = crear_usuario(c, clave + "@ejemplo.com", nombre, ape, cp, "dueno", barrio)
        ids[clave] = uid
        c.execute("INSERT INTO casas VALUES(?,?,?,?,?,?)", (uid,) + casa)
        for esp, n, cant, instr, alarma, med in seres:
            c.execute("INSERT INTO seres(usuario_id,especie_id,nombre,cantidad,instr,alarma,medicacion) VALUES(?,?,?,?,?,?,?)",
                      (uid, esp_id[esp], n, cant, instr, alarma, med))
    hoy_s = hoy().isoformat()
    lejos = (hoy() + timedelta(days=420)).isoformat()
    for (clave, nombre, barrio, cp, km, edad, dl, esp, rat, res, serv, fr, tarifa, libre, zonas, x) in CUIDADORES:
        uid = crear_usuario(c, clave + "@ejemplo.com", nombre, "", cp, "cuidador", barrio, bot=0, clave_bot=clave)
        ids[clave] = uid
        c.execute("INSERT INTO perfiles VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (uid, x.get("bio", ""), edad, km, x.get("an", 1), 1, x.get("ex", 0), "reptil,ave" if x.get("ex") else "",
                   x.get("medic", 0), x.get("ver", 1), dl, rat, res, serv, fr, tarifa, 1))
        for z in zonas:
            c.execute("INSERT INTO zonas_cuidador VALUES(?,?)", (uid, z))
        for e in esp:
            c.execute("INSERT INTO especies_cuidador VALUES(?,?)", (uid, e))
        if libre:
            c.execute("INSERT INTO disponibilidad(cuidador_id,inicio,fin) VALUES(?,?,?)", (uid, hoy_s, lejos))
        else:
            c.execute("INSERT INTO disponibilidad(cuidador_id,inicio,fin) VALUES(?,?,?)", (uid, "2027-07-01", "2027-08-31"))
    set_cfg(c, "seguro", "EN CONTRATACIÓN")
    set_cfg(c, "robots_auto", "1")  # modo presentación (AUTO_PRESENTAR)
    set_cfg(c, "calor", "")
    return ids

def publicar(c, dueno_id, d):
    seres_ids = [int(x) for x in d.get("seres", [])]
    propios = {s["id"] for s in seres_de_usuario(c, dueno_id)}
    if not seres_ids or not set(seres_ids) <= propios:
        raise ApiError("Elige al menos un animal o planta de tu ficha")
    inicio, fin = d.get("inicio"), d.get("fin")
    try:
        di, df = pd(inicio), pd(fin)
    except Exception:
        raise ApiError("Revisa las fechas")
    if di < hoy() + timedelta(days=1):
        raise ApiError("El primer día tiene que ser a partir de mañana")
    if df <= di:
        raise ApiError("La vuelta tiene que ser después del primer día")
    if (df - di).days > 30:
        raise ApiError("Como máximo 30 días por anuncio")
    u = fila(c, "SELECT * FROM usuarios WHERE id=?", dueno_id)
    if not zona_activa(u["cp"]):
        raise ApiError("Aún no hay cuidadores en tu barrio. Te avisamos.")
    if fila(c, "SELECT 1 FROM anuncios WHERE dueno_id=? AND estado IN ('abierto','asignado','reservado','en_curso')", dueno_id):
        raise ApiError("Ya tienes un anuncio activo. En esta prueba solo puede haber uno a la vez.")
    seres = seres_por_ids(c, seres_ids)
    opt = {k: bool(v) for k, v in (d.get("opt") or {}).items() if k in OPCIONALES}
    franja = d.get("franja") if d.get("franja") in ("m", "t", "n") else "t"
    plan = calcular_plan(seres, inicio, fin, bool(d.get("habitada")))
    urgente = 1 if (di - hoy()).days < 2 else 0
    cur = c.execute("""INSERT INTO anuncios(dueno_id,inicio,fin,franja,habitada,opt,nota,cp,plan,estado,avisados,urgente,creado)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (dueno_id, inicio, fin, franja, 1 if d.get("habitada") else 0, json.dumps(opt), (d.get("nota") or "")[:400],
                     u["cp"], json.dumps(plan), "abierto", 0, urgente, ahora()))
    aid = cur.lastrowid
    for s in seres_ids:
        c.execute("INSERT INTO anuncio_seres VALUES(?,?)", (aid, s))
    a = anuncio_completo(c, aid)
    tanda = enviar_avisos(c, a)
    evento(c, dueno_id, "solicitud_publicada", {"anuncio": aid, "idoneos": len(tanda), "precision": [k for k, v in opt.items() if v],
                                                "n_precision": sum(1 for v in opt.values() if v), "servicio": plan["servicio"]})
    notificar(c, dueno_id, "publicado", "Anuncio publicado. Hemos avisado a %d %s" % (len(tanda), "cuidador idóneo" if len(tanda) == 1 else "cuidadores idóneos"),
              "%s – %s" % (fmt_d(inicio), fmt_d(fin)), "#/anuncio/%d" % aid)
    if cfg(c, "robots_auto") == "1":
        # Modo presentación: estos usuarios registrados se presentan solos si el anuncio les encaja.
        claves = {p["usuario_id"]: fila(c, "SELECT clave_bot FROM usuarios WHERE id=?", p["usuario_id"])["clave_bot"] for p in tanda}
        auto = [p for p in tanda if claves[p["usuario_id"]] in AUTO_PRESENTAR]
        auto.sort(key=lambda p: AUTO_PRESENTAR.index(claves[p["usuario_id"]]))
        for i, p in enumerate(auto):
            luego(8 + i * 12, robot_presentarse, aid, p["usuario_id"])
    return aid

def escenario(nombre):
    cancelar_timers()
    for f in os.listdir(FOTOS):
        try:
            os.remove(os.path.join(FOTOS, f))
        except OSError:
            pass
    c = conectar()
    for t in [r["name"] for r in filas(c, "SELECT name FROM sqlite_master WHERE type='table'")]:
        c.execute("DROP TABLE IF EXISTS %s" % t)
    ids = sembrar(c)
    set_cfg(c, "escenario", nombre)
    marta, irene = ids["marta"], ids["irene"]
    seres = [s["id"] for s in seres_de_usuario(c, marta)]
    ini = (hoy() + timedelta(days=11)).isoformat()
    fin = (hoy() + timedelta(days=16)).isoformat()
    set_cfg(c, "robots_auto", "0")  # los escenarios se construyen sin llegadas automáticas
    if nombre != "limpio":
        aid = publicar(c, marta, {"inicio": ini, "fin": fin, "seres": seres, "franja": "t", "opt": {"del": True}})
        # que los avisos de la preparación no salgan como «nuevos»
        robot_presentarse(c, aid, ids["javier"])
        robot_presentarse(c, aid, ids["sofia"])
        if nombre in ("elegida", "reserva", "calor", "fin"):
            kid = presentar(c, aid, irene, "¡Hola, Marta! Vivo a cuatro calles, en la plaza de la Corredera. Tengo calatheas y sé lo delicadas que son con el agua del grifo. Me encantaría conocer a Lola.")
            mensaje(c, kid, marta, "¡Hola, Irene! ¿Cómo riegas las calatheas?")
            mensaje(c, kid, irene, "Con agua filtrada o reposada desde la noche anterior, y les pulverizo las hojas.")
            h = datetime.combine(hoy() + timedelta(days=3), datetime.min.time()).replace(hour=19)
            elegir(c, marta, kid, [int(h.timestamp() * 1000), int((h + timedelta(hours=1)).timestamp() * 1000)])
            if nombre in ("reserva", "calor", "fin"):
                elegir_hueco(c, aid, int(h.timestamp() * 1000))
                seguimos(c, aid, "dueno", True)
                seguimos(c, aid, "cuidador", True)
            if nombre in ("calor", "fin"):
                visita_ejemplo(c, aid)
            if nombre == "calor":
                ola_de_calor(c)
            if nombre == "fin":
                a = anuncio_completo(c, aid)
                for _ in a["plan"]["dias_visita"][1:]:
                    visita_ejemplo(c, aid)
    c.execute("UPDATE notificaciones SET leida=1")
    c.execute("DELETE FROM eventos")
    set_cfg(c, "robots_auto", "1")
    set_cfg(c, "sesion", "")
    c.close()
    HUB.send("todos", {"type": "reset"})

def visita_ejemplo(c, anuncio_id):
    a = anuncio_completo(c, anuncio_id)
    hechas = {r["dia"] for r in filas(c, "SELECT dia FROM visitas WHERE anuncio_id=? AND extra=0", anuncio_id)}
    pend = [d for d in a["plan"]["dias_visita"] if d not in hechas]
    if not pend:
        raise ApiError("No quedan visitas pendientes")
    abierta = fila(c, "SELECT * FROM visitas WHERE anuncio_id=? AND salida IS NULL", anuncio_id)
    vid = abierta["id"] if abierta else llegada(c, a["elegido_id"], anuncio_id, pend[0])
    v = fila(c, "SELECT * FROM visitas WHERE id=?", vid)
    tareas = json.loads(v["tareas"])
    for t in tareas:
        if t["estado"] is None:
            t["estado"] = "hecha"
    c.execute("UPDATE visitas SET tareas=?, ejemplo=1 WHERE id=?", (json.dumps(tareas, ensure_ascii=False), vid))
    for i, src in enumerate(["visita-gata.jpg", "visita-riego.jpg"]):
        nombre = "v%d-%d-%s.jpg" % (vid, i, secrets.token_hex(3))
        with open(os.path.join(PUBLIC, "img", src), "rb") as fsrc, open(os.path.join(FOTOS, nombre), "wb") as fdst:
            fdst.write(fsrc.read())
        c.execute("INSERT INTO fotos(visita_id,archivo,ejemplo) VALUES(?,?,1)", (vid, nombre))
    salida(c, a["elegido_id"], vid, "Todo bien. Lola ha comido y ha estado un rato en el balcón.", ejemplo=True)

def ola_de_calor(c):
    dia = hoy() + timedelta(days=2)
    set_cfg(c, "calor", dia.isoformat())
    n = 0
    for a in filas(c, "SELECT id FROM anuncios WHERE estado IN ('reservado','en_curso')"):
        a = anuncio_completo(c, a["id"])
        sens = [s for s in a["seres"] if s["calor"] >= 0.8]
        if sens:
            nombres = " y ".join(sorted({s["nombre"].lower() if s["cat"] == "pl" else s["nombre"] for s in sens}))
            notificar(c, a["dueno_id"], "calor", "Ola de calor el %s. Tus %s necesitarán una visita extra" % (["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"][dia.weekday()], nombres),
                      "Unos 12 €, orientativo · Previsión de 38 °C", "#/reserva/%d" % a["id"])
            n += 1
    evento(c, None, "ola_calor_aviso", {"reservas_afectadas": n})
    return n

# ---------------------------------------------------------------- vistas JSON
def publico_cuidador(c, uid, anuncio=None):
    u = fila(c, "SELECT id,nombre,barrio,es_bot FROM usuarios WHERE id=?", uid)
    p = fila(c, "SELECT * FROM perfiles WHERE usuario_id=?", uid)
    u.update({k: p[k] for k in ("bio", "edad", "km", "del", "rating", "n_res", "n_serv", "franjas", "tarifa", "acepta_an", "acepta_pl", "acepta_ex", "verificado")})
    u["especies"] = [r["especie"] for r in filas(c, "SELECT especie FROM especies_cuidador WHERE cuidador_id=?", uid)]
    ins = [{"t": "Plantas", "aval": "Vivero socio"}]
    if p["del"]:
        ins.append({"t": "Plantas delicadas", "aval": "Vivero socio"})
    if p["acepta_an"] and p["acepta_pl"]:
        ins.append({"t": "Animales y plantas", "aval": "Vivero socio"})
    if p["acepta_ex"]:
        ins.append({"t": "Exóticos · reptiles y aves", "aval": "Veterinario de exóticos"})
    u["insignias"] = ins
    if anuncio:
        claves = especies_clave(anuncio["seres"])
        u["coinciden"] = [e for e in claves if e in u["especies"]]
        u["precio"] = round(anuncio["plan"]["total"] * (p["tarifa"] or 1))
    return u

def resumen_anuncio(c, a, para=None):
    a = dict(a)
    cands = filas(c, "SELECT * FROM candidaturas WHERE anuncio_id=? ORDER BY creado", a["id"])
    a["n_cands"] = len([k for k in cands if k["estado"] in ("enviada", "elegida")])
    a["dueno"] = fila(c, "SELECT id,nombre,barrio FROM usuarios WHERE id=?", a["dueno_id"])
    a["encuentro"] = fila(c, "SELECT * FROM encuentros WHERE anuncio_id=?", a["id"])
    if a["encuentro"]:
        a["encuentro"]["huecos"] = json.loads(a["encuentro"]["huecos"])
    if a.get("elegido_id"):
        a["elegido"] = publico_cuidador(c, a["elegido_id"], a)
    return a

def no_leidos(c, uid):
    n = fila(c, "SELECT COUNT(*) n FROM notificaciones WHERE usuario_id=? AND leida=0", uid)["n"]
    m = fila(c, """SELECT COUNT(DISTINCT m.candidatura_id) n FROM mensajes m JOIN candidaturas k ON k.id=m.candidatura_id
                   JOIN anuncios a ON a.id=k.anuncio_id
                   WHERE m.leido=0 AND m.sistema=0 AND m.autor_id<>? AND (k.cuidador_id=? OR a.dueno_id=?)""", uid, uid, uid)["n"]
    return {"notifs": n, "chats": m}

# ---------------------------------------------------------------- servidor HTTP
RUTAS = []

def ruta(metodo, patron, auth=True):
    rx = re.compile("^" + re.sub(r"<(\w+)>", r"(?P<\1>[^/]+)", patron) + "$")

    def deco(fn):
        RUTAS.append((metodo, rx, fn, auth))
        return fn
    return deco

class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "TSV-POC"

    def log_message(self, fmt, *args):
        if "/api/stream" not in self.path and "/api/test/estado" not in self.path:
            print("%s  %s" % (datetime.now().strftime("%H:%M:%S"), fmt % args))

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, data, ctype, extra=None):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.manejar("GET")

    def do_POST(self):
        self.manejar("POST")

    def manejar(self, metodo):
        url = urlparse(self.path)
        path = url.path
        self.qs = parse_qs(url.query)
        if path.startswith("/api/"):
            if path == "/api/stream":
                return self.stream()
            for m, rx, fn, auth in RUTAS:
                mt = rx.match(path)
                if m == metodo and mt:
                    c = conectar()
                    try:
                        body = {}
                        n = int(self.headers.get("Content-Length") or 0)
                        if n:
                            body = json.loads(self.rfile.read(n) or b"{}")
                        uid = None
                        tok = (self.headers.get("Authorization") or "").replace("Bearer ", "")
                        if tok:
                            s = fila(c, "SELECT usuario_id FROM sesiones WHERE token=?", tok)
                            uid = s["usuario_id"] if s else None
                        if auth and not uid:
                            return self.send_json({"error": "Tu sesión ha caducado. Vuelve a entrar.", "auth": False}, 401)
                        res = fn(self, c, uid, body, **mt.groupdict())
                        if isinstance(res, tuple):
                            return self.send_bytes(*res)
                        return self.send_json(res if res is not None else {"ok": True})
                    except ApiError as e:
                        return self.send_json({"error": e.msg}, e.code)
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        return self.send_json({"error": "Algo ha fallado en el servidor: %s" % e}, 500)
                    finally:
                        c.close()
            return self.send_json({"error": "No existe"}, 404)
        if path.startswith("/fotos/"):
            f = os.path.join(FOTOS, os.path.basename(path))
            if os.path.isfile(f):
                with open(f, "rb") as fh:
                    return self.send_bytes(fh.read(), "image/jpeg")
            return self.send_json({"error": "No existe"}, 404)
        if path == "/":
            path = "/index.html"
        f = os.path.normpath(os.path.join(PUBLIC, path.lstrip("/")))
        if not f.startswith(PUBLIC) or not os.path.isfile(f):
            return self.send_json({"error": "No existe"}, 404)
        ctype = mimetypes.guess_type(f)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",):
            ctype += "; charset=utf-8"
        with open(f, "rb") as fh:
            self.send_bytes(fh.read(), ctype)

    def stream(self):
        tok = (self.qs.get("token") or [""])[0]
        mod = (self.qs.get("mod") or [""])[0] == "1"
        c = conectar()
        s = fila(c, "SELECT usuario_id FROM sesiones WHERE token=?", tok)
        c.close()
        if not s and not mod:
            return self.send_json({"error": "sin sesión"}, 401)
        clave = "mod" if mod else s["usuario_id"]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = HUB.sub(clave)
        qt = HUB.sub("todos")
        try:
            self.wfile.write(b": hola\n\n")
            self.wfile.flush()
            while True:
                msg = None
                for qq in (q, qt):
                    try:
                        msg = qq.get_nowait()
                        break
                    except queue.Empty:
                        pass
                if msg is None:
                    try:
                        msg = q.get(timeout=0.5)
                    except queue.Empty:
                        msg = None
                if msg is None:
                    self._ping = getattr(self, "_ping", 0) + 1
                    if self._ping % 30 == 0:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                    continue
                self.wfile.write(("data: %s\n\n" % json.dumps(msg, ensure_ascii=False, default=str)).encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            HUB.unsub(clave, q)
            HUB.unsub("todos", qt)
        self.close_connection = True

# ---------------------------------------------------------------- API: cuenta
def nueva_sesion(c, uid):
    tok = secrets.token_urlsafe(24)
    c.execute("INSERT INTO sesiones VALUES(?,?,?)", (tok, uid, ahora()))
    return tok

@ruta("POST", "/api/entrar", auth=False)
def api_entrar(h, c, uid, b):
    u = fila(c, "SELECT * FROM usuarios WHERE correo=?", (b.get("correo") or "").strip().lower())
    if not u or hash_clave(b.get("clave") or "", u["sal"]) != u["hash"]:
        raise ApiError("El correo o la contraseña no coinciden")
    if u["es_bot"]:
        raise ApiError("Esta cuenta es un cuidador simulado y no se puede usar para entrar")
    evento(c, u["id"], "entrada", {})
    return {"token": nueva_sesion(c, u["id"])}

@ruta("POST", "/api/registro", auth=False)
def api_registro(h, c, uid, b):
    correo = (b.get("correo") or "").strip().lower()
    nombre = (b.get("nombre") or "").strip()
    cp = (b.get("cp") or "").strip()
    rol = b.get("rol")
    errores = {}
    if not nombre:
        errores["nombre"] = "Escribe tu nombre"
    if not re.match(r"^\S+@\S+\.\S+$", correo):
        errores["correo"] = "Escribe un correo válido, por ejemplo nombre@correo.com"
    if len(b.get("clave") or "") < 8:
        errores["clave"] = "La contraseña necesita al menos 8 caracteres"
    if not re.match(r"^28\d{3}$", cp):
        errores["cp"] = "Escribe un código postal de Madrid, por ejemplo 28004"
    if rol not in ("dueno", "cuidador"):
        errores["rol"] = "Elige qué quieres hacer"
    if fila(c, "SELECT 1 FROM usuarios WHERE correo=?", correo):
        errores["correo"] = "Ya hay una cuenta con este correo"
    if errores:
        return {"errores": errores}
    nid = crear_usuario(c, correo, nombre, (b.get("apellido") or "").strip(), cp, rol, clave=b["clave"])
    c.execute("INSERT INTO casas(usuario_id) VALUES(?)", (nid,))
    if rol == "cuidador":
        c.execute("INSERT INTO perfiles VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (nid, "", None, 1.0, 1, 1, 0, "", 0, 0, 0, None, 0, 0, "mt", 1.0, 1))
        if zona_activa(cp):
            c.execute("INSERT INTO zonas_cuidador VALUES(?,?)", (nid, cp))
        HUB.send("mod", {"type": "refresh"})
    evento(c, nid, "alta_completada", {"rol": rol, "zona_activa": zona_activa(cp)})
    return {"token": nueva_sesion(c, nid)}

@ruta("POST", "/api/salir")
def api_salir(h, c, uid, b):
    tok = (h.headers.get("Authorization") or "").replace("Bearer ", "")
    c.execute("DELETE FROM sesiones WHERE token=?", (tok,))

@ruta("GET", "/api/yo")
def api_yo(h, c, uid, b):
    u = fila(c, "SELECT id,nombre,apellido,correo,cp,barrio,rol FROM usuarios WHERE id=?", uid)
    u["zona_activa"] = zona_activa(u["cp"])
    u["zona_unica"] = ZONA_UNICA
    u["no_leidos"] = no_leidos(c, uid)
    u["seguro"] = cfg(c, "seguro")
    u["calor"] = cfg(c, "calor")
    if u["rol"] == "cuidador":
        u["perfil"] = publico_cuidador(c, uid)
        u["perfil"]["zonas"] = [r["cp"] for r in filas(c, "SELECT cp FROM zonas_cuidador WHERE cuidador_id=?", uid)]
        u["perfil"]["disponibilidad"] = filas(c, "SELECT * FROM disponibilidad WHERE cuidador_id=? ORDER BY inicio", uid)
        u["perfil"]["medicacion"] = fila(c, "SELECT medicacion FROM perfiles WHERE usuario_id=?", uid)["medicacion"]
    return u

@ruta("GET", "/api/catalogo", auth=False)
def api_catalogo(h, c, uid, b):
    return {"especies": filas(c, "SELECT * FROM especies ORDER BY cat DESC, nombre"), "zonas": ZONAS, "opcionales": OPCIONALES}

# ---------------------------------------------------------------- API: casa
@ruta("GET", "/api/casa")
def api_casa(h, c, uid, b):
    return {"casa": fila(c, "SELECT * FROM casas WHERE usuario_id=?", uid) or {}, "seres": seres_de_usuario(c, uid)}

@ruta("POST", "/api/casa")
def api_casa_guardar(h, c, uid, b):
    c.execute("INSERT OR IGNORE INTO casas(usuario_id) VALUES(?)", (uid,))
    c.execute("UPDATE casas SET direccion=?, acceso=?, instr_acceso=?, veterinario=?, emergencia=? WHERE usuario_id=?",
              (b.get("direccion", ""), b.get("acceso", ""), b.get("instr_acceso", ""), b.get("veterinario", ""), b.get("emergencia", ""), uid))
    evento(c, uid, "ficha_editada", {"campo": "casa"})

@ruta("POST", "/api/seres")
def api_ser_nuevo(h, c, uid, b):
    e = fila(c, "SELECT * FROM especies WHERE id=?", int(b.get("especie_id") or 0))
    if not e:
        raise ApiError("Elige una especie del catálogo")
    if not e["activa"]:
        evento(c, uid, "perro_rechazado", {})
        raise ApiError("De momento no cuidamos perros. Te avisaremos cuando empecemos.")
    nombre = (b.get("nombre") or "").strip() or e["nombre"]
    cant = max(1, min(99, int(b.get("cantidad") or 1)))
    c.execute("INSERT INTO seres(usuario_id,especie_id,nombre,cantidad,instr,alarma,medicacion) VALUES(?,?,?,?,?,?,?)",
              (uid, e["id"], nombre, cant, b.get("instr", ""), b.get("alarma", ""), 1 if b.get("medicacion") else 0))
    evento(c, uid, "ficha_editada", {"campo": "ser_vivo", "especie": e["nombre"]})

@ruta("POST", "/api/seres/borrar")
def api_ser_borrar(h, c, uid, b):
    if fila(c, """SELECT 1 FROM anuncio_seres x JOIN anuncios a ON a.id=x.anuncio_id WHERE x.ser_id=?
                  AND a.estado IN ('abierto','asignado','reservado','en_curso')""", int(b.get("id") or 0)):
        raise ApiError("Está incluido en un anuncio activo. Cancélalo antes de quitarlo.")
    c.execute("DELETE FROM seres WHERE id=? AND usuario_id=?", (int(b.get("id") or 0), uid))

# ---------------------------------------------------------------- API: anuncios (dueño)
@ruta("POST", "/api/idoneos")
def api_idoneos(h, c, uid, b):
    u = fila(c, "SELECT cp FROM usuarios WHERE id=?", uid)
    ids = [int(x) for x in b.get("seres", [])]
    seres = [s for s in seres_de_usuario(c, uid) if s["id"] in ids]
    try:
        pd(b["inicio"]); pd(b["fin"])
        valid = pd(b["fin"]) > pd(b["inicio"])
    except Exception:
        valid = False
    if not seres or not valid:
        return {"n": 0, "plan": calcular_plan(seres or [], b.get("inicio") or hoy().isoformat(), b.get("fin") or (hoy() + timedelta(days=1)).isoformat(), False) if valid else None, "sugerencia": None, "nuevos": 0}
    opt = {k: bool(v) for k, v in (b.get("opt") or {}).items() if k in OPCIONALES}
    lista = idoneos(c, u["cp"], b["inicio"], b["fin"], seres, b.get("franja", "t"), opt, uid)
    return {"n": len(lista), "plan": calcular_plan(seres, b["inicio"], b["fin"], bool(b.get("habitada"))),
            "sugerencia": sugerencia(c, u["cp"], b["inicio"], b["fin"], seres, b.get("franja", "t"), opt, uid) if not lista else None,
            "nuevos": sum(1 for p in lista if (p["n_serv"] or 0) <= 2), "claves": especies_clave(seres)}

@ruta("POST", "/api/anuncios")
def api_publicar(h, c, uid, b):
    return {"id": publicar(c, uid, b)}

@ruta("GET", "/api/anuncios/mios")
def api_mis_anuncios(h, c, uid, b):
    return [resumen_anuncio(c, anuncio_completo(c, a["id"])) for a in filas(c, "SELECT id FROM anuncios WHERE dueno_id=? ORDER BY creado DESC", uid)]

@ruta("GET", "/api/anuncio/<aid>")
def api_anuncio(h, c, uid, b, aid):
    a = anuncio_completo(c, int(aid))
    if a["dueno_id"] == uid:
        a = resumen_anuncio(c, a)
        cands = []
        for k in filas(c, "SELECT * FROM candidaturas WHERE anuncio_id=? ORDER BY creado", a["id"]):
            k["cuidador"] = publico_cuidador(c, k["cuidador_id"], a)
            k["no_leidos"] = fila(c, "SELECT COUNT(*) n FROM mensajes WHERE candidatura_id=? AND leido=0 AND autor_id<>? AND sistema=0", k["id"], uid)["n"]
            cands.append(k)
        a["candidaturas"] = cands
        if a["estado"] == "abierto":
            a["idoneos_ahora"] = len(idoneos(c, a["cp"], a["inicio"], a["fin"], a["seres"], a["franja"], a["opt"], uid))
        return a
    # vista del cuidador: solo barrio, nunca la dirección (CASA-03)
    aviso = fila(c, "SELECT * FROM avisos WHERE anuncio_id=? AND cuidador_id=?", a["id"], uid)
    k = fila(c, "SELECT * FROM candidaturas WHERE anuncio_id=? AND cuidador_id=?", a["id"], uid)
    if not aviso and not k:
        raise ApiError("No tienes acceso a esta solicitud", 403)
    if aviso and not aviso["visto"]:
        c.execute("UPDATE avisos SET visto=1 WHERE anuncio_id=? AND cuidador_id=?", (a["id"], uid))
        evento(c, uid, "aviso_visto", {"anuncio": a["id"]})
    p = fila(c, "SELECT tarifa FROM perfiles WHERE usuario_id=?", uid)
    total = round(a["plan"]["total"] * (p["tarifa"] or 1))
    out = resumen_anuncio(c, a)
    out.pop("elegido", None)
    out["candidatura"] = k
    out["cobras"] = round(total * (1 - COMISION), 2)
    out["total_cuidador"] = total
    out["disponible"] = a["estado"] == "abierto" or (k and k["estado"] == "elegida")
    out["km"] = fila(c, "SELECT km FROM perfiles WHERE usuario_id=?", uid)["km"]
    return out

@ruta("POST", "/api/anuncio/<aid>/cancelar")
def api_cancelar(h, c, uid, b, aid):
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", int(aid))
    if not a or a["dueno_id"] != uid or a["estado"] not in ("abierto", "asignado"):
        raise ApiError("Este anuncio no se puede cancelar sin coste")
    c.execute("UPDATE anuncios SET estado='cancelado' WHERE id=?", (a["id"],))
    for k in filas(c, "SELECT * FROM candidaturas WHERE anuncio_id=? AND estado IN ('enviada','elegida')", a["id"]):
        c.execute("UPDATE candidaturas SET estado='cerrada' WHERE id=?", (k["id"],))
        notificar(c, k["cuidador_id"], "cancelado", "Esta solicitud ya no está disponible", "La dueña la ha cancelado", "#/servicios")
    for av in filas(c, "SELECT cuidador_id FROM avisos WHERE anuncio_id=?", a["id"]):
        avisar_cambio(av["cuidador_id"])
    evento(c, uid, "reserva_cancelada", {"anuncio": a["id"], "quien": "dueno", "fase": a["estado"]})

@ruta("POST", "/api/anuncio/<aid>/precision")
def api_relajar(h, c, uid, b, aid):
    a = anuncio_completo(c, int(aid))
    if a["dueno_id"] != uid or a["estado"] != "abierto":
        raise ApiError("Solo puedes ajustar un anuncio abierto")
    opt = {k: bool(v) for k, v in (b.get("opt") or {}).items() if k in OPCIONALES}
    c.execute("UPDATE anuncios SET opt=?, sin_respuesta=0 WHERE id=?", (json.dumps(opt), a["id"]))
    a = anuncio_completo(c, a["id"])
    tanda = enviar_avisos(c, a)
    evento(c, uid, "precision_relajada", {"anuncio": a["id"], "precision": [k for k, v in opt.items() if v], "nuevos_avisos": len(tanda)})
    return {"nuevos": len(tanda)}

@ruta("POST", "/api/elegir")
def api_elegir(h, c, uid, b):
    elegir(c, uid, int(b.get("cand")), b.get("huecos") or [])

# ---------------------------------------------------------------- API: cuidador
@ruta("GET", "/api/solicitudes")
def api_solicitudes(h, c, uid, b):
    out = []
    for av in filas(c, "SELECT * FROM avisos WHERE cuidador_id=? ORDER BY enviado DESC", uid):
        a = anuncio_completo(c, av["anuncio_id"])
        k = fila(c, "SELECT * FROM candidaturas WHERE anuncio_id=? AND cuidador_id=?", a["id"], uid)
        p = fila(c, "SELECT tarifa FROM perfiles WHERE usuario_id=?", uid)
        total = round(a["plan"]["total"] * (p["tarifa"] or 1))
        out.append({"id": a["id"], "estado": a["estado"], "inicio": a["inicio"], "fin": a["fin"], "barrio": a["barrio"],
                    "servicio": a["plan"]["servicio"], "visitas": a["plan"]["visitas"], "seres": [{"nombre": s["nombre"], "cat": s["cat"], "cantidad": s["cantidad"], "especie": s["especie"]} for s in a["seres"]],
                    "dueno": fila(c, "SELECT nombre FROM usuarios WHERE id=?", a["dueno_id"])["nombre"], "visto": av["visto"], "enviado": av["enviado"],
                    "candidatura": k, "cobras": round(total * (1 - COMISION), 2), "total": total, "urgente": a["urgente"],
                    "elegido_yo": a["elegido_id"] == uid})
    return out

@ruta("POST", "/api/candidaturas")
def api_candidatura(h, c, uid, b):
    return {"id": presentar(c, int(b.get("anuncio")), uid, (b.get("mensaje") or "")[:600])}

@ruta("POST", "/api/candidaturas/<kid>/retirar")
def api_retirar(h, c, uid, b, kid):
    k = fila(c, "SELECT * FROM candidaturas WHERE id=? AND cuidador_id=?", int(kid), uid)
    if not k or k["estado"] != "enviada":
        raise ApiError("No puedes retirar esta candidatura")
    c.execute("UPDATE candidaturas SET estado='retirada' WHERE id=?", (k["id"],))
    mensaje(c, k["id"], uid, "Ha retirado su candidatura.", sistema=True)
    a = fila(c, "SELECT dueno_id FROM anuncios WHERE id=?", k["anuncio_id"])
    avisar_cambio(a["dueno_id"])
    evento(c, uid, "candidatura_retirada", {"anuncio": k["anuncio_id"]})

@ruta("GET", "/api/servicios")
def api_servicios(h, c, uid, b):
    out = []
    for k in filas(c, "SELECT * FROM candidaturas WHERE cuidador_id=? ORDER BY creado DESC", uid):
        a = anuncio_completo(c, k["anuncio_id"])
        out.append({"cand": k, "anuncio": {"id": a["id"], "estado": a["estado"], "inicio": a["inicio"], "fin": a["fin"], "barrio": a["barrio"],
                    "servicio": a["plan"]["servicio"], "seres": [{"nombre": s["nombre"], "cat": s["cat"], "cantidad": s["cantidad"]} for s in a["seres"]],
                    "dueno": fila(c, "SELECT nombre FROM usuarios WHERE id=?", a["dueno_id"])["nombre"], "elegido_yo": a["elegido_id"] == uid}})
    return out

@ruta("POST", "/api/perfil")
def api_perfil(h, c, uid, b):
    u = fila(c, "SELECT rol FROM usuarios WHERE id=?", uid)
    if u["rol"] != "cuidador":
        raise ApiError("Solo para cuidadores", 403)
    c.execute("UPDATE perfiles SET bio=?, acepta_an=?, acepta_pl=?, franjas=?, medicacion=? WHERE usuario_id=?",
              ((b.get("bio") or "")[:400], 1 if b.get("acepta_an") else 0, 1 if b.get("acepta_pl") else 0,
               "".join(f for f in "mtn" if f in (b.get("franjas") or "")) or "t", 1 if b.get("medicacion") else 0, uid))
    if "zonas" in b:
        c.execute("DELETE FROM zonas_cuidador WHERE cuidador_id=?", (uid,))
        for z in b["zonas"]:
            if z in ZONAS:
                c.execute("INSERT INTO zonas_cuidador VALUES(?,?)", (uid, z))
    if "especies" in b:
        c.execute("DELETE FROM especies_cuidador WHERE cuidador_id=?", (uid,))
        for e in b["especies"]:
            c.execute("INSERT INTO especies_cuidador VALUES(?,?)", (uid, e))
    evento(c, uid, "perfil_editado", {})
    return {"nuevos_avisos": avisos_por_disponibilidad(c, uid)}

@ruta("POST", "/api/disponibilidad")
def api_dispo(h, c, uid, b):
    if b.get("borrar"):
        c.execute("DELETE FROM disponibilidad WHERE id=? AND cuidador_id=?", (int(b["borrar"]), uid))
        return {"nuevos_avisos": 0}
    try:
        i, f = pd(b["inicio"]), pd(b["fin"])
    except Exception:
        raise ApiError("Revisa las fechas")
    if f < i:
        raise ApiError("La fecha final tiene que ser posterior")
    c.execute("INSERT INTO disponibilidad(cuidador_id,inicio,fin) VALUES(?,?,?)", (uid, i.isoformat(), f.isoformat()))
    evento(c, uid, "disponibilidad_marcada", {"dias": (f - i).days + 1})
    return {"nuevos_avisos": avisos_por_disponibilidad(c, uid)}

def avisos_por_disponibilidad(c, uid):
    """Arquitectura §5: al ampliar disponibilidad o perfil, avisar de anuncios abiertos que ahora encajan."""
    n = 0
    for a in filas(c, "SELECT id FROM anuncios WHERE estado='abierto'"):
        if fila(c, "SELECT 1 FROM avisos WHERE anuncio_id=? AND cuidador_id=?", a["id"], uid):
            continue
        a = anuncio_completo(c, a["id"])
        if any(p["usuario_id"] == uid for p in idoneos(c, a["cp"], a["inicio"], a["fin"], a["seres"], a["franja"], a["opt"], a["dueno_id"])):
            c.execute("INSERT INTO avisos(anuncio_id,cuidador_id,enviado) VALUES(?,?,?)", (a["id"], uid, ahora()))
            c.execute("UPDATE anuncios SET avisados=avisados+1 WHERE id=?", (a["id"],))
            du = fila(c, "SELECT nombre FROM usuarios WHERE id=?", a["dueno_id"])["nombre"]
            notificar(c, uid, "solicitud", "Nueva solicitud en %s" % a["barrio"], "%s · %s – %s" % (du, fmt_d(a["inicio"]), fmt_d(a["fin"])), "#/solicitud/%d" % a["id"], a["dueno_id"])
            n += 1
    return n

# ---------------------------------------------------------------- API: chat
@ruta("GET", "/api/chats")
def api_chats(h, c, uid, b):
    out = []
    for k in filas(c, """SELECT k.* FROM candidaturas k JOIN anuncios a ON a.id=k.anuncio_id
                         WHERE (k.cuidador_id=? OR a.dueno_id=?) ORDER BY k.creado DESC""", uid, uid):
        a = fila(c, "SELECT * FROM anuncios WHERE id=?", k["anuncio_id"])
        otro = k["cuidador_id"] if a["dueno_id"] == uid else a["dueno_id"]
        ult = fila(c, "SELECT * FROM mensajes WHERE candidatura_id=? ORDER BY id DESC LIMIT 1", k["id"])
        nl = fila(c, "SELECT COUNT(*) n FROM mensajes WHERE candidatura_id=? AND leido=0 AND sistema=0 AND autor_id<>?", k["id"], uid)["n"]
        out.append({"id": k["id"], "estado": k["estado"], "anuncio_id": a["id"], "anuncio_estado": a["estado"],
                    "otro": fila(c, "SELECT id,nombre,barrio,rol FROM usuarios WHERE id=?", otro), "ultimo": ult, "no_leidos": nl,
                    "ts": ult["creado"] if ult else k["creado"]})
    out.sort(key=lambda x: -x["ts"])
    return out

@ruta("GET", "/api/chat/<kid>")
def api_chat(h, c, uid, b, kid):
    k, a = cand_info(c, int(kid))
    if not puede_ver_chat(uid, k, a):
        raise ApiError("No tienes acceso a esta conversación", 403)
    c.execute("UPDATE mensajes SET leido=1 WHERE candidatura_id=? AND autor_id<>? AND leido=0", (k["id"], uid))
    c.execute("UPDATE notificaciones SET leida=1 WHERE usuario_id=? AND enlace=?", (uid, "#/mensajes/%d" % k["id"]))
    soy_dueno = a["dueno_id"] == uid
    otro = k["cuidador_id"] if soy_dueno else a["dueno_id"]
    out = {"cand": k, "anuncio": {"id": a["id"], "estado": a["estado"], "inicio": a["inicio"], "fin": a["fin"], "elegido_id": a["elegido_id"]},
           "mensajes": filas(c, "SELECT * FROM mensajes WHERE candidatura_id=? ORDER BY id", k["id"]), "yo": uid, "soy_dueno": soy_dueno,
           "contacto_visible": contacto_visible(a)}
    out["otro"] = publico_cuidador(c, otro, anuncio_completo(c, a["id"])) if soy_dueno else fila(c, "SELECT id,nombre,barrio FROM usuarios WHERE id=?", otro)
    return out

@ruta("POST", "/api/chat/<kid>")
def api_chat_enviar(h, c, uid, b, kid):
    k, a = cand_info(c, int(kid))
    if not puede_ver_chat(uid, k, a):
        raise ApiError("No tienes acceso a esta conversación", 403)
    texto = (b.get("texto") or "").strip()[:1000]
    if not texto:
        raise ApiError("Escribe un mensaje")
    if k["estado"] in ("descartada", "cerrada", "retirada") and a["estado"] not in ("reservado", "en_curso", "completado"):
        raise ApiError("Esta conversación está cerrada")
    m = mensaje(c, k["id"], uid, texto)
    otro = k["cuidador_id"] if a["dueno_id"] == uid else a["dueno_id"]
    yo = fila(c, "SELECT nombre FROM usuarios WHERE id=?", uid)["nombre"]
    ob = fila(c, "SELECT es_bot FROM usuarios WHERE id=?", otro)
    evento(c, uid, "mensaje_enviado", {"cand": k["id"], "oculto": bool(m["oculto"]), "largo": len(texto)})
    if ob["es_bot"]:
        HUB.send(uid, {"type": "typing", "cand": k["id"]})
        luego(3.2, robot_responder, k["id"], texto)
    else:
        notificar(c, otro, "mensaje", "%s te ha escrito" % yo, m["texto"][:60] + ("…" if len(m["texto"]) > 60 else ""), "#/mensajes/%d" % k["id"], uid)
    return m

@ruta("POST", "/api/escribiendo")
def api_typing(h, c, uid, b):
    k, a = cand_info(c, int(b.get("cand")))
    if puede_ver_chat(uid, k, a):
        otro = k["cuidador_id"] if a["dueno_id"] == uid else a["dueno_id"]
        HUB.send(otro, {"type": "typing", "cand": k["id"]})

# ---------------------------------------------------------------- API: encuentro, reserva y visitas
def anuncio_de_parte(c, uid, aid):
    a = anuncio_completo(c, int(aid))
    if uid not in (a["dueno_id"], a["elegido_id"]):
        raise ApiError("No tienes acceso a esta reserva", 403)
    return a

@ruta("GET", "/api/reserva/<aid>")
def api_reserva(h, c, uid, b, aid):
    a = anuncio_de_parte(c, uid, aid)
    soy_dueno = a["dueno_id"] == uid
    out = resumen_anuncio(c, a)
    out["soy_dueno"] = soy_dueno
    out["cand"] = fila(c, "SELECT * FROM candidaturas WHERE anuncio_id=? AND cuidador_id=?", a["id"], a["elegido_id"])
    visitas = filas(c, "SELECT * FROM visitas WHERE anuncio_id=? ORDER BY dia, extra", a["id"])
    for v in visitas:
        v["tareas"] = json.loads(v["tareas"])
        v["fotos"] = filas(c, "SELECT * FROM fotos WHERE visita_id=?", v["id"])
        v["resumen"] = resumen_tareas(v["tareas"])
    out["visitas"] = visitas
    out["extras"] = filas(c, "SELECT * FROM extras WHERE anuncio_id=? ORDER BY id DESC", a["id"])
    out["calor"] = cfg(c, "calor")
    out["calor_sens"] = [s["nombre"] for s in a["seres"] if s["calor"] >= 0.8]
    out["seguro"] = cfg(c, "seguro")
    if not soy_dueno and a["estado"] in ("reservado", "en_curso"):
        out["casa"] = fila(c, "SELECT * FROM casas WHERE usuario_id=?", a["dueno_id"])
        evento(c, uid, "acceso_dato_sensible", {"anuncio": a["id"], "dato": "direccion"})
    elif soy_dueno:
        out["casa"] = fila(c, "SELECT * FROM casas WHERE usuario_id=?", uid)
    res = filas(c, "SELECT * FROM resenas WHERE anuncio_id=?", a["id"])
    mia = [r for r in res if r["autor_id"] == uid]
    otra = [r for r in res if r["autor_id"] != uid]
    out["resena_mia"] = mia[0] if mia else None
    out["resena_otra"] = otra[0] if (otra and mia) else None
    out["resena_otra_existe"] = bool(otra)
    out["confianza"] = bool(fila(c, "SELECT 1 FROM confianza WHERE dueno_id=? AND cuidador_id=?", a["dueno_id"], a["elegido_id"])) if a["elegido_id"] else False
    p = fila(c, "SELECT tarifa FROM perfiles WHERE usuario_id=?", a["elegido_id"]) if a["elegido_id"] else None
    if p:
        total = round(a["plan"]["total"] * (p["tarifa"] or 1))
        out["total_cuidador"] = total
        out["cobras"] = round(total * (1 - COMISION), 2)
    return out

@ruta("POST", "/api/encuentro/<aid>/hueco")
def api_hueco(h, c, uid, b, aid):
    a = anuncio_de_parte(c, uid, aid)
    if a["elegido_id"] != uid:
        raise ApiError("Solo la persona elegida elige el hueco", 403)
    elegir_hueco(c, a["id"], int(b.get("ts")))

@ruta("POST", "/api/encuentro/<aid>/seguimos")
def api_seguimos(h, c, uid, b, aid):
    a = anuncio_de_parte(c, uid, aid)
    seguimos(c, a["id"], "dueno" if a["dueno_id"] == uid else "cuidador", bool(b.get("si")))

@ruta("POST", "/api/visita/<aid>/llegada")
def api_llegada(h, c, uid, b, aid):
    return {"id": llegada(c, uid, int(aid), int(b.get("dia", 0)), bool(b.get("extra")))}

@ruta("POST", "/api/visita/<vid>/tareas")
def api_tareas(h, c, uid, b, vid):
    v = fila(c, "SELECT * FROM visitas WHERE id=?", int(vid))
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", v["anuncio_id"]) if v else None
    if not v or a["elegido_id"] != uid or v["salida"]:
        raise ApiError("No puedes editar esta visita", 403)
    tareas = json.loads(v["tareas"])
    cambios = {int(t["ser_id"]): t for t in b.get("tareas", [])}
    for t in tareas:
        if t["ser_id"] in cambios:
            t["estado"] = cambios[t["ser_id"]].get("estado")
            t["motivo"] = (cambios[t["ser_id"]].get("motivo") or "")[:200]
    c.execute("UPDATE visitas SET tareas=? WHERE id=?", (json.dumps(tareas, ensure_ascii=False), v["id"]))

@ruta("POST", "/api/visita/<vid>/foto")
def api_foto(h, c, uid, b, vid):
    v = fila(c, "SELECT * FROM visitas WHERE id=?", int(vid))
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", v["anuncio_id"]) if v else None
    if not v or a["elegido_id"] != uid or v["salida"]:
        raise ApiError("No puedes añadir fotos a esta visita", 403)
    if fila(c, "SELECT COUNT(*) n FROM fotos WHERE visita_id=?", v["id"])["n"] >= 10:
        raise ApiError("Máximo 10 fotos por visita")
    data = b.get("data") or ""
    if not data.startswith("data:image/jpeg;base64,"):
        raise ApiError("Formato de foto no válido")
    raw = base64.b64decode(data.split(",", 1)[1])
    if len(raw) > 3_000_000:
        raise ApiError("La foto es demasiado grande")
    nombre = "v%d-%s.jpg" % (v["id"], secrets.token_hex(6))
    with open(os.path.join(FOTOS, nombre), "wb") as fh:
        fh.write(raw)
    c.execute("INSERT INTO fotos(visita_id,archivo) VALUES(?,?)", (v["id"], nombre))
    evento(c, uid, "foto_subida", {"visita": v["id"], "kb": len(raw) // 1024})
    return {"archivo": nombre}

@ruta("POST", "/api/visita/<vid>/foto/borrar")
def api_foto_borrar(h, c, uid, b, vid):
    v = fila(c, "SELECT * FROM visitas WHERE id=?", int(vid))
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", v["anuncio_id"]) if v else None
    if not v or a["elegido_id"] != uid or v["salida"]:
        raise ApiError("No puedes quitar fotos de esta visita", 403)
    c.execute("DELETE FROM fotos WHERE id=? AND visita_id=?", (int(b.get("id") or 0), v["id"]))

@ruta("POST", "/api/visita/<vid>/salida")
def api_salida(h, c, uid, b, vid):
    salida(c, uid, int(vid), (b.get("nota") or "")[:400])

@ruta("POST", "/api/reserva/<aid>/cancelar")
def api_cancelar_cuidador(h, c, uid, b, aid):
    cancelar_cuidador(c, uid, int(aid))

@ruta("POST", "/api/reserva/<aid>/terminar")
def api_terminar(h, c, uid, b, aid):
    a = anuncio_de_parte(c, uid, aid)
    if a["estado"] not in ("reservado", "en_curso"):
        raise ApiError("Esta reserva no está en curso")
    completar(c, a["id"])

@ruta("POST", "/api/extra/<aid>")
def api_pedir_extra(h, c, uid, b, aid):
    pedir_extra(c, uid, int(aid))

@ruta("POST", "/api/extra/<xid>/responder")
def api_resp_extra(h, c, uid, b, xid):
    x = fila(c, "SELECT * FROM extras WHERE id=?", int(xid))
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", x["anuncio_id"]) if x else None
    if not x or a["elegido_id"] != uid:
        raise ApiError("No puedes responder a esta petición", 403)
    aceptar_extra(c, x["id"], bool(b.get("si")))

@ruta("POST", "/api/resena")
def api_resena(h, c, uid, b):
    a = anuncio_de_parte(c, uid, int(b.get("anuncio")))
    if a["estado"] != "completado":
        raise ApiError("Solo se puede valorar un servicio terminado")
    if fila(c, "SELECT 1 FROM resenas WHERE anuncio_id=? AND autor_id=?", a["id"], uid):
        raise ApiError("Ya has valorado este servicio")
    puntos = int(b.get("puntos") or 0)
    if not 1 <= puntos <= 5:
        raise ApiError("Elige de 1 a 5 estrellas")
    destino = a["elegido_id"] if uid == a["dueno_id"] else a["dueno_id"]
    c.execute("INSERT INTO resenas(anuncio_id,autor_id,destino_id,puntos,texto,aspecto,creada) VALUES(?,?,?,?,?,?,?)",
              (a["id"], uid, destino, puntos, (b.get("texto") or "")[:600], b.get("aspecto") or "", ahora()))
    if uid == a["dueno_id"] and b.get("confianza"):
        c.execute("INSERT INTO confianza VALUES(?,?)", (uid, a["elegido_id"]))
        evento(c, uid, "cuidador_confianza_marcado", {"cuidador": a["elegido_id"]})
    yo = fila(c, "SELECT nombre FROM usuarios WHERE id=?", uid)["nombre"]
    if fila(c, "SELECT COUNT(*) n FROM resenas WHERE anuncio_id=?", a["id"])["n"] == 2:
        for x in (a["dueno_id"], a["elegido_id"]):
            notificar(c, x, "resena", "Ya podéis ver vuestras reseñas", "Se publican cuando escribís los dos", "#/reserva/%d" % a["id"])
    else:
        notificar(c, destino, "resena", "%s ya ha valorado el servicio" % yo, "La verás cuando escribas la tuya", "#/reserva/%d" % a["id"], uid)
        if fila(c, "SELECT es_bot FROM usuarios WHERE id=?", destino)["es_bot"]:
            luego(4, robot_resena, a["id"], destino)
    evento(c, uid, "resena_publicada", {"anuncio": a["id"], "puntos": puntos, "aspecto": b.get("aspecto")})

def robot_resena(c, aid, bot_id):
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", aid)
    if fila(c, "SELECT 1 FROM resenas WHERE anuncio_id=? AND autor_id=?", aid, bot_id):
        return
    c.execute("INSERT INTO resenas(anuncio_id,autor_id,destino_id,puntos,texto,aspecto,creada) VALUES(?,?,?,?,?,?,?)",
              (aid, bot_id, a["dueno_id"], 5, "Casa muy bien explicada y todo a punto. ¡Repetiría!", "Instrucciones claras", ahora()))
    for x in (a["dueno_id"], bot_id):
        notificar(c, x, "resena", "Ya podéis ver vuestras reseñas", "Se publican cuando escribís los dos", "#/reserva/%d" % aid)

# ---------------------------------------------------------------- API: avisos y analítica
@ruta("GET", "/api/notifs")
def api_notifs(h, c, uid, b):
    return filas(c, "SELECT * FROM notificaciones WHERE usuario_id=? ORDER BY id DESC LIMIT 60", uid)

@ruta("POST", "/api/notifs/leidas")
def api_notifs_leidas(h, c, uid, b):
    if b.get("id"):
        c.execute("UPDATE notificaciones SET leida=1 WHERE id=? AND usuario_id=?", (int(b["id"]), uid))
    else:
        c.execute("UPDATE notificaciones SET leida=1 WHERE usuario_id=?", (uid,))

@ruta("POST", "/api/ev", auth=False)
def api_ev(h, c, uid, b):
    evento(c, uid, "ui_" + re.sub(r"[^a-z0-9_]", "", (b.get("nombre") or "")[:40]), b.get("datos") or {})

@ruta("POST", "/api/seq")
def api_seq(h, c, uid, b):
    c.execute("INSERT INTO respuestas(ts,sesion,participante,usuario_id,tarea,seq,esperaba) VALUES(?,?,?,?,?,?,?)",
              (ahora(), cfg(c, "sesion", ""), cfg(c, "participante", ""), uid, b.get("tarea", ""), int(b.get("seq") or 0), (b.get("esperaba") or "")[:600]))
    evento(c, uid, "seq_respondida", {"tarea": b.get("tarea"), "seq": b.get("seq")})

# ---------------------------------------------------------------- API: sala de test (moderación)
@ruta("GET", "/api/test/estado", auth=False)
def api_test_estado(h, c, uid, b):
    usuarios = filas(c, """SELECT u.id,u.nombre,u.correo,u.rol,u.es_bot,u.cp,u.barrio,p.verificado FROM usuarios u
                           LEFT JOIN perfiles p ON p.usuario_id=u.id ORDER BY u.es_bot, u.rol, u.id""")
    anuncios = []
    for a in filas(c, "SELECT id FROM anuncios ORDER BY id DESC"):
        a = anuncio_completo(c, a["id"])
        ya = {r["cuidador_id"] for r in filas(c, "SELECT cuidador_id FROM candidaturas WHERE anuncio_id=?", a["id"])}
        avisados = filas(c, "SELECT u.id,u.nombre,u.es_bot FROM avisos v JOIN usuarios u ON u.id=v.cuidador_id WHERE v.anuncio_id=?", a["id"])
        anuncios.append({"id": a["id"], "dueno": fila(c, "SELECT nombre FROM usuarios WHERE id=?", a["dueno_id"])["nombre"], "estado": a["estado"],
                         "inicio": a["inicio"], "fin": a["fin"], "elegido": (fila(c, "SELECT nombre FROM usuarios WHERE id=?", a["elegido_id"]) or {}).get("nombre"),
                         "bots_disponibles": [x for x in avisados if x["id"] not in ya],
                         "visitas_pend": len([d for d in a["plan"].get("dias_visita", []) if not fila(c, "SELECT 1 FROM visitas WHERE anuncio_id=? AND dia=? AND extra=0 AND salida IS NOT NULL", a["id"], d)])})
    return {"usuarios": usuarios, "anuncios": anuncios, "config": {r["k"]: r["v"] for r in filas(c, "SELECT * FROM config")},
            "eventos": filas(c, "SELECT * FROM eventos ORDER BY id DESC LIMIT 80"),
            "respuestas": filas(c, "SELECT * FROM respuestas ORDER BY id DESC LIMIT 40")}

@ruta("POST", "/api/test/entrar", auth=False)
def api_test_entrar(h, c, uid, b):
    u = fila(c, "SELECT * FROM usuarios WHERE correo=? AND es_bot=0", (b.get("correo") or "").lower())
    if not u:
        raise ApiError("Esa cuenta de prueba no existe")
    evento(c, u["id"], "entrada", {"rapida": True})
    return {"token": nueva_sesion(c, u["id"])}

@ruta("POST", "/api/test/escenario", auth=False)
def api_test_escenario(h, c, uid, b):
    nombre = b.get("nombre") or "limpio"
    if nombre not in ("limpio", "candidaturas", "elegida", "reserva", "calor", "fin"):
        raise ApiError("Escenario desconocido")
    c.close()
    escenario(nombre)

@ruta("POST", "/api/test/sesion", auth=False)
def api_test_sesion(h, c, uid, b):
    sid = datetime.now().strftime("%Y%m%d-%H%M")
    set_cfg(c, "sesion", sid if b.get("participante") else "")
    set_cfg(c, "participante", (b.get("participante") or "")[:60])
    evento(c, None, "sesion_inicio" if b.get("participante") else "sesion_fin", {"participante": b.get("participante"), "rol": b.get("rol")})
    return {"sesion": sid}

@ruta("POST", "/api/test/tarea", auth=False)
def api_test_tarea(h, c, uid, b):
    evento(c, None, "tarea_" + ("inicio" if b.get("accion") == "inicio" else "fin"),
           {"tarea": b.get("tarea"), "rol": b.get("rol"), "segundos": b.get("segundos"), "resultado": b.get("resultado")})

@ruta("POST", "/api/test/pedir-seq", auth=False)
def api_test_pedir_seq(h, c, uid, b):
    u = fila(c, "SELECT id FROM usuarios WHERE correo=?", (b.get("correo") or "").lower())
    if not u:
        raise ApiError("No hay nadie con esa cuenta")
    HUB.send(u["id"], {"type": "seq", "tarea": b.get("tarea"), "titulo": b.get("titulo")})

@ruta("POST", "/api/test/robot", auth=False)
def api_test_robot(h, c, uid, b):
    robot_presentarse(c, int(b["anuncio"]), int(b["bot"]))

@ruta("POST", "/api/test/sin-respuesta", auth=False)
def api_test_sin_respuesta(h, c, uid, b):
    a = fila(c, "SELECT * FROM anuncios WHERE id=?", int(b["anuncio"]))
    if not a or a["estado"] != "abierto":
        raise ApiError("El anuncio tiene que estar abierto")
    c.execute("UPDATE anuncios SET sin_respuesta=1 WHERE id=?", (a["id"],))
    notificar(c, a["dueno_id"], "sin_respuesta", "Aún nadie se ha presentado a tu anuncio",
              "¿Quieres quitar algún requisito para avisar a más cuidadores?", "#/anuncio/%d" % a["id"])
    evento(c, None, "simulado_sin_respuesta", {"anuncio": a["id"]})

@ruta("POST", "/api/test/calor", auth=False)
def api_test_calor(h, c, uid, b):
    return {"afectadas": ola_de_calor(c)}

@ruta("POST", "/api/test/visita", auth=False)
def api_test_visita(h, c, uid, b):
    visita_ejemplo(c, int(b["anuncio"]))

@ruta("POST", "/api/test/verificar", auth=False)
def api_test_verificar(h, c, uid, b):
    c.execute("UPDATE perfiles SET verificado=1 WHERE usuario_id=?", (int(b["usuario"]),))
    notificar(c, int(b["usuario"]), "verificado", "Tu identidad está verificada", "Ya puedes recibir avisos de solicitudes", "#/perfil")
    evento(c, int(b["usuario"]), "cuidador_verificado", {})
    avisos_por_disponibilidad(c, int(b["usuario"]))

@ruta("POST", "/api/test/config", auth=False)
def api_test_config(h, c, uid, b):
    if b.get("k") in ("robots_auto", "seguro"):
        set_cfg(c, b["k"], b.get("v", ""))

@ruta("GET", "/api/test/eventos.csv", auth=False)
def api_test_csv(h, c, uid, b):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "hora", "sesion", "usuario_id", "rol", "evento", "datos"])
    for e in filas(c, "SELECT * FROM eventos ORDER BY id"):
        w.writerow([e["id"], datetime.fromtimestamp(e["ts"] / 1000).strftime("%Y-%m-%d %H:%M:%S"), e["sesion"], e["usuario_id"], e["rol"], e["nombre"], e["datos"]])
    return (("﻿" + buf.getvalue()).encode(), "text/csv; charset=utf-8", {"Content-Disposition": "attachment; filename=eventos-test.csv"})

@ruta("GET", "/api/test/respuestas.csv", auth=False)
def api_test_csv2(h, c, uid, b):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["hora", "sesion", "participante", "usuario_id", "tarea", "facilidad_1a7", "que_esperaba"])
    for r in filas(c, "SELECT * FROM respuestas ORDER BY id"):
        w.writerow([datetime.fromtimestamp(r["ts"] / 1000).strftime("%Y-%m-%d %H:%M:%S"), r["sesion"], r["participante"], r["usuario_id"], r["tarea"], r["seq"], r["esperaba"]])
    return (("﻿" + buf.getvalue()).encode(), "text/csv; charset=utf-8", {"Content-Disposition": "attachment; filename=respuestas-test.csv"})

# ---------------------------------------------------------------- arranque
def main():
    os.makedirs(FOTOS, exist_ok=True)
    if not os.path.exists(DB_PATH):
        print("Creando la base de datos con los datos de prueba…")
        escenario("limpio")
    srv = ThreadingHTTPServer((HOST, PORT), H)
    srv.daemon_threads = True
    print("\n  Todo Sigue Vivo · POC")
    print("  Web:            http://localhost:%d/" % PORT)
    print("  Área privada:   http://localhost:%d/area-privada.html" % PORT)
    print("  Sala de test:   http://localhost:%d/sala.html" % PORT)
    print("  Para parar: Ctrl + C\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor parado.")

if __name__ == "__main__":
    main()
