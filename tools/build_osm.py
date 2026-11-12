#!/usr/bin/env python3
"""
Ubica los pórticos de tarifas/2026.json en el mapa y arma la red de autopistas de la RM
para calcular rutas en el teléfono, sin servicios pagados.

Entrada (rama `osm`, la genera el flujo .github/workflows/osm-porticos.yml desde Overpass):
  osm/rm_gantries.json  pórticos (highway=toll_gantry) y plazas (barrier=toll_booth)
  osm/rm_roads.json     autopistas, troncales y sus enlaces

Salida:
  osm/porticos_rm.json  coordenadas y rumbo de cada pórtico con tarifa, más los pendientes
  tarifas/rutas_rm.json red vial simplificada para calcular rutas

Datos © colaboradores de OpenStreetMap, licencia ODbL (https://www.openstreetmap.org/copyright).
Uso: python3 tools/build_osm.py <rm_gantries.json> <rm_roads.json>
"""
import json, math, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

WAY_TO_CONCESSION = {
    "Autopista Central": "autopista-central", "General Velásquez": "autopista-central",
    "Autopista Vespucio Sur": "vespucio-sur", "Autopista Vespucio Norte": "vespucio-norte",
    "Túnel San Cristóbal": "tunel-san-cristobal", "Autopista Nororiente": "nororiente",
    "Autopista Vespucio Oriente": "avo", "Autopista Aeropuerto": "amb", "Ruta 78": "ruta-78",
    "Autopista Costanera Norte": "costanera-norte", "Avenida Presidente Kennedy": "costanera-norte",
    "Ruta 68": "ruta-68",
}
PENDING_NAMES = {"costanera-norte": "Costanera Norte", "ruta-68": "Ruta 68", "avo": "Vespucio Oriente"}
SPEED = {"motorway": 80, "motorway_link": 45, "trunk": 50, "trunk_link": 35}
GATE_TOLERANCE_M = 60  # distancia máxima de un pórtico a su calzada


def xy(lat, lon, lat0):
    return lon * 111320.0 * math.cos(math.radians(lat0)), lat * 110540.0


def bearing(a, b):
    la1, la2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    y = math.sin(dl) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def dist_m(a, b):
    ax, ay = xy(a[0], a[1], a[0]); bx, by = xy(b[0], b[1], a[0])
    return math.hypot(ax - bx, ay - by)


def seg_dist(p, a, b):
    px, py = xy(p[0], p[1], p[0]); ax, ay = xy(a[0], a[1], p[0]); bx, by = xy(b[0], b[1], p[0])
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)


def norm(code):
    c = re.sub(r"[^A-Z0-9.\-]", "", code.upper())
    c = re.sub(r"(?<=[A-Z])-(?=\d)", "", c)
    return re.sub(r"(?<=[A-Z])0+(?=\d)", "", c)


def oneway(tags):
    o = tags.get("oneway")
    if o in ("yes", "1", "true"):
        return 1
    if o == "-1":
        return -1
    if o == "no":
        return 0
    if tags.get("junction") == "roundabout" or tags.get("highway") in ("motorway", "motorway_link"):
        return 1
    return 0


