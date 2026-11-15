# -*- coding: utf-8 -*-
"""
HSL3 14783 – Kamera-Proxy (v0.6, Prüffassung)

Holt Bilder und MJPEG-Ströme von Netzwerkkameras (Axis, beliebige Standbild-Adresse oder ONVIF)
mit Anmeldung (Digest oder Basic, bei ONVIF zusätzlich WS-Security) und gibt sie über die Weiterleitung des HomeServers aus – gleiche Adresse und gleiches Zertifikat
wie der HS, ohne Anmeldung im Browser:

    https://<HS>/<E1>/                    Prüfseite (Kameras, Standbild, Live-Bild, Bilder/s)
    https://<HS>/<E1>/<Name>.jpg?k=<E3>   Standbild
    https://<HS>/<E1>/<Name>.mjpg?k=<E3>  MJPEG-Strom (von der Kamera durchgereicht oder,
                                          wenn sie keinen anbietet, aus Standbildern gebaut)
    https://<HS>/<E1>/test?k=<E3>         Prüfung aller Kameras als JSON

Erlaubte Zusatz-Parameter an die Kamera: resolution, fps, compression, camera
(z. B. …/einfahrt.mjpg?k=…&resolution=1280x720&fps=10).

Adresse je Kamera (E6, E10, …):
    <Kamera> oder https://<Kamera>                Axis (feste Pfade /axis-cgi/…)
    https://<Kamera>/pfad/bild.cgi?…              diese Adresse ist das Standbild
    onvif://<Kamera>[?resolution=1280x720]        Adressen per ONVIF ermitteln

Zugangsdaten stehen nur im Baustein. Sie werden nie ausgegeben, geloggt oder an den Browser
geschickt. Der Schlüssel E3 schützt alle Adressen außer der leeren Prüfseite.
"""
import base64
import hashlib
import http.client
import io
import os
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

VERSION = "0.6"
CAMS = 6
JPG_PATH = "/axis-cgi/jpg/image.cgi"
MJPG_PATH = "/axis-cgi/mjpg/video.cgi"
ONVIF_PATH = "/onvif/device_service"
ONVIF_RES = (1280, 720)              # Wunsch-Auflösung bei ONVIF, wenn keine angegeben ist
ONVIF_RETRY = 15                     # Sekunden bis zur nächsten ONVIF-Abfrage nach einem Fehler
FPS_DEFAULT, FPS_MAX = 8.0, 15.0     # Strom aus Standbildern
BOUNDARY = "hsframe"
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


