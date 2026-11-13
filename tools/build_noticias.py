"""Titulares recientes sobre autopistas, peajes, TAG, bencinas y tránsito en Chile → noticias.json.

Lee los RSS públicos de Google Noticias (edición Chile) y guarda solo el titular, el medio, la hora y el
enlace a la nota original (no se copia el contenido). La app los muestra en la barra EN VIVO.
Uso: python3 tools/build_noticias.py salida.json
"""
import datetime, email.utils, html, json, re, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

UA = "tagme-datos/1.0 (+https://github.com/2010CR7/tagme-datos)"
QUERIES = [
    '(autopista OR autopistas OR peaje OR peajes OR "free flow" OR pórtico) Chile when:2d',
    '(TAG autopistas OR "pago tardío" OR concesionaria) Chile when:3d',
    '(precio bencina OR precio combustibles OR ENAP OR MEPCO) Chile when:4d',
    '(accidente OR desvío OR cierre OR congestión) (autopista OR "Ruta 5" OR "Ruta 68" OR Costanera OR Vespucio) when:1d',
    '("permiso de circulación" OR "revisión técnica" OR SOAP OR "licencia de conducir") Chile when:4d',
]
KEYWORDS = ("autopista", "peaje", "tag", "pórtico", "portico", "free flow", "bencina", "combustible", "diésel", "diesel",
            "parafina", "enap", "mepco", "tránsito", "transito", "ruta 5", "ruta 68", "ruta 78", "costanera", "vespucio",
            "concesion", "permiso de circulación", "revisión técnica", "soap", "licencia de conducir", "uoct", "carretera",
            "taco", "congestión", "accidente", "desvío", "cierre", "conductores", "automovilistas", "vehículos", "pago tardío")
PRICE = ("bencina", "combustible", "diésel", "diesel", "parafina", "enap", "mepco", "tarifa", "precio", "alza", "baja", "reajuste")
ALERT = ("accidente", "desvío", "cierre", "cortes", "corte ", "congestión", "taco", "volcamiento", "colisión", "suspend", "emergencia")

def fetch(q):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "es-419", "gl": "CL", "ceid": "CL:es-419"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return ET.fromstring(r.read())

def items(root, now):
    for it in root.iter("item"):
        title = html.unescape((it.findtext("title") or "").strip())
        link = (it.findtext("link") or "").strip()
        src = (it.findtext("source") or "").strip()
        when = it.findtext("pubDate")
        try: dt = email.utils.parsedate_to_datetime(when)
        except (TypeError, ValueError): continue
        if not title or not link.startswith("https://") or now - dt > datetime.timedelta(days=4): continue
        if src and title.endswith(" - " + src): title = title[: -len(src) - 3]
        yield title.strip(), src, dt, link

def kind(t):
    l = t.lower()
    if any(k in l for k in ALERT): return "aviso"
    if any(k in l for k in PRICE): return "precio"
    return "noticia"

def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    seen, out = set(), []
    for q in QUERIES:
        try: root = fetch(q)
        except Exception as e:
            print("falló una búsqueda:", type(e).__name__); continue
        for title, src, dt, link in items(root, now):
            low = title.lower()
            if not any(k in low for k in KEYWORDS): continue
            key = re.sub(r"\W+", "", low)[:60]
            if key in seen: continue
            seen.add(key)
            out.append({"kind": kind(title), "text": title[:160], "source": src[:40],
                        "time": dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "url": link})
    out.sort(key=lambda x: x["time"], reverse=True)
    out = out[:15]
    if not out: sys.exit("Sin titulares: no se publica")
    json.dump({"updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "Google Noticias (titulares y enlaces a cada medio)",
               "items": out}, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
    print(len(out), "titulares")

if __name__ == "__main__":
    main()
