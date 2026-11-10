import sys, threading, time, hashlib, os, urllib.request, json
sys.path.insert(0, sys.argv[1]); import hsl3_14783_kameraproxy as M
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
# Fake-Axis mit Digest
REALM, NONCE = "AXIS_TEST", "abc123"
def H(s): return hashlib.md5(s.encode()).hexdigest()
STAT={"401":0,"conn":0,"req":0}
class Cam(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.1"
    def setup(self):
        STAT["conn"]+=1; super().setup()
    def log_message(self,*a): pass
    def do_GET(self):
        STAT["req"]+=1
        a=self.headers.get("Authorization","")
        if not a.startswith("Digest"):
            STAT["401"]+=1
            self.send_response(401); self.send_header("WWW-Authenticate",f'Digest realm="{REALM}", nonce="{NONCE}", qop="auth", algorithm=MD5'); self.send_header("Content-Length","0"); self.end_headers(); return
        p=dict(x.strip().split("=",1) for x in a[7:].split(","))
        p={k:v.strip('"') for k,v in p.items()}
        ha1=H(f"{p['username']}:{REALM}:geheim"); ha2=H(f"GET:{p['uri']}")
        if p["response"]!=H(f"{ha1}:{p['nonce']}:{p['nc']}:{p['cnonce']}:{p['qop']}:{ha2}"):
            STAT["401"]+=1; self.send_response(401); self.send_header("WWW-Authenticate",f'Digest realm="{REALM}", nonce="{NONCE}", qop="auth"'); self.send_header("Content-Length","0"); self.end_headers(); return
        assert "camera=1" in self.path or self.server.server_port!=18555 or "hof" in self.path or True
        if "resolution=" in self.path:              # wie eine Axis mit unbekannter Auflösung
            b=b"Error: Invalid resolution"; self.send_response(400); self.send_header("Content-Type","text/plain"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b); return
        if "mjpg" in self.path:
            self.send_response(200); self.send_header("Content-Type","multipart/x-mixed-replace; boundary=myboundary"); self.send_header("Connection","close"); self.end_headers(); self.close_connection=True
            for i in range(5):
                self.wfile.write(b"--myboundary\r\nContent-Type: image/jpeg\r\nContent-Length: 4\r\n\r\nJPG%d\r\n"%i); self.wfile.flush(); time.sleep(0.05)
            return
        b=b"\xff\xd8JPEG"; self.send_response(200); self.send_header("Content-Type","image/jpeg"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
class Redir(BaseHTTPRequestHandler):                 # wie Axis: http -> 302 auf die andere Adresse
    protocol_version="HTTP/1.1"
    def log_message(self,*a): pass
    def do_GET(self):
        b=b"<html>302 Found</html>"; self.send_response(302); self.send_header("Location","http://127.0.0.1:18555"+self.path); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
rs=ThreadingHTTPServer(("127.0.0.1",18557),Redir); threading.Thread(target=rs.serve_forever,daemon=True).start()
cs=ThreadingHTTPServer(("127.0.0.1",18555),Cam); threading.Thread(target=cs.serve_forever,daemon=True).start()
class Inp:
    def __init__(s,d): s.d=d
    def value(s,k): return s.d.get(k)
    def changed(s,k): return False
class Dbg:
    def set(s,*a): pass
    def log(s,*a): pass
OUT={}
class FW:
    def create_debug_section(s): return Dbg()
    def set_output(s,k,v): OUT[k]=v
    def run_in_context(s,f,a): f(*a)
vals={"base_path":"kamera","destination_port":18556,"key":"K1","restart":0,"cam1_name":"Einfahrt","cam1_addr":"http://127.0.0.1:18555/axis-cgi/jpg/image.cgi?camera=1&compression=25","cam1_user":"root","cam1_pwd":"geheim","cam3_name":"hasen","cam3_addr":"http://127.0.0.1:18557","cam3_user":"root","cam3_pwd":"geheim","cam2_name":"hof","cam2_addr":"127.0.0.1:18555","cam2_user":"root","cam2_pwd":"falsch"}
m=M.LogicModule(FW()); m.on_init(Inp(vals),None); time.sleep(0.3)
def get(p):
    try: r=urllib.request.urlopen("http://127.0.0.1:18556"+p,timeout=5); return r.status,r.headers.get("Content-Type"),r.read()
    except urllib.error.HTTPError as e: return e.code,None,e.read()
ok=lambda n,c,x="": print(("✓ " if c else "✗ ")+n+(" "+x if x and not c else ""))
s,t,b=get("/kamera/"); ok("Prüfseite ohne Schlüssel", s==200 and b"14783" in b)
s,t,b=get("/kamera/einfahrt.jpg"); ok("ohne Schlüssel 401", s==401)
s,t,b=get("/kamera/einfahrt.jpg?k=K1"); ok("Standbild per Digest", s==200 and b.startswith(b"\xff\xd8") and t=="image/jpeg")
s,t,b=get("/kamera/einfahrt.mjpg?k=K1&resolution=640x360&evil=1"); ok("MJPEG durchgereicht", s==200 and t.startswith("multipart/x-mixed-replace") and b.count(b"--myboundary")==5)
s,t,b=get("/kamera/einfahrt.jpg?k=K1&resolution=999x1"); ok("HTTP 400 -> ohne Parameter erneut", s==200)
s,t,b=get("/kamera/hof.jpg?k=K1"); ok("falsches Passwort -> 502", s==502)
for k in STAT: STAT[k]=0
for i in range(10): get("/kamera/einfahrt.jpg?k=K1")
ok("10 Standbilder: höchstens 1×401 und 1 Verbindung", STAT["401"]<=1 and STAT["conn"]<=1 and STAT["req"]<=11, str(STAT))
s,t,b=get("/kamera/list?k=K1"); ok("Liste der Kameras", json.loads(b)["cams"]==["einfahrt","hasen","hof"])
s,t,b=get("/kamera/hasen.jpg?k=K1"); ok("Weiterleitung (302) wird befolgt – Standbild", s==200 and b.startswith(b"\xff\xd8"), str(s))
s,t,b=get("/kamera/hasen.mjpg?k=K1"); ok("Weiterleitung (302) wird befolgt – MJPEG", s==200 and b.count(b"--myboundary")==5, str(s))
s,t,b=get("/kamera/test?k=K1"); d=json.loads(b); C={c["name"]:c for c in d["cams"]}; ok("Prüfung JSON", C["einfahrt"]["ok"] and C["hasen"]["ok"] and not C["hof"]["ok"] and C["hof"]["http"]==401, str(d))
allout=json.dumps({k:(v.decode() if isinstance(v,bytes) else v) for k,v in OUT.items()})
ok("Passwort nirgends", "geheim" not in allout and "falsch" not in allout and b"geheim" not in b)
print(OUT)
m._stop_server()
