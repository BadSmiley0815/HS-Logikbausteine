# -*- coding: utf-8 -*-
"""Erzeugt DE-log14783.html und EN-log14783.html im Aufbau der Experten-Hilfe
(Inhalt, nummerierte Kapitel, Ein-/Ausgangstabellen, Hinweis-Kästen) – wie bei 14778.
Namen und Startwerte kommen aus config.json. Aufruf: python help/make_help.py"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
M = json.load(io.open(os.path.join(SRC, "config.json"), encoding="utf-8"))["module"]
ID, VER = M["id"], M["version"]

STYLE = """body { background: none; }
table.ex { border-collapse: collapse; margin: 8px 0 14px 0; width: 100%; }
table.ex th { background: #3c4a57; color: #fff; text-align: left; padding: 6px 9px; }
table.ex td { padding: 6px 9px; border-bottom: 1px solid #e3e7ea; vertical-align: top; }
table.ex tr:nth-child(even) td { background: #f7f9fa; }
table.ex td.nm { font-weight: bold; white-space: nowrap; }
.descr ul { margin: 4px 0 4px 18px; padding: 0; } .descr li { margin: 3px 0; }"""

L = {
    "de": dict(back="Zurück", fwd="Vor", search="Suchen", help="Hilfe", logic="Logik", toc="Inhalt",
               nr="Nr.", name="Name", init="Init", descr="Beschreibung", warn="Achtung", hint="Hinweis",
               send='s = <a href="logic2.html#_Toc17193931">send</a>, sbc = <a href="logic2.html#_Toc17193931">send by change</a>'),
    "en": dict(back="Back", fwd="Forward", search="Search", help="Help", logic="Logic", toc="Contents",
               nr="No.", name="Name", init="Init", descr="Description", warn="Attention", hint="Note",
               send='s = <a href="logic2.html#_Toc17193931">send</a>, sbc = <a href="logic2.html#_Toc17193931">send by change</a>'),
}

CAM_DE = {
    "name": "Name der Kamera, Teil der Adresse: <code>einfahrt</code> &rarr; <code>…/kamera/einfahrt.jpg</code>. Der QC-Client ordnet die Kamera über diesen Namen zu. Leer = Kamera nicht benutzt.",
    "addr": "<code>&lt;Kamera&gt;</code> (Axis), ganze Standbild-Adresse oder <code>onvif://&lt;Kamera&gt;</code> – siehe Kapitel „Adresse der Kamera“.",
    "user": "Benutzer an der Kamera. Eigener Benutzer nur mit Zuschauer-Recht empfohlen. Axis führt ONVIF-Konten getrennt von den normalen Konten.",
    "pwd": "Passwort an der Kamera. Wird nie ausgegeben oder protokolliert.",
}
CAM_EN = {
    "name": "Camera name, part of the URL: <code>einfahrt</code> &rarr; <code>…/kamera/einfahrt.jpg</code>. Empty = camera not used.",
    "addr": "<code>&lt;camera&gt;</code> (Axis), full still image URL, or <code>onvif://&lt;camera&gt;</code> – see chapter “Camera address”.",
    "user": "Camera user. A separate viewer-only account is recommended. Axis keeps ONVIF accounts separate from regular accounts.",
    "pwd": "Camera password. Never output or logged.",
}
IN_DE = {
    "base_path": "Basis-Pfad: <code>kamera</code> &rarr; <code>https://&lt;HS&gt;/kamera/</code>. Der HomeServer leitet diese Adresse an den Port von E2 weiter.",
    "destination_port": "Interner Port, Standard 8095. Nicht 0 (sonst 503) und nicht doppelt (8092 = 14770, 8093 = 14778, 8094 = 14779).",
    "key": "Zugangsschlüssel. Steht in jeder Bild-Adresse als <code>?k=…</code>. Leer = ohne Schutz (nicht empfohlen).",
    "restart": "Der Experte verlangt einen mit einem KO belegten Eingang. 1 = Server neu starten.",
}
IN_EN = {
    "base_path": "Base path: <code>kamera</code> &rarr; <code>https://&lt;HS&gt;/kamera/</code>. The HomeServer forwards this URL to the port of I2.",
    "destination_port": "Internal port, default 8095. Not 0 (otherwise 503) and not used twice.",
    "key": "Access key, part of every image URL as <code>?k=…</code>. Empty = unprotected (not recommended).",
    "restart": "The Experte requires one input connected to a communication object. 1 = restart server.",
}
OUT_DE = {
    "status": "Status als Klartext, z. B. „Bereit: /kamera/ (Port 8095), 2 Kamera(s)“.",
    "requests": "Zahl der Abrufe seit dem Start.",
    "streams": "Gerade laufende Live-Ströme (je Kamera höchstens 4).",
    "test": "Ergebnis der letzten Prüfung (<code>…/test</code>), z. B. „einfahrt OK 120 ms; hof HTTP 401“.",
}
OUT_EN = {
    "status": "Status text, e.g. “Bereit: /kamera/ (Port 8095), 2 Kamera(s)”.",
    "requests": "Number of requests since start.",
    "streams": "Live streams currently running (at most 4 per camera).",
    "test": "Result of the last check (<code>…/test</code>).",
}


def box(kind, title, text):
    return ('<div class="alert-box ibox-%s"><div class="box-title">%s</div><div class="box-text"><div class="descr">%s</div></div></div>'
            % (kind, title, text))


def table(head, rows):
    return ('<table class="ex"><tr>%s</tr>%s</table>' % (
        "".join("<th>%s</th>" % h for h in head),
        "".join('<tr><td class="nm">%s</td>%s</tr>' % (r[0], "".join("<td>%s</td>" % c for c in r[1:])) for r in rows)))


def init(v):
    return ('io-init string center', '"%s"' % v) if isinstance(v, str) else ('io-init center', "%g" % v)


def io_tables(lang):
    t = L[lang]
    de = lang == "de"
    tr = M["translations"][0]
    rows = []
    for n, i in enumerate(M["inputs"], 1):
        label = tr["translation_inputs"][n - 1]["label"] if de else i["label"]
        ident = i["identifier"]
        d = (IN_DE if de else IN_EN).get(ident) or (CAM_DE if de else CAM_EN)[ident.split("_", 1)[1]]
        c, v = init(i["init_value"])
        rows.append('<tr><td class="io-nr input center">%d</td><td class="io-name">%s</td><td class="%s">%s</td>'
                    '<td class="io-descr"><div class="descr">%s</div></td></tr>' % (n, label, c, v, d))
    ins = ('<div><table class="table-in"><tr><th class="io-nr center">%s</th><th class="io-name">%s</th><th class="io-init center">%s</th>'
           '<th class="io-descr">%s</th></tr>%s</table></div>' % (t["nr"], t["name"], t["init"], t["descr"], "".join(rows)))
    rows = []
    for n, o in enumerate(M["outputs"], 1):
        label = tr["translation_outputs"][n - 1]["label"] if de else o["label"]
        c, v = init(o["init_value"])
        rows.append('<tr><td class="io-nr output center">%d</td><td class="io-name">%s</td><td class="%s">%s</td><td class="o-sbc center">s</td>'
                    '<td class="io-descr"><div class="descr">%s</div></td></tr>' % (n, label, c, v, (OUT_DE if de else OUT_EN)[o["identifier"]]))
    outs = ('<div><table class="table-out"><tr><th class="io-nr center">%s</th><th class="io-name">%s</th><th class="io-init center">%s</th>'
            '<th class="o-sbc center"><a href="logic2.html#_Toc17193931">SBC</a></th><th class="io-descr">%s</th></tr>%s</table>'
            '<div class="small">%s</div></div>' % (t["nr"], t["name"], t["init"], t["descr"], "".join(rows), t["send"]))
    return ins, outs


def info(rows):
    return '<table class="table-logic-info">%s</table>' % "".join("<tr><th>%s</th><td>%s</td></tr>" % r for r in rows)


def chapters_de():
    ins, outs = io_tables("de")
    return [
        ("Beschreibung", '<div class="descr">Holt Standbilder und Live-Bilder von bis zu 6 Netzwerkkameras und gibt sie über die Weiterleitung des HomeServers aus – '
         'gleiche Adresse und gleiches Zertifikat wie der HS. Der Browser muss sich nicht an der Kamera anmelden; die Zugangsdaten stehen nur im Baustein.<br><br>'
         '&bull; <b>Kameras:</b> Axis, jede Kamera mit einer Standbild-Adresse, oder ONVIF (der Baustein ermittelt die Adressen selbst).<br>'
         '&bull; <b>Anmeldung an der Kamera:</b> Digest oder Basic, bei ONVIF zusätzlich WS-Security. http oder https; selbst ausgestellte Zertifikate werden angenommen.<br>'
         '&bull; <b>Live-Bild:</b> MJPEG der Kamera wird durchgereicht. Bietet die Kamera keinen an, baut der Baustein den Strom aus schnell nachgeladenen Standbildern.<br>'
         '&bull; <b>Prüfseite</b> unter <code>https://&lt;HS&gt;/kamera/</code> mit Standbild, Live-Bild und Bildern pro Sekunde je Kamera.</div>'
         + box("warn", "Achtung", "E2 muss im Experten eingetragen sein (8095). Steht er auf 0, leitet der HomeServer nicht weiter (503 Service Unavailable).")
         + box("hint", "Hinweis", "Der Schlüssel (E3) steht in jeder Bild-Adresse und ist damit für jeden Benutzer der Visu sichtbar. "
               "An der Kamera deshalb einen eigenen Benutzer nur mit Zuschauer-Recht anlegen.")),
        ("Eingänge", ins),
        ("Ausgänge", outs),
        ("Sonstiges", info([("Neuberechnung bei Start:", "Ja"), ("Baustein ist remanent:", "Nein"), ("Interne Bezeichnung:", ID),
                            ("Version:", VER + " (Prüffassung)"), ("Kontext:", M["context"]), ("Kategorie:", "Visualisierung"),
                            ("Autor:", "Roman Rausch / Elektro Rausch")])),
        ("Adresse der Kamera", '<div class="descr">Die Art der Kamera ergibt sich aus dem Eintrag in „Adresse“ (E6, E10, E14, E18, E22, E26):</div>'
         + table(["Eintrag", "Art", "Verhalten"], [
             ["<code>&lt;Kamera&gt;</code><br><code>https://&lt;Kamera&gt;</code>", "Axis",
              "Standbild <code>/axis-cgi/jpg/image.cgi</code>, Live-Bild <code>/axis-cgi/mjpg/video.cgi</code>. Braucht ein normales Axis-Konto. "
              "Vorgaben sind möglich: <code>https://&lt;Kamera&gt;?resolution=1280x720&amp;compression=25&amp;camera=1</code>."],
             ["<code>https://&lt;Kamera&gt;/pfad/bild.cgi?…</code>", "Standbild-Adresse",
              "Genau diese Adresse wird als Standbild abgerufen, alle Parameter bleiben erhalten. Beispiel: "
              "<code>https://&lt;Kamera&gt;/onvif-cgi/jpg/image.cgi?resolution=1280x720&amp;compression=30</code>. Live-Bild aus Standbildern."],
             ["<code>onvif://&lt;Kamera&gt;</code>", "ONVIF",
              "Der Baustein fragt die Kamera nach Profilen und Standbild-Adresse (Benutzer = ONVIF-Konto). Er probiert erst https, dann http; "
              "ein Port ist möglich (<code>onvif://&lt;Kamera&gt;:8080</code>). Live-Bild aus Standbildern."],
         ])
         + '<div class="descr"><b>Auflösung bei ONVIF:</b> <code>onvif://&lt;Kamera&gt;?resolution=1280x720</code>. Ohne Angabe gilt 1280x720. '
           'Gewählt wird das Profil der Kamera, das der Auflösung am nächsten kommt.</div>'
         + box("hint", "Hinweis", "Axis: Ein ONVIF-Konto gilt für <code>onvif://…</code> und <code>/onvif-cgi/…</code>, nicht für <code>/axis-cgi/…</code>.")),
        ("Adressen für Browser und QC-Client", table(["Adresse", "Inhalt"], [
            ["<code>https://&lt;HS&gt;/kamera/</code>", "Prüfseite: Schlüssel eingeben, zeigt je Kamera Standbild (mit Bildern/s) und Live-Bild"],
            ["<code>…/kamera/&lt;Name&gt;.jpg?k=&lt;Schlüssel&gt;</code>", "Standbild"],
            ["<code>…/kamera/&lt;Name&gt;.mjpg?k=&lt;Schlüssel&gt;</code>", "Live-Bild als MJPEG-Strom"],
            ["<code>…/kamera/list?k=&lt;Schlüssel&gt;</code>", "Namen der Kameras (für den QC-Client)"],
            ["<code>…/kamera/test?k=&lt;Schlüssel&gt;</code>", "Prüfung aller Kameras als JSON"],
        ]) + '<div class="descr"><b>Zusatz-Parameter:</b> <code>resolution</code>, <code>fps</code>, <code>compression</code>, <code>camera</code> – '
             'z. B. <code>&amp;resolution=1280x720&amp;fps=10</code>. Lehnt die Kamera einen Parameter ab, geht es mit der Vorgabe aus „Adresse“ weiter.<br>'
             '<b>Live-Bild aus Standbildern:</b> Vorgabe 8 Bilder/s, mit <code>&amp;fps=…</code> 1 bis 15. Wie viele Bilder wirklich ankommen, hängt von Kamera, Auflösung und HS ab.<br>'
             '<b>RTSP/H.264</b> kann der Baustein nicht umwandeln; die RTSP-Adresse einer ONVIF-Kamera zeigt die Prüfseite nur an.<br>'
             '<b>QC-Client:</b> unter „Kamera-Proxy“ Adresse (<code>https://&lt;HS&gt;/kamera/</code>) und Schlüssel eintragen. Kameras, deren Name im Plugin zum Namen im Baustein passt, laufen dann über den Proxy.</div>'),
        ("Fehlersuche", '<div class="descr">Die Prüfseite zeigt je Kamera <code>art</code>, <code>http</code> (Antwort der Kamera), <code>detail</code> (Fehlertext der Kamera) und <code>ziel</code>. '
         'Bei ONVIF zusätzlich <code>profile</code>, <code>profil</code> (gewählt), <code>standbild</code>, <code>strom</code> (RTSP, nur Auskunft) und <code>uhr</code> (Abweichung der Kamera-Uhr).</div>'
         + table(["Anzeige", "Bedeutung"], [
             ["401", "Benutzer oder Passwort falsch"],
             ["400", "Kamera lehnt die Anfrage ab, Grund steht in <code>detail</code>. Bei ONVIF mit „not authorized“: ONVIF-Konto oder Passwort falsch"],
             ["404", "Pfad gibt es nicht. Keine Axis-Kamera? Dann die ganze Standbild-Adresse oder <code>onvif://…</code> eintragen"],
             ["Fehler ohne http", "Kamera nicht erreichbar (Adresse, Port, http/https)"],
             ["503 vom HomeServer", "E2 Port fehlt oder ist doppelt vergeben"],
         ]) + '<div class="descr">Nach einem ONVIF-Fehler fragt der Baustein die Kamera frühestens nach 15 Sekunden neu.</div>'),
        ("Änderungen", table(["Version", "Änderung"], [
            ["0.5", "Adresse mit Pfad wird als Standbild-Adresse übernommen (bisher wurde der Pfad verworfen) · ONVIF mit wählbarer Auflösung · "
                    "Live-Bild aus Standbildern, wenn die Kamera keinen MJPEG-Strom anbietet · 6 statt 3 Kameras (E17–E28 neu, E1–E16 unverändert) · abgelehnte Parameter werden gemerkt"],
            ["0.4", "Weiterleitungen der Kamera (z. B. http &rarr; https) werden befolgt"],
            ["0.3", "Verbindungen zur Kamera bleiben offen, Anmeldung wird gespeichert · Adresse <code>…/list</code> für den QC-Client"],
            ["0.2", "Ohne feste Auflösung · bei HTTP 400 automatisch ohne Zusatz-Parameter · ganze Kamera-URL als Adresse · Fehlertext der Kamera auf der Prüfseite"],
            ["0.1", "Erste Prüffassung"],
        ])),
    ]


def chapters_en():
    ins, outs = io_tables("en")
    return [
        ("Description", '<div class="descr">Fetches still images and live images from up to 6 network cameras and serves them through the HomeServer forwarding – '
         'same address and certificate as the HS. The browser does not log in to the camera; credentials are stored in the module only.<br><br>'
         '&bull; <b>Cameras:</b> Axis, any camera with a still image URL, or ONVIF (the module discovers the URLs itself).<br>'
         '&bull; <b>Camera login:</b> digest or basic, for ONVIF also WS-Security. http or https; self-signed certificates are accepted.<br>'
         '&bull; <b>Live image:</b> the camera\'s MJPEG stream is passed through. If the camera offers none, the module builds the stream from still images.<br>'
         '&bull; <b>Test page</b> at <code>https://&lt;HS&gt;/kamera/</code>.</div>'
         + box("warn", "Attention", "I2 must be set in the Experte (8095). With 0 the HomeServer does not forward (503 Service Unavailable).")),
        ("Inputs", ins),
        ("Outputs", outs),
        ("Miscellaneous", info([("Recalculation at start:", "Yes"), ("Module is remanent:", "No"), ("Internal designation:", ID),
                                ("Version:", VER + " (test release)"), ("Context:", M["context"]), ("Category:", "Visualisation"),
                                ("Author:", "Roman Rausch / Elektro Rausch")])),
        ("Camera address", table(["Entry", "Type", "Behaviour"], [
            ["<code>&lt;camera&gt;</code><br><code>https://&lt;camera&gt;</code>", "Axis",
             "Still image <code>/axis-cgi/jpg/image.cgi</code>, live image <code>/axis-cgi/mjpg/video.cgi</code>. Needs a regular Axis account."],
            ["<code>https://&lt;camera&gt;/path/image.cgi?…</code>", "Still image URL", "Exactly this URL is fetched as still image. Live image built from still images."],
            ["<code>onvif://&lt;camera&gt;</code>", "ONVIF",
             "Profiles and snapshot URL are discovered via ONVIF (https first, then http). Resolution: <code>onvif://&lt;camera&gt;?resolution=1280x720</code> (default 1280x720). Live image built from still images."],
        ])),
        ("URLs", table(["URL", "Content"], [
            ["<code>https://&lt;HS&gt;/kamera/</code>", "Test page"],
            ["<code>…/kamera/&lt;name&gt;.jpg?k=&lt;key&gt;</code>", "Still image"],
            ["<code>…/kamera/&lt;name&gt;.mjpg?k=&lt;key&gt;</code>", "Live image as MJPEG stream (from still images: default 8 fps, <code>&amp;fps=</code> 1–15)"],
            ["<code>…/kamera/list?k=&lt;key&gt;</code>", "Camera names"],
            ["<code>…/kamera/test?k=&lt;key&gt;</code>", "Check of all cameras as JSON"],
        ])),
    ]


def ent(s):
    return "".join(c if ord(c) < 128 else "&#%d;" % ord(c) for c in s)


def page(lang, title, chapters):
    t = L[lang]
    toc = "".join('<div class="t-line"><div class="t-chapter"><a href="#auto_index_anchor_%d_">%d.</a></div>'
                  '<div class="t-text"><a href="#auto_index_anchor_%d_">%s</a></div></div>' % (n, n, n, c[0]) for n, c in enumerate(chapters, 1))
    body = "".join('<h2 class="t-line"><a id="auto_index_anchor_%d_"></a><span class="t-chapter">%d.</span><span class="t-text">%s</span></h2>\n%s\n'
                   % (n, n, c[0], c[1]) for n, c in enumerate(chapters, 1))
    return ent('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN">\n<html><head><link rel="stylesheet" href="style.css"><title>%s - %s</title>'
               '<style>%s</style>\n<meta http-equiv="Content-Type" content="text/html;charset=UTF-8"></head><body>\n'
               '<div class="top-title">%s</div>\n<div class="nav"><a href="javascript:history.back()">%s</a> / <a href="javascript:history.forward()">%s</a> | '
               '<a href="hlpsearch.html">%s</a> | <a href="index.html">%s</a> / <a href="logic.html">%s</a> / %s</div>\n'
               '<div class="index"><div class="index-title"><a id="doc_index_1_"></a>%s</div>%s</div>\n<div class="content">\n%s</div></body></html>\n'
               % (t["logic"], title, STYLE, title, t["back"], t["fwd"], t["search"], t["help"], t["logic"], title, t["toc"], toc, body))


if __name__ == "__main__":
    for lang, title, ch in (("DE", ID + " Kamera-Proxy", chapters_de()), ("EN", ID + " Camera proxy", chapters_en())):
        p = os.path.join(SRC, "%s-log%s.html" % (lang, ID))
        io.open(p, "w", encoding="ascii", newline="\n").write(page(lang.lower(), title, ch))
        print("OK", p)
