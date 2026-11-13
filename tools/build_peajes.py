"""Peajes y pórticos de todo Chile desde OpenStreetMap (osm/cl_tolls.json) → osm/peajes_cl.json.

Agrupa las casetas de una misma plaza (una por pista) en un solo punto y quita lo que ya está
en el mapa de Santiago (osm/porticos_rm.json). Uso: python3 tools/build_peajes.py osm/cl_tolls.json
Datos © colaboradores de OpenStreetMap (ODbL).
"""
import json, math, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

def meters(a, b):
    return math.hypot((a[0] - b[0]) * 110540, (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0])))

def region(lat, lon):
    # Aproximación por latitud (la mayoría de los peajes están en la Ruta 5 y rutas transversales).
    if lat > -19.2: return "Arica y Parinacota"
    if lat > -21.6: return "Tarapacá"
    if lat > -26.0: return "Antofagasta"
    if lat > -29.2: return "Atacama"
    if lat > -32.2: return "Coquimbo"
    if lat > -34.0:
        if lon < -71.05 or lat > -33.0: return "Valparaíso"
        return "Metropolitana"
    if lat > -34.95: return "O'Higgins"
    if lat > -36.2: return "Maule"
    if lat > -37.1: return "Ñuble"
    if lat > -38.45: return "Biobío"
    if lat > -39.6: return "La Araucanía"
    if lat > -40.6: return "Los Ríos"
    if lat > -44.0: return "Los Lagos"
    if lat > -49.0: return "Aysén"
    return "Magallanes"

def clean(name):
    if not name: return None
    n = name.strip()
    for p in ("Peaje Troncal ", "Peaje troncal ", "Plaza de Peaje ", "Plaza de peaje ", "Peaje "):
        if n.startswith(p): n = n[len(p):]
    return n or None

def main(src):
    els = json.load(open(src))["elements"]
    pts = []
    for e in els:
        t = e.get("tags", {})
        lat = e.get("lat") or e.get("center", {}).get("lat")
        lon = e.get("lon") or e.get("center", {}).get("lon")
        if lat is None: continue
        kind = "portico" if t.get("highway") == "toll_gantry" else "plaza"
        pts.append({"lat": lat, "lon": lon, "kind": kind, "name": clean(t.get("name")), "troncal": "troncal" in (t.get("name") or "").lower()})
    # Lo que ya tiene posición en el mapa de Santiago no se repite.
    known = []
    rm = ROOT / "osm" / "porticos_rm.json"
    if rm.exists():
        d = json.load(open(rm))
        for codes in d.get("placed", {}).values():
            for poss in codes.values():
                for p in poss:
                    known.append((p[0], p[1]))
        for g in d.get("pending", []):
            known.append((g["lat"], g["lon"]))
    pack = ROOT / "tarifas" / "2026.json"
    if pack.exists():
        for c in json.load(open(pack))["concessions"]:
            for g in c["gantries"]:
                for p in g.get("pos", []):
                    known.append((p[0], p[1]))
    clusters = []
    for p in pts:
        if any(meters((p["lat"], p["lon"]), k) < 600 for k in known): continue
        for c in clusters:
            if c["kind"] == p["kind"] and meters((p["lat"], p["lon"]), (c["lat"], c["lon"])) < 400:
                c["members"].append(p); break
        else:
            clusters.append({"lat": p["lat"], "lon": p["lon"], "kind": p["kind"], "members": [p]})
    out = []
    for i, c in enumerate(sorted(clusters, key=lambda c: -c["lat"])):
        lat = sum(m["lat"] for m in c["members"]) / len(c["members"])
        lon = sum(m["lon"] for m in c["members"]) / len(c["members"])
        name = next((m["name"] for m in c["members"] if m["name"]), None)
        reg = region(lat, lon)
        out.append({
            "id": f"cl-{i + 1:03d}",
            "name": name or ("Pórtico" if c["kind"] == "portico" else "Plaza de peaje"),
            "named": name is not None,
            "kind": c["kind"],
            "troncal": any(m["troncal"] for m in c["members"]),
            "region": reg,
            "lat": round(lat, 5), "lon": round(lon, 5),
        })
    dst = ROOT / "osm" / "peajes_cl.json"
    json.dump({"license": "© colaboradores de OpenStreetMap (ODbL)", "tolls": out}, open(dst, "w"), ensure_ascii=False, indent=0)
    by = {}
    for o in out: by[o["region"]] = by.get(o["region"], 0) + 1
    print(len(out), "puntos;", sum(o["named"] for o in out), "con nombre;", by)

if __name__ == "__main__":
    main(sys.argv[1])
