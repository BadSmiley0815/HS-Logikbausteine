# -*- coding: utf-8 -*-
"""
HSL3 14771 – Verlaufsspeicher für Diagramme (v2.7)

Zeichnet einen Wert (Temperatur, Leistung, Zählerstand …) im HomeServer auf.
Die Diagramme der HTML5-Visu holen die Werte über den Visu-Server (Baustein 14770,
E5 = dessen Instanz-ID) – oder wie bisher über ein 14-Byte-KO an A1.

Ringpuffer (Kalendergrenzen in Ortszeit, Woche beginnt Montag):
    i  Minute   1440 Werte  (24 Stunden)
    h  Stunde   8784 Werte  (1 Jahr)
    d  Tag      3660 Werte  (10 Jahre)
    w  Woche     520 Werte  (10 Jahre)
    M  Monat     240 Werte  (20 Jahre)
    y  Jahr       50 Werte  (50 Jahre)

Speicherung: komprimiert in bis zu 20 remanenten Speichervariablen (je < 10.000 Zeichen),
alle 10 Minuten sowie nach Reset/Import/Löschen/Moduswechsel.

Modus (E3):
    0 = Mittelwert je Intervall   1 = Letzter Wert
    2 = Differenz (Zählerstand → Verbrauch)   3 = Maximum

Zeilen löschen (E10, Zahl – bei jedem Telegramm ausgeführt):
    Die Übersichtsseite des Visu-Servers zeigt vor jeder Zeile eine Nummer. Diese Nummer an E10
    senden → die Zeile wird gelöscht (zur Lücke, die Zeitachse bleibt richtig).
    Erste Ziffer = Ansicht: 1xxxx Minute, 2xxxx Stunde, 3xxxx Tag, 4xxxx Woche, 5xxxx Monat, 6xxxx Jahr;
    der Rest zählt ab dem ältesten Wert (Stunde 20001 = älteste Stundenzeile).
    -1 = alle Werte löschen.

E11 Im Diagramm anzeigen (1 = ja, 0 = ausblenden): steuert, ob der Verlauf in den
    SVG-Diagrammen des Visu-Servers (chart.svg) gezeichnet wird – z. B. über einen Visu-Knopf.

A1 (optional, E9=1): kompakter Text für ein 14-Byte-KO wie in v1.1
    HSH2;<jetzt>;<modus>;<dez>|i,<t_letzter>:v,…|h,…|d,…|w,…|M,…|y,…
    (je Ansicht nur die letzten 120/72/62/104/36/20 Werte, damit es ins KO passt)
"""
import base64
import json
import threading
import time
import zlib

SERIES = (("i", 1440), ("h", 8784), ("d", 3660), ("w", 520), ("M", 240), ("y", 50))
KO_N = {"i": 120, "h": 72, "d": 62, "w": 104, "M": 36, "y": 20}
STATE_VERSION = 3
STORES = 20
SAVE_EVERY = 600          # remanent sichern: spätestens alle 10 Minuten (bei neuen Werten)
CHUNK = 9900


def slot_start(ts, unit):
    """Beginn des Intervalls, in dem ts liegt (Ortszeit)."""
    if unit == "i":
        return int(ts // 60 * 60)
    lt = time.localtime(ts)
    if unit == "h":
        return int(time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, lt.tm_hour, 0, 0, 0, 0, -1)))
    if unit == "d":
        return int(time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1)))
    if unit == "w":
        return int(time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday - lt.tm_wday, 0, 0, 0, 0, 0, -1)))
    if unit == "M":
        return int(time.mktime((lt.tm_year, lt.tm_mon, 1, 0, 0, 0, 0, 0, -1)))
    return int(time.mktime((lt.tm_year, 1, 1, 0, 0, 0, 0, 0, -1)))


_JUMP = {"i": 60, "h": 3600 + 60, "d": 26 * 3600, "w": 7 * 86400 + 26 * 3600, "M": 32 * 86400, "y": 367 * 86400}


def next_start(t, unit):
    return slot_start(t + _JUMP[unit], unit)


def pack(obj):
    raw = base64.b64encode(zlib.compress(json.dumps(obj, separators=(",", ":")).encode("ascii"), 9))
    return [raw[i:i + CHUNK] for i in range(0, len(raw), CHUNK)] or [b""]


def unpack(chunks):
    raw = b"".join(c for c in chunks if isinstance(c, bytes) and c)
    if not raw:
        return None
    return json.loads(zlib.decompress(base64.b64decode(raw)).decode("ascii"))