def main(gantries_path, roads_path):
    roads = json.load(open(roads_path))["elements"]
    coords = {e["id"]: (e["lat"], e["lon"]) for e in roads if e["type"] == "node"}
    ways = [e for e in roads if e["type"] == "way" and all(n in coords for n in e["nodes"])]
    gnodes = [e for e in json.load(open(gantries_path))["elements"] if e["type"] == "node"]

    # ---------- Pórticos: autopista más cercana y rumbo de circulación
    on_way = defaultdict(list)  # nodo -> [(way, índice)]
    for w in ways:
        for i, n in enumerate(w["nodes"]):
            on_way[n].append((w, i))
    grid = defaultdict(list)  # celdas de ~1 km para buscar segmentos cercanos
    for w in ways:
        for a, b in zip(w["nodes"], w["nodes"][1:]):
            grid[(round(coords[a][0], 2), round(coords[a][1], 2))].append((w, a, b))

    def nearest_segment(p):
        best = (1e9, None, None, None)
        for dy in (-0.01, 0, 0.01):
            for dx in (-0.01, 0, 0.01):
                for w, a, b in grid.get((round(p[0] + dy, 2), round(p[1] + dx, 2)), []):
                    d = seg_dist(p, coords[a], coords[b])
                    if d < best[0]:
                        best = (d, w, a, b)
        return best

    def travel_bearings(g):
        p = (g["lat"], g["lon"])
        found = on_way.get(g["id"])
        if found:
            w, i = found[0]
            n = w["nodes"]
            a, b = coords[n[max(i - 1, 0)]], coords[n[min(i + 1, len(n) - 1)]]
            way, dist = w, 0
        else:
            dist, way, a1, b1 = nearest_segment(p)
            if way is None or dist > GATE_TOLERANCE_M:
                return None, None, []
            a, b = coords[a1], coords[b1]
        br = bearing(a, b)
        ow = oneway(way["tags"])
        if ow == -1:
            return way, dist, [(br + 180) % 360]
        if ow == 0:
            return way, dist, [br, (br + 180) % 360]
        return way, dist, [br]

    pack = json.load(open(ROOT / "tarifas" / "2026.json"))
    ours = {c["id"]: {norm(g["code"]): g["code"] for g in c["gantries"]} for c in pack["concessions"]}
    by_name = {c["id"]: {g["name"].lower(): g["code"] for g in c["gantries"]} for c in pack["concessions"]}
    placed = defaultdict(lambda: defaultdict(list))
    pending = []
    for g in gnodes:
        tags = g.get("tags", {})
        way, dist, brs = travel_bearings(g)
        if way is None:
            continue
        cid = WAY_TO_CONCESSION.get(way["tags"].get("name"))
        ref = tags.get("ref", "")
        if cid is None and re.fullmatch(r"P6\d", ref):
            cid = "nororiente"  # pórticos laterales en los enlaces de Nororiente
        if cid is None:
            continue
        name = tags.get("name", "")
        if not ref:
            m = re.match(r"\s*(P[A-Z]?\s?\d+(?:\.\d+)?)", name)
            ref = m.group(1) if m else ""
        code = None
        if cid == "tunel-san-cristobal":
            code = {"P101": "TSC-EK", "P102": "TSC-KE"}.get(norm(ref).replace("PC", "P"))
        elif cid in ("ruta-78", "amb"):
            label = name.lower().replace("peaje acceso vial amb", "acceso al aeropuerto")
            code = by_name[cid].get(label) or (next(iter(ours[cid].values())) if cid == "amb" else None)
        elif cid in ours and cid != "avo":
            code = ours[cid].get(norm(ref)) or ours[cid].get(norm(ref).removeprefix("P"))
        pos = [[round(g["lat"], 6), round(g["lon"], 6), round(b)] for b in brs]
        if code:
            placed[cid][code] += pos
        elif cid in PENDING_NAMES:
            for p in pos:
                pending.append({"concession": cid, "concessionName": PENDING_NAMES[cid], "code": ref or "?",
                                "name": re.sub(r"^\s*P[A-Z]?\s?[\d.]+\s*-?\s*", "", name) or (ref or "Pórtico"),
                                "lat": p[0], "lon": p[1], "bearing": p[2]})
    total = sum(len(v) for v in ours.values())
    done = sum(len(v) for k, v in placed.items())
    for cid in ours:
        missing = sorted(set(ours[cid].values()) - set(placed[cid]))
        print(f"{cid}: {len(placed[cid])}/{len(ours[cid])}" + (f"  faltan {missing[:12]}" if missing and cid != "avo" else ""))
    print(f"ubicados {done}/{total}; pendientes en el mapa {len(pending)}")
    (ROOT / "osm").mkdir(exist_ok=True)
    (ROOT / "osm" / "porticos_rm.json").write_text(json.dumps(
        {"license": "© colaboradores de OpenStreetMap (ODbL)", "placed": placed, "pending": pending},
        ensure_ascii=False, indent=1))

    # ---------- Red vial: nodos clave + geometría simplificada
    use = defaultdict(int)
    for w in ways:
        for n in w["nodes"]:
            use[n] += 1
        use[w["nodes"][0]] += 1; use[w["nodes"][-1]] += 1
    keep = {n for n, k in use.items() if k > 1} | {g["id"] for g in gnodes}

    def simplify(pts, tol=6.0):
        if len(pts) < 3:
            return pts
        a, b = coords[pts[0]], coords[pts[-1]]
        dmax, idx = 0, 0
        for i in range(1, len(pts) - 1):
            d = seg_dist(coords[pts[i]], a, b)
            if d > dmax:
                dmax, idx = d, i
        if dmax <= tol:
            return [pts[0], pts[-1]]
        return simplify(pts[: idx + 1], tol)[:-1] + simplify(pts[idx:], tol)

    index, out_nodes, edges = {}, [], []

    def nid(n):
        if n not in index:
            index[n] = len(out_nodes)
            out_nodes.append([round(coords[n][0] * 1e5), round(coords[n][1] * 1e5)])
        return index[n]

    for w in ways:
        t = w["tags"]
        hw = t.get("highway")
        speed = SPEED.get(hw, 40)
        ms = re.match(r"\d+", t.get("maxspeed", ""))
        if ms:
            speed = min(speed, int(ms.group()) * 0.9) if hw != "motorway" else int(ms.group()) * 0.85
        ow = oneway(t)
        nodes = w["nodes"] if ow != -1 else w["nodes"][::-1]
        pieces, cur = [], [nodes[0]]
        for n in nodes[1:]:
            cur.append(n)
            if n in keep:
                pieces.append(cur); cur = [n]
        if len(cur) > 1:
            pieces.append(cur)
        for piece in pieces:
            pts = simplify(piece)
            for a, b in zip(pts, pts[1:]):
                secs = dist_m(coords[a], coords[b]) / (speed / 3.6)
                edges.append([nid(a), nid(b), max(1, round(secs * 10)), 0 if ow else 1])
    graph = {"license": "© colaboradores de OpenStreetMap (ODbL)", "scale": 100000,
             "nodes": out_nodes, "edges": edges,
             "note": "edges: [desde, hasta, décimas de segundo, 1 si es doble sentido]"}
    out = ROOT / "tarifas" / "rutas_rm.json"
    out.write_text(json.dumps(graph, separators=(",", ":")))
    print(f"{out}: {len(out_nodes)} nodos, {len(edges)} tramos, {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
