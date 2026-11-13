"""Tarifas 2026 de peajes interurbanos (fuera de las autopistas urbanas de Santiago).

Transcritas a mano de los PDF "Valores de Peajes y Pórticos 2026" que publica la Dirección General
de Concesiones del MOP en https://concesiones.mop.gob.cl/peajes-y-porticos/ (un PDF por concesión).
Montos en pesos para auto/camioneta y moto, tarifa normal y, si existe, punta.

Cada peaje del mapa (osm/peajes_cl.json) se asigna a una concesión:
  1. por nombre (alias de plaza, se buscan en todas las concesiones),
  2. por zona (caja lat/lon; las rutas transversales se revisan antes que los tramos de la Ruta 5).
Dentro de la concesión, la plaza se fija por nombre, por un punto conocido (anchor, < 2 km), por la
marca "troncal" de OSM o, si todas las plazas cobran lo mismo, directamente. Si no se puede saber
cuál plaza es, el peaje queda con su concesión y la app muestra todas sus tarifas.
"""

MOP = "https://concesiones.mop.gob.cl/uploads/sites/4/2026/"

def P(id, name, auto, moto, autoPunta=None, motoPunta=None, alias=(), anchor=None, kind="troncal", note=None):
    d = {"id": id, "name": name, "kind": kind, "auto": auto, "moto": moto}
    if autoPunta is not None: d["autoPunta"] = autoPunta
    if motoPunta is not None: d["motoPunta"] = motoPunta
    if note: d["note"] = note
    d["_alias"] = list(alias)
    d["_anchor"] = anchor
    return d

def L(auto, moto, alias=("lateral",), name="Laterales"):
    return P("lateral", name, auto, moto, alias=alias, kind="lateral")

