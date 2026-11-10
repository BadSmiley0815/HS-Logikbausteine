# -*- coding: utf-8 -*-
"""
HSL3 14783 – Kamera-Proxy (v0.2, Prüffassung)

Holt Bilder und MJPEG-Ströme von Netzwerkkameras (z. B. Axis) mit Anmeldung (Digest oder Basic)
und gibt sie über die Weiterleitung des HomeServers aus – gleiche Adresse und gleiches Zertifikat
wie der HS, ohne Anmeldung im Browser:

    https://<HS>/<E1>/                    Prüfseite (Kameras, Standbild, Live-Bild, Bilder/s)
    https://<HS>/<E1>/<Name>.jpg?k=<E3>   Standbild
    https://<HS>/<E1>/<Name>.mjpg?k=<E3>  MJPEG-Strom (wird unverändert durchgereicht)
    https://<HS>/<E1>/test?k=<E3>         Prüfung aller Kameras als JSON

Erlaubte Zusatz-Parameter an die Kamera: resolution, fps, compression, camera
(z. B. …/einfahrt.mjpg?k=…&resolution=1280x720&fps=10).

Zugangsdaten stehen nur im Baustein. Sie werden nie ausgegeben, geloggt oder an den Browser
geschickt. Der Schlüssel E3 schützt alle Adressen außer der leeren Prüfseite.
"""
import base64
import hmac
import json
import re
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "0.2"
CAMS = 3
JPG_PATH = "/axis-cgi/jpg/image.cgi"
MJPG_PATH = "/axis-cgi/mjpg/video.cgi"
PASS_PARAMS = ("resolution", "fps", "compression", "camera")
MAX_STREAMS_PER_CAM = 4
MAX_STREAM_SECONDS = 3600
TIMEOUT = 8

_SSL = ssl.create_default_context()
_SSL.check_hostname = False          # Kameras im LAN haben meist selbst signierte Zertifikate
_SSL.verify_mode = ssl.CERT_NONE

PAGE = """<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>14783 Kamera-Proxy</title><style>
body{font:14px/1.45 system-ui,Segoe UI,sans-serif;margin:20px;background:#111;color:#eee}h1{font-size:19px}
input,button{font:inherit;padding:6px 10px;border-radius:8px;border:1px solid #555;background:#222;color:#eee}
.cam{margin:18px 0;padding:12px;border:1px solid #333;border-radius:10px}.row{display:flex;gap:12px;flex-wrap:wrap}
.row div{flex:1 1 320px}img{width:100%;background:#000;border-radius:8px;min-height:120px}.m{color:#9a9}.e{color:#e88}
pre{white-space:pre-wrap;background:#1b1b1b;padding:8px;border-radius:8px}</style></head><body>
<h1>14783 Kamera-Proxy <span class="m">v@@VER@@</span></h1>
<p>Schlüssel (E3): <input id="k" type="password" autocomplete="off"> <button onclick="go()">Prüfen</button></p>
<pre id="t">Schlüssel eingeben und „Prüfen“ drücken.</pre><div id="c"></div>
<script>
const base=location.pathname.replace(/\\/?$/,"/");let K="";
function q(n,ext,extra){return base+encodeURIComponent(n)+"."+ext+"?k="+encodeURIComponent(K)+(extra||"");}
async function go(){K=document.getElementById("k").value;const t=document.getElementById("t");t.textContent="prüfe …";
 try{const r=await fetch(base+"test?k="+encodeURIComponent(K));const d=await r.json();t.textContent=JSON.stringify(d,null,1);
  if(!r.ok)return;document.getElementById("c").innerHTML=d.cams.map(c=>`<div class="cam"><b>${c.name}</b> <span class="${c.ok?"m":"e"}">${c.ok?"erreichbar":"Fehler"}</span>
   <div class="row"><div>Standbild, schnell nachgeladen: <span id="f_${c.name}">–</span><br><img id="j_${c.name}"></div>
   <div>MJPEG-Strom über den HS:<br><img src="${q(c.name,"mjpg","")}"></div></div></div>`).join("");
  d.cams.forEach(c=>{const im=document.getElementById("j_"+c.name);let n=0,t0=Date.now();
   im.onload=()=>{n++;const s=(Date.now()-t0)/1000;document.getElementById("f_"+c.name).textContent=(n/s).toFixed(1)+" Bilder/s";setTimeout(()=>im.src=q(c.name,"jpg","&_="+Date.now()),150)};
   im.src=q(c.name,"jpg","");});
 }catch(e){t.textContent="Fehler: "+e;}}
</script></body></html>"""


