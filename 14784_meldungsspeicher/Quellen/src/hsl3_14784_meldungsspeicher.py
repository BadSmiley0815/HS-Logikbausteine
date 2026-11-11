# -*- coding: utf-8 -*-
"""
HSL3 14784 – Meldungsspeicher (v1.0)

Eigenes Meldungsarchiv im HomeServer – unabhängig von den Meldungsarchiven des Experten.
Eine Instanz = ein Archiv (z. B. „Wetterstation“, „Alarmanlage“).

Melder 1–16 (E7–E22, 1 Bit/Zahl) mit Text je Melder (E23–E38):
    "Text EIN|Text AUS|Stufe"
      - nur "Windalarm"            → „Windalarm – ein“ / „Windalarm – aus“, Stufe 1
      - "Alarm Tor 1|"             → nur EIN wird gemeldet (AUS leer = keine Meldung)
      - "|Netz ok"                 → nur AUS wird gemeldet
      - "Scharf|Unscharf|0"        → Stufe 0 = Info, 1 = Warnung, 2 = Alarm
    Gemeldet wird nur bei Wertwechsel (E5 = 1: jedes Telegramm). Werte ≠ 0 zählen als EIN.
E6 Freitext (14-Byte-Text oder Text): jeder neue Text wird mit Stufe aus E4 gespeichert.

Abruf über den Visu-Server 14770 (ab v1.11), E1 = dessen Instanz-ID:
    GET  https://<HS>/visu-daten/api/messages            alle Archive (Name, Anzahl, offene Alarme)
    GET  https://<HS>/visu-daten/api/messages?id=wetter  Einträge (n=, since=)
    POST https://<HS>/visu-daten/api/messages/ack        {"id": "wetter"} – alle quittieren

Speicherung: komprimiert in bis zu 20 remanenten Speichervariablen, nach jeder Meldung
(höchstens alle 10 s gebündelt) – Einträge bleiben nach Neustart erhalten.
"""
import base64
import json
import threading
import time
import zlib

VERSION = "1.0"
N_MELDER = 16
STATE_VERSION = 1
STORES = 20
CHUNK = 9900
SAVE_DELAY = 10
LEVELS = ("Info", "Warnung", "Alarm")


