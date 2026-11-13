"""Precios de combustibles de todas las estaciones de servicio de Chile → bencinas.json.

Fuente: API oficial de la Comisión Nacional de Energía (https://api.cne.cl, datos de Bencina en Línea).
Uso en GitHub Actions (secretos CNE_EMAIL y CNE_PASSWORD):  python3 tools/build_bencinas.py salida.json
Para probar con una respuesta guardada:                  python3 tools/build_bencinas.py salida.json --raw estaciones.json
La clave nunca se imprime ni se guarda: solo se usa para pedir el token de la sesión.
"""
import json, os, sys, urllib.parse, urllib.request, datetime

BASE = "https://api.cne.cl"
UA = "tagme-datos/1.0 (+https://github.com/2010CR7/tagme-datos)"
# Código CNE → nombre. Las claves con "A" adelante son el precio en autoservicio.
FUELS = {"93": "Gasolina 93", "95": "Gasolina 95", "97": "Gasolina 97", "DI": "Diésel", "GLP": "GLP vehicular", "GNC": "GNC", "KE": "Kerosene"}

def http(url, data=None, token=None):
    headers = {"Accept": "application/json", "User-Agent": UA}
    if token: headers["Authorization"] = f"Bearer {token}"
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))

def download():
    email, password = os.environ.get("CNE_EMAIL"), os.environ.get("CNE_PASSWORD")
    if not email or not password:
        sys.exit("Faltan los secretos CNE_EMAIL / CNE_PASSWORD")
    login = http(BASE + "/api/login", {"email": email, "password": password})
    token = login.get("token") if isinstance(login, dict) else None
    if not token:
        sys.exit("La CNE no entregó token (revisa el correo y la clave guardados como secretos)")
    data = http(BASE + "/api/v4/estaciones", token=token)
    if isinstance(data, dict) and "data" in data: data = data["data"]
    if not isinstance(data, list):
        sys.exit("Respuesta inesperada de la CNE: " + str(data)[:200])
    return data

def num(v):
    try:
        f = float(str(v).replace(",", "."))
        return int(round(f)) if f > 0 else None
    except (TypeError, ValueError):
        return None

def compact(stations):
    out, dates = [], []
    for s in stations:
        u = s.get("ubicacion") or {}
        lat, lon = num_f(u.get("latitud")), num_f(u.get("longitud"))
        if lat is None or lon is None or not (-56 < lat < -17 and -110 < lon < -66): continue
        prices = {}
        for key, p in (s.get("precios") or {}).items():
            base = key[1:] if key.startswith("A") and key[1:] in FUELS else key
            if base not in FUELS or not isinstance(p, dict): continue
            v = num(p.get("precio"))
            if v is None or not (300 < v < 5000): continue
            prices[("a" if base != key else "") + base] = v
            if p.get("fecha_actualizacion"): dates.append(str(p["fecha_actualizacion"]))
        if not prices: continue
        d = s.get("distribuidor") or {}
        out.append({
            "id": str(s.get("codigo") or ""),
            "brand": str(d.get("marca") or d.get("nombre") or "Sin marca").strip().title()[:30],
            "address": str(u.get("direccion") or "").strip()[:80],
            "comuna": str(u.get("nombre_comuna") or u.get("comuna") or "").strip(),
            "region": str(u.get("nombre_region") or u.get("region") or "").strip(),
            "lat": round(lat, 5), "lon": round(lon, 5),
            "p": prices,
        })
    return out, max(dates) if dates else None

def num_f(v):
    try: return float(str(v).replace(",", "."))
    except (TypeError, ValueError): return None

def main():
    dst = sys.argv[1]
    if "--raw" in sys.argv:
        raw = json.load(open(sys.argv[sys.argv.index("--raw") + 1]))
        if isinstance(raw, dict) and "data" in raw: raw = raw["data"]
    else:
        raw = download()
    stations, latest = compact(raw)
    if len(stations) < 50 and "--raw" not in sys.argv:
        sys.exit(f"Muy pocas estaciones ({len(stations)}): no se publica")
    doc = {
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pricesAsOf": latest,
        "source": "Comisión Nacional de Energía (Bencina en Línea), api.cne.cl",
        "fuels": FUELS,
        "stations": stations,
    }
    json.dump(doc, open(dst, "w"), ensure_ascii=False, separators=(",", ":"))
    print(len(stations), "estaciones;", sum("93" in s["p"] or "a93" in s["p"] for s in stations), "con 93")

if __name__ == "__main__":
    main()