class LogicModule:
    def __init__(self, hsl3):
        self.fw = hsl3
        self.debug = self.fw.create_debug_section()
        self._lock = threading.Lock()
        self.base_path = "kamera"
        self.port = 8095
        self.port_missing = False
        self.key = ""
        self.cams = {}
        self.streams = {}
        self.requests = 0
        self._httpd = self._stop = self._thread = None

    # ------------------------------------------------------------ Lebenszyklus
    def on_init(self, inputs, store):
        self._read_inputs(inputs)
        self._start()

    def on_calc(self, inputs):
        old = (self.base_path, self.port)
        self._read_inputs(inputs)
        restart = False
        try:
            restart = inputs.changed("restart") and self._num(inputs.value("restart"), 0) == 1
        except Exception:
            pass
        if restart or (self.base_path, self.port) != old:
            self._start()
        else:
            self._status_ready()

    def _read_inputs(self, inputs):
        self.base_path = self._text(inputs.value("base_path")).strip("/ ") or "kamera"
        self.port = int(self._num(inputs.value("destination_port"), 8095))
        self.port_missing = self.port <= 0
        if self.port_missing:
            self.port = 8095
        self.key = self._text(inputs.value("key")).strip()
        cams = {}
        for i in range(1, CAMS + 1):
            name = self._text(inputs.value("cam%d_name" % i)).strip().lower()
            addr = self._text(inputs.value("cam%d_addr" % i)).strip()
            if not name or not addr:
                continue
            if "://" not in addr:
                addr = "http://" + addr
            u = urllib.parse.urlsplit(addr)            # nur Schema://Host[:Port], ein Pfad wird ignoriert
            addr = "%s://%s" % (u.scheme or "http", u.netloc or u.path.split("/")[0])
            cams[name] = {"addr": addr,
                          "user": self._text(inputs.value("cam%d_user" % i)),
                          "pwd": self._text(inputs.value("cam%d_pwd" % i))}
        with self._lock:
            self.cams = cams
        self.debug.set("Kameras", ", ".join(sorted(cams)) or "keine")
        self.debug.set("Schutz", "Schlüssel gesetzt" if self.key else "OHNE Schlüssel")

    # ------------------------------------------------------------ Server
    def _start(self):
        self._stop_server()
        try:
            httpd = ThreadingHTTPServer(("0.0.0.0", self.port), self._handler())
            httpd.daemon_threads = True
            httpd.timeout = 0.5
            stop = threading.Event()
            th = threading.Thread(target=self._serve, args=(httpd, stop), daemon=True)
            self._httpd, self._stop, self._thread = httpd, stop, th
            th.start()
            self._status_ready()
        except OSError as e:
            self._status("Fehler beim Start auf Port %d: %s" % (self.port, e))

    def _status_ready(self):
        if self.port_missing:
            self._status("E2 Port fehlt! 8095 eintragen, sonst leitet der HS nicht weiter (503)")
        else:
            self._status("Bereit: /%s/ (Port %d), %d Kamera(s)%s" % (
                self.base_path, self.port, len(self.cams), "" if self.key else " - OHNE Schluessel"))

    @staticmethod
    def _serve(httpd, stop):
        try:
            while not stop.is_set():
                httpd.handle_request()
        finally:
            try:
                httpd.server_close()
            except OSError:
                pass

    def _stop_server(self):
        if self._stop is not None:
            self._stop.set()
        if self._thread is not None:
            self._thread.join(2.0)
        self._httpd = self._stop = self._thread = None

    def _handler(self):
        module = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"
            server_version = "Kamera-Proxy-14783/" + VERSION
            sys_version = ""

            def log_message(self, *a):
                pass

            def do_GET(self):
                module._handle(self)

        return H

    # ------------------------------------------------------------ Anfragen (HTTP-Thread)
    def _handle(self, h):
        try:
            parsed = urllib.parse.urlsplit(h.path)
            params = dict(urllib.parse.parse_qsl(parsed.query))
            route = parsed.path
            prefix = "/" + self.base_path
            if route == prefix or route.startswith(prefix + "/"):
                route = route[len(prefix):]
            route = route.strip("/")
            if route in ("", "index.html"):
                return self._send(h, 200, "text/html; charset=utf-8", PAGE.replace("@@VER@@", VERSION).encode("utf-8"))
            if not self._authorized(params):
                return self._send(h, 401, "text/plain; charset=utf-8", "Schluessel fehlt oder falsch".encode())
            if route == "test":
                return self._json(h, 200, self._test_all())
            name, _, ext = route.rpartition(".")
            name = urllib.parse.unquote(name).lower()
            with self._lock:
                cam = self.cams.get(name)
            if not cam or ext not in ("jpg", "mjpg"):
                return self._send(h, 404, "text/plain; charset=utf-8", b"Kamera unbekannt")
            extra = {k: v for k, v in params.items() if k in PASS_PARAMS}
            if ext == "jpg":
                return self._jpg(h, cam, extra)
            return self._mjpg(h, name, cam, extra)
        except (ConnectionError, OSError, socket.timeout):
            return
        except Exception as e:
            try:
                self._send(h, 500, "text/plain; charset=utf-8", ("Interner Fehler: %s" % type(e).__name__).encode())
            except Exception:
                pass
        finally:
            self.fw.run_in_context(self._count_request, ())

    def _authorized(self, params):
        if not self.key:
            return True
        return hmac.compare_digest((params.get("k") or params.get("key") or "").encode("utf-8"), self.key.encode("utf-8"))

    # ------------------------------------------------------------ Kamera
    @staticmethod
    def _opener(cam):
        pm = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        pm.add_password(None, cam["addr"], cam["user"], cam["pwd"])
        return urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=_SSL),
            urllib.request.HTTPDigestAuthHandler(pm),
            urllib.request.HTTPBasicAuthHandler(pm))

    def _open(self, cam, path, extra):
        url = cam["addr"] + path + ("?" + urllib.parse.urlencode(extra) if extra else "")
        try:
            return self._opener(cam).open(urllib.request.Request(url, headers={"User-Agent": "HS-14783/" + VERSION}), timeout=TIMEOUT)
        except urllib.error.HTTPError as e:
            if e.code == 400 and extra:                # Kamera kennt einen Parameter nicht (z. B. Auflösung) -> ohne
                return self._open(cam, path, {})
            raise

    @staticmethod
    def _detail(e):
        """Kurzer Fehlertext der Kamera (ohne HTML), hilft bei HTTP 400/404."""
        try:
            t = e.read(600).decode("utf-8", "replace")
        except Exception:
            return ""
        t = re.sub(r"<[^>]+>", " ", t)
        return " ".join(t.split())[:160]

    def _jpg(self, h, cam, extra):
        try:
            r = self._open(cam, JPG_PATH, extra)
            body = r.read()
            ctype = r.headers.get("Content-Type", "image/jpeg")
        except urllib.error.HTTPError as e:
            return self._send(h, 502, "text/plain; charset=utf-8", ("Kamera: HTTP %d" % e.code).encode())
        except Exception as e:
            return self._send(h, 504, "text/plain; charset=utf-8", ("Kamera nicht erreichbar: %s" % type(e).__name__).encode())
        self._send(h, 200, ctype, body)

    def _mjpg(self, h, name, cam, extra):
        with self._lock:
            if self.streams.get(name, 0) >= MAX_STREAMS_PER_CAM:
                busy = True
            else:
                busy = False
                self.streams[name] = self.streams.get(name, 0) + 1
        if busy:
            return self._send(h, 503, "text/plain; charset=utf-8", b"Zu viele Zuschauer")
        self.fw.run_in_context(self._publish_streams, ())
        try:
            try:
                r = self._open(cam, MJPG_PATH, extra)
            except urllib.error.HTTPError as e:
                return self._send(h, 502, "text/plain; charset=utf-8", ("Kamera: HTTP %d" % e.code).encode())
            except Exception as e:
                return self._send(h, 504, "text/plain; charset=utf-8", ("Kamera nicht erreichbar: %s" % type(e).__name__).encode())
            h.send_response(200)
            h.send_header("Content-Type", r.headers.get("Content-Type", "multipart/x-mixed-replace; boundary=myboundary"))
            h.send_header("Cache-Control", "no-store")
            h.send_header("X-Accel-Buffering", "no")
            h.end_headers()
            end = time.time() + MAX_STREAM_SECONDS
            try:
                while time.time() < end:
                    chunk = r.read1(16384) if hasattr(r, "read1") else r.read(16384)
                    if not chunk:
                        break
                    h.wfile.write(chunk)
                    h.wfile.flush()
            finally:
                try:
                    r.close()
                except Exception:
                    pass
        finally:
            with self._lock:
                self.streams[name] = max(0, self.streams.get(name, 1) - 1)
            self.fw.run_in_context(self._publish_streams, ())

    def _test_all(self):
        out = []
        with self._lock:
            cams = dict(self.cams)
        for name, cam in sorted(cams.items()):
            t0 = time.time()
            res = {"name": name, "ok": False}
            try:
                r = self._open(cam, JPG_PATH, {})
                body = r.read()
                res.update(ok=True, http=r.status, bytes=len(body), ms=int((time.time() - t0) * 1000),
                           type=r.headers.get("Content-Type", ""))
            except urllib.error.HTTPError as e:
                res.update(http=e.code, error="HTTP %d%s" % (e.code, " (Anmeldung abgelehnt)" if e.code == 401 else ""),
                           auth=(e.headers.get("WWW-Authenticate") or "").split(" ")[0],
                           server=(e.headers.get("Server") or "")[:40], detail=self._detail(e))
            except Exception as e:
                res.update(error="%s: %s" % (type(e).__name__, str(getattr(e, "reason", e))[:120]))
            res["ziel"] = cam["addr"].split("://")[0] + "://…" + JPG_PATH
            out.append(res)
        self.fw.run_in_context(self._publish_test, (out,))
        return {"version": VERSION, "cams": out}

    # ------------------------------------------------------------ im Kontext
    def _count_request(self):
        self.requests += 1
        self.fw.set_output("requests", float(self.requests))

    def _publish_streams(self):
        with self._lock:
            n = sum(self.streams.values())
        self.fw.set_output("streams", float(n))
        self.debug.set("Ströme", str(n))

    def _publish_test(self, out):
        txt = "; ".join("%s %s" % (c["name"], "OK %d ms" % c.get("ms", 0) if c["ok"] else c.get("error", "Fehler")) for c in out)
        self.fw.set_output("test", self._ascii(txt))
        self.debug.set("Prüfung", txt)

    # ------------------------------------------------------------ Hilfen
    def _json(self, h, status, data):
        self._send(h, status, "application/json; charset=utf-8",
                   json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    @staticmethod
    def _send(h, status, ctype, body):
        h.send_response(status)
        h.send_header("Content-Type", ctype)
        h.send_header("Content-Length", str(len(body)))
        h.send_header("Cache-Control", "no-store")
        h.send_header("X-Content-Type-Options", "nosniff")
        h.end_headers()
        if body:
            h.wfile.write(body)

    @staticmethod
    def _ascii(text):
        t = text
        for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"), ("ß", "ss"), ("–", "-")):
            t = t.replace(a, b)
        return t.encode("ascii", "replace")[:200]

    def _status(self, text):
        self.fw.set_output("status", self._ascii(text))
        self.debug.set("Status", text)

    @staticmethod
    def _text(v):
        if isinstance(v, bytes):
            try:
                return v.decode("utf-8")
            except UnicodeDecodeError:
                return v.decode("iso-8859-15", "replace")
        return "" if v is None else str(v)

    @staticmethod
    def _num(v, default):
        try:
            return float(v)
        except (TypeError, ValueError):
            return default