class LogicModule:
    def __init__(self, hsl3):
        self.fw = hsl3
        self.debug = self.fw.create_debug_section()
        self._lock = threading.RLock()
        self.state = None
        self.mode = 0
        self.dec = 1
        self.hid = ""
        self.name = ""
        self.unit = ""
        self.ko_out = 1
        self.show = 1
        self.server_id = 0
        self._server = None
        self._iid = 0
        self._pending_import = None
        self.last_save_hour = None

    # ------------------------------------------------------------ Lebenszyklus
    def on_init(self, inputs, store):
        self._iid = int(self.fw.get_instance_id())
        self.mode = self._int(inputs.value("mode"), 0)
        self._read_inputs(inputs)
        try:
            st = unpack([store.value("h%02d" % k) for k in range(1, STORES + 1)])
        except Exception as e:
            self.debug.log("Gespeicherter Verlauf unlesbar, starte neu: %r" % (e,))
            st = None
        # Gespeicherten Verlauf IMMER übernehmen – auch wenn E3 beim Start noch nicht (oder anders) belegt ist.
        # (Bis v2.4 wurde bei abweichendem Modus gelöscht; KO-belegte Eingänge haben beim Start oft noch 0.)
        if not st or st.get("v") != STATE_VERSION or "s" not in st:
            st = self._empty()
        else:
            self.mode = self._int(st.get("mode"), self.mode)
        self.state = st
        # Startwert des Eingangs NICHT übernehmen (oft nur Initialwert 0 → falscher Zählerverbrauch)
        self._tick(time.time(), force_publish=True)

    def on_calc(self, inputs):
        old_server = self.server_id
        self._read_inputs(inputs)
        if self.server_id != old_server:
            self._unregister()
            self._register()
        if inputs.changed("reset") and self._int(inputs.value("reset"), 0) == 1:
            with self._lock:
                self.state = self._empty()
                self.state["last"] = self._num(inputs.value("value"))
            self._save()
            self._publish()
            self._status("Verlauf gelöscht")
            return
        try:
            if inputs.changed("delete"):
                self._status(self.delete_row(self._int(inputs.value("delete"), 0)))
        except Exception as e:
            self._status("Loeschen fehlgeschlagen: %s" % e)
        if inputs.changed("mode"):
            new = self._int(inputs.value("mode"), 0)
            if new != self.state.get("mode"):
                with self._lock:
                    self.mode = new
                    self.state["mode"] = new          # vorhandene Werte bleiben (E4 = 1 löscht bei Bedarf)
                self._save()
                self._publish()
                self._status("Modus %d - vorhandene Werte behalten (E4=1 loescht)" % new)
        if inputs.changed("value"):
            v = self._num(inputs.value("value"))
            if v is not None:
                self._tick(time.time())
                self._sample(v)

    def on_timer(self, timer):
        if self._pending_import is not None:
            self._apply_import()
        self._tick(time.time())

    def _read_inputs(self, inputs):
        self.dec = max(0, min(4, self._int(inputs.value("decimals"), 1)))
        self.server_id = self._int(inputs.value("server"), 0)
        self.hid = self._text(inputs.value("hist_id")).strip() or str(self._iid)
        self.name = self._text(inputs.value("name")).strip() or ("Verlauf " + self.hid)
        self.unit = self._text(inputs.value("unit")).strip()
        self.ko_out = self._int(inputs.value("ko_out"), 1)
        self.show = 0 if self._int(inputs.value("show"), 1) == 0 else 1

    # ------------------------------------------------------------ Visu-Server
    def _register(self):
        if self._server is not None or self.server_id <= 0:
            return
        try:
            srv = self.fw.get_instance(self.server_id)
            if srv is None or not hasattr(srv, "register_history"):
                raise ValueError("Instanz %d ist kein Visu-Server" % self.server_id)
            srv.register_history(self)
            self._server = srv
            self._status("Angemeldet am Visu-Server (Instanz %d)" % self.server_id)
        except Exception as e:
            self._status("Visu-Server %d nicht erreichbar: %s" % (self.server_id, e))

    def _unregister(self):
        if self._server is not None:
            try:
                self._server.unregister_history(self)
            except Exception:
                pass
        self._server = None

    # Aufrufe durch den Visu-Server (HTTP-Thread) – nur lesen bzw. vormerken
    def instance_id(self):
        return self._iid

    def history_id(self):
        return self.hid

    def info(self):
        with self._lock:
            pts = {k: len(self.state["s"][k]["vals"]) for k, n in SERIES}
        return {"id": self.hid, "name": self.name, "unit": self.unit, "mode": self.mode, "dec": self.dec,
                "points": pts, "instance": self._iid, "show": self.show}

    def series(self, u, n=None):
        if u not in dict(SERIES):
            u = "h"
        with self._lock:
            a = self.state["s"][u]
            vals = list(a["vals"][-n:] if n else a["vals"])
            t_last = slot_start(a["t"] - 1, u)
            last = self.state.get("last")
        return {"id": self.hid, "name": self.name, "unit": self.unit, "mode": self.mode, "dec": self.dec,
                "u": u, "t_last": t_last * 1000, "vals": vals, "current": last, "now": int(time.time() * 1000), "show": self.show}

    def export_state(self):
        with self._lock:
            return json.loads(json.dumps(self.state))

    def queue_import(self, state, merge=False):
        self._pending_import = (state, merge)   # wird beim nächsten Timer-Tick im Kontext übernommen

    def _apply_import(self):
        (st, merge), self._pending_import = self._pending_import, None
        try:
            if not isinstance(st, dict) or st.get("v") != STATE_VERSION or "s" not in st:
                raise ValueError("falsches Format")
            if merge:
                if st.get("mode") != self.state.get("mode"):
                    raise ValueError("anderer Modus in der Sicherung - nur Ueberschreiben moeglich")
                n = self._merge(st)
                self._save()
                self._publish()
                self._status("Sicherung ergaenzt: %d fehlende Werte uebernommen" % n)
                return
            with self._lock:
                self.state = st
                self.mode = st.get("mode", self.mode)
            self._save()
            self._publish()
            self._status("Verlauf wiederhergestellt (ueberschrieben)")
        except Exception as e:
            self._status("Import fehlgeschlagen: %s" % e)

    # ------------------------------------------------------------ Zeilen löschen (E10)
    ROW_BASE = {"i": 10000, "h": 20000, "d": 30000, "w": 40000, "M": 50000, "y": 60000}

    def delete_row(self, num):
        """num = Zeilennummer wie auf der Übersichtsseite, -1 = alles löschen, 0 = nichts."""
        if num == 0:
            return "E10: 0 = keine Aktion"
        if num < 0:
            with self._lock:
                last = self.state.get("last")
                self.state = self._empty()
                self.state["last"] = last
            self._save()
            self._publish()
            return "Alle Werte geloescht"
        unit = {v // 10000: k for k, v in self.ROW_BASE.items()}.get(num // 10000)
        row = num % 10000
        if unit is None or row < 1:
            return "Zeile %d gibt es nicht (1xxxx Minute ... 6xxxx Jahr)" % num
        with self._lock:
            vals = self.state["s"][unit]["vals"]
            if row > len(vals):
                return "Zeile %d gibt es nicht (Ansicht hat %d Zeilen)" % (num, len(vals))
            old, vals[row - 1] = vals[row - 1], None
        self._save()
        self._publish()
        return "Zeile %d geloescht (Wert %s)" % (num, self._fmt(old) if old is not None else "war leer")

    @staticmethod
    def _slot_times(a, key, count):
        """Startzeiten der letzten count Zeilen (älteste zuerst) einer Ansicht."""
        t = slot_start(a["t"] - 1, key)
        out = []
        for _ in range(count):
            out.append(t)
            t = slot_start(t - 1, key)
        out.reverse()
        return out

    def _merge(self, st):
        """Nur fehlende Werte aus der Sicherung übernehmen (vorhandene bleiben)."""
        added = 0
        with self._lock:
            for key, n in SERIES:
                cur, bak = self.state["s"][key], (st.get("s") or {}).get(key)
                if not bak or not bak.get("vals"):
                    continue
                bt = self._slot_times(bak, key, len(bak["vals"]))
                bmap = {t: v for t, v in zip(bt, bak["vals"]) if v is not None}
                if not bmap:
                    continue
                ct = self._slot_times(cur, key, len(cur["vals"]))
                cmap = {t: v for t, v in zip(ct, cur["vals"]) if v is not None}
                oldest = min(bmap)
                if ct:
                    oldest = min(oldest, ct[0])
                times = []
                t = slot_start(cur["t"] - 1, key)
                while t >= oldest and len(times) < n:
                    times.append(t)
                    t = slot_start(t - 1, key)
                times.reverse()
                vals = []
                for t in times:
                    if t in cmap:
                        vals.append(cmap[t])
                    elif t in bmap:
                        vals.append(bmap[t])
                        added += 1
                    else:
                        vals.append(None)
                while vals and vals[0] is None:
                    vals.pop(0)
                cur["vals"] = vals
        return added

    # ------------------------------------------------------------ Verarbeitung
    def _tick(self, now, force_publish=False):
        self._register()
        changed = self._close_slots(now)
        if changed and (self.last_save_hour is None or now - self.last_save_hour >= SAVE_EVERY):
            self.last_save_hour = now
            self._save()
        if changed or force_publish:
            self._publish()
        self.fw.set_timer("tick", max(1, int(slot_start(now, "i") + 61 - now)))

    def _empty(self):
        now = time.time()
        st = {"v": STATE_VERSION, "mode": self.mode, "last": None, "s": {}}
        for key, n in SERIES:
            st["s"][key] = {"t": slot_start(now, key), "vals": [], "sum": 0.0, "cnt": 0, "max": None, "first": None}
        return st

    def _sample(self, v):
        with self._lock:
            st = self.state
            for key, n in SERIES:
                a = st["s"][key]
                a["sum"] += v
                a["cnt"] += 1
                a["max"] = v if a["max"] is None else max(a["max"], v)
                if a["first"] is None:
                    a["first"] = st["last"] if st["last"] is not None else v
            st["last"] = v
        self.debug.set("Letzter Wert", str(v))

    def _slot_value(self, a):
        last = self.state["last"]
        if self.mode == 2:
            if a["first"] is None or last is None:
                return 0.0 if last is not None else None
            return max(0.0, last - a["first"])
        if self.mode == 3:
            return a["max"] if a["max"] is not None else last
        if self.mode == 1:
            return last
        return a["sum"] / a["cnt"] if a["cnt"] else last

    def _close_slots(self, now):
        changed = False
        with self._lock:
            for key, n in SERIES:
                a = self.state["s"][key]
                cur = slot_start(now, key)
                if cur <= a["t"]:
                    continue
                a["vals"].append(self._round(self._slot_value(a)))
                t, gaps = next_start(a["t"], key), 0
                while t < cur and gaps < n:
                    a["vals"].append(None)
                    t, gaps = next_start(t, key), gaps + 1
                del a["vals"][:-n]
                a["t"] = cur
                a["sum"], a["cnt"], a["max"] = 0.0, 0, None
                a["first"] = self.state["last"]
                changed = True
        return changed

    def _round(self, v):
        if v is None:
            return None
        return round(v, self.dec) if self.dec else int(round(v))

    # ------------------------------------------------------------ Ausgabe / Speichern
    def _fmt(self, v):
        if v is None:
            return ""
        s = ("%." + str(self.dec) + "f") % v if self.dec else str(int(v))
        return s.rstrip("0").rstrip(".") if "." in s else s

    def _publish(self):
        total = sum(len(self.state["s"][k]["vals"]) for k, n in SERIES)
        self.fw.set_output("count", float(total))
        self.debug.set("Werte", str(total))
        if not self.ko_out:
            return
        parts = ["HSH2;%d;%d;%d" % (int(time.time()), self.mode, self.dec)]
        for key, n in SERIES:
            a = self.state["s"][key]
            parts.append("%s,%d:%s" % (key, slot_start(a["t"] - 1, key),
                                       ",".join(self._fmt(v) for v in a["vals"][-KO_N[key]:])))
        text = "|".join(parts)
        self.fw.set_output("history", text.encode("ascii"))
        self.debug.set("KO-Zeichen", str(len(text)))

    def _save(self):
        with self._lock:
            chunks = pack(self.state)
        if len(chunks) > STORES:
            # sollte praktisch nie passieren: dann die Minutenwerte opfern
            with self._lock:
                self.state["s"]["i"]["vals"] = self.state["s"]["i"]["vals"][-240:]
                chunks = pack(self.state)
        for k in range(1, STORES + 1):
            self.fw.set_store("h%02d" % k, chunks[k - 1] if k <= len(chunks) else b"")
        self.debug.set("Speicher", "%d Zeichen in %d Variablen (%s)" % (sum(len(c) for c in chunks), len(chunks),
                                                                         time.strftime("%d.%m. %H:%M")))

    def _status(self, text):
        t = text
        for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"),
                     ("ß", "ss"), ("–", "-"), ("…", "...")):
            t = t.replace(a, b)
        self.fw.set_output("status", t.encode("ascii", "replace")[:200])
        self.debug.set("Status", text)

    # ------------------------------------------------------------ Hilfen
    @staticmethod
    def _num(v):
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(v.decode("ascii").replace(",", ".")) if isinstance(v, bytes) else None
        except Exception:
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
                return v.decode("utf-8")           # der HS liefert Texte als UTF-8
            except UnicodeDecodeError:
                return v.decode("iso-8859-15", "replace")
        return "" if v is None else str(v)