# Orden: rutas transversales y accesos primero, después los tramos de la Ruta 5 (de norte a sur).
CONCESSIONS = [
    {"id": "acceso-iquique", "name": "Acceso Iquique", "route": "Rutas 1 y 16", "pdf": "01/ACCESO-IQUIQUE.pdf",
     "box": [(-20.7, -20.0, -70.4, -69.6)],
     "plazas": [P("r16", "Troncal Ruta 16", 2350, 700, anchor=(-20.216, -69.903)),
                P("r1", "Troncal Ruta 1", 1550, 450, anchor=(-20.496, -70.162))]},
    {"id": "rutas-del-loa", "name": "Rutas del Loa", "route": "Ruta 25 (Carmen Alto – Calama)", "pdf": "01/RUTAS-DEL-LOA.pdf",
     "box": [(-23.0, -22.2, -69.6, -68.7)],
     "plazas": [P("troncal", "Troncal", 3350, 1700, alias=("cerritos bayos",))]},
    {"id": "antofagasta", "name": "Autopista de la Región de Antofagasta", "route": "Rutas 1 y 5", "pdf": "01/ANTOFAGASTA.pdf",
     "box": [(-23.8, -23.0, -70.7, -69.9)],
     "plazas": [P("aeropuerto", "Acceso Aeropuerto", 1150, 550, alias=("aeropuerto",), kind="lateral"),
                P("r1", "Troncal Ruta 1", 1700, 800, anchor=(-23.311, -70.419)),
                P("r5", "Troncal Ruta 5", 2850, 1350, anchor=(-23.454, -70.125))]},
    {"id": "ruta-43", "name": "Ruta 43 La Serena – Ovalle", "route": "Ruta 43", "pdf": "01/RUTA-43.pdf",
     "box": [(-30.75, -30.0, -71.33, -70.9)],
     "plazas": [P("troncal", "Troncal", 3700, 1100)]},
    {"id": "nogales-puchuncavi", "name": "Camino Nogales – Puchuncaví", "route": "Ruta F-20", "pdf": "01/NOGALES-PUCHUNCAVI.pdf",
     "box": [(-32.85, -32.6, -71.5, -71.24)],
     "plazas": [P("nogales", "Troncal Nogales", 1950, 800, 3900, 1550, anchor=(-32.753, -71.253)),
                P("bypass", "Bypass Puchuncaví", 500, 200, 1000, 400, alias=("puchuncav",), anchor=(-32.714, -71.44))]},
    {"id": "ruta-60-ch", "name": "Ruta 60 CH", "route": "Ruta 60 CH (Los Andes – Viña del Mar)", "pdf": "01/RUTA-60-CH.pdf",
     "box": [(-33.0, -32.74, -71.36, -70.6)],
     "plazas": [P("quillota", "Troncal Quillota", 5350, 1600, 8050, 2400),
                P("quillota-lat", "Quillota Lateral", 3050, 900, 4600, 1400, kind="lateral"),
                P("lateral", "Laterales", 2050, 600, 3100, 900, alias=("lateral",), kind="lateral"),
                P("panquehue", "Panquehue", 2300, 700, 3450, 1050, alias=("panquehue",)),
                P("monasterio", "Monasterio", 1300, 400, 1900, 550, alias=("monasterio",))]},
    {"id": "los-libertadores", "name": "Autopista Los Libertadores", "route": "Ruta 57 (Santiago – Colina – Los Andes)", "pdf": "02/LOS-LIBERTADORES-FEBRERO.pdf",
     "box": [(-33.3, -32.9, -70.70, -70.55)],
     "plazas": [P("chacabuco", "Troncal Chacabuco", 3300, 1000, alias=("chacabuco",), anchor=(-33.001, -70.687)),
                P("canteras", "Las Canteras", 1200, 400, alias=("las canteras",)),
                P("chicureo", "Chicureo / San José", 1400, 400, alias=("chicureo", "san jose"))]},
    {"id": "ruta-68", "name": "Ruta 68 Santiago – Valparaíso – Viña del Mar", "route": "Ruta 68", "pdf": "01/RUTA-68.pdf",
     "box": [(-33.36, -33.03, -71.6, -70.85)],
     "plazas": [L(1100, 300, name="Laterales y Troncal Sur"),
                P("troncal", "Troncales Lo Prado y Zapata", 2700, 800, 4000, 1200)]},
    {"id": "red-vial-litoral", "name": "Red Vial Litoral Central", "route": "Rutas F-90, F-962-G y G-984", "pdf": "01/RED-VIAL.pdf",
     "box": [(-33.62, -33.35, -71.72, -71.4)],
     "plazas": [P("f90", "Troncal Ruta F-90", 1950, 600, 2900, 850, alias=("f-90",)),
                P("f965", "Troncal F-965-G", 1300, 400),
                P("sector1", "Troncal Sector 1 (F-94)", 4100, 1250),
                P("las-cruces", "Las Cruces (G-984)", 850, 250, alias=("las cruces",), kind="lateral")]},
    {"id": "variante-melipilla", "name": "Variante Melipilla", "route": "Ruta 78 (variante)", "pdf": "01/VARIANTE-MELIPILLA.pdf",
     "box": [],
     "plazas": [P("troncal", "Troncal", 3900, 1150, alias=("variante melipilla",))]},
    {"id": "ruta-78", "name": "Autopista del Sol (Ruta 78)", "route": "Ruta 78 Santiago – San Antonio", "pdf": "07/RUTA-78.pdf",
     "box": [(-33.75, -33.55, -71.45, -70.85)],
     "plazas": [P("puangue", "Puangue", 1161, 348, 1742, 697, alias=("puangue",)),
                P("pomaire", "Pomaire / Melipilla", 599, 180, 899, 359, alias=("pomaire",)),
                P("el-paico", "El Paico", 375, 113, 563, 225, alias=("el paico",))]},
    {"id": "ruta-66", "name": "Ruta 66 Camino de la Fruta", "route": "Ruta 66 (San Antonio – Pelequén)", "pdf": "01/RUTA-66-CAMINO-DE-LA-FRUTA.pdf",
     "box": [(-34.35, -33.7, -71.75, -71.0)],
     "plazas": [P("las-aranas", "Troncal Las Arañas", 2050, 600, alias=("las aranas",), note="Con TAG. Sin TAG: $2.550"),
                P("san-pedro", "Troncal San Pedro", 1100, 350, alias=("san pedro",), note="Con TAG. Sin TAG: $1.400")]},
    {"id": "itata", "name": "Ruta del Itata", "route": "Ruta 152 (Chillán – Concepción)", "pdf": "01/ITATA.pdf",
     "box": [(-36.85, -36.6, -72.95, -72.4)],
     "plazas": [P("agua-amarilla", "Agua Amarilla", 4400, 2200, alias=("agua amarilla",)),
                P("rafael", "Rafael", 1700, 800, alias=("rafael",)),
                P("nueva-aldea", "Nueva Aldea", 1000, 500, alias=("nueva aldea",), anchor=(-36.659, -72.457))]},
    {"id": "interportuaria", "name": "Ruta Interportuaria Talcahuano – Penco", "route": "Ruta Interportuaria", "pdf": "01/INTERPORTUARIA.pdf",
     "box": [(-36.86, -36.68, -73.2, -72.95)],
     "plazas": [P("troncal", "Plazas Talcahuano, Penco y Aeropuerto", 1750, 550, 2500, 750,
                  alias=("talcahuano", "penco", "ramal alessandri"), note="Penco viniendo del aeropuerto: $1.250 / $1.800")]},
    {"id": "conce-cabrero", "name": "Concepción – Cabrero", "route": "Ruta 146", "pdf": "01/CONCE-CABRERO.pdf",
     "box": [(-37.05, -36.85, -72.8, -72.5)],
     "plazas": [P("huinanco", "Troncal Huinanco", 3900, 1150, alias=("huinanco",)),
                P("puentes-negros", "Troncal Puentes Negros", 550, 150, alias=("puentes negros",))]},
    {"id": "ruta-160", "name": "Ruta 160", "route": "Ruta 160 (Coronel – Tres Pinos)", "pdf": "01/RUTA-160.pdf",
     "box": [(-37.75, -37.0, -73.6, -72.95)],
     "plazas": [P("chivilingo", "Chivilingo", 2750, 800, alias=("chivilingo",)),
                P("curanilahue", "Curanilahue", 0, 600, alias=("curanilahue",), note="Autos no pagan en esta plaza"),
                P("pilpilco", "Pilpilco", 600, 600, alias=("pilpilco",))]},
    {"id": "nahuelbuta", "name": "Ruta Nahuelbuta", "route": "Ruta 180 (Los Ángeles – Angol)", "pdf": "01/NAHUELBUTA.pdf",
     "box": [(-37.85, -37.45, -72.75, -72.45)],
     "plazas": [P("renaico", "Troncal Renaico", 2250, 700, alias=("renaico",)),
                P("coihue", "Troncal Coihue", 1300, 400, alias=("coihue",)),
                P("santa-fe", "Lateral Santa Fe", 0, 0, alias=("santa fe",), kind="lateral", note="Autos y motos no pagan")]},
    # Ruta 5 Norte
    {"id": "vallenar-caldera", "name": "Ruta 5 Vallenar – Caldera", "route": "Ruta 5 Norte", "pdf": "03/VALLENAR-CALDERA.pdf",
     "box": [(-28.6, -26.9, -71.2, -70.2)],
     "plazas": [P("puerto-viejo", "Troncal Puerto Viejo", 1750, 500, alias=("puerto viejo",)),
                P("totoral", "Troncal Totoral", 2900, 850, alias=("totoral",))]},
    {"id": "la-serena-vallenar", "name": "Ruta 5 La Serena – Vallenar", "route": "Ruta 5 Norte", "pdf": "01/LA-SERENA-VALLENAR.pdf",
     "box": [(-29.9, -28.6, -71.5, -70.4)],
     "plazas": [P("cachiyuyo", "Troncal Cachiyuyo", 3150, 950, alias=("cachiyuyo",)),
                P("punta-colorada", "Troncal Punta Colorada", 3150, 950, alias=("punta colorada",))]},
    {"id": "los-vilos-la-serena", "name": "Ruta 5 Los Vilos – La Serena", "route": "Ruta 5 Norte", "pdf": "01/LOS-VILOS-LA-SERENA.pdf",
     "box": [(-31.95, -29.9, -71.8, -71.0)],
     "plazas": [L(1100, 350, alias=("lateral", "tongoy", "guanaqueros", "ovalle", "combarbal"), name="Laterales (Combarbalá, Ovalle, Tongoy, Guanaqueros)"),
                P("troncal", "Troncales Norte y Sur", 4250, 1250, alias=("puerto oscuro",))]},
    {"id": "santiago-los-vilos", "name": "Ruta 5 Santiago – Los Vilos", "route": "Ruta 5 Norte", "pdf": "05/STGO-LOS-VILOS.pdf",
     "box": [(-32.75, -31.95, -71.7, -70.9), (-33.36, -33.15, -70.85, -70.705)],
     "plazas": [P("lampa", "Lampa", 900, 300, alias=("lampa",)),
                P("las-vegas", "Las Vegas", 2900, 900, alias=("las vegas", "llay llay")),
                P("pichidangui", "Pichidangui", 2900, 900, alias=("pichidangui",)),
                P("el-melon", "Túnel El Melón", 2900, 900, alias=("melon",)),
                P("lo-marcoleta", "Pórtico Lo Marcoleta", 181, 54, 362, 109, alias=("marcoleta",)),
                P("buenaventura", "Pórtico Buenaventura", 218, 65, 436, 131, alias=("buenaventura",)),
                P("la-montana", "Pórtico La Montaña", 397, 119, 794, 238, alias=("la montana",)),
                P("lo-pinto", "Pórtico Lo Pinto", 486, 146, 972, 292, alias=("lo pinto",))]},
    # Ruta 5 Sur
    {"id": "santiago-talca", "name": "Ruta 5 Santiago – Talca", "route": "Ruta 5 Sur", "pdf": "04/SANTIAGO-TALCA.pdf",
     "box": [(-35.45, -33.75, -71.8, -70.6)],
     "plazas": [P("troncal", "Troncal Ruta 5", 3800, 1100, alias=("angostura",)),
                L(900, 300),
                P("rio-maipo", "Troncal Río Maipo", 621, 186, alias=("rio maipo",)),
                P("gabriela", "Troncal Gabriela", 621, 186, alias=("gabriela",)),
                P("tocornal", "Troncal Tocornal", 207, 62, alias=("tocornal",))]},
    {"id": "talca-chillan", "name": "Ruta 5 Talca – Chillán", "route": "Ruta 5 Sur", "pdf": "01/TALCA-CHILLAN.pdf",
     "box": [(-36.58, -35.45, -72.15, -71.5)],
     "plazas": [P("troncal", "Troncal", 3300, 1000), L(800, 200)]},
    {"id": "chillan-collipulli", "name": "Ruta 5 Chillán – Collipulli", "route": "Ruta 5 Sur", "pdf": "01/CHILLAN-COLLIPULLI.pdf",
     "box": [(-37.95, -36.58, -72.7, -72.0)],
     "plazas": [P("troncal", "Troncales", 3400, 1000, alias=("santa clara", "las maicas")), L(800, 300)]},
    {"id": "collipulli-temuco", "name": "Ruta 5 Collipulli – Temuco", "route": "Ruta 5 Sur", "pdf": "01/COLLIPULLI-TEMUCO.pdf",
     "box": [(-38.74, -37.95, -72.8, -72.2)],
     "plazas": [P("troncal", "Troncal", 3600, 1000, alias=("pua",)), L(900, 300)]},
    {"id": "temuco-rio-bueno", "name": "Ruta 5 Temuco – Río Bueno", "route": "Ruta 5 Sur", "pdf": "01/TEMUCO-RIO-BUENO.pdf",
     "box": [(-40.35, -38.74, -73.2, -72.4)],
     "plazas": [P("troncal", "Troncal", 3600, 1100, alias=("quepe",)), L(900, 300, alias=("lateral", "union", "licanco"))]},
    {"id": "rio-bueno-puerto-montt", "name": "Ruta 5 Río Bueno – Puerto Montt", "route": "Ruta 5 Sur", "pdf": "01/RIO-BUENO-PTO-MONTT.pdf",
     "box": [(-41.5, -40.35, -73.3, -72.8)],
     "plazas": [P("troncal", "Troncal", 3600, 1100), L(900, 300),
                P("bypass", "Troncal By Pass Puerto Montt", 1100, 300, alias=("by pass", "bypass"))]},
    {"id": "puerto-montt-pargua", "name": "Ruta 5 Puerto Montt – Pargua", "route": "Ruta 5 Sur", "pdf": "01/PTO-MONTT-PARGUA.pdf",
     "box": [(-41.95, -41.5, -73.9, -72.9)],
     "plazas": [P("troncal", "Troncal", 3100, 900),
                P("trapen", "Trapén", 850, 250, alias=("trapen",), kind="lateral", anchor=(-41.517, -73.078)),
                P("maullin", "Maullín", 650, 200, alias=("maullin",), kind="lateral", anchor=(-41.589, -73.233)),
                P("calbuco", "Calbuco", 1450, 400, alias=("calbuco",), kind="lateral", anchor=(-41.723, -73.374))]},
]