class CamClient:
    """HTTP(S)-Zugriff auf eine Kamera mit offen gehaltenen Verbindungen und zwischengespeicherter
    Anmeldung (Digest MD5/SHA-256 oder Basic): nach der ersten Anfrage geht jede weitere ohne
    zusätzliche 401-Runde und ohne neuen Verbindungsaufbau an die Kamera."""
    POOL = 4

    def __init__(self, addr, user, pwd):
        u = urllib.parse.urlsplit(addr)
        self.https = u.scheme == "https"
        self.host = u.hostname or ""
        self.port = u.port or (443 if self.https else 80)
        self.user, self.pwd = user, pwd
        self.key = (addr, user, pwd)
        self.lock = threading.Lock()
        self.idle = []
        self.auth = None            # {"scheme": "digest"/"basic", realm, nonce, qop, opaque, algorithm}
        self.nc = 0

    def _new_conn(self):
        if self.https:
            return http.client.HTTPSConnection(self.host, self.port, timeout=TIMEOUT, context=_SSL)
        return http.client.HTTPConnection(self.host, self.port, timeout=TIMEOUT)

    @staticmethod
    def _parse(headers):
        best = None
        for raw in headers.get_all("WWW-Authenticate") or []:
            scheme, _, rest = raw.strip().partition(" ")
            p = {k.lower(): (v1 if v1 or q else v2) for k, q, v1, v2 in
                 re.findall(r'([\w-]+)\s*=\s*(?:(")([^"]*)"|([^,\s]*))', rest)}
            p["scheme"] = scheme.lower()
            if p["scheme"] == "digest" and (best is None or best["scheme"] != "digest" or "sha-256" in p.get("algorithm", "").lower()):
                best = p
            elif p["scheme"] == "basic" and best is None:
                best = p
        return best

    def _header(self, uri, method="GET"):
        a = self.auth
        if not a:
            return None
        if a["scheme"] == "basic":
            return "Basic " + base64.b64encode(("%s:%s" % (self.user, self.pwd)).encode("utf-8")).decode("ascii")
        alg = (a.get("algorithm") or "MD5").upper()
        hf = (lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest()) if alg.startswith("SHA-256") else \
             (lambda x: hashlib.md5(x.encode("utf-8")).hexdigest())
        with self.lock:
            self.nc += 1
            nc = "%08x" % self.nc
        cnonce = os.urandom(8).hex()
        ha1 = hf("%s:%s:%s" % (self.user, a.get("realm", ""), self.pwd))
        if alg.endswith("-SESS"):
            ha1 = hf("%s:%s:%s" % (ha1, a.get("nonce", ""), cnonce))
        ha2 = hf(method + ":" + uri)
        qops = [q.strip() for q in a.get("qop", "").split(",") if q.strip()]
        if "auth" in qops:
            resp = hf("%s:%s:%s:%s:auth:%s" % (ha1, a["nonce"], nc, cnonce, ha2))
            extra = ', qop=auth, nc=%s, cnonce="%s"' % (nc, cnonce)
        else:
            resp = hf("%s:%s:%s" % (ha1, a.get("nonce", ""), ha2))
            extra = ""
        h = 'Digest username="%s", realm="%s", nonce="%s", uri="%s", algorithm=%s, response="%s"%s' % (
            self.user, a.get("realm", ""), a.get("nonce", ""), uri, a.get("algorithm") or "MD5", resp, extra)
        if a.get("opaque"):
            h += ', opaque="%s"' % a["opaque"]
        return h

    def _send(self, uri, conn, method="GET", body=None, ctype=None):
        hd = {"User-Agent": "HS-14783/" + VERSION, "Connection": "keep-alive"}
        ah = self._header(uri, method)
        if ah:
            hd["Authorization"] = ah
        if body is not None:
            hd["Content-Type"] = ctype or "application/octet-stream"
        conn.request(method, uri, body=body, headers=hd)
        return conn.getresponse()

    def get(self, uri, stream=False, method="GET", body=None, ctype=None):
        """Liefert (Antwort, Verbindung). Bei stream=False ist der Inhalt schon gelesen (Antwort.body).
        Weiterleitungen (z. B. http -> https) werden befolgt und für die Kamera gemerkt."""
        attempt = redirects = 0
        while attempt < 3:
            attempt += 1
            conn = None
            if not stream:
                with self.lock:
                    conn = self.idle.pop() if self.idle else None
            reused = conn is not None
            conn = conn or self._new_conn()
            try:
                r = self._send(uri, conn, method, body, ctype)
            except (http.client.HTTPException, OSError):
                conn.close()
                if reused:
                    continue                    # Kamera hat die offene Verbindung inzwischen geschlossen
                raise
            if r.status == 401 and attempt < 3:
                ch = self._parse(r.headers)
                r.read()
                if r.will_close:
                    conn.close()
                else:
                    with self.lock:
                        if len(self.idle) < self.POOL:
                            self.idle.append(conn)
                        else:
                            conn.close()
                if ch and (self.auth is None or ch.get("nonce") != self.auth.get("nonce") or ch["scheme"] != self.auth["scheme"]):
                    with self.lock:
                        self.auth, self.nc = ch, 0
                    continue
                if ch and ch.get("stale", "").lower() == "true":
                    continue
                raise urllib.error.HTTPError(uri, 401, "Unauthorized", r.headers, io.BytesIO(b""))
            if r.status in (301, 302, 303, 307, 308) and r.headers.get("Location") and redirects < 3:
                loc = r.headers.get("Location")
                r.read()
                conn.close()
                redirects += 1
                cur = "%s://%s:%d%s" % ("https" if self.https else "http", self.host, self.port, uri)
                u = urllib.parse.urlsplit(urllib.parse.urljoin(cur, loc))
                https, host = u.scheme == "https", u.hostname or self.host
                port = u.port or (443 if https else 80)
                if (https, host, port) != (self.https, self.host, self.port):
                    self.close()                        # andere Adresse: alte offene Verbindungen verwerfen
                    with self.lock:
                        self.https, self.host, self.port = https, host, port
                        self.auth, self.nc = None, 0
                uri = (u.path or "/") + ("?" + u.query if u.query else "")
                attempt -= 1                            # Weiterleitung zählt nicht als Versuch
                continue
            if stream and r.status == 200:
                return r, conn
            body = r.read()
            if r.will_close:
                conn.close()
            else:
                with self.lock:
                    if len(self.idle) < self.POOL:
                        self.idle.append(conn)
                    else:
                        conn.close()
            if r.status != 200:
                raise urllib.error.HTTPError(uri, r.status, r.reason, r.headers, io.BytesIO(body))
            r.body = body
            return r, None
        raise urllib.error.HTTPError(uri, 401, "Unauthorized", http.client.HTTPMessage(), io.BytesIO(b""))

    def close(self):
        with self.lock:
            for c in self.idle:
                try:
                    c.close()
                except Exception:
                    pass
            self.idle = []


