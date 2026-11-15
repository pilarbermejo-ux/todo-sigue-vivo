"""Adapta servidor.py (la POC con servidor propio) para que funcione dentro del navegador con Pyodide.

La lógica de negocio, la base de datos SQLite y la API son exactamente las mismas que en la POC.
Solo cambia el «transporte»:
- las peticiones llegan desde JavaScript (sin HTTP) a manejar();
- el tiempo real se emite a JavaScript (tsvEmit) en vez de por Server-Sent Events;
- los temporizadores de los cuidadores en modo presentación usan setTimeout del navegador;
- los datos se guardan en IndexedDB (carpeta /datos montada con IDBFS), solo en este navegador.
"""
import hashlib, json, os, traceback

import servidor as S
from js import tsvEmit, tsvPersist, setTimeout, clearTimeout
from pyodide.ffi import create_once_callable

S.PUBLIC = "/public"
S.DATOS = "/datos"
S.FOTOS = "/datos/fotos"
S.DB_PATH = "/datos/tsv.db"


def conectar():
    c = S.sqlite3.connect(S.DB_PATH, isolation_level=None, check_same_thread=False)
    c.row_factory = S.sqlite3.Row
    return c


S.conectar = conectar


# Pyodide no incluye pbkdf2_hmac (no trae OpenSSL). En la demo todas las contraseñas son de
# ejemplo y viven solo en el navegador de quien la visita, así que basta con un SHA-256 con sal.
def hash_clave(clave, sal):
    return hashlib.sha256((sal + ":" + clave).encode()).hexdigest()


S.hash_clave = hash_clave


def _send(clave, msg):
    tsvEmit(str(clave), json.dumps(msg, ensure_ascii=False, default=str))


S.HUB.send = _send

_timers = []


def luego(seg, fn, *args):
    gen = S.GENERACION[0]

    def run(*_):
        if gen != S.GENERACION[0]:
            return
        c = S.conectar()
        try:
            fn(c, *args)
        except Exception as e:
            print("robot:", e)
        finally:
            c.close()
            tsvPersist()

    _timers.append(setTimeout(create_once_callable(run), int(seg * 1000)))


def cancelar_timers():
    S.GENERACION[0] += 1
    for t in _timers:
        clearTimeout(t)
    _timers.clear()


S.luego = luego
S.cancelar_timers = cancelar_timers


def _json(obj, code=200):
    return [code, json.dumps(obj, ensure_ascii=False, default=str), "application/json; charset=utf-8"]


def manejar(metodo, path, body_txt, tok):
    c = S.conectar()
    try:
        for m, rx, fn, auth in S.RUTAS:
            mt = rx.match(path)
            if m != metodo or not mt:
                continue
            body = json.loads(body_txt) if body_txt else {}
            uid = None
            if tok:
                s = S.fila(c, "SELECT usuario_id FROM sesiones WHERE token=?", tok)
                uid = s["usuario_id"] if s else None
            if auth and not uid:
                return _json({"error": "Tu sesión ha caducado. Vuelve a entrar.", "auth": False}, 401)
            res = fn(None, c, uid, body, **mt.groupdict())
            if isinstance(res, tuple):
                return [200, res[0].decode("utf-8"), res[1]]
            return _json(res if res is not None else {"ok": True})
        return _json({"error": "No existe"}, 404)
    except S.ApiError as e:
        return _json({"error": e.msg}, e.code)
    except Exception as e:
        traceback.print_exc()
        return _json({"error": "Algo ha fallado en la demo: %s" % e}, 500)
    finally:
        c.close()


def uid_de(tok):
    c = S.conectar()
    try:
        s = S.fila(c, "SELECT usuario_id FROM sesiones WHERE token=?", tok or "")
        return s["usuario_id"] if s else None
    finally:
        c.close()


def iniciar():
    os.makedirs(S.FOTOS, exist_ok=True)
    nueva = not os.path.exists(S.DB_PATH)
    if not nueva:
        c = S.conectar()
        try:
            nueva = not S.fila(c, "SELECT 1 FROM sqlite_master WHERE name='usuarios'")
        finally:
            c.close()
    if nueva:
        S.escenario("limpio")
    return nueva
