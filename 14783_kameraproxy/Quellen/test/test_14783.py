import sys, threading, time, hashlib, os, urllib.request, json, base64, re, calendar
sys.path.insert(0, sys.argv[1]); import hsl3_14783_kameraproxy as M
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
# Fake-Axis mit Digest
REALM, NONCE = "AXIS_TEST", "abc123"
def H(s): return hashlib.md5(s.encode()).hexdigest()
STAT={"401":0,"conn":0,"req":0,"last":""}
class Cam(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.1"
    def setup(self):
        STAT["conn"]+=1; super().setup()
    def log_message(self,*a): pass
    def do_GET(self):
        STAT["req"]+=1; STAT["last"]=self.path
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
# Fake-ONVIF-Kamera: SOAP mit WS-Security (Uhr geht 1 h vor), Standbild per Basic, kein MJPEG
OPW, SKEW = "onvifpw", 3600
OST={"calls":[],"gets":[],"bad":0}
SOAP='<?xml version="1.0"?><SOAP-ENV:Envelope xmlns:SOAP-ENV="http://www.w3.org/2003/05/soap-envelope" xmlns:tt="http://www.onvif.org/ver10/schema" xmlns:tds="http://www.onvif.org/ver10/device/wsdl" xmlns:trt="http://www.onvif.org/ver10/media/wsdl"><SOAP-ENV:Body>%s</SOAP-ENV:Body></SOAP-ENV:Envelope>'
def prof(tok,name,enc,w,h): return '<trt:Profiles fixed="true" token="%s"><tt:Name>%s</tt:Name><tt:VideoSourceConfiguration token="v"><tt:Name>quelle</tt:Name><tt:Bounds x="0" y="0" width="3840" height="2160"/></tt:VideoSourceConfiguration><tt:VideoEncoderConfiguration token="e"><tt:Name>enc</tt:Name><tt:Encoding>%s</tt:Encoding><tt:Resolution><tt:Width>%d</tt:Width><tt:Height>%d</tt:Height></tt:Resolution></tt:VideoEncoderConfiguration></trt:Profiles>'%(tok,name,enc,w,h)
RES={"p_4k":"3840x2160","p_720":"1280x720"}
class OCam(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.1"
    def log_message(self,*a): pass
    def out(self,code,body,ct="application/soap+xml; charset=utf-8",extra=()):
        b=body.encode() if isinstance(body,str) else body
        self.send_response(code); self.send_header("Content-Type",ct); self.send_header("Content-Length",str(len(b)))
        for k,v in extra: self.send_header(k,v)
        self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        x=self.rfile.read(int(self.headers.get("Content-Length",0))).decode()
        op=re.search(r"<(?:\w+:)?(Get\w+)",x).group(1); OST["calls"].append((self.path,op))
        if op=="GetSystemDateAndTime":
            t=time.gmtime(time.time()+SKEW)
            return self.out(200,SOAP%('<tds:GetSystemDateAndTimeResponse><tds:SystemDateAndTime><tt:DateTimeType>NTP</tt:DateTimeType><tt:UTCDateTime><tt:Time><tt:Hour>%d</tt:Hour><tt:Minute>%d</tt:Minute><tt:Second>%d</tt:Second></tt:Time><tt:Date><tt:Year>%d</tt:Year><tt:Month>%d</tt:Month><tt:Day>%d</tt:Day></tt:Date></tt:UTCDateTime></tds:SystemDateAndTime></tds:GetSystemDateAndTimeResponse>'%(t.tm_hour,t.tm_min,t.tm_sec,t.tm_year,t.tm_mon,t.tm_mday)))
        m=re.search(r"<wsse:Username>(.*?)</wsse:Username>.*?<wsse:Password[^>]*>(.*?)</wsse:Password>.*?<wsse:Nonce[^>]*>(.*?)</wsse:Nonce>.*?<wsu:Created>(.*?)</wsu:Created>",x,re.S)
        good=False
        if m:
            u,d,n,c=m.groups(); t=calendar.timegm(time.strptime(c,"%Y-%m-%dT%H:%M:%SZ"))
            good=u=="onvifuser" and abs(t-(time.time()+SKEW))<5 and d==base64.b64encode(hashlib.sha1(base64.b64decode(n)+c.encode()+OPW.encode()).digest()).decode()
        if not good:
            OST["bad"]+=1; return self.out(400,SOAP%'<SOAP-ENV:Fault><SOAP-ENV:Reason><SOAP-ENV:Text xml:lang="en">Sender not Authorized</SOAP-ENV:Text></SOAP-ENV:Reason></SOAP-ENV:Fault>')
        tok=(re.search(r"ProfileToken>(.*?)<",x) or [0,""])[1]
        if op=="GetCapabilities": r='<tds:GetCapabilitiesResponse><tds:Capabilities><tt:Media><tt:XAddr>http://10.9.9.9/onvif/media_service</tt:XAddr><tt:StreamingCapabilities/></tt:Media></tds:Capabilities></tds:GetCapabilitiesResponse>'
        elif op=="GetProfiles": r='<trt:GetProfilesResponse>'+prof("p_4k","gross","H264",3840,2160)+prof("p_720","klein","JPEG",1280,720)+'</trt:GetProfilesResponse>'
        elif op=="GetSnapshotUri": r='<trt:GetSnapshotUriResponse><trt:MediaUri><tt:Uri>http://10.9.9.9/onvif-cgi/jpg/image.cgi?resolution=%s&amp;compression=30</tt:Uri></trt:MediaUri></trt:GetSnapshotUriResponse>'%RES[tok]
        elif op=="GetStreamUri": r='<trt:GetStreamUriResponse><trt:MediaUri><tt:Uri>rtsp://10.9.9.9/onvif-media/media.amp?profile=%s&amp;sessiontimeout=60</tt:Uri></trt:MediaUri></trt:GetStreamUriResponse>'%tok
        else: return self.out(400,SOAP%"<SOAP-ENV:Fault/>")
        self.out(200,SOAP%r)
    def do_GET(self):
        OST["gets"].append(self.path)
        if self.headers.get("Authorization","")!="Basic "+base64.b64encode(("onvifuser:"+OPW).encode()).decode():
            return self.out(401,"",extra=[("WWW-Authenticate",'Basic realm="cam"')])
        if self.path.startswith("/onvif-cgi/jpg/image.cgi") or self.path.startswith("/axis-cgi/jpg/image.cgi"):
            return self.out(200,b"\xff\xd8ONVIF","image/jpeg")
        self.out(404,"not found","text/plain")
os_=ThreadingHTTPServer(("127.0.0.1",18558),OCam); threading.Thread(target=os_.serve_forever,daemon=True).start()
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
vals={"base_path":"kamera","destination_port":18556,"key":"K1","restart":0,"cam1_name":"Einfahrt","cam1_addr":"http://127.0.0.1:18555/axis-cgi/jpg/image.cgi?camera=1&compression=25","cam1_user":"root","cam1_pwd":"geheim","cam3_name":"hasen","cam3_addr":"http://127.0.0.1:18557","cam3_user":"root","cam3_pwd":"geheim","cam2_name":"hof","cam2_addr":"127.0.0.1:18555","cam2_user":"root","cam2_pwd":"falsch",
      "cam4_name":"Garten","cam4_addr":"http://127.0.0.1:18555/custom/snap.cgi?foo=1&compression=20","cam4_user":"root","cam4_pwd":"geheim",
      "cam5_name":"strasse","cam5_addr":"onvif://127.0.0.1:18558","cam5_user":"onvifuser","cam5_pwd":OPW,
      "cam6_name":"tor","cam6_addr":"127.0.0.1:18558","cam6_user":"onvifuser","cam6_pwd":OPW}
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
s,t,b=get("/kamera/list?k=K1"); ok("Liste der Kameras", json.loads(b)["cams"]==["einfahrt","garten","hasen","hof","strasse","tor"])
s,t,b=get("/kamera/hasen.jpg?k=K1"); ok("Weiterleitung (302) wird befolgt – Standbild", s==200 and b.startswith(b"\xff\xd8"), str(s))
s,t,b=get("/kamera/hasen.mjpg?k=K1"); ok("Weiterleitung (302) wird befolgt – MJPEG", s==200 and b.count(b"--myboundary")==5, str(s))
s,t,b=get("/kamera/test?k=K1"); d=json.loads(b); C={c["name"]:c for c in d["cams"]}; ok("Prüfung JSON", C["einfahrt"]["ok"] and C["hasen"]["ok"] and not C["hof"]["ok"] and C["hof"]["http"]==401, str(d))
def frames(p,n=3):
    r=urllib.request.urlopen("http://127.0.0.1:18556"+p,timeout=5); t=r.headers.get("Content-Type"); b=b""; t0=time.time()
    while b.count(b"--hsframe")<n:
        c=r.read(32)
        if not c: break
        b+=c
    r.close(); return t,b,time.time()-t0
# --- 0.5: ganze Standbild-Adresse
s,t,b=get("/kamera/garten.jpg?k=K1"); ok("Adresse mit Pfad: Pfad und Parameter werden übernommen", s==200 and STAT["last"]=="/custom/snap.cgi?foo=1&compression=20", STAT["last"])
s,t,b=get("/kamera/garten.jpg?k=K1&compression=50"); ok("Adresse mit Pfad: Browser-Parameter überschreibt Vorgabe", s==200 and STAT["last"]=="/custom/snap.cgi?foo=1&compression=50", STAT["last"])
s,t,b=get("/kamera/garten.jpg?k=K1&resolution=640x360"); ok("Adresse mit Pfad: HTTP 400 -> Vorgabe", s==200 and STAT["last"]=="/custom/snap.cgi?foo=1&compression=20", STAT["last"])
n0=STAT["req"]; s,t,b=get("/kamera/garten.jpg?k=K1&resolution=640x360"); ok("abgelehnte Parameter werden gemerkt (1 Abruf)", s==200 and STAT["req"]-n0==1, str(STAT["req"]-n0))
t,b,dt=frames("/kamera/garten.mjpg?k=K1&fps=10"); ok("Strom aus Standbildern (Adresse mit Pfad)", t=="multipart/x-mixed-replace; boundary=hsframe" and b"Content-Length: 6\r\n\r\n\xff\xd8JPEG\r\n--hsframe" in b, repr(b[:120]))
ok("Strom aus Standbildern hält die Bildrate (10/s)", 0.15<dt<1.0, "%.2f s"%dt)
# --- 0.5: ONVIF
t0=time.time(); s,t,b=get("/kamera/strasse.jpg?k=K1"); ok("ONVIF: Standbild (erst https, dann http; %.1f s)"%(time.time()-t0), s==200 and b==b"\xff\xd8ONVIF", str((s,b)))
ok("ONVIF: Standard 1280x720 -> kleines Profil", OST["gets"][-1]=="/onvif-cgi/jpg/image.cgi?resolution=1280x720&compression=30", OST["gets"][-1])
ok("ONVIF: WS-Security mit Kamera-Uhr (+1 h) angenommen", OST["bad"]==0, str(OST["bad"]))
ok("ONVIF: Mediendienst aus GetCapabilities, Host bleibt", ("/onvif/media_service","GetProfiles") in OST["calls"] and ("/onvif/device_service","GetCapabilities") in OST["calls"], str(OST["calls"]))
s,t,b=get("/kamera/strasse.jpg?k=K1&resolution=3840x2160"); ok("ONVIF: Auflösung wählbar -> großes Profil", s==200 and OST["gets"][-1]=="/onvif-cgi/jpg/image.cgi?resolution=3840x2160&compression=30", OST["gets"][-1])
s,t,b=get("/kamera/strasse.jpg?k=K1&resolution=640x360&compression=60"); ok("ONVIF: Zwischengröße über Parameter der Kamera", s==200 and OST["gets"][-1]=="/onvif-cgi/jpg/image.cgi?resolution=640x360&compression=60", OST["gets"][-1])
for i in range(5): get("/kamera/strasse.jpg?k=K1")
ok("ONVIF: Ermittlung nur einmal", [c[1] for c in OST["calls"]].count("GetProfiles")==1 and [c[1] for c in OST["calls"]].count("GetSnapshotUri")==2, str(OST["calls"]))
t,b,dt=frames("/kamera/strasse.mjpg?k=K1"); ok("ONVIF: Strom aus Standbildern", t.endswith("boundary=hsframe") and b.count(b"\xff\xd8ONVIF")>=2)
t,b,dt=frames("/kamera/tor.mjpg?k=K1"); ok("Axis-Pfade ohne MJPEG (404) -> Strom aus Standbildern", t.endswith("boundary=hsframe") and b.count(b"\xff\xd8ONVIF")>=2)
s,t,b=get("/kamera/test?k=K1"); d=json.loads(b); C={c["name"]:c for c in d["cams"]}; o=C["strasse"]
ok("Prüfung zeigt Art, Profile, Standbild und Strom ohne Host", o["ok"] and o["art"]=="onvif" and len(o["profile"])==2 and o["profil"]=="klein 1280x720" and o["standbild"].startswith("/onvif-cgi/") and o["strom"]=="rtsp://…/onvif-media/media.amp?profile=p_720&sessiontimeout=60" and b"10.9.9.9" not in b and b"127.0.0.1" not in b and C["garten"]["art"]=="url" and C["garten"]["ziel"]=="http://…/custom/snap.cgi" and C["einfahrt"]["art"]=="axis", str(d))
ok("ONVIF-Passwort nirgends", OPW.encode() not in b and "onvifuser" not in str(d))
v2=dict(vals, cam5_pwd="daneben"); m.on_calc(Inp(v2)); s,t,b=get("/kamera/strasse.jpg?k=K1"); ok("ONVIF: falsches Passwort -> 502", s==502 and OST["bad"]>=1, str(s))
n0=len(OST["calls"]); s,t,b=get("/kamera/strasse.jpg?k=K1"); ok("ONVIF: nach Fehler nicht sofort neu abfragen", s==502 and len(OST["calls"])==n0, str(len(OST["calls"])-n0))
m.on_calc(Inp(vals)); s,t,b=get("/kamera/strasse.jpg?k=K1"); ok("ONVIF: Passwort korrigiert -> läuft wieder", s==200, str(s))
s,t,b=get("/kamera/test?k=K1")
allout=json.dumps({k:(v.decode() if isinstance(v,bytes) else v) for k,v in OUT.items()})
ok("Passwort nirgends", "geheim" not in allout and "falsch" not in allout and OPW not in allout and b"geheim" not in b)
print(OUT)
m._stop_server()