def pack(obj):
    raw = base64.b64encode(zlib.compress(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8"), 9))
    return [raw[i:i + CHUNK] for i in range(0, len(raw), CHUNK)] or [b""]


def unpack(chunks):
    raw = b"".join(c for c in chunks if isinstance(c, bytes) and c)
    if not raw:
        return None
    return json.loads(zlib.decompress(base64.b64decode(raw)).decode("utf-8"))


def parse_text(spec, default_level=1):
    """'Text EIN|Text AUS|Stufe' → (text_ein, text_aus, stufe). None = keine Meldung."""
    spec = (spec or "").strip()
    if not spec:
        return None, None, default_level
    parts = spec.split("|")
    if len(parts) == 1:
        return spec + " – ein", spec + " – aus", default_level
    on = parts[0].strip() or None
    off = parts[1].strip() or None
    lvl = default_level
    if len(parts) > 2:
        try:
            lvl = max(0, min(2, int(parts[2].strip())))
        except ValueError:
            pass
    return on, off, lvl


class LogicModule:
    def __init__(self, hsl3):
        self.fw = hsl3
        self.debug = self.fw.create_debug_section()
        self._lock = threading.RLock()
        self.state = None
        self.server_id = 0
        self._server = None
        self._iid = 0
        self.aid = ""
        self.name = ""
        self.maxn = 2000
        self.every = 0
        self.free_level = 1
        self.texts = [(None, None, 1)] * N_MELDER
        self._dirty = False
        self._pending_ack = False
        self._pending_import = None

    # ------------------------------------------------------------ Lebenszyklus
    def on_init(self, inputs, store):
        self._iid = int(self.fw.get_instance_id())
        self._read_inputs(inputs)
        try:
            st = unpack([store.value("m%02d" % k) for k in range(1, STORES + 1)])
        except Exception as e:
            self.debug.log("Gespeicherte Meldungen unlesbar, starte leer: %r" % (e,))
            st = None
        if not isinstance(st, dict) or st.get("v") != STATE_VERSION:
            st = {"v": STATE_VERSION, "seq": 0, "e": [], "last": {}}
        self.state = st
        # Startwerte merken, aber NICHT melden (beim Start kommen oft Initialwerte)
        for i in range(1, N_MELDER + 1):
            k = str(i)
            if k not in self.state["last"]:
                v = self._bit(inputs.value("m%d" % i))
                if v is not None:
                    self.state["last"][k] = v
        self._register()
        self._publish()
        self.fw.set_timer("tick", 30)

    def on_calc(self, inputs):
        old_server = self.server_id
        self._read_inputs(inputs)
        if self.server_id != old_server:
            self._unregister()
            self._register()
        if inputs.changed("clear") and self._int(inputs.value("clear"), 0) == 1:
            with self._lock:
                self.state["e"] = []
            self._save_now()
            self._publish()
            self._status("Alle Meldungen geloescht")
            return
        if inputs.changed("ack") and self._int(inputs.value("ack"), 0) == 1:
            self.acknowledge()
        if inputs.changed("free"):
            t = self._text(inputs.value("free")).strip()
            if t:
                self._add(t, self.free_level, 0, None)
        for i in range(1, N_MELDER + 1):
            ident = "m%d" % i
            if not inputs.changed(ident):
                continue
            v = self._bit(inputs.value(ident))
            if v is None:
                continue
            k = str(i)
            prev = self.state["last"].get(k)
            self.state["last"][k] = v
            if prev == v and not self.every:
                continue
            on, off, lvl = self.texts[i - 1]
            text = on if v else off
            if text:
                self._add(text, lvl if v else 0, i, v)
            else:
                self._dirty = True

    def on_timer(self, timer):
        if self._pending_import is not None:
            self._apply_import()
        if self._pending_ack:
            self._pending_ack = False
            self.acknowledge()
        self._register()
        if self._dirty:
            self._save_now()
        self.fw.set_timer("tick", 30)

    def _read_inputs(self, inputs):
        self.server_id = self._int(inputs.value("server"), 0)
        self.aid = self._text(inputs.value("arch_id")).strip() or str(self._iid)
        self.name = self._text(inputs.value("name")).strip() or ("Meldungen " + self.aid)
        self.maxn = max(50, min(10000, self._int(inputs.value("max"), 2000)))
        self.free_level = max(0, min(2, self._int(inputs.value("level"), 1)))
        self.every = 1 if self._int(inputs.value("every"), 0) == 1 else 0
        self.texts = [parse_text(self._text(inputs.value("t%d" % i)), 1) for i in range(1, N_MELDER + 1)]

    # ------------------------------------------------------------ Meldungen
    def _add(self, text, level, melder, value):
        with self._lock:
            self.state["seq"] += 1
            self.state["e"].append([int(time.time() * 1000), level, text, melder, value, 0, self.state["seq"]])
            del self.state["e"][:-self.maxn]
        self._dirty = True
        self.fw.set_output("last", text.encode("utf-8")[:250])
        self.debug.set("Letzte Meldung", "%s (%s)" % (text, LEVELS[level]))
        self._publish()
        self.fw.set_timer("tick", SAVE_DELAY)

    def acknowledge(self):
        with self._lock:
            n = 0
            for e in self.state["e"]:
                if not e[5]:
                    e[5] = 1
                    n += 1
        self._dirty = True
        self._publish()
        self._status("%d Meldungen quittiert" % n)
        self._save_now()

    # ------------------------------------------------------------ Visu-Server (14770 ab v1.11)
    def _register(self):
        if self._server is not None or self.server_id <= 0:
            return
        try:
            srv = self.fw.get_instance(self.server_id)
            if srv is None or not hasattr(srv, "register_messages"):
                raise ValueError("Instanz %d ist kein Visu-Server ab v1.11" % self.server_id)
            srv.register_messages(self)
            self._server = srv
            self._status("Angemeldet am Visu-Server (Instanz %d)" % self.server_id)
        except Exception as e:
            self._status("Visu-Server %d nicht erreichbar: %s" % (self.server_id, e))

    def _unregister(self):
        if self._server is not None:
            try:
                self._server.unregister_messages(self)
            except Exception:
                pass
        self._server = None

    # Aufrufe durch den Visu-Server (HTTP-Thread) – nur lesen bzw. vormerken
    def instance_id(self):
        return self._iid

    def archive_id(self):
        return self.aid

    def info(self):
        with self._lock:
            e = self.state["e"]
            open_alarms = sum(1 for x in e if x[1] == 2 and not x[5])
            open_all = sum(1 for x in e if x[1] > 0 and not x[5])
            last = e[-1] if e else None
        return {"id": self.aid, "name": self.name, "count": len(e), "open": open_all, "open_alarms": open_alarms,
                "last": self._entry(last) if last else None, "instance": self._iid}

    def entries(self, n=None, since=None):
        with self._lock:
            e = list(self.state["e"])
        if since:
            e = [x for x in e if x[6] > since]
        if n:
            e = e[-n:]
        e.reverse()                         # neueste zuerst
        return {"id": self.aid, "name": self.name, "now": int(time.time() * 1000),
                "entries": [self._entry(x) for x in e]}

    @staticmethod
    def _entry(x):
        return {"t": x[0], "level": x[1], "text": x[2], "melder": x[3], "value": x[4], "ack": x[5], "seq": x[6]}

    def queue_ack(self):
        self._pending_ack = True
        self.fw.run_in_context(self._kick, ())

    def _kick(self):
        self.fw.set_timer("tick", 1)

    def export_state(self):
        with self._lock:
            return json.loads(json.dumps(self.state))

    def queue_import(self, state, merge=False):
        self._pending_import = (state, merge)
        self.fw.run_in_context(self._kick, ())

    def _apply_import(self):
        (st, merge), self._pending_import = self._pending_import, None
        try:
            if not isinstance(st, dict) or st.get("v") != STATE_VERSION:
                raise ValueError("falsches Format")
            with self._lock:
                if merge:
                    have = set((x[0], x[2]) for x in self.state["e"])
                    add = [x for x in st.get("e", []) if (x[0], x[2]) not in have]
                    self.state["e"] = sorted(self.state["e"] + add, key=lambda x: x[0])[-self.maxn:]
                    msg = "Sicherung ergaenzt: %d Meldungen" % len(add)
                else:
                    self.state = st
                    msg = "Meldungen wiederhergestellt (ueberschrieben)"
                seq = 0
                for x in self.state["e"]:
                    seq += 1
                    x[6] = seq
                self.state["seq"] = seq
            self._save_now()
            self._publish()
            self._status(msg)
        except Exception as e:
            self._status("Import fehlgeschlagen: %s" % e)

    # ------------------------------------------------------------ Ausgabe / Speichern
    def _publish(self):
        with self._lock:
            e = self.state["e"]
            n = len(e)
            open_all = sum(1 for x in e if x[1] > 0 and not x[5])
            open_alarms = sum(1 for x in e if x[1] == 2 and not x[5])
        self.fw.set_output("count", float(n))
        self.fw.set_output("open", float(open_all))
        self.fw.set_output("alarm", 1.0 if open_alarms else 0.0)
        self.debug.set("Meldungen", "%d (offen %d, Alarme %d)" % (n, open_all, open_alarms))

    def _save_now(self):
        self._dirty = False
        with self._lock:
            chunks = pack(self.state)
            while len(chunks) > STORES and len(self.state["e"]) > 50:
                del self.state["e"][:len(self.state["e"]) // 4]
                chunks = pack(self.state)
        for k in range(1, STORES + 1):
            self.fw.set_store("m%02d" % k, chunks[k - 1] if k <= len(chunks) else b"")
        self.debug.set("Speicher", "%d Zeichen in %d Variablen (%s)" % (sum(len(c) for c in chunks), len(chunks),
                                                                         time.strftime("%d.%m. %H:%M:%S")))

    def _status(self, text):
        t = text
        for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"),
                     ("ß", "ss"), ("–", "-"), ("…", "...")):
            t = t.replace(a, b)
        self.fw.set_output("status", t.encode("ascii", "replace")[:200])
        self.debug.set("Status", text)

    # ------------------------------------------------------------ Hilfen
    @staticmethod
    def _bit(v):
        if isinstance(v, (int, float)):
            return 1 if v else 0
        if isinstance(v, bytes):
            s = v.strip()
            if not s:
                return None
            try:
                return 1 if float(s.decode("ascii").replace(",", ".")) else 0
            except Exception:
                return 1
        return None

    @staticmethod
    def _int(v, default):
        try:
            return int(float(v))
        except Exception:
            return default

    @staticmethod
    def _text(v):
        if isinstance(v, bytes):
            try:
                return v.decode("utf-8")
            except UnicodeDecodeError:
                return v.decode("iso-8859-15", "replace")
        return "" if v is None else str(v)