# ---------------------------------------------------------------- ONVIF
_ENV = ('<?xml version="1.0" encoding="UTF-8"?><s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">'
        '<s:Header>%s</s:Header><s:Body>%s</s:Body></s:Envelope>')
_SEC = ('<wsse:Security s:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" '
        'xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"><wsse:UsernameToken>'
        '<wsse:Username>%s</wsse:Username>'
        '<wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">%s</wsse:Password>'
        '<wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">%s</wsse:Nonce>'
        '<wsu:Created>%s</wsu:Created></wsse:UsernameToken></wsse:Security>')
_TDS = 'xmlns:tds="http://www.onvif.org/ver10/device/wsdl"'
_TRT = 'xmlns:trt="http://www.onvif.org/ver10/media/wsdl"'


def _esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _unesc(t):
    for a, b in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'"), ("&amp;", "&")):
        t = t.replace(a, b)
    return t


def _els(xml, name):
    """Alle Elemente <präfix:name …>Inhalt</präfix:name> als (Attribute, Inhalt) – ohne XML-Bibliothek."""
    return re.findall(r"<(?:[\w.-]+:)?%s(\s[^>]*)?>(.*?)</(?:[\w.-]+:)?%s\s*>" % (name, name), xml, re.S)


def _first(xml, name):
    m = _els(xml, name)
    return _unesc(m[0][1].strip()) if m else ""


def _int(t):
    try:
        return int(t)
    except (TypeError, ValueError):
        return 0


