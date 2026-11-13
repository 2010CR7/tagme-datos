"""Red vial de Chile para calcular rutas en el teléfono (© colaboradores de OpenStreetMap, ODbL).

Entrada: un archivo OPL con las vías motorway/trunk/primary (y sus enlaces) y las casetas de peaje,
filtrado con osmium desde el extracto de Chile de Geofabrik (ver .github/workflows/red-vial-chile.yml).

Salidas:
  tarifas/rutas_cl.bin       grafo compacto (ver formato abajo), se copia a la app
  osm/peajes_vias.json       para cada caseta de peaje: tipo de vía donde está (troncal o enlace) y ruta

Formato de rutas_cl.bin (big endian, como DataOutputStream de Java):
  "TMR1", int n, n × (int lat·1e5, int lon·1e5), int m, m × (int desde, int hasta, int décimas de segundo, byte 1 = doble sentido)
Uso: python3 tools/build_red_cl.py red.opl
"""
import json, math, pathlib, struct, sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEED = {"motorway": 100, "trunk": 90, "primary": 70, "secondary": 60,
         "motorway_link": 50, "trunk_link": 45, "primary_link": 40, "secondary_link": 35}
TOLERANCE_M = 25          # simplificación de la geometría (Douglas–Peucker)
MIN_COMPONENT = 40        # se descartan islas sueltas de menos nodos


def unescape(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == "%":
            j = s.index("%", i + 1)
            out.append(chr(int(s[i + 1:j], 16)))
            i = j + 1
        else:
            out.append(s[i]); i += 1
    return "".join(out)


def tags_of(field):
    t = {}
    if not field:
        return t
    for kv in field.split(","):
        if "=" in kv:
            k, v = kv.split("=", 1)
            t[unescape(k)] = unescape(v)
    return t


def read_opl(path):
    nodes, ways, booths = {}, [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split(" ")
            kind, oid = parts[0][0], int(parts[0][1:])
            fields = {p[0]: p[1:] for p in parts[1:] if p}
            if kind == "n":
                if "x" not in fields or not fields["x"]:
                    continue
                lat, lon = float(fields["y"]), float(fields["x"])
                nodes[oid] = (lat, lon)
                t = tags_of(fields.get("T"))
                if t.get("barrier") == "toll_booth" or t.get("highway") == "toll_gantry":
                    booths.append({"id": oid, "lat": lat, "lon": lon, "name": t.get("name")})
            elif kind == "w":
                t = tags_of(fields.get("T"))
                hw = t.get("highway")
                if hw not in SPEED:
                    continue
                refs = [int(x[1:]) for x in fields.get("N", "").split(",") if x]
                ways.append((oid, t, refs))
    return nodes, ways, booths


def meters(a, b):
    return math.hypot((a[0] - b[0]) * 110540, (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0])))


def seg_dist(p, a, b):
    k = 111320 * math.cos(math.radians(p[0]))
    px, py = p[1] * k, p[0] * 110540
    ax, ay = a[1] * k, a[0] * 110540
    bx, by = b[1] * k, b[0] * 110540
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def simplify(ids, coords):
    """Douglas–Peucker sobre una lista de ids; conserva los extremos."""
    if len(ids) <= 2:
        return ids
    keep = [False] * len(ids)
    keep[0] = keep[-1] = True
    stack = [(0, len(ids) - 1)]
    while stack:
        i, j = stack.pop()
        best, k = 0, -1
        for x in range(i + 1, j):
            d = seg_dist(coords[ids[x]], coords[ids[i]], coords[ids[j]])
            if d > best:
                best, k = d, x
        if best > TOLERANCE_M:
            keep[k] = True
            stack += [(i, k), (k, j)]
    return [n for n, kp in zip(ids, keep) if kp]


def speed(t):
    v = t.get("maxspeed", "")
    if v.isdigit() and 20 <= int(v) <= 130:
        return min(int(v), SPEED[t["highway"]] + 20)
    return SPEED[t["highway"]]


def direction(t):
    ow = t.get("oneway")
    if ow in ("yes", "true", "1"): return 1
    if ow == "-1": return -1
    if ow == "no": return 0
    if t.get("junction") == "roundabout" or t["highway"] in ("motorway", "motorway_link"): return 1
    return 0