def fold(s):
    s = (s or "").lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n"), ("ü", "u")):
        s = s.replace(a, b)
    return s

def _km(a, b):
    import math
    return math.hypot((a[0] - b[0]) * 110.54, (a[1] - b[1]) * 111.32 * math.cos(math.radians(a[0])))

def _in(box, lat, lon):
    return any(b[0] <= lat <= b[1] and b[2] <= lon <= b[3] for b in box)

def assign(t):
    """Devuelve (concesión, plaza o None) para un peaje {name, named, troncal, lat, lon}."""
    name = fold(t["name"]) if t.get("named") else ""
    pos = (t["lat"], t["lon"])
    conc = plaza = None
    # 1. Por nombre: alias específicos (no los genéricos "lateral"/"troncal"), cerca de la zona de la concesión.
    if name:
        for c in CONCESSIONS:
            for p in c["plazas"]:
                if any(a not in ("lateral", "troncal") and a in name for a in p["_alias"]):
                    near = not c["box"] or _in([(b[0] - 0.3, b[1] + 0.3, b[2] - 0.3, b[3] + 0.3) for b in c["box"]], *pos)
                    if near:
                        conc, plaza = c, p
                        break
            if conc: break
    # 2. Por zona.
    if conc is None:
        conc = next((c for c in CONCESSIONS if _in(c["box"], *pos)), None)
        if conc is None:
            return None, None
    if plaza is None:
        ps = conc["plazas"]
        anchored = [p for p in ps if p["_anchor"] and _km(p["_anchor"], pos) < 2]
        if anchored: plaza = anchored[0]
        elif name and "lateral" in name: plaza = next((p for p in ps if p["kind"] == "lateral"), None)
        # Según la vía donde está la caseta (red de OpenStreetMap): en un enlace es lateral, en la ruta es troncal.
        elif t.get("road") == "link" and sum(p["kind"] == "lateral" for p in ps) == 1:
            plaza = next(p for p in ps if p["kind"] == "lateral")
        elif t.get("road") == "link" and any(p["id"] == "lateral" for p in ps):
            plaza = next(p for p in ps if p["id"] == "lateral")
        elif t.get("road") == "main" and any(p["id"] == "troncal" for p in ps):
            plaza = next(p for p in ps if p["id"] == "troncal")
        elif (t.get("troncal") or "troncal" in name) and sum(p["kind"] == "troncal" for p in ps) == 1:
            plaza = next(p for p in ps if p["kind"] == "troncal")
        elif len({(p["auto"], p.get("autoPunta")) for p in ps}) == 1: plaza = ps[0]
    return conc, plaza

def public():
    out = []
    for c in CONCESSIONS:
        out.append({
            "id": c["id"], "name": c["name"], "route": c["route"],
            "source": MOP + c["pdf"],
            "plazas": [{k: v for k, v in p.items() if not k.startswith("_")} for p in c["plazas"]],
        })
    return out
