"""Beispielbild Ablauf (bilder/beispiel_ablauf.png) aus einer Simulation mit dem Baustein-Code."""
import os, sys, time, importlib.util
Q = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
os.environ["TZ"]="UTC"; time.tzset()
sys.argv=['x',os.path.join(Q, 'src', 'hsl3_14785_bewaesserung.py')]
src=open(os.path.join(Q, 'test', 'test_14785.py')).read()
exec(src.split('# ------------------------------------------------------------ 1 Planung')[0])
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as md, datetime as dt
s=Sim(1, k1_t=10,k2_t=6,k3_t=15,k4_t=15,k5_t=15,k3_par=1,k4_par=1,k5_par=1,max_par=3,
      end="06:00",overlap=3,psu_mode=0,psu_pre=2,psu_post=5,pump_delay=3,relief=3)
s.set(1,k1_t=8,k2_t=0,k3_t=6,k4_t=0,k5_t=0)
o=s.run(hm(5),hm(5,0,5))
st=o[0]["st1t"]; dur=o[0]["dur1"]
rows=[("Netzteil 24 V",0,"psu"),("Pumpe",0,"pump")]+[("K%d"%(k+1),0,"k%d_valve"%(k+1)) for k in range(5)]+[("K%d (Folge)"%(k+6),1,"k%d_valve"%(k+1)) for k in (0,2)]
s.run(hm(5,0,6),hm(6,2),[r[2] for r in rows])
def spans(b,key):
    ev=[(t,v) for (t,bb,k,v) in s.log if bb==b and k==key]; out=[];on=None
    for t,v in ev:
        if v==1 and on is None: on=t
        if v==0 and on is not None: out.append((on,t)); on=None
    return out
f=lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).replace(tzinfo=None)
fig,ax=plt.subplots(figsize=(10,4.6),dpi=150)
col={"psu":"#8c8c8c","pump":"#2f6db5"}
for i,(lab,b,key) in enumerate(rows):
    c=col.get(key,"#3a9a52" if b==0 else "#d08a1e")
    for a,e in spans(b,key):
        ax.barh(i,md.date2num(f(e))-md.date2num(f(a)),left=md.date2num(f(a)),height=0.6,color=c)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows]); ax.invert_yaxis()
ax.xaxis_date(); ax.xaxis.set_major_formatter(md.DateFormatter("%H:%M")); ax.xaxis.set_major_locator(md.MinuteLocator(byminute=range(0,60,5)))
ax.set_xlim(md.date2num(f(hm(5,8))),md.date2num(f(hm(6,2))))
ax.axvline(md.date2num(f(hm(6))),color="#c0392b",ls="--",lw=1); ax.text(md.date2num(f(hm(6,0,20))),-0.6,"gewünschtes Ende 06:00",color="#c0392b",fontsize=8,va="bottom")
ax.grid(axis="x",color="#e5e5e5"); ax.set_axisbelow(True)
for sp in ("top","right"): ax.spines[sp].set_visible(False)
ax.set_title("Beispiel Lauf 1: Master K1–K5 + Folge K6–K10 · berechnete Startzeit %s (%d min)"%(st,dur),fontsize=10,loc="left")
fig.text(0.01,0.01,"K1/K2 Regner nacheinander, K3–K5 Tropfer parallel (max. 3), Übergabe an die Folge mit 3 s Überlappung – Simulation mit dem Baustein-Code",fontsize=7.5,color="#555")
fig.tight_layout(rect=(0,0.04,1,1)); fig.savefig(os.path.join(Q, '..', 'bilder', 'beispiel_ablauf.png'))
print(st,dur,[ (r[0],[(time.strftime('%H:%M:%S',time.gmtime(a)),time.strftime('%H:%M:%S',time.gmtime(e))) for a,e in spans(r[1],r[2])]) for r in rows])
