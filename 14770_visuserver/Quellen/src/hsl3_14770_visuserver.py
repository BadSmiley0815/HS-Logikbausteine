# -*- coding: utf-8 -*-
"""
HSL3 14770 – Visu-Server (v1.10)

Datenzentrale für die HTML5-Visu (homeserver-webapp). Der HomeServer leitet
https://<HS>/<Basis-Pfad>/… an diesen Baustein weiter (HSL3-Eingänge base_path /
destination_port) – gleiche Adresse und gleiches Zertifikat wie die Visu selbst.

Aufgaben:
  * Einrichtung der Visu speichern (Kacheln, Räume, Favoriten …) – für alle Geräte gleich
  * Verläufe der Bausteine 14771 (ab v2.0) für Diagramme ausliefern
  * Sichern/Wiederherstellen aller Daten als JSON

Speicherung: komprimiert, verteilt auf remanente Speichervariablen mit je < 10.000 Zeichen
(Test auf HS 4.x: pro Variable bleiben nach einem Neustart genau 10.000 Zeichen erhalten,
20 Variablen à 9.999 Zeichen überstanden Neustart und Projektübertragung).

Eingänge:
  E1  base_path          Basis-Pfad, Standard "visu-daten"  → https://<HS>/visu-daten/
  E2  destination_port   interner Port, Standard 8092
  E3  Schlüssel          Zugangsschlüssel; die Visu schickt ihn bei jedem Abruf mit.
                         Leer = kein Schutz (nicht empfohlen).
  E5  Lese-Schlüssel     nur Lesen der Verläufe (Diagrammseite chart, z. B. als iFrame in
                         der Experten-Visu). Leer = Lesen nur mit dem Schlüssel E3.
  E4  Neustart/Auslöser  für den Experten, der mindestens einen mit einem KO belegten
                         Eingang verlangt. Beliebiges KO anschließen (z. B. ein internes
                         KO oder das Schlüssel-/Status-KO). Wert 1 = Server neu starten,
                         jeder andere Wert = nur Ausgänge neu senden. Unbelegt = ohne Funktion.
Ausgänge:
  A1  Instanz-ID         an E5 der Verlaufs-Bausteine 14771 anschließen
  A2  Status
  A3  Anzahl Abrufe
  A4  Anzahl angemeldeter Verläufe
  A5  Stand der Einrichtung (Unix-Zeit in ms / 1000)

Diagrammseite (v1.8):
  GET  chart?id=a,b&u=h&n=168&key=<Lese-Schlüssel>&title=…&refresh=60&nav=1&ymin=&ymax=&color=
       schlanke Seite nur mit dem Diagramm (Mausover mit Werten), zum Einbetten per iFrame

Diagramm als Bild (v1.9):
  GET  chart.svg?id=a,b&u=i&n=&key=<Lese-Schlüssel>&title=…&w=940&h=420&ymin=&ymax=&color=&bg=fff&view=table
       Min/Max/Mittel unter dem Titel, Höchst-/Tiefstwert beschriftet (bis 31 Werte: jeder Wert);
       view=table: Wertetabelle (Zeit | Wert), neueste zuerst
       v1.10 chart-Seite: Legende anklicken = Verlauf ein-/ausblenden (sofort, Auswahl bleibt im Browser),
       zweite Achse für zweite Einheit, Kennzahlenzeile; Einbau in die Experten-Visu per Textelement
       „@iframe=/visu-daten/chart?id=…“ und Visu-Adresse mit &extras=1
       v1.10 chart.svg: mehrere Verläufe in einem Bild; zweite Einheit (z. B. %) auf eigener rechter Achse
       (gestrichelt); % mit 0–100 fest; ymin2/ymax2 für die rechte Achse; hide=<Kennung,…> blendet aus;
       14771 E11 = 0 blendet ebenfalls aus (grau „(aus)“ in der Legende)
  GET  chart.png?…  (v1.10) dasselbe Diagramm als PNG – für das Kamera-Element der Experten-Visu,
       das sein Bild zyklisch neu lädt (Live-Diagramm); 4 s Zwischenspeicher je Aufruf
       fertiges SVG-Bild – für die Experten-/Firmware-Visu (/hsvisu/), die kein HTML im Text
       zulässt: Textelement, CSS-Stil
       background:url(/visu-daten/chart.svg?id=…&u=i&w=940&h=420) no-repeat center/100% 100%

API (JSON, Schlüssel per Header "X-Visu-Key" oder ?key=):
  GET  api/ping                 Version, Anzahl Verläufe, Stand der Einrichtung
  GET  api/config               {rev, config}
  GET  api/config/rev           {rev}
  POST api/config               Body {rev, config} → speichern
  GET  api/histories            angemeldete Verläufe
  GET  api/history?id=…&u=h&n=168   Werte einer Ansicht (u: i,h,d,w,M,y)
  GET  api/export               Sicherung (Einrichtung + alle Verläufe)
  POST api/import?mode=merge|replace   Wiederherstellung (Body = Sicherung); merge = nur fehlende Werte/Kacheln
"""
import base64
import hmac
import json
import threading
import time
import urllib.parse
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "1.10"
CFG_STORES = 10          # 10 × 9.900 Zeichen ≈ 99 KB komprimiert
CHUNK = 9900
MAX_BODY = 4 * 1024 * 1024