def _res(text):
    """'1280x720' -> (1280, 720), sonst None."""
    m = re.match(r"^\s*(\d{2,5})\s*[xX*]\s*(\d{2,5})\s*$", text or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def _masked(uri):
    """Pfad und Abfrage einer Adresse für die Prüfseite: ohne Host, ohne Anmeldung, heikle Werte verdeckt."""
    u = urllib.parse.urlsplit(uri)
    q = ["%s=%s" % (k, "…" if re.search(r"user|usr|pass|pwd|auth|token|key|login", k, re.I) else v)
         for k, v in urllib.parse.parse_qsl(u.query, keep_blank_values=True)]
    return (u.path or "/") + ("?" + "&".join(q) if q else "")


def _epoch(y, mo, d, h, mi, sec):
    """UTC-Zeit in Sekunden seit 1970 (ohne Zusatzmodul)."""
    leap = lambda j: j % 4 == 0 and (j % 100 != 0 or j % 400 == 0)
    days = sum(366 if leap(j) else 365 for j in range(1970, y))
    md = [31, 29 if leap(y) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    days += sum(md[:mo - 1]) + d - 1
    return days * 86400 + h * 3600 + mi * 60 + sec


class Onvif:
    """Ermittelt per ONVIF (GetSystemDateAndTime, GetCapabilities, GetProfiles, GetSnapshotUri, GetStreamUri)
    die Standbild- und Strom-Adresse einer Kamera. Anmeldung: WS-Security UsernameToken (PasswordDigest),
    die Uhr der Kamera wird vorher gelesen. Das Ergebnis wird gemerkt, nach Fehlern frühestens nach
    ONVIF_RETRY Sekunden neu abgefragt."""

    def __init__(self, host, cands, path, user, pwd):
        self.host, self.cands, self.path, self.user, self.pwd = host, cands, path, user, pwd
        self.lock = threading.Lock()
        self.client = None
        self.more = {}                  # weitere Clients, falls das Standbild auf einem anderen Port liegt
        self.offset = 0.0               # Uhr der Kamera minus Uhr des HS
        self.media = path
        self.profiles = []
        self.src = {}
        self.last = None
        self.used = ""                  # zuletzt wirklich abgerufene Standbild-Adresse (für die Prüfseite)
        self.ready = self.stale = False
        self.tried = 0.0
        self.error = None

    # -- SOAP
    def _sec(self):
        nonce = os.urandom(16)
        created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + self.offset))
        dig = hashlib.sha1(nonce + created.encode("ascii") + self.pwd.encode("utf-8")).digest()
        return _SEC % (_esc(self.user), base64.b64encode(dig).decode("ascii"),
                       base64.b64encode(nonce).decode("ascii"), created)

    def _call(self, client, path, body, auth=True):
        env = _ENV % (self._sec() if auth and self.user else "", body)
        r, _ = client.get(path, method="POST", body=env.encode("utf-8"), ctype="application/soap+xml; charset=utf-8")
        return r.body.decode("utf-8", "replace")

    # -- Ablauf
    def _discover(self):
        self.close()
        client = last = None
        xml = ""
        for scheme, port in self.cands:                 # onvif://… probiert erst https, dann http
            c = CamClient("%s://%s:%d" % (scheme, self.host, port), self.user, self.pwd)
            try:
                xml = self._call(c, self.path, "<tds:GetSystemDateAndTime %s/>" % _TDS, auth=False)
            except urllib.error.HTTPError:
                xml = ""                                # erreichbar, Uhrzeit nur mit Anmeldung -> ohne Abgleich
            except Exception as e:
                last = e
                c.close()
                continue
            client = c
            break
        if client is None:
            raise last or OSError("ONVIF nicht erreichbar")
        self.client = client
        self.offset = 0.0
        utc = _els(xml, "UTCDateTime")
        if utc:
            v = [_int(_first(utc[0][1], n)) for n in ("Year", "Month", "Day", "Hour", "Minute", "Second")]
            if v[0] > 2000 and 1 <= v[1] <= 12 and v[2]:
                self.offset = _epoch(*v) - time.time()
        self.media = self.path
        try:                                            # Adresse des Mediendienstes; ohne Antwort gilt der Gerätedienst
            cap = self._call(client, self.path, "<tds:GetCapabilities %s><tds:Category>Media</tds:Category></tds:GetCapabilities>" % _TDS)
            med = _els(cap, "Media")
            x = urllib.parse.urlsplit(_first(med[0][1], "XAddr")) if med else None
            if x and x.path:
                self.media = x.path                     # nur der Pfad: Host und http/https bleiben wie eingetragen
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise
        xml = self._call(client, self.media, "<trt:GetProfiles %s/>" % _TRT)
        profiles = []
        for attrs, inner in _els(xml, "Profiles"):
            m = re.search(r'\btoken\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', attrs or "")
            if not m:
                continue
            enc = _els(inner, "VideoEncoderConfiguration")
            e = enc[0][1] if enc else ""
            profiles.append({"token": _unesc(m.group(1) or m.group(2) or ""), "name": _first(inner, "Name"),
                             "enc": _first(e, "Encoding"), "w": _int(_first(e, "Width")), "h": _int(_first(e, "Height"))})
        if not profiles:
            raise ValueError("ONVIF: keine Profile")
        self.profiles, self.src, self.last, self.used = profiles, {}, None, ""

    def _pick(self, want):
        sized = [p for p in self.profiles if p["w"] and p["h"]]
        if not sized:
            return self.profiles[0]
        area = want[0] * want[1]
        return min(sized, key=lambda p: (abs(p["w"] * p["h"] - area), abs(p["w"] - want[0])))

    def _snapshot(self, p):
        tok = "<trt:ProfileToken>%s</trt:ProfileToken>" % _esc(p["token"])
        uri = _first(self._call(self.client, self.media, "<trt:GetSnapshotUri %s>%s</trt:GetSnapshotUri>" % (_TRT, tok)), "Uri")
        if not uri:
            raise ValueError("ONVIF: Kamera nennt kein Standbild")
        u = urllib.parse.urlsplit(uri)
        client = self.client
        try:
            port = u.port
        except ValueError:
            port = None
        if u.scheme in ("http", "https") and port and port != client.port:
            key = (u.scheme, port)
            if key not in self.more:
                self.more[key] = CamClient("%s://%s:%d" % (u.scheme, self.host, port), self.user, self.pwd)
            client = self.more[key]
        stream = ""
        try:
            stream = _first(self._call(
                self.client, self.media,
                '<trt:GetStreamUri %s xmlns:tt="http://www.onvif.org/ver10/schema"><trt:StreamSetup><tt:Stream>RTP-Unicast</tt:Stream>'
                '<tt:Transport><tt:Protocol>RTSP</tt:Protocol></tt:Transport></trt:StreamSetup>%s</trt:GetStreamUri>' % (_TRT, tok)), "Uri")
        except Exception:
            pass                                        # nur Auskunft für die Prüfseite
        return {"profile": p, "client": client, "path": u.path or "/",
                "query": urllib.parse.parse_qsl(u.query, keep_blank_values=True),
                "show": _masked(uri), "stream": (stream.split("://")[0] + "://…" + _masked(stream)) if stream else ""}

    def source(self, want):
        """Quelle des Standbilds für die gewünschte Auflösung (w, h)."""
        with self.lock:
            now = time.time()
            if not self.ready or (self.stale and now - self.tried >= ONVIF_RETRY):
                if not self.ready and self.error is not None and now - self.tried < ONVIF_RETRY:
                    raise self.error
                self.tried = now
                try:
                    self._discover()
                except Exception as e:
                    self.ready, self.error = False, e
                    raise
                self.ready, self.stale, self.error = True, False, None
            p = self._pick(want)
            s = self.src.get(p["token"])
            if s is None:
                s = self.src[p["token"]] = self._snapshot(p)
            self.last = s
            return s

    def info(self):
        with self.lock:
            out = {"profile": ["%s %dx%d %s" % (p["name"] or p["token"], p["w"], p["h"], p["enc"]) for p in self.profiles]}
            s = self.last
            if self.ready and s:
                p = s["profile"]
                out.update(profil="%s %dx%d" % (p["name"] or p["token"], p["w"], p["h"]), standbild=self.used or s["show"],
                           strom=s["stream"], uhr="%+d s" % round(self.offset))
            return out

    def close(self):
        for c in [self.client] + list(self.more.values()):
            if c is not None:
                c.close()
        self.client, self.more = None, {}