def main(src):
    coords, ways, booths = read_opl(src)
    ways = [w for w in ways if all(r in coords for r in w[2]) and len(w[2]) >= 2]
    use = defaultdict(int)
    for _, _, refs in ways:
        for i, r in enumerate(refs):
            use[r] += 2 if i in (0, len(refs) - 1) else 1
    booth_ids = {b["id"] for b in booths}
    # Nodos que deben quedar: cruces, extremos y casetas.
    anchor = {r for r, c in use.items() if c >= 2} | booth_ids

    # Caseta → vía donde está.
    booth_way = {}
    for _, t, refs in ways:
        for r in refs:
            if r in booth_ids:
                prev = booth_way.get(r)
                cls = t["highway"]
                if prev is None or ("_link" in prev["highway"] and "_link" not in cls):
                    booth_way[r] = {"highway": cls, "ref": t.get("ref"), "road": t.get("name")}

    index, out_nodes = {}, []
    def idx(r):
        if r not in index:
            index[r] = len(out_nodes)
            out_nodes.append(coords[r])
        return index[r]

    edges = {}
    for _, t, refs in ways:
        d = direction(t)
        if d == -1:
            refs, d = list(reversed(refs)), 1
        v = speed(t) / 3.6
        # Cortar en nodos ancla y simplificar cada tramo.
        start = 0
        for i in range(1, len(refs)):
            if refs[i] in anchor or i == len(refs) - 1:
                piece = simplify(refs[start:i + 1], coords)
                for a, b in zip(piece, piece[1:]):
                    if a == b: continue
                    ds = max(1, round(meters(coords[a], coords[b]) / v * 10))
                    ia, ib = idx(a), idx(b)
                    key = (ia, ib)
                    rev = (ib, ia)
                    if d == 0 and rev in edges:
                        edges[rev] = (min(edges[rev][0], ds), 1)
                    elif key in edges:
                        edges[key] = (min(edges[key][0], ds), max(edges[key][1], 0 if d else 1))
                    else:
                        edges[key] = (ds, 0 if d else 1)
                start = i

    # Quitar islas pequeñas (componentes débiles).
    n = len(out_nodes)
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb
    size = defaultdict(int)
    for i in range(n): size[find(i)] += 1
    alive = [size[find(i)] >= MIN_COMPONENT for i in range(n)]
    remap, nodes2 = {}, []
    for i in range(n):
        if alive[i]:
            remap[i] = len(nodes2); nodes2.append(out_nodes[i])
    edges2 = [(remap[a], remap[b], t, bi) for (a, b), (t, bi) in edges.items() if alive[a] and alive[b]]

    out = ROOT / "tarifas" / "rutas_cl.bin"
    with open(out, "wb") as f:
        f.write(b"TMR1")
        f.write(struct.pack(">i", len(nodes2)))
        for lat, lon in nodes2:
            f.write(struct.pack(">ii", round(lat * 1e5), round(lon * 1e5)))
        f.write(struct.pack(">i", len(edges2)))
        for a, b, t, bi in edges2:
            f.write(struct.pack(">iiib", a, b, t, bi))
    km = sum(meters(nodes2[a], nodes2[b]) for a, b, _, _ in edges2) / 1000
    print(f"rutas_cl.bin: {len(nodes2)} nodos, {len(edges2)} tramos, {km:,.0f} km, {out.stat().st_size / 1e6:.1f} MB")

    vias = [{"lat": round(b["lat"], 6), "lon": round(b["lon"], 6), "name": b["name"], **booth_way.get(b["id"], {"highway": None})} for b in booths]
    (ROOT / "osm" / "peajes_vias.json").write_text(json.dumps({"license": "© colaboradores de OpenStreetMap (ODbL)", "booths": vias}, ensure_ascii=False, indent=0))
    on = sum(1 for v in vias if v["highway"])
    print(f"peajes_vias.json: {len(vias)} casetas, {on} sobre la red cargada")


if __name__ == "__main__":
    main(sys.argv[1])