PAGE = """<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>14770 Visu-Server (v@@VER@@)</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;color:#222;background:#f6f7f9}
main{max-width:900px;margin:0 auto;padding:16px}
h2{margin:.2em 0}.mu{color:#777;font-size:.9em}
.card{background:#fff;border:1px solid #e3e5e8;border-radius:10px;padding:12px 14px;margin:12px 0}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
input,select,button{font:inherit;padding:6px 9px;border:1px solid #c9ccd1;border-radius:7px;background:#fff}
button{cursor:pointer;background:#eef2f7}button:hover{background:#e2e8f0}
table{border-collapse:collapse;width:100%;font-size:.95em}
td,th{border-bottom:1px solid #eee;padding:4px 8px;text-align:left}
th{position:sticky;top:0;background:#fafafa}td.n{text-align:right;font-variant-numeric:tabular-nums}
.tw{max-height:60vh;overflow:auto}code{background:#f2f2f2;padding:1px 5px;border-radius:5px;cursor:copy}
.back{display:inline-block;margin:0 0 10px;padding:7px 12px;border:1px solid #c9ccd1;border-radius:8px;background:#fff;color:#222;text-decoration:none;cursor:pointer}
.back:hover{background:#eef2f7}.err{color:#b00020}.ok{color:#11772d}
</style></head><body><main>
<a id="back" class="back" hidden>&larr; Zurück zum Diagramm</a>
<h2>14770 – Visu-Server (v@@VER@@)</h2><div class="mu">Baustein-ID 14770 · Version @@VER@@</div>
<div class="card row"><input id="k" type="password" placeholder="Schlüssel (E3)" autocomplete="current-password">
<button onclick="load()">Anzeigen</button><span id="info" class="mu"></span></div>
<div class="card"><div class="row">
<label>Verlauf <select id="hs" onchange="show()"></select></label>
<label>Ansicht <select id="u" onchange="show()">
<option value="i">Minute (24 h)</option><option value="h" selected>Stunde (1 Jahr)</option><option value="d">Tag (10 Jahre)</option>
<option value="w">Woche (10 Jahre)</option><option value="M">Monat (20 Jahre)</option><option value="y">Jahr (50 Jahre)</option></select></label>
<label><input type="checkbox" id="gaps" onchange="show()"> Lücken zeigen</label>
<button onclick="refresh(this)" title="Werte neu laden">&#x21bb; Aktualisieren</button><button onclick="csv()">CSV</button><span id="ts" class="mu"></span></div>
<p id="hint" class="mu">Zeile löschen: die Nummer (Nr.) an E10 des Bausteins 14771 senden, -1 löscht alle Werte dieses Verlaufs. Klick auf die Nummer kopiert sie.</p>
<div class="tw"><table id="t"></table></div></div>
<div class="card"><b>Sicherung</b><div class="row" style="margin-top:6px">
<button onclick="exp()">Sicherung herunterladen</button>
</div><div class="row" style="margin-top:8px"><label>Beim Einspielen <select id="im"><option value="merge">nur fehlende Werte ergänzen</option><option value="replace">alles überschreiben</option></select></label>
<label>Sicherung einspielen <input type="file" id="f" accept=".json,application/json" onchange="imp(this)"></label></div>
<div id="imsg" class="mu"></div></div>
</main><script>
const base=location.origin+location.pathname.replace(/\\/?(index\\.html)?$/,'/');
const $=s=>document.getElementById(s);
let H=[],cur=null;
const P=new URLSearchParams(location.search);let want={id:P.get('id'),u:P.get('u')};
try{let k=sessionStorage.getItem('vk')||'';
 if(!k){const c=JSON.parse(localStorage.getItem('hs-visu-config-v1')||'{}');k=c.srvKey||'';}$('k').value=k;}catch(e){}
(function(){const b=$('back'),bk=P.get('back');
 if(bk&&/^https?:\/\//.test(bk)&&bk.indexOf(location.origin+'/')===0){b.href=bk;b.hidden=false;}
 else if(document.referrer&&history.length>1){b.textContent='\u2190 Zurück';b.onclick=e=>{e.preventDefault();history.back();};b.hidden=false;}})();
if(want.u&&/^[ihdwMy]$/.test(want.u))$('u').value=want.u;
async function j(p,o){o=o||{};o.headers=Object.assign({'X-Visu-Key':$('k').value},o.headers||{});o.cache='no-store';
 const r=await fetch(base+p,o);let d=null;try{d=await r.json();}catch(e){}
 if(!r.ok) throw new Error((d&&d.error)||('HTTP '+r.status));return d;}
async function load(){try{sessionStorage.setItem('vk',$('k').value);}catch(e){}
 try{const p=await j('api/ping');const h=await j('api/histories');H=h.histories.sort((a,b)=>a.name.localeCompare(b.name));
  $('info').innerHTML='<span class="ok">verbunden</span> · Einrichtung vom '+(p.config_rev?new Date(p.config_rev).toLocaleString('de-DE'):'–')+' · '+H.length+' Verläufe';
  const old=$('hs').value;$('hs').innerHTML=H.map(x=>'<option value="'+esc(x.id)+'">'+esc(x.name)+' ('+esc(x.id)+')'+(x.unit?' – '+esc(x.unit):'')+'</option>').join('');
  if(want.id&&H.some(x=>x.id===want.id)){$('hs').value=want.id;want.id=null;}else if(H.some(x=>x.id===old))$('hs').value=old;show();}
 catch(e){$('info').innerHTML='<span class="err">Fehler: '+esc(e.message)+'</span>';}}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function back(t,u,k){const d=new Date(t);if(u==='i')return t-k*60000;if(u==='h')d.setHours(d.getHours()-k);
 else if(u==='d')d.setDate(d.getDate()-k);else if(u==='w')d.setDate(d.getDate()-7*k);else if(u==='M')d.setMonth(d.getMonth()-k);
 else d.setFullYear(d.getFullYear()-k);return d.getTime();}
const p2=n=>String(n).padStart(2,'0');
function fdate(t){const d=new Date(t);return p2(d.getDate())+'.'+p2(d.getMonth()+1)+'.'+d.getFullYear();}
function ftime(t){const d=new Date(t);return p2(d.getHours())+':'+p2(d.getMinutes());}
const WD=['So','Mo','Di','Mi','Do','Fr','Sa'],MN=['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'];
function label(t,u){const d=new Date(t);if(u==='i'||u==='h')return WD[d.getDay()]+' '+fdate(t)+' '+ftime(t);
 if(u==='d')return WD[d.getDay()]+' '+fdate(t);if(u==='w')return 'KW ab '+fdate(t);if(u==='M')return MN[d.getMonth()]+' '+d.getFullYear();return String(d.getFullYear());}
const RB={i:10000,h:20000,d:30000,w:40000,M:50000,y:60000};
async function show(){const id=$('hs').value,u=$('u').value;if(!id){$('t').innerHTML='<tr><td class="mu">Kein Verlauf angemeldet.</td></tr>';return;}
 try{cur=await j('api/history?id='+encodeURIComponent(id)+'&u='+u);const n=cur.vals.length,rows=[];
  for(let k=0;k<n;k++){const v=cur.vals[n-1-k];if(v===null&&!$('gaps').checked)continue;const t=back(cur.t_last,u,k);
   rows.push('<tr><td>'+(v===null?'<span class="mu">'+(RB[u]+n-k)+'</span>':'<code title="kopieren" onclick="cp(this)">'+(RB[u]+n-k)+'</code>')+'</td><td>'+label(t,u)+'</td><td class="n">'+(v===null?'<span class="mu">–</span>':esc(String(v).replace('.',','))+(cur.unit?' '+esc(cur.unit):''))+'</td></tr>');}
  $('ts').textContent='Stand '+new Date().toLocaleTimeString('de-DE');
  $('t').innerHTML='<tr><th>Nr.</th><th>Zeit</th><th style="text-align:right">Wert</th></tr>'+(rows.join('')||'<tr><td colspan="3" class="mu">Noch keine Werte in dieser Ansicht.</td></tr>');}
 catch(e){$('t').innerHTML='<tr><td class="err">'+esc(e.message)+'</td></tr>';}}
async function refresh(b){b.disabled=true;try{await load();}finally{b.disabled=false;}}
function cp(el){navigator.clipboard&&navigator.clipboard.writeText(el.textContent);el.style.background='#d9f2df';setTimeout(()=>el.style.background='',700);}
function dl(name,data,type){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([data],{type}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000);}
function csv(){if(!cur)return;const u=$('u').value,n=cur.vals.length,l=['Zeit;Wert'];
 for(let k=n-1;k>=0;k--){const v=cur.vals[n-1-k];if(v===null)continue;l.push(label(back(cur.t_last,u,k),u)+';'+String(v).replace('.',','));}
 dl(cur.id+'_'+u+'.csv','﻿'+l.join('\\r\\n'),'text/csv');}
async function exp(){try{const d=await j('api/export');dl('visu-server-sicherung-'+new Date().toISOString().slice(0,10)+'.json',JSON.stringify(d),'application/json');}
 catch(e){$('imsg').innerHTML='<span class="err">'+esc(e.message)+'</span>';}}
async function imp(inp){const f=inp.files[0];inp.value='';if(!f)return;
 const mode=$('im').value;
 if(!confirm('Sicherung „'+f.name+'“ einspielen?\\n'+(mode==='merge'?'Nur fehlende Werte und fehlende Kacheln werden ergänzt, Vorhandenes bleibt.':'Einrichtung und Verläufe werden ÜBERSCHRIEBEN.')))return;
 $('imsg').textContent='wird eingespielt …';
 try{const d=await j('api/import?mode='+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:await f.text()});
  $('imsg').innerHTML='<span class="ok">'+(d.mode==='merge'?'Ergänzt':'Überschrieben')+':</span> Einrichtung '+(d.config?'✓'+(d.tiles_added!==undefined?' ('+d.tiles_added+' Kacheln neu)':''):'–')+', '+d.histories_queued.length+' Verläufe'+
   (d.histories_unknown.length?' · <span class="err">nicht angemeldet: '+esc(d.histories_unknown.join(', '))+'</span>':'')+
   ' – die Verläufe werden innerhalb einer Minute übernommen.';setTimeout(load,65000);}
 catch(e){$('imsg').innerHTML='<span class="err">Fehler: '+esc(e.message)+'</span>';}}
if($('k').value)load();else j('api/ping').then(load,()=>{});
</script></body></html>""".replace("@@VER@@", VERSION)