class Resp:
    """Einheitliche Antwort für Standbild (Inhalt gelesen) und Strom (offene Verbindung)."""
    def __init__(self, r, conn):
        self.r, self.conn, self.status, self.headers = r, conn, r.status, r.headers
        self._buf = getattr(r, "body", None)

    def read(self, n=-1):
        if self._buf is not None:
            b, self._buf = self._buf, b""
            return b
        return self.r.read(n)

    def read1(self, n):
        if self._buf is not None:
            return self.read()
        return self.r.read1(n) if hasattr(self.r, "read1") else self.r.read(n)

    def close(self):
        try:
            self.r.close()
        finally:
            if self.conn is not None:
                self.conn.close()


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
            key = (addr, self._text(inputs.value("cam%d_user" % i)), self._text(inputs.value("cam%d_pwd" % i)))
            old = self.cams.get(name)
            cams[name] = old if old and old["key"] == key else self._make_cam(*key)
        with self._lock:
            for n, c in self.cams.items():
                if cams.get(n) is not c:
                    self._close_cam(c)
            self.cams = cams
        self.debug.set("Kameras", ", ".join(sorted(cams)) or "keine")
        self.debug.set("Schutz", "Schlüssel gesetzt" if self.key else "OHNE Schlüssel")

    @staticmethod
    def _make_cam(addr, user, pwd):
        """Art der Kamera aus der Adresse: nur Host -> Axis, Adresse mit Pfad -> dieses Standbild, onvif://… -> ONVIF."""
        cam = {"key": (addr, user, pwd), "mode": "axis", "client": None, "onvif": None,
               "jpg": JPG_PATH, "mjpg": MJPG_PATH, "fixed": {}, "skip": set()}
        if addr.lower().startswith("onvif://"):
            u, schemes, onvif = urllib.parse.urlsplit("http://" + addr[8:]), ("https", "http"), True
        else:
            if "://" not in addr:
                addr = "http://" + addr
            u = urllib.parse.urlsplit(addr)
            schemes = ("https" if u.scheme.lower() == "https" else "http",)
            onvif = u.path.rstrip("/").lower() == ONVIF_PATH
        q = urllib.parse.parse_qsl(u.query, keep_blank_values=True)
        cam["params"] = {k: v for k, v in q if k in PASS_PARAMS}     # ?resolution=…&camera=… gilt als Vorgabe
        host = u.hostname or ""
        if ":" in host:
            host = "[%s]" % host
        try:
            port = u.port
        except ValueError:
            port = None
        if onvif:
            path = u.path if u.path.strip("/") else ONVIF_PATH
            cam.update(mode="onvif", jpg=None, mjpg=None,
                       onvif=Onvif(host, [(s, port or (443 if s == "https" else 80)) for s in schemes], path, user, pwd))
            return cam
        cam["client"] = CamClient("%s://%s%s" % (schemes[0], host, ":%d" % port if port else ""), user, pwd)
        if u.path not in ("", "/", JPG_PATH, MJPG_PATH):               # ganze Standbild-Adresse einer beliebigen Kamera
            cam.update(mode="url", jpg=u.path, mjpg=None, fixed={k: v for k, v in q if k not in PASS_PARAMS})
        return cam

    @staticmethod
    def _close_cam(cam):
        if cam["client"] is not None:
            cam["client"].close()
        if cam["onvif"] is not None:
            cam["onvif"].close()

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
            if route == "list":                        # Namen der Kameras (für den QC-Client), ohne Kamera-Abruf
                with self._lock:
                    names = sorted(self.cams)
                return self._json(h, 200, {"version": VERSION, "cams": names})
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
    def _source(self, cam, kind, extra):
        """Liefert (Client, Pfad, Liste möglicher Parameter-Sätze – der erste ist der gewünschte)."""
        if cam["mode"] == "onvif":
            want = _res(extra.get("resolution")) or _res(cam["params"].get("resolution")) or ONVIF_RES
            s = cam["onvif"].source(want)
            base = dict(s["query"])
            over = dict(base)
            for src in (cam["params"], extra):          # nur Parameter, die die Kamera in ihrer Adresse selbst nennt
                over.update({k: v for k, v in src.items() if k in base})
            if "resolution" in base:
                over["resolution"] = "%dx%d" % want
            return s["client"], s["path"], [over, base]
        full = dict(cam["fixed"])
        full.update(cam["params"])
        dflt = dict(full)
        full.update(extra)                              # Anfrage aus dem Browser überschreibt die Vorgabe aus der Adresse
        return cam["client"], cam[kind], [full, dflt, dict(cam["fixed"])]

    def _open(self, cam, kind, extra, stream=False):
        """Öffnet Standbild (kind "jpg") oder Strom ("mjpg"). Lehnt die Kamera Parameter ab (HTTP 400),
        geht es mit der Vorgabe und dann ohne weiter; abgelehnte Sätze werden gemerkt."""
        try:
            client, path, cands = self._source(cam, kind, extra)
            uris = []
            for q in cands:
                uri = path + ("?" + urllib.parse.urlencode(q) if q else "")
                if uri not in uris:
                    uris.append(uri)
            todo = [u for u in uris if u not in cam["skip"]] or uris[-1:]
            for n, uri in enumerate(todo):
                try:
                    r = Resp(*client.get(uri, stream=stream))
                    if cam["mode"] == "onvif":
                        cam["onvif"].used = _masked(uri)
                    return r
                except urllib.error.HTTPError as e:
                    if e.code != 400 or n == len(todo) - 1:
                        raise
                    if len(cam["skip"]) > 50:
                        cam["skip"].clear()
                    cam["skip"].add(uri)
        except urllib.error.HTTPError as e:
            if cam["mode"] == "onvif" and e.code != 400:
                cam["onvif"].stale = True               # Adresse könnte sich geändert haben -> später neu ermitteln
            raise
        except Exception:
            if cam["mode"] == "onvif":
                cam["onvif"].stale = True
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
            r = self._open(cam, "jpg", extra)
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
            r = first = None
            still = {k: v for k, v in extra.items() if k != "fps"}
            try:
                if cam["mjpg"]:
                    try:
                        r = self._open(cam, "mjpg", extra, stream=True)
                    except urllib.error.HTTPError:
                        r = None                        # Kamera bietet keinen MJPEG-Strom -> aus Standbildern bauen
                if r is None:
                    first = self._open(cam, "jpg", still).read()
            except urllib.error.HTTPError as e:
                return self._send(h, 502, "text/plain; charset=utf-8", ("Kamera: HTTP %d" % e.code).encode())
            except Exception as e:
                return self._send(h, 504, "text/plain; charset=utf-8", ("Kamera nicht erreichbar: %s" % type(e).__name__).encode())
            h.send_response(200)
            h.send_header("Content-Type", r.headers.get("Content-Type", "multipart/x-mixed-replace; boundary=myboundary")
                          if r is not None else "multipart/x-mixed-replace; boundary=" + BOUNDARY)
            h.send_header("Cache-Control", "no-store")
            h.send_header("X-Accel-Buffering", "no")
            h.end_headers()
            end = time.time() + MAX_STREAM_SECONDS
            if r is None:
                return self._push(h, cam, still, first, extra.get("fps"), end)
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

    def _push(self, h, cam, extra, body, fps, end):
        """MJPEG-Strom aus schnell nachgeladenen Standbildern (für Kameras ohne eigenen MJPEG-Strom)."""
        step = 1.0 / min(FPS_MAX, max(1.0, self._num(fps, FPS_DEFAULT)))
        errors = 0
        while time.time() < end:
            t0 = time.time()
            if body:
                h.wfile.write(("--%s\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % (BOUNDARY, len(body))).encode("ascii"))
                h.wfile.write(body)
                h.wfile.write(b"\r\n")
                h.wfile.flush()
            try:
                body = self._open(cam, "jpg", extra).read()
                errors = 0
            except (urllib.error.HTTPError, http.client.HTTPException, OSError, ValueError):
                body, errors = None, errors + 1
                if errors >= 5:                         # Kamera weg -> Strom beenden, der Browser baut neu auf
                    return
                time.sleep(1.0)
            wait = step - (time.time() - t0)
            if wait > 0:
                time.sleep(wait)

    def _test_all(self):
        out = []
        with self._lock:
            cams = dict(self.cams)
        for name, cam in sorted(cams.items()):
            try:                                       # einmal vorab, damit „ms“ die Zeit mit gespeicherter Anmeldung zeigt
                self._open(cam, "jpg", {}).read()
            except Exception:
                pass
            t0 = time.time()
            res = {"name": name, "ok": False}
            try:
                r = self._open(cam, "jpg", {})
                body = r.read()
                res.update(ok=True, http=r.status, bytes=len(body), ms=int((time.time() - t0) * 1000),
                           type=r.headers.get("Content-Type", ""))
            except urllib.error.HTTPError as e:
                res.update(http=e.code, error="HTTP %d%s" % (e.code, " (Anmeldung abgelehnt)" if e.code == 401 else ""),
                           auth=(e.headers.get("WWW-Authenticate") or "").split(" ")[0],
                           server=(e.headers.get("Server") or "")[:40], detail=self._detail(e))
            except Exception as e:
                res.update(error="%s: %s" % (type(e).__name__, str(getattr(e, "reason", e))[:120]))
            res["art"] = cam["mode"]
            if cam["mode"] == "onvif":
                res.update(cam["onvif"].info())
                res["live"] = "Standbilder"
            else:
                res["ziel"] = ("https" if cam["client"].https else "http") + "://…" + cam["jpg"]
                res["live"] = "MJPEG der Kamera, sonst Standbilder" if cam["mjpg"] else "Standbilder"
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