CHART = r"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>14770 Diagramm</title>
<style>
html,body{margin:0;height:100%;overflow:hidden;font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#222;background:transparent}
#w{position:absolute;inset:0;display:flex;flex-direction:column;padding:4px 6px;box-sizing:border-box}
#top{display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px;min-height:18px}
#ttl{font-weight:bold}
#leg{display:flex;flex-wrap:wrap;gap:2px 12px}
.li{display:flex;align-items:center;gap:4px;white-space:nowrap;cursor:pointer;user-select:none;padding:1px 4px;border-radius:4px}
.li:hover{background:#eef2f7}.li.off{opacity:.45;text-decoration:line-through}
#st{display:flex;flex-wrap:wrap;gap:0 14px;font-size:11px;min-height:14px}
.sw{display:inline-block;width:12px;height:3px;border-radius:2px}
#nav{margin-left:auto;display:flex;gap:3px}
#nav button{font:inherit;font-size:11px;padding:1px 6px;border:1px solid #9aa4b1;border-radius:4px;background:#f3f5f8;cursor:pointer}
#nav button.zr{background:#fff3e0;border-color:#e67700;color:#a14d00}
#nav button.on{background:#2b6cb0;border-color:#2b6cb0;color:#fff}
#c{flex:1;position:relative;min-height:60px}
svg{position:absolute;inset:0;width:100%;height:100%;display:block}
.ax{stroke:#9aa4b1;stroke-width:1}.gr{stroke:#dde2e8;stroke-width:1}
.tx{fill:#555;font-size:11px}
#tip{position:absolute;pointer-events:none;background:rgba(255,255,255,.96);border:1px solid #9aa4b1;border-radius:5px;padding:4px 7px;font-size:12px;white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,.15);display:none;z-index:2}
#msg{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#888}
#sb{display:none;align-items:center;gap:8px;margin:3px 0 0;font-size:11px;color:#555}#rg{flex:1;margin:0;height:18px;accent-color:#2b6cb0;cursor:pointer}#rgl{white-space:nowrap;min-width:150px;text-align:right}
</style></head><body><div id="w"><div id="top"><span id="ttl"></span><span id="leg"></span><span id="nav"></span></div><div id="st"></div>
<div id="c"><svg id="s"></svg><div id="tip"></div><div id="msg">lädt …</div></div><div id="sb"><input type="range" id="rg" min="0" max="1000" value="1000" title="Zeitraum verschieben"><span id="rgl"></span></div></div>
<script>
(function(){
var P=new URLSearchParams(location.search);
var base=location.pathname.replace(/\/chart(\.html)?\/?$/,'/');
var ids=(P.get('id')||'').split(',').map(function(x){return x.trim();}).filter(Boolean);
var key=P.get('key')||'';
var U=P.get('u')||'h', N=parseInt(P.get('n')||'0',10)||0;
var REF=Math.max(10,parseInt(P.get('refresh')||'60',10)||60);
var YMIN=P.has('ymin')?parseFloat(P.get('ymin')):null, YMAX=P.has('ymax')?parseFloat(P.get('ymax')):null;
var COL=['#2b6cb0','#d9480f','#2f9e44','#9c36b5','#c2255c','#0c8599','#e67700','#5c5f66'];
if(P.get('color'))COL=P.get('color').split(',').map(function(c){return '#'+c.replace('#','');}).concat(COL);
var NAV=[['i',60,'1 h'],['i',720,'12 h'],['i',1440,'24 h'],['h',48,'48 h'],['h',168,'7 Tage'],['h',720,'30 Tage'],['d',365,'1 Jahr',92],['d',730,'2 Jahre',92],['d',1095,'3 Jahre',92]];
var WIN=0,SCR=null,REQ=null,ZOOM=null,DRAG=null;
var DEF={i:1440,h:168,d:60,w:104,M:24,y:20};
var OFF=(P.get('hide')||'').split(',').filter(Boolean);try{var _o=JSON.parse(localStorage.getItem('rx_off_'+ids.join(','))||'null');if(_o)OFF=_o;}catch(e){}
var S=[], TT=document.getElementById('tip'), SV=document.getElementById('s'), C=document.getElementById('c');
document.getElementById('ttl').textContent=P.get('title')||'';
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function back(t,u,k){var d=new Date(t);if(u==='i')return t-k*60000;if(u==='h')return t-k*3600000;
 if(u==='d')d.setDate(d.getDate()-k);else if(u==='w')d.setDate(d.getDate()-7*k);else if(u==='M')d.setMonth(d.getMonth()-k);else d.setFullYear(d.getFullYear()-k);return d.getTime();}
var p2=function(n){return (n<10?'0':'')+n;};
var WD=['So','Mo','Di','Mi','Do','Fr','Sa'],MN=['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'];
function lab(t,u,long){var d=new Date(t),dt=p2(d.getDate())+'.'+p2(d.getMonth()+1)+'.',hm=p2(d.getHours())+':'+p2(d.getMinutes());
 if(u==='i')return long?WD[d.getDay()]+' '+dt+' '+hm:hm;
 if(u==='h')return long?WD[d.getDay()]+' '+dt+' '+hm:(d.getHours()===0?dt:hm);
 if(u==='d')return long?WD[d.getDay()]+' '+dt+d.getFullYear():dt;
 if(u==='w')return long?'KW ab '+dt+d.getFullYear():dt;
 if(u==='M')return MN[d.getMonth()]+(long||d.getMonth()===0?' '+d.getFullYear():'');return String(d.getFullYear());}
var MIN=60000,HR=3600000,DY=86400000;
var STEPS=[[MIN,'m'],[5*MIN,'m'],[10*MIN,'m'],[15*MIN,'m'],[30*MIN,'m'],[HR,'m'],[2*HR,'m'],[3*HR,'m'],[6*HR,'m'],[12*HR,'m'],[DY,'d'],[2*DY,'d'],[7*DY,'d'],[14*DY,'d'],[1,'M'],[3,'M'],[6,'M'],[12,'y'],[24,'y'],[60,'y'],[120,'y']];
function xticks(t0,t1,n){var span=t1-t0,st=STEPS[STEPS.length-1];
 for(var i=0;i<STEPS.length;i++){var s=STEPS[i],len=s[1]==='M'||s[1]==='y'?s[0]*30.4*DY:s[0];if(span/len<=n){st=s;break;}}
 var out=[],d=new Date(t0);
 if(st[1]==='m'){d.setSeconds(0,0);var off=d.getTimezoneOffset()*MIN,t=Math.ceil((d.getTime()-off)/st[0])*st[0]+off;
  for(;t<=t1;t+=st[0]){var q=new Date(t);out.push([t,(q.getHours()===0&&q.getMinutes()===0&&span>12*HR)?p2(q.getDate())+'.'+p2(q.getMonth()+1)+'.':p2(q.getHours())+':'+p2(q.getMinutes())]);}}
 else if(st[1]==='d'){d.setHours(0,0,0,0);if(d.getTime()<t0)d.setDate(d.getDate()+1);var k=st[0]/DY;
  if(k===7){while(d.getDay()!==1)d.setDate(d.getDate()+1);}
  for(;d.getTime()<=t1;d.setDate(d.getDate()+k))out.push([d.getTime(),p2(d.getDate())+'.'+p2(d.getMonth()+1)+'.']);}
 else{var m=st[1]==='y'?st[0]:st[0];d.setHours(0,0,0,0);d.setDate(1);if(d.getTime()<t0)d.setMonth(d.getMonth()+1);
  while(d.getMonth()%Math.min(m,12)!==0)d.setMonth(d.getMonth()+1);
  for(;d.getTime()<=t1;d.setMonth(d.getMonth()+m))out.push([d.getTime(),m>=12?String(d.getFullYear()):MN[d.getMonth()]+(d.getMonth()===0?' '+d.getFullYear():'')]);}
 return out;}
function fmt(v,dec){if(v===null||v===undefined)return '–';return Number(v).toLocaleString('de-DE',{minimumFractionDigits:dec,maximumFractionDigits:dec});}
function nav(){var h='';NAV.forEach(function(x){if(x[0]===U&&(x[1]||DEF[x[0]])===(N||DEF[U]))WIN=(x[3]||0)*DY;});NAV.forEach(function(x,i){h+='<button data-i="'+i+'"'+(x[0]===U&&(x[1]||DEF[x[0]])===(N||DEF[U])?' class="on"':'')+'>'+x[2]+'</button>';});
 var n=document.getElementById('nav');n.innerHTML=(ZOOM?'<button class="zr" id="zr" title="Zoom aufheben (oder Doppelklick ins Diagramm)">&#8634; Zoom zurück</button>':'')+(P.get('nav')==='0'?'':h);var zr=document.getElementById('zr');if(zr)zr.onclick=function(){ZOOM=null;nav();draw();};
 Array.prototype.forEach.call(n.querySelectorAll('button[data-i]'),function(b){b.onclick=function(){var x=NAV[+b.dataset.i];U=x[0];N=x[1];WIN=(x[3]||0)*DY;SCR=null;ZOOM=null;nav();load();};});}
function get(id){return fetch(base+'api/history?id='+encodeURIComponent(id)+'&u='+U+'&n='+(N||DEF[U])+(key?'&key='+encodeURIComponent(key):''),{cache:'no-store'})
 .then(function(r){return r.json().then(function(d){if(!r.ok)throw new Error(d&&d.error||('HTTP '+r.status));return d;});});}
function load(){if(!ids.length){msg('Kein Verlauf angegeben (?id=…)');return;}
 Promise.all(ids.map(get)).then(function(rs){var tl=Math.max.apply(null,rs.map(function(d){return d.t_last||0;}));REQ={t0:back(tl,U,(N||DEF[U])-1),t1:tl};S=rs.map(function(d,i){var n=d.vals.length,pts=[];
   for(var k=0;k<n;k++){pts.push([back(d.t_last,U,n-1-k),d.vals[k]]);}
   return {id:d.id,name:d.name||d.id,unit:d.unit||'',dec:(d.dec===undefined?1:d.dec),col:COL[i%COL.length],pts:pts,cur:d.current,on:OFF.indexOf(d.id)<0};});
  legend();draw();msg('');}).catch(function(e){msg('Fehler: '+e.message);});}
function msg(t){var m=document.getElementById('msg');m.textContent=t;m.style.display=t?'flex':'none';}
function legend(){var lg=document.getElementById('leg');lg.innerHTML=S.map(function(s,i){return '<span class="li'+(s.on?'':' off')+'" data-i="'+i+'" title="Klick: ein-/ausblenden"><span class="sw" style="background:'+s.col+'"></span>'+esc(s.name)+': <b>'+fmt(s.cur,s.dec)+(s.unit?' '+esc(s.unit):'')+'</b></span>';}).join('');
 Array.prototype.forEach.call(lg.querySelectorAll('.li'),function(el){el.onclick=function(){var s=S[+el.dataset.i];s.on=!s.on;
  OFF=S.filter(function(x){return !x.on;}).map(function(x){return x.id;});try{localStorage.setItem('rx_off_'+ids.join(','),JSON.stringify(OFF));}catch(e){}legend();draw();};});
 document.getElementById('st').innerHTML=S.filter(function(s){return s.on;}).map(function(s){var v=s.pts.map(function(p){return p[1];}).filter(function(x){return x!==null;});
  if(!v.length)return '';var mn=Math.min.apply(null,v),mx=Math.max.apply(null,v),av=v.reduce(function(a,b){return a+b;},0)/v.length,u=s.unit?' '+esc(s.unit):'';
  return '<span style="color:'+s.col+'">'+esc(s.name)+': '+(mn===mx?'konstant '+fmt(mn,s.dec)+u:'Min '+fmt(mn,s.dec)+' · Max '+fmt(mx,s.dec)+' · Ø '+fmt(av,s.dec)+u)+'</span>';}).join('');}
function nice(lo,hi,n){var r=hi-lo||Math.abs(hi)||1,st=Math.pow(10,Math.floor(Math.log10(r/n))),e=r/n/st;st*=e>5?10:e>2?5:e>1?2:1;
 var a=Math.floor(lo/st)*st,b=Math.ceil(hi/st)*st,t=[];for(var v=a;v<=b+st/2;v+=st)t.push(+v.toFixed(10));return {a:a,b:b,t:t,st:st};}
var G=null;
function draw(){var W=C.clientWidth,H=C.clientHeight;if(!W||!H)return;
 var V=S.filter(function(s){return s.on;}),units=[];
 V.forEach(function(s){if(s.pts.some(function(p){return p[1]!==null;})&&units.indexOf(s.unit)<0)units.push(s.unit);});
 S.forEach(function(s){s.ax=(units.length>1&&s.unit===units[1])?1:0;});
 var t0=Infinity,t1=-Infinity,lo=[Infinity,Infinity],hi=[-Infinity,-Infinity];
 V.forEach(function(s){s.pts.forEach(function(p){if(p[0]<t0)t0=p[0];if(p[0]>t1)t1=p[0];if(p[1]!==null){if(p[1]<lo[s.ax])lo[s.ax]=p[1];if(p[1]>hi[s.ax])hi[s.ax]=p[1];}});});
 if(REQ&&isFinite(t0)){t0=Math.min(t0,REQ.t0);t1=Math.max(t1,REQ.t1);}
 var sb=document.getElementById('sb'),win=WIN&&isFinite(t0)&&(t1-t0)>WIN;sb.style.display=win?'flex':'none';
 if(win){var full=t1-t0,rg=document.getElementById('rg');if(SCR===null){SCR=1;rg.value=1000;}
  var e1=t0+WIN+SCR*(full-WIN);t0=e1-WIN;t1=e1;
  var df=function(t){var d=new Date(t);return p2(d.getDate())+'.'+p2(d.getMonth()+1)+'.'+d.getFullYear();};
  document.getElementById('rgl').textContent=df(t0)+' – '+df(t1);
  rg.oninput=function(){SCR=rg.value/1000;if(!rg._r){rg._r=1;requestAnimationFrame(function(){rg._r=0;draw();});}};}
 if(ZOOM){var f0=t0,f1=t1,zw=ZOOM[1]-ZOOM[0];if(ZOOM[0]<f0)ZOOM=[f0,f0+zw];if(ZOOM[1]>f1)ZOOM=[f1-zw,f1];t0=ZOOM[0];t1=ZOOM[1];
  if(f1-f0>zw+1){var rz=document.getElementById('rg');sb.style.display='flex';rz.value=Math.round((t0-f0)/(f1-f0-zw)*1000);
   var dz=function(t){var d=new Date(t);return p2(d.getDate())+'.'+p2(d.getMonth()+1)+'. '+p2(d.getHours())+':'+p2(d.getMinutes());};
   document.getElementById('rgl').textContent=dz(t0)+' – '+dz(t1);
   rz.oninput=function(){var a=f0+rz.value/1000*(f1-f0-zw);ZOOM=[a,a+zw];if(!rz._r){rz._r=1;requestAnimationFrame(function(){rz._r=0;draw();});}};}else sb.style.display='none';}
 var inr=function(p){return p[0]>=t0-1&&p[0]<=t1+1;};
 if(!isFinite(lo[0])){SV.innerHTML='';G=null;msg(S.length&&!V.length?'Alle Werte ausgeblendet – Legende anklicken':'Noch keine Werte');return;}
 msg('');var two=units.length>1,ny=Math.max(2,Math.floor(H/40));
 function scale(k){var a=lo[k],b=hi[k];if(units[k]==='%'&&a>=0&&b<=100){var t=[];for(var v=0;v<=100;v+=ny>=5?20:25)t.push(v);return {a:0,b:100,t:t,st:20};}
  if(k===0){if(YMIN!==null)a=YMIN;if(YMAX!==null)b=YMAX;}if(a===b){a-=1;b+=1;}return nice(a,b,ny);}
 var ax=[scale(0)];if(two)ax.push(scale(1));
 var labs=ax.map(function(yt){var dec=Math.max(0,-Math.floor(Math.log10(yt.st)+1e-9));return yt.t.map(function(v){return fmt(v,dec);});});
 var wl=function(l){return 8+6.5*Math.max.apply(null,l.map(function(x){return x.length;}));};
 var L=wl(labs[0]),R=two?wl(labs[1]):8,T=two?20:8,B=18;
 var pw=W-L-R,ph=H-T-B,X=function(t){return L+(t1===t0?pw/2:(t-t0)/(t1-t0)*pw);},Y=function(v,k){var yt=ax[k||0];return T+ph-(v-yt.a)/(yt.b-yt.a)*ph;};
 var o='';ax[0].t.forEach(function(v,i){var y=Y(v,0).toFixed(1);o+='<line class="gr" x1="'+L+'" x2="'+(L+pw)+'" y1="'+y+'" y2="'+y+'"/><text class="tx" x="'+(L-4)+'" y="'+(+y+4)+'" text-anchor="end">'+labs[0][i]+'</text>';});
 if(two){var rc=V.filter(function(s){return s.ax===1;})[0].col,lc=V.filter(function(s){return s.ax===0;})[0].col;
  ax[1].t.forEach(function(v,i){var y=Y(v,1).toFixed(1);o+='<text class="tx" x="'+(L+pw+4)+'" y="'+(+y+4)+'" style="fill:'+rc+'">'+labs[1][i]+'</text>';});
  o+='<text class="tx" x="'+(L-4)+'" y="11" text-anchor="end" style="fill:'+lc+'">'+esc(units[0])+'</text><text class="tx" x="'+(L+pw+4)+'" y="11" style="fill:'+rc+'">'+esc(units[1])+'</text>';
  o+='<line class="ax" x1="'+(L+pw)+'" x2="'+(L+pw)+'" y1="'+T+'" y2="'+(T+ph)+'"/>';}
 var nx=Math.max(2,Math.floor(pw/80)),ticks=xticks(t0,t1,nx);
 ticks.forEach(function(tk,i){var x=X(tk[0]);if(x<L-1||x>L+pw+1)return;o+='<line class="gr" x1="'+x.toFixed(1)+'" x2="'+x.toFixed(1)+'" y1="'+T+'" y2="'+(T+ph)+'"/><text class="tx" x="'+x.toFixed(1)+'" y="'+(H-4)+'" text-anchor="'+(x-L<20?'start':L+pw-x<20?'end':'middle')+'">'+esc(tk[1])+'</text>';});
 o+='<line class="ax" x1="'+L+'" x2="'+L+'" y1="'+T+'" y2="'+(T+ph)+'"/><line class="ax" x1="'+L+'" x2="'+(L+pw)+'" y1="'+(T+ph)+'" y2="'+(T+ph)+'"/>';
 V.forEach(function(s){var yt=ax[s.ax],d='',pen=false,n=0;s.pts.forEach(function(p){if(!inr(p))return;if(p[1]===null){pen=false;return;}n++;var v=Math.min(Math.max(p[1],yt.a),yt.b);d+=(pen?'L':'M')+X(p[0]).toFixed(1)+' '+Y(v,s.ax).toFixed(1);pen=true;});
  o+='<path d="'+d+'" fill="none" stroke="'+s.col+'" stroke-width="1.8" stroke-linejoin="round"'+(s.ax?' stroke-dasharray="6 4"':'')+'/>';
  if(n<=60)s.pts.forEach(function(p){if(p[1]!==null&&inr(p)){var v=Math.min(Math.max(p[1],yt.a),yt.b);o+='<circle cx="'+X(p[0]).toFixed(1)+'" cy="'+Y(v,s.ax).toFixed(1)+'" r="2.3" fill="'+s.col+'"/>';}});});
 o+='<rect id="selr" x="0" y="'+T+'" width="0" height="'+ph+'" fill="#2b6cb0" fill-opacity=".12" stroke="#2b6cb0" stroke-opacity=".5" style="display:none"/><line id="hl" class="ax" x1="0" x2="0" y1="'+T+'" y2="'+(T+ph)+'" style="display:none"/><g id="dots"></g><rect id="hit" x="'+L+'" y="'+T+'" width="'+pw+'" height="'+ph+'" fill="transparent"/>';
 SV.setAttribute('viewBox','0 0 '+W+' '+H);SV.innerHTML=o;G={X:X,Y:Y,L:L,pw:pw,t0:t0,t1:t1,ax:ax,T:T,ph:ph,inr:inr};
 var hit=document.getElementById('hit');hit.style.cursor='crosshair';
 hit.onmousedown=function(e){var r=SV.getBoundingClientRect();DRAG=e.clientX-r.left;e.preventDefault();};
 hit.onmouseup=function(e){if(DRAG===null)return;var r=SV.getBoundingClientRect(),x2=e.clientX-r.left,a=Math.min(DRAG,x2),b=Math.max(DRAG,x2);DRAG=null;document.getElementById('selr').style.display='none';
  if(b-a>6){var tf=function(x){return G.t0+(Math.min(Math.max(x,G.L),G.L+G.pw)-G.L)/G.pw*(G.t1-G.t0);};ZOOM=[tf(a),tf(b)];TT.style.display='none';nav();draw();}};
 hit.ondblclick=function(){if(ZOOM){ZOOM=null;nav();draw();}};
 hit.onmousemove=function(e){if(DRAG!==null){var r=SV.getBoundingClientRect(),x2=e.clientX-r.left,sr=document.getElementById('selr');
   sr.setAttribute('x',Math.max(G.L,Math.min(DRAG,x2)));sr.setAttribute('width',Math.abs(x2-DRAG));sr.style.display='';}hover(e);};hit.onmouseleave=function(){TT.style.display='none';document.getElementById('hl').style.display='none';document.getElementById('dots').innerHTML='';};
 hit.ontouchstart=hit.ontouchmove=function(e){if(e.touches[0]){hover(e.touches[0]);e.preventDefault();}};}
function hover(e){if(!G)return;var r=SV.getBoundingClientRect(),mx=e.clientX-r.left,t=G.t0+(mx-G.L)/G.pw*(G.t1-G.t0),best=null;
 S.forEach(function(s){if(s.on)s.pts.forEach(function(p){if(p[1]!==null&&G.inr(p)&&(best===null||Math.abs(p[0]-t)<Math.abs(best-t)))best=p[0];});});
 if(best===null)return;var x=G.X(best),h='<b>'+esc(lab(best,U,true))+'</b>',dots='';
 S.forEach(function(s){if(!s.on)return;var q=null;s.pts.forEach(function(p){if(p[0]===best)q=p;});var v=q?q[1]:null;
  h+='<br><span class="sw" style="background:'+s.col+'"></span> '+esc(s.name)+': <b>'+fmt(v,s.dec)+(v!==null&&s.unit?' '+esc(s.unit):'')+'</b>';
  if(v!==null){var yt=G.ax[s.ax],vv=Math.min(Math.max(v,yt.a),yt.b);dots+='<circle cx="'+x.toFixed(1)+'" cy="'+G.Y(vv,s.ax).toFixed(1)+'" r="3.5" fill="'+s.col+'" stroke="#fff" stroke-width="1.5"/>';}});
 var hl=document.getElementById('hl');hl.setAttribute('x1',x);hl.setAttribute('x2',x);hl.style.display='';document.getElementById('dots').innerHTML=dots;
 TT.innerHTML=h;TT.style.display='block';var tw=TT.offsetWidth,th=TT.offsetHeight,cw=C.clientWidth;
 var lx=x+12;if(lx+tw>cw)lx=x-12-tw;if(lx<0)lx=0;TT.style.left=lx+'px';TT.style.top=Math.max(0,Math.min(e.clientY-r.top-th/2,C.clientHeight-th))+'px';}
window.addEventListener('resize',draw);document.addEventListener('mouseup',function(e){var h=document.getElementById('hit');if(DRAG!==null&&h&&e.target!==h)h.onmouseup(e);});nav();load();setInterval(load,REF*1000);
})();
</script></body></html>
"""

READ_ROUTES = ("api/ping", "api/histories", "api/history", "chart.svg", "chart.png")


# ---------------------------------------------------------------- SVG-Diagramm (v1.9)
SVG_N = {"i": 1440, "h": 168, "d": 31, "w": 52, "M": 24, "y": 20}
PNG_CACHE_S = 4
SVG_COL = ["2b6cb0", "d9480f", "2f9e44", "9c36b5", "c2255c", "0c8599", "e67700", "5c5f66"]
_WD = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


def _xml(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _svg_back(t_ms, u, k):
    """Zeitpunkt (ms) k Schritte vor t_ms in Ansicht u."""
    import datetime
    if u == "i":
        return t_ms - k * 60000
    if u == "h":
        return t_ms - k * 3600000
    d = datetime.datetime.fromtimestamp(t_ms / 1000.0)
    if u == "d":
        d = d - datetime.timedelta(days=k)
    elif u == "w":
        d = d - datetime.timedelta(days=7 * k)
    elif u == "M":
        m = d.month - 1 - k
        d = d.replace(year=d.year + m // 12, month=m % 12 + 1, day=1)
    else:
        d = d.replace(year=d.year - k, month=1, day=1)
    return int(time.mktime(d.timetuple()) * 1000)


def _svg_label(t_ms, u, span_ms):
    lt = time.localtime(t_ms / 1000.0)
    if u == "i":
        return time.strftime("%H:%M", lt)
    if u == "h":
        return "%s %02d.%02d." % (_WD[lt.tm_wday], lt.tm_mday, lt.tm_mon) if span_ms > 2 * 86400000 else time.strftime("%H:%M", lt)
    if u in ("d", "w"):
        return "%02d.%02d." % (lt.tm_mday, lt.tm_mon)
    if u == "M":
        return "%02d/%02d" % (lt.tm_mon, lt.tm_year % 100)
    return str(lt.tm_year)


def _fmt(v, dec):
    try:
        dec = int(dec)
    except (TypeError, ValueError):
        dec = -1
    if dec < 0:
        s = ("%.2f" % v).rstrip("0").rstrip(".")
    else:
        s = "%.*f" % (dec, v)
    return s.replace(".", ",")


def _nice(lo, hi):
    import math
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    r = hi - lo
    s = 10 ** math.floor(math.log10(r / 4.0))
    st = s * 10
    for m in (1, 2, 2.5, 5, 10):
        if r / (m * s) <= 5:
            st = m * s
            break
    return math.floor(lo / st) * st, math.ceil(hi / st) * st, st


# ---------------------------------------------------------------- Zeichenflächen (v1.10)
# Ein Diagramm-Layout, zwei Ausgaben: SVG (Hintergrundbild) und PNG (Kamera-Element, ohne Bibliothek).
# PNG-Schrift: Liberation Sans (SIL Open Font License 1.1) als 4-Bit-Bitmaps, eingebettet.
_FONT_B64 = "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"
_FONT = None


def _font():
    global _FONT
    if _FONT is None:
        raw = zlib.decompress(base64.b64decode(_FONT_B64))
        n = int.from_bytes(raw[:4], "big")
        _FONT = (json.loads(raw[4:4 + n].decode("utf-8")), raw[4 + n:])
    return _FONT


def _rgb(c):
    c = (c or "000").lstrip("#")
    if len(c) == 3:
        c = "".join(x * 2 for x in c)
    try:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    except ValueError:
        return (0, 0, 0)


class SvgCanvas(object):
    def __init__(self, W, H, fs, bg):
        self.W, self.H = W, H
        self.o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
                  'font-family="Arial,Helvetica,sans-serif" font-size="%d">' % (W, H, W, H, fs)]
        if bg and bg not in ("none", "transparent"):
            self.o.append('<rect width="100%%" height="100%%" fill="#%s"/>' % _xml(bg))

    @staticmethod
    def measure(s, size, bold=False):
        return len(s) * size * (0.6 if bold else 0.55)

    def rect(self, x, y, w, h, col, op=1.0, rx=0):
        self.o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"%s fill="#%s"%s/>' % (
            x, y, w, h, (' rx="%g"' % rx) if rx else "", _xml(col), (' fill-opacity="%g"' % op) if op < 1 else ""))

    def hline(self, x1, x2, y, col):
        self.o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="#%s"/>' % (x1, x2, y, y, _xml(col)))

    def vline(self, x, y1, y2, col):
        self.o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="#%s"/>' % (x, x, y1, y2, _xml(col)))

    def poly(self, segs, col, width=1.8, dash=False):
        d = "".join("M" + "L".join("%.1f %.1f" % xy for xy in sg) for sg in segs if len(sg) > 1)
        if d:
            self.o.append('<path d="%s" fill="none" stroke="#%s" stroke-width="%g" stroke-linejoin="round"%s/>' % (
                d, _xml(col), width, ' stroke-dasharray="6 4"' if dash else ""))

    def circle(self, x, y, r, col):
        self.o.append('<circle cx="%.1f" cy="%.1f" r="%g" fill="#%s"/>' % (x, y, r, _xml(col)))

    def text(self, x, y, s, size, col, anchor="start", bold=False, halo=False):
        self.o.append('<text x="%.1f" y="%.1f" font-size="%d"%s%s fill="#%s"%s>%s</text>' % (
            x, y, size, (' text-anchor="%s"' % anchor) if anchor != "start" else "", ' font-weight="bold"' if bold else "",
            _xml(col), ' stroke="#fff" stroke-width="3" paint-order="stroke"' if halo else "", _xml(s)))

    def out(self):
        return ("".join(self.o) + "</svg>").encode("utf-8")


class PngCanvas(object):
    """Einfacher Rasterizer: RGB-Puffer, kantengeglättete Linien/Kreise, Bitmap-Schrift, PNG ohne Bibliothek."""

    def __init__(self, W, H, fs, bg):
        self.W, self.H = W, H
        self.bg = _rgb(bg if bg and bg not in ("none", "transparent") else "fff")
        self.px = bytearray(bytes(self.bg) * (W * H))

    def _blend(self, i, c, a):
        if a >= 0.999:
            self.px[i:i + 3] = bytes(c)
            return
        p = self.px
        p[i] = int(p[i] + (c[0] - p[i]) * a)
        p[i + 1] = int(p[i + 1] + (c[1] - p[i + 1]) * a)
        p[i + 2] = int(p[i + 2] + (c[2] - p[i + 2]) * a)

    def rect(self, x, y, w, h, col, op=1.0, rx=0):
        c = _rgb(col)
        if op < 1:
            c = tuple(int(self.bg[k] + (c[k] - self.bg[k]) * op) for k in range(3))
        x0, x1 = max(0, int(round(x))), min(self.W, int(round(x + w)))
        y0, y1 = max(0, int(round(y))), min(self.H, int(round(y + h)))
        if x1 <= x0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.W + x0) * 3
            self.px[i:i + len(row)] = row

    def hline(self, x1, x2, y, col):
        self.rect(min(x1, x2), int(y), abs(x2 - x1) + 1, 1, col)

    def vline(self, x, y1, y2, col):
        self.rect(int(x), min(y1, y2), 1, abs(y2 - y1) + 1, col)

    def _cover(self, cov, x, y, a):
        if 0 <= x < self.W and 0 <= y < self.H and a > 0:
            k = y * self.W + x
            if cov.get(k, 0) < a:
                cov[k] = a

    def _seg(self, cov, x1, y1, x2, y2, r):
        dx, dy = x2 - x1, y2 - y1
        ll = dx * dx + dy * dy
        for yy in range(int(min(y1, y2) - r - 1), int(max(y1, y2) + r + 2)):
            for xx in range(int(min(x1, x2) - r - 1), int(max(x1, x2) + r + 2)):
                px, py = xx + 0.5 - x1, yy + 0.5 - y1
                t = 0.0 if ll == 0 else max(0.0, min(1.0, (px * dx + py * dy) / ll))
                ex, ey = px - t * dx, py - t * dy
                d = (ex * ex + ey * ey) ** 0.5
                a = r + 0.5 - d
                if a > 0:
                    self._cover(cov, xx, yy, 1.0 if a >= 1 else a)

    def _paint(self, cov, col):
        c = _rgb(col)
        for k, a in cov.items():
            self._blend(k * 3, c, a)

    def poly(self, segs, col, width=1.8, dash=False):
        cov, r = {}, width / 2.0
        for sg in segs:
            run = 0.0
            for (x1, y1), (x2, y2) in zip(sg, sg[1:]):
                L = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                if dash:
                    # 6 an, 4 aus – in Stücke zerlegen
                    pos = 0.0
                    while pos < L:
                        ph = (run + pos) % 10.0
                        step = min(L - pos, (6.0 - ph) if ph < 6 else (10.0 - ph))
                        if ph < 6 and L > 0:
                            a0, a1 = pos / L, (pos + step) / L
                            self._seg(cov, x1 + (x2 - x1) * a0, y1 + (y2 - y1) * a0, x1 + (x2 - x1) * a1, y1 + (y2 - y1) * a1, r)
                        pos += max(step, 1e-3)
                    run += L
                else:
                    self._seg(cov, x1, y1, x2, y2, r)
        self._paint(cov, col)

    def circle(self, x, y, r, col):
        cov = {}
        for yy in range(int(y - r - 1), int(y + r + 2)):
            for xx in range(int(x - r - 1), int(x + r + 2)):
                d = ((xx + 0.5 - x) ** 2 + (yy + 0.5 - y) ** 2) ** 0.5
                a = r + 0.5 - d
                if a > 0:
                    self._cover(cov, xx, yy, 1.0 if a >= 1 else a)
        self._paint(cov, col)

    @staticmethod
    def _face(size, bold):
        meta = _font()[0]
        if bold:
            return meta["b15"] if size >= 14 else meta["b13"]
        return meta["r11"] if size <= 11 else (meta["r12"] if size == 12 else meta["r13"])

    @classmethod
    def measure(cls, s, size, bold=False):
        g = cls._face(size, bold)["g"]
        return sum(g.get(ch, g["?"])[0] for ch in s)

    def _glyphs(self, x, y, s, face, c, dx=0, dy=0):
        blob = _font()[1]
        g = face["g"]
        for ch in s:
            adv, w, h, xo, yo, off = g.get(ch, g["?"])
            if off >= 0:
                gx, gy = int(round(x + xo)) + dx, int(round(y + yo)) + dy
                for j in range(h):
                    yy = gy + j
                    if not 0 <= yy < self.H:
                        continue
                    for i in range(w):
                        xx = gx + i
                        if not 0 <= xx < self.W:
                            continue
                        n = j * w + i
                        b = blob[off + n // 2]
                        v = (b >> 4) if n % 2 == 0 else (b & 15)
                        if v:
                            self._blend((yy * self.W + xx) * 3, c, v / 15.0)
            x += adv

    def text(self, x, y, s, size, col, anchor="start", bold=False, halo=False):
        face = self._face(size, bold)
        w = self.measure(s, size, bold)
        if anchor == "end":
            x -= w
        elif anchor == "middle":
            x -= w / 2.0
        if halo:
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
                self._glyphs(x, y, s, face, self.bg, dx, dy)
        self._glyphs(x, y, s, face, _rgb(col))

    def out(self):
        import struct
        W, H = self.W, self.H
        raw = bytearray()
        rl = W * 3
        for yy in range(H):
            raw.append(0)
            raw += self.px[yy * rl:(yy + 1) * rl]

        def chunk(t, d):
            return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b""))


def render_chart(series, u, p, fmt="svg"):
    """series = Liste von Verlauf.series(u, n); p = URL-Parameter; fmt svg|png → bytes.
    Ausgeblendete Verläufe (14771 E11 = 0 oder hide=<Kennung,…>) stehen nur grau in der Legende.
    Zwei verschiedene Einheiten: erste Einheit linke Achse, zweite Einheit rechte Achse (gestrichelt)."""
    def num(k, d):
        try:
            return float(p.get(k, ""))
        except ValueError:
            return d
    W = int(max(200, min(3000, num("w", 940))))
    H = int(max(120, min(2000, num("h", 420))))
    cols = [c.strip().lstrip("#") for c in p.get("color", "").split(",") if c.strip()] + SVG_COL
    bg = p.get("bg", "fff").lstrip("#")
    fs = max(9, min(16, int(H / 32)))
    title = p.get("title") or (series[0]["name"] if len(series) == 1 else "")
    cv = (PngCanvas if fmt == "png" else SvgCanvas)(W, H, fs, bg)
    M = cv.measure
    hide = set(x.strip() for x in p.get("hide", "").split(",") if x.strip())
    vis = [s.get("show", 1) != 0 and s.get("id") not in hide for s in series]
    if p.get("view") == "table":
        _table(cv, [s for s, on in zip(series, vis) if on], len(series), u, W, H, fs, cols, title)
        return cv.out()
    multi = len(series) > 1
    cv.text(6, fs * 1.4, title, fs, "222", bold=True)
    pts_all, t0, t1 = [], None, None
    for s, on in zip(series, vis):
        vals = s.get("vals") or []
        n = len(vals)
        pts = [(_svg_back(s["t_last"], u, n - 1 - k), v) for k, v in enumerate(vals) if v is not None]
        pts_all.append(pts if on else [])
        if n and on:
            a, b = _svg_back(s["t_last"], u, n - 1), s["t_last"]
            t0 = a if t0 is None else min(t0, a)
            t1 = b if t1 is None else max(t1, b)
    units = []
    for s, pts in zip(series, pts_all):
        if pts and s.get("unit", "") not in units:
            units.append(s.get("unit", ""))
    side = [1 if (len(units) > 1 and s.get("unit", "") == units[1]) else 0 for s in series]
    two = len(units) > 1
    L, T, B = fs * 4.2, fs * (4.8 if two else 4.0), fs * 2
    R = fs * 4.2 if two else 10
    # Legende rechts oben: Farbfeld, Name, aktueller Wert; ausgeblendete grau
    lx = W - 10
    for i, s in reversed(list(enumerate(series))):
        cur = s.get("current")
        val = "–" if cur is None else _fmt(cur, s.get("dec")) + (" " + s["unit"] if s.get("unit") else "")
        t = (s["name"] + " " if multi else "") + (val if vis[i] else "(aus)")
        c = cols[i % len(cols)] if vis[i] else "aaaaaa"
        cv.text(lx, fs * 1.4, t, fs, c, anchor="end", bold=True)
        lx -= M(t, fs, True) + fs * 0.5
        if multi:
            cv.rect(lx - fs * 0.8, fs * 0.6, fs * 0.8, fs * 0.8, c, rx=2)
            lx -= fs * 1.6
    if not any(pts_all):
        msg = "Verlauf nicht gefunden" if not series else ("Alle Verläufe ausgeblendet" if not any(vis) else "Noch keine Werte")
        cv.text(W / 2, H / 2, msg, fs, "888", anchor="middle")
        return cv.out()
    sfs = max(8, fs - 1)
    sx = 6
    for i, (s, pts) in enumerate(zip(series, pts_all)):
        if not pts:
            continue
        vv = [v for _, v in pts]
        un = (" " + s["unit"]) if s.get("unit") else ""
        dec = s.get("dec")
        if s.get("mode") == 2:
            txt = "Summe %s%s · Max %s%s" % (_fmt(sum(vv), dec), un, _fmt(max(vv), dec), un)
        elif min(vv) == max(vv):
            txt = "konstant %s%s" % (_fmt(vv[0], dec), un)
        else:
            txt = "Min %s · Max %s · Ø %s%s" % (_fmt(min(vv), dec), _fmt(max(vv), dec), _fmt(sum(vv) / len(vv), dec), un)
        if multi:
            txt = s["name"] + ": " + txt
        cv.text(sx, fs * 2.9, txt, sfs, cols[i % len(cols)])
        sx += M(txt, sfs) + fs * 1.5
    bars = [s.get("mode") == 2 for s in series]

    def scale(k):
        ys = [v for i, pts in enumerate(pts_all) if side[i] == k for _, v in pts]
        withbar = any(bars[i] and pts_all[i] for i in range(len(series)) if side[i] == k)
        lo, hi = min(ys + ([0] if withbar else [])), max(ys)
        if units[k] == "%" and lo >= 0 and hi <= 100:
            return 0.0, 100.0, 20.0
        pre = "" if k == 0 else "2"
        lo = num("ymin" + pre, lo) if ("ymin" + pre) in p else lo
        hi = num("ymax" + pre, hi) if ("ymax" + pre) in p else hi
        nlo, nhi, st = _nice(lo, hi)
        if ("ymin" + pre) in p:
            nlo = lo
        if ("ymax" + pre) in p:
            nhi = hi
        return nlo, nhi, st
    ax = [scale(0)] + ([scale(1)] if two else [])
    span = max(1, t1 - t0)
    X = lambda t: L + (t - t0) * (W - L - R) / float(span)

    def Y(v, k=0):
        lo, hi, _ = ax[k]
        return T + (hi - v) * (H - T - B) / float(hi - lo or 1)

    def clamp(v, k=0):
        return max(ax[k][0], min(ax[k][1], v))
    lo, hi, st = ax[0]
    v = lo
    while v <= hi + st * 1e-6:
        y = Y(v)
        cv.hline(L, W - R, y, "e6e6e6")
        cv.text(L - 4, y + fs * 0.35, _fmt(v, -1), fs, "666", anchor="end")
        v += st
    if two:
        rc, lc = cols[side.index(1) % len(cols)], cols[side.index(0) % len(cols)]
        cv.text(L - 4, T - fs * 0.8, units[0], sfs, lc, anchor="end")
        cv.text(W - R + 4, T - fs * 0.8, units[1], sfs, rc)
        lo2, hi2, st2 = ax[1]
        v = lo2
        while v <= hi2 + st2 * 1e-6:
            cv.text(W - R + 4, Y(v, 1) + fs * 0.35, _fmt(v, -1), fs, rc)
            v += st2
    nt = max(2, min(8, int((W - L - R) / (fs * 7))))
    for i in range(nt + 1):
        t = t0 + span * i / float(nt)
        anc = "start" if i == 0 else ("end" if i == nt else "middle")
        cv.text(X(t), H - fs * 0.6, _svg_label(t, u, span), fs, "666", anchor=anc)
    cv.vline(L, T, H - B, "999")
    cv.hline(L, W - R, H - B, "999")
    if two:
        cv.vline(W - R, T, H - B, "999")
    step = {"i": 60e3, "h": 36e5, "d": 864e5, "w": 6048e5, "M": 2.7e9, "y": 3.2e10}[u] * 1.5
    for i, pts in enumerate(pts_all):
        if not pts:
            continue
        c, k = cols[i % len(cols)], side[i]
        if bars[i]:
            bw = max(1.0, (W - L - R) / float(max(1, len(series[i]["vals"]))) * 0.7)
            y0 = Y(max(0, ax[k][0]), k)
            for t, val in pts:
                y = Y(clamp(val, k), k)
                cv.rect(X(t) - bw / 2, min(y, y0), bw, abs(y0 - y), c, op=0.75)
            continue
        prev, segs = None, []
        for t, val in pts:
            if prev is None or t - prev > step:
                segs.append([])
            segs[-1].append((X(t), Y(clamp(val, k), k)))
            prev = t
        cv.poly(segs, c, 1.8, dash=(k == 1))
        dots = len(pts) <= 60
        for sg in segs:
            if len(sg) == 1 or dots:
                for x, y in sg:
                    cv.circle(x, y, 2.6, c)
    lf = max(8, fs - 2)
    nvis = sum(1 for pts in pts_all if pts)
    for i, pts in enumerate(pts_all):
        if not pts:
            continue
        c, dec, k = cols[i % len(cols)], series[i].get("dec"), side[i]
        tmax, vmax = max(pts, key=lambda x: x[1])
        tmin, vmin = min(pts, key=lambda x: x[1])
        if vmax == vmin:
            continue                      # konstante Linie: Wert steht in der Kennzahlenzeile
        if len(pts) <= 31 and nvis == 1:
            marks = [(t, v, "") for t, v in pts]
        else:
            marks = [(tmax, vmax, "▲ "), (tmin, vmin, "▼ ")]
        for t, v, pre in marks:
            x, y = X(t), Y(clamp(v, k), k)
            ty = y + lf * 1.3 if pre == "▼ " else y - lf * 0.6
            if ty < T + lf:
                ty = y + lf * 1.3
            if ty > H - B - 2:
                ty = y - lf * 0.6
            anc = "end" if x > W - R - 30 else ("start" if x < L + 30 else "middle")
            cv.circle(x, y, 3, c)
            cv.text(x, ty, pre + _fmt(v, dec), lf, c if multi else "333", anchor=anc, halo=True)
    return cv.out()


def render_svg(series, u, p):
    return render_chart(series, u, p, "svg").decode("utf-8")


def _table(cv, series, alln, u, W, H, fs, cols, title):
    """Wertetabelle: Zeit | Wert je Verlauf, neueste zuerst."""
    cv.text(6, fs * 1.4, title, fs, "222", bold=True)
    if not series:
        cv.text(W / 2, H / 2, "Alle Verläufe ausgeblendet" if alln else "Verlauf nicht gefunden", fs, "888", anchor="middle")
        return
    rows = {}
    for i, s in enumerate(series):
        vals = s.get("vals") or []
        n = len(vals)
        for k, v in enumerate(vals):
            if v is not None:
                rows.setdefault(_svg_back(s["t_last"], u, n - 1 - k), {})[i] = v
    rh = fs * 1.55
    top = fs * 3.2
    per_col = max(1, int((H - top - 4) / rh))
    hdrs = [(s["name"] if len(series) > 1 else "Wert") + (" [%s]" % s["unit"] if s.get("unit") else "") for s in series]
    cw_time = fs * (11 if u in ("i", "h") else 7)
    cw_val = max([fs * 6.5] + [cv.measure(x, fs, True) + fs for x in hdrs])
    block = cw_time + cw_val * len(series) + fs * 2
    nblocks = max(1, int((W - 6) / block))
    keys = sorted(rows, reverse=True)[:per_col * nblocks]

    def tl(t):
        lt = time.localtime(t / 1000.0)
        if u in ("i", "h"):
            return "%s %02d.%02d. %02d:%02d" % (_WD[lt.tm_wday], lt.tm_mday, lt.tm_mon, lt.tm_hour, lt.tm_min)
        if u in ("d", "w"):
            return "%s %02d.%02d.%02d" % (_WD[lt.tm_wday], lt.tm_mday, lt.tm_mon, lt.tm_year % 100)
        if u == "M":
            return "%02d/%04d" % (lt.tm_mon, lt.tm_year)
        return str(lt.tm_year)
    for b in range(nblocks):
        x0 = 6 + b * block
        y = top
        cv.text(x0, y, "Zeit", fs, "666", bold=True)
        for i, s in enumerate(series):
            cv.text(x0 + cw_time + cw_val * (i + 1), y, hdrs[i], fs, cols[i % len(cols)], anchor="end", bold=True)
        for r, t in enumerate(keys[b * per_col:(b + 1) * per_col - 1]):
            y = top + rh * (r + 1)
            if r % 2 == 0:
                cv.rect(x0 - 3, y - fs * 1.05, block - fs, rh, "f2f4f7")
            cv.text(x0, y, tl(t), fs, "333")
            for i, s in enumerate(series):
                v = rows[t].get(i)
                cv.text(x0 + cw_time + cw_val * (i + 1), y, "–" if v is None else _fmt(v, s.get("dec")), fs, "222", anchor="end")
    if not keys:
        cv.text(W / 2, H / 2, "Noch keine Werte", fs, "888", anchor="middle")


def pack(obj):
    """JSON → zlib → base64 (ASCII) → Liste von Stücken < 10.000 Zeichen."""
    raw = base64.b64encode(zlib.compress(json.dumps(obj, separators=(",", ":")).encode("utf-8"), 9))
    return [raw[i:i + CHUNK] for i in range(0, len(raw), CHUNK)] or [b""]


def unpack(chunks):
    raw = b"".join(c for c in chunks if c)
    if not raw:
        return None
    return json.loads(zlib.decompress(base64.b64decode(raw)).decode("utf-8"))


class LogicModule:
    def __init__(self, hsl3):
        self.fw = hsl3
        self.debug = self.fw.create_debug_section()
        self._lock = threading.RLock()
        self._histories = {}            # id(obj) -> Verlaufs-Baustein
        self._png_lock = threading.Lock()
        self._png_cache = {}
        self.base_path = "visu-daten"
        self.port = 8092
        self.key = ""
        self.read_key = ""
        self.config = None
        self.config_rev = 0
        self.requests = 0
        self._httpd = self._stop = self._thread = None

    # ------------------------------------------------------------ Lebenszyklus
    def on_init(self, inputs, store):
        self._read_inputs(inputs)
        try:
            data = unpack([store.value("c%02d" % k) for k in range(1, CFG_STORES + 1)])
            if isinstance(data, dict):
                self.config, self.config_rev = data.get("config"), int(data.get("rev") or 0)
        except Exception as e:
            self.debug.log("Einrichtung unlesbar: %r" % (e,))
        self.fw.set_output("instance_id", float(self.fw.get_instance_id()))
        self.fw.set_output("config_rev", float(self.config_rev) / 1000.0)
        self._start()
        self._publish_counts()

    def on_calc(self, inputs):
        old = (self.base_path, self.port)
        self._read_inputs(inputs)
        restart = False
        try:
            if inputs.changed("restart"):
                restart = self._num(inputs.value("restart"), 0) == 1
                self.fw.set_output("instance_id", float(self.fw.get_instance_id()))
                self.fw.set_output("config_rev", float(self.config_rev) / 1000.0)
                self.fw.set_output("requests", float(self.requests))
                self._publish_counts()
        except Exception as e:
            self.debug.log("E4: %r" % (e,))
        if restart or (self.base_path, self.port) != old:
            self._start()

    def _read_inputs(self, inputs):
        self.base_path = self._text(inputs.value("base_path")).strip("/ ") or "visu-daten"
        self.port = int(self._num(inputs.value("destination_port"), 8092))
        self.port_missing = self.port <= 0
        if self.port_missing:
            self.port = 8092
        self.key = self._text(inputs.value("key")).strip()
        try:
            self.read_key = self._text(inputs.value("read_key")).strip()
        except Exception:
            self.read_key = ""
        self.debug.set("Schutz", ("Schlüssel gesetzt" if self.key else "OHNE Schlüssel") +
                       (", Lese-Schlüssel gesetzt" if self.read_key else ""))

    # ------------------------------------------------------------ Anmeldung der Verläufe
    # Aufruf durch 14771 im gemeinsamen Kontext
    def register_history(self, hist):
        with self._lock:
            self._histories[id(hist)] = hist
        self.fw.run_in_context(self._publish_counts, ())
        return True

    def unregister_history(self, hist):
        with self._lock:
            self._histories.pop(id(hist), None)
        self.fw.run_in_context(self._publish_counts, ())

    def _catalog(self):
        """{hid: Baustein}; bei doppelter ID gewinnt die kleinste Instanz-ID."""
        with self._lock:
            hs = list(self._histories.values())
        out = {}
        for h in sorted(hs, key=lambda x: x.instance_id()):
            try:
                hid = h.history_id()
            except Exception:
                continue
            out.setdefault(hid, h)
        return out

    def _publish_counts(self):
        n = len(self._catalog())
        self.fw.set_output("history_count", float(n))
        self.debug.set("Verläufe", str(n))

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
            if getattr(self, "port_missing", False):
                self._status("E2 Port fehlt! Im Experten 8092 eintragen, sonst leitet der HS nicht weiter (503)")
            else:
                self._status("Bereit: /%s/ (Port %d)%s" % (self.base_path, self.port, "" if self.key else " - OHNE Schluessel"))
        except OSError as e:
            self._status("Fehler beim Start auf Port %d: %s" % (self.port, e))

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
            server_version = "Visu-Server-14770/" + VERSION
            sys_version = ""

            def log_message(self, *a):
                pass

            def do_GET(self):
                module._handle(self, "GET")

            def do_POST(self):
                module._handle(self, "POST")

            def do_OPTIONS(self):
                module._send(self, 204, "text/plain", b"")

        return H

    # ------------------------------------------------------------ Anfragen (HTTP-Thread)
    def _handle(self, h, method):
        try:
            parsed = urllib.parse.urlsplit(h.path)
            params = dict(urllib.parse.parse_qsl(parsed.query))
            route = parsed.path
            prefix = "/" + self.base_path
            if route == prefix or route.startswith(prefix + "/"):
                route = route[len(prefix):]
            route = route.strip("/")
            if route in ("", "index.html"):
                return self._send(h, 200, "text/html; charset=utf-8", PAGE.encode("utf-8"))
            if route in ("chart", "chart.html"):
                return self._send(h, 200, "text/html; charset=utf-8", CHART.encode("utf-8"))
            if not self._authorized(h, params, read_only=(method == "GET" and route in READ_ROUTES)):
                return self._json(h, 401, {"error": "Schlüssel fehlt oder falsch"})
            body = None
            if method == "POST":
                body = self._read_body(h)
                if not body:
                    return self._json(h, 400, {"error": "Keine Daten empfangen"})
                if len(body) > MAX_BODY:
                    return self._json(h, 413, {"error": "Daten zu groß (max. 4 MB)"})
            if route == "chart.svg":
                return self._send(h, 200, "image/svg+xml; charset=utf-8", self.chart_svg(params).encode("utf-8"))
            if route == "chart.png":
                return self._send(h, 200, "image/png", self.chart_png(params))
            status, data = self.dispatch(method, route, params, body)
            self._json(h, status, data)
        except (ConnectionError, OSError):
            return
        except Exception as e:
            try:
                self._json(h, 500, {"error": "Interner Fehler: %r" % (e,)})
            except Exception:
                pass
        finally:
            self.fw.run_in_context(self._count_request, ())

    @staticmethod
    def _read_body(h):
        """Body mit Content-Length oder – falls der HS-Proxy so weiterleitet – chunked."""
        if "chunked" in (h.headers.get("Transfer-Encoding") or "").lower():
            out = b""
            while len(out) <= MAX_BODY:
                line = h.rfile.readline(100).strip()
                size = int(line.split(b";")[0] or b"0", 16)
                if size == 0:
                    h.rfile.readline(100)
                    break
                out += h.rfile.read(size)
                h.rfile.readline(10)
            return out
        n = int(h.headers.get("Content-Length") or 0)
        if n <= 0:
            return b""
        return h.rfile.read(min(n, MAX_BODY + 1))

    def _authorized(self, h, params, read_only=False):
        if not self.key:
            return True
        given = (h.headers.get("X-Visu-Key") or params.get("key") or "").encode("utf-8")
        if hmac.compare_digest(given, self.key.encode("utf-8")):
            return True
        return bool(read_only and self.read_key) and hmac.compare_digest(given, self.read_key.encode("utf-8"))

    def chart_svg(self, params):
        """SVG-Diagramm eines oder mehrerer Verläufe (Parameter wie chart)."""
        u = params.get("u", "i")
        if u not in SVG_N:
            u = "i"
        try:
            n = int(params.get("n", "0")) or SVG_N[u]
        except ValueError:
            n = SVG_N[u]
        cat = self._catalog()
        series = []
        for hid in [x.strip() for x in params.get("id", "").split(",") if x.strip()][:8]:
            h = cat.get(hid)
            if h is not None:
                series.append(h.series(u, n))
        if not params.get("id") and cat:
            series.append(sorted(cat.values(), key=lambda x: x.instance_id())[0].series(u, n))
        return render_svg(series, u, params)

    def _chart_series(self, params):
        u = params.get("u", "i")
        if u not in SVG_N:
            u = "i"
        try:
            n = int(params.get("n", "0")) or SVG_N[u]
        except ValueError:
            n = SVG_N[u]
        cat = self._catalog()
        series = [cat[hid].series(u, n) for hid in [x.strip() for x in params.get("id", "").split(",") if x.strip()][:8] if hid in cat]
        if not params.get("id") and cat:
            series.append(sorted(cat.values(), key=lambda x: x.instance_id())[0].series(u, n))
        return series, u

    def chart_png(self, params):
        """PNG des Diagramms (für das Kamera-Element der Experten-Visu); 4 s Zwischenspeicher je Aufruf."""
        key = tuple(sorted((k, v) for k, v in params.items() if k != "key"))
        now = time.time()
        with self._png_lock:
            hit = self._png_cache.get(key)
            if hit and now - hit[0] < PNG_CACHE_S:
                return hit[1]
        series, u = self._chart_series(params)
        data = render_chart(series, u, params, "png")
        with self._png_lock:
            if len(self._png_cache) > 20:
                self._png_cache.clear()
            self._png_cache[key] = (now, data)
        return data

    def dispatch(self, method, route, params, body):
        """(Status, JSON-Objekt) – ohne Netzwerk testbar."""
        if route == "api/ping":
            return 200, {"ok": True, "version": VERSION, "histories": len(self._catalog()),
                         "config_rev": self.config_rev, "time": int(time.time() * 1000)}
        if route == "api/config/rev":
            return 200, {"rev": self.config_rev}
        if route == "api/config" and method == "GET":
            return 200, {"rev": self.config_rev, "config": self.config}
        if route == "api/config" and method == "POST":
            data = json.loads(body.decode("utf-8"))
            if not isinstance(data, dict) or "config" not in data:
                return 400, {"error": "config fehlt"}
            rev = int(data.get("rev") or time.time() * 1000)
            res = self._in_context(self._save_config, (data["config"], rev))
            return (200 if res.get("ok") else 500), res
        if route == "api/histories":
            return 200, {"histories": [h.info() for h in self._catalog().values()]}
        if route == "api/history":
            h = self._catalog().get(params.get("id", ""))
            if h is None:
                return 404, {"error": "Verlauf nicht gefunden", "id": params.get("id")}
            u = params.get("u", "h")
            try:
                n = int(params.get("n", "0")) or None
            except ValueError:
                n = None
            return 200, h.series(u, n)
        if route == "api/export":
            return 200, {"format": "visu-server-export", "version": 1,
                         "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                         "config": {"rev": self.config_rev, "config": self.config},
                         "histories": [{"id": hid, "state": h.export_state()} for hid, h in self._catalog().items()]}
        if route == "api/import" and method == "POST":
            data = json.loads(body.decode("utf-8"))
            if not isinstance(data, dict) or data.get("format") != "visu-server-export":
                return 400, {"error": "keine Visu-Server-Sicherung"}
            merge = params.get("mode", "replace") == "merge"
            result = {"config": False, "histories_queued": [], "histories_unknown": [],
                      "mode": "merge" if merge else "replace"}
            cfg = data.get("config") or {}
            if cfg.get("config") is not None:
                new_cfg = cfg["config"]
                if merge:
                    new_cfg, added = self._merge_config(self.config, new_cfg)
                    result["tiles_added"] = added
                res = self._in_context(self._save_config, (new_cfg, int(time.time() * 1000)))
                result["config"] = bool(res.get("ok"))
            cat = self._catalog()
            for item in data.get("histories") or []:
                h = cat.get(item.get("id"))
                if h is None:
                    result["histories_unknown"].append(item.get("id"))
                else:
                    h.queue_import(item.get("state"), merge)
                    result["histories_queued"].append(item.get("id"))
            return 200, result
        return 404, {"error": "unbekannt: " + route}

    @staticmethod
    def _merge_config(cur, bak):
        """Nur Kacheln aus der Sicherung ergänzen, die es noch nicht gibt (gleicher Typ + Quelle + Name)."""
        cur_tiles = list((cur or {}).get("tiles") or []) if isinstance(cur, dict) else []
        sig = lambda t: (t.get("type"), str(t.get("key") or ""), str(t.get("name") or ""))
        have = set(sig(t) for t in cur_tiles if isinstance(t, dict))
        added = 0
        for t in (bak or {}).get("tiles") or []:
            if isinstance(t, dict) and sig(t) not in have:
                cur_tiles.append(t)
                have.add(sig(t))
                added += 1
        out = dict(cur) if isinstance(cur, dict) else {}
        out["tiles"] = cur_tiles
        return out, added

    def _in_context(self, fn, args, timeout=10):
        """fn im Kontext des Bausteins ausführen (set_store ist nur dort erlaubt) und warten."""
        done = threading.Event()
        res = {}

        def run():
            try:
                res.update(fn(*args) or {})
            except Exception as e:
                res.update({"ok": False, "error": repr(e)})
            done.set()

        self.fw.run_in_context(run, ())
        if not done.wait(timeout):
            return {"ok": False, "error": "Zeitüberschreitung"}
        return res

    # ------------------------------------------------------------ im Kontext
    def _save_config(self, config, rev):
        chunks = pack({"rev": rev, "config": config})
        if len(chunks) > CFG_STORES:
            return {"ok": False, "error": "Einrichtung zu groß (%d Zeichen komprimiert)" % sum(len(c) for c in chunks)}
        for k in range(1, CFG_STORES + 1):
            self.fw.set_store("c%02d" % k, chunks[k - 1] if k <= len(chunks) else b"")
        with self._lock:
            self.config, self.config_rev = config, rev
        self.fw.set_output("config_rev", float(rev) / 1000.0)
        self.debug.set("Einrichtung", "%s, %d Zeichen" % (time.strftime("%d.%m. %H:%M:%S"), sum(len(c) for c in chunks)))
        return {"ok": True, "rev": rev}

    def _count_request(self):
        self.requests += 1
        self.fw.set_output("requests", float(self.requests))

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
        h.send_header("Access-Control-Allow-Origin", "*")
        h.send_header("Access-Control-Allow-Headers", "X-Visu-Key, Content-Type")
        h.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        h.end_headers()
        if body:
            h.wfile.write(body)

    def _status(self, text):
        t = text
        for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"),
                     ("ß", "ss"), ("–", "-"), ("…", "...")):
            t = t.replace(a, b)
        self.fw.set_output("status", t.encode("ascii", "replace")[:200])
        self.debug.set("Status", text)

    @staticmethod
    def _text(v):
        if isinstance(v, bytes):
            try:
                return v.decode("utf-8")           # der HS liefert Texte als UTF-8
            except UnicodeDecodeError:
                return v.decode("iso-8859-15", "replace")
        return "" if v is None else str(v)

    @staticmethod
    def _num(v, default):
        try:
            return float(v)
        except (TypeError, ValueError):
            return default
