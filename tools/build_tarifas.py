#!/usr/bin/env python3
"""
Genera tarifas/2026.json a partir de los cuadros tarifarios oficiales 2026 publicados por cada concesionaria.
Cada valor se transcribió del PDF indicado en "sources". Si una concesionaria publica un cuadro nuevo,
se actualizan los datos de este archivo y se vuelve a ejecutar:  python3 tools/build_tarifas.py
"""
import json, re, pathlib
from decimal import Decimal, ROUND_HALF_UP

ROOT = pathlib.Path(__file__).resolve().parent.parent
FETCHED = "2026-11-10"

def d(x):  # "1.170,18" -> Decimal
    return Decimal(str(x).replace("$", "").replace(".", "").replace(",", ".").strip())

def money(x):
    return float(Decimal(x).quantize(Decimal("0.01"), ROUND_HALF_UP))

def bands(spec):
    """'LABORAL TS 07:00-07:30; SABADO TBP 10:00-13:00 / 17:00-19:00' -> lista de bloques."""
    out = []
    for part in filter(None, (p.strip() for p in spec.split(";"))):
        day, kind, ranges = part.split(" ", 2)
        for r in ranges.split("/"):
            a, b = [x.strip() for x in r.split("-")]
            out.append({"day": day, "from": a.zfill(5), "to": b.zfill(5), "type": kind})
    return out

SOURCES = [
    ("src-ac-2026", "Autopista Central", "https://www.autopistacentral.cl/wp-content/uploads/2026/03/ACSA_afiche_25x32-cm_ajuste_24-1.pdf", "Tarifas 2026 (desde 17-03-2026)"),
    ("src-vs-2026", "Vespucio Sur", "https://www.vespuciosur.cl/wp-content/uploads/2025/12/VS_tarifas_2026.pdf", "Tarifas 2026"),
    ("src-avn-2026", "Vespucio Norte", "https://www.vespucionorte.cl/Content/AVN/pdfs/AVN_Tarifas2026-2.pdf", "Tarifas 2026 (desde 01-02-2026)"),
    ("src-tsc-2026", "Túnel San Cristóbal", "https://www.tunelsancristobal.cl/Content/TSC/pdfs/TSC_Tarifas2026-2.pdf", "Tarifas 2026 (desde 01-02-2026)"),
    ("src-an-2026", "Autopista Nororiente", "https://www.autopistanororiente.cl/wp-content/uploads/2025/12/AN_tarifas_2026.pdf", "Tarifas 2026"),
    ("src-avo-2026", "Vespucio Oriente (AVO)", "https://www.avo.cl/descargas/tarifas_avo1_2026.pdf", "Tarifas 2026"),
    ("src-amb-2026", "Acceso Vial AMB", "https://www.accesovialamb.cl/wp-content/uploads/2026/06/AMB_tarifas_2026_ok.pdf", "Tarifas 2026"),
    ("src-r78-2026", "Autopista Ruta 78", "https://www.autopistaruta78.cl/storage/app/media/tarifas-2026-v2.pdf", "Tarifas 2026"),
    ("src-cn-2026", "Costanera Norte", "https://web.costaneranorte.cl/wp-content/uploads/2026/06/CN_Tarifas_2026_2doSemestre.pdf", "Tarifas 2026, 2° semestre (desde 01-07-2026)"),
    ("src-feriados", "Biblioteca del Congreso Nacional", "https://www.bcn.cl/leyfacil/recurso/feriados", "Feriados legales de Chile"),
]

# Feriados legales (leyes vigentes; los trasladables ya están en su lunes).
HOLIDAYS = [
    ("2026-01-01", "Año Nuevo"), ("2026-04-03", "Viernes Santo"), ("2026-04-04", "Sábado Santo"),
    ("2026-05-01", "Día del Trabajo"), ("2026-05-21", "Glorias Navales"), ("2026-06-21", "Día de los Pueblos Indígenas"),
    ("2026-06-29", "San Pedro y San Pablo"), ("2026-07-16", "Virgen del Carmen"), ("2026-08-15", "Asunción de la Virgen"),
    ("2026-09-18", "Independencia Nacional"), ("2026-09-19", "Glorias del Ejército"), ("2026-10-12", "Encuentro de Dos Mundos"),
    ("2026-10-31", "Iglesias Evangélicas y Protestantes"), ("2026-11-01", "Todos los Santos"),
    ("2026-12-08", "Inmaculada Concepción"), ("2026-12-25", "Navidad"),
    ("2027-01-01", "Año Nuevo"), ("2027-03-26", "Viernes Santo"), ("2027-03-27", "Sábado Santo"),
    ("2027-05-01", "Día del Trabajo"), ("2027-05-21", "Glorias Navales"), ("2027-06-21", "Día de los Pueblos Indígenas"),
    ("2027-06-28", "San Pedro y San Pablo"), ("2027-07-16", "Virgen del Carmen"), ("2027-08-15", "Asunción de la Virgen"),
    ("2027-09-18", "Independencia Nacional"), ("2027-09-19", "Glorias del Ejército"), ("2027-10-11", "Encuentro de Dos Mundos"),
    ("2027-10-31", "Iglesias Evangélicas y Protestantes"), ("2027-11-01", "Todos los Santos"),
    ("2027-12-08", "Inmaculada Concepción"), ("2027-12-25", "Navidad"),
]

def gantry(code, name, direction, rates, spec="", km=None):
    g = {"code": code, "name": name, "dir": direction, "rates": rates, "bands": bands(spec)}
    if km is not None:
        g["km"] = float(km)
    return g

def rates3(c1, c2, c3, moto=None):
    """Cada argumento: lista [TBFP, TBP, TS] (puede faltar TBP/TS). Motos = categoría 1 salvo que se indique."""
    names = ["TBFP", "TBP", "TS"]
    def one(v):
        return {names[i]: money(d(x)) for i, x in enumerate(v) if x is not None}
    out = {"AUTO": one(c1), "BUS_CAMION": one(c2), "CAMION_REMOLQUE": one(c3)}
    out["MOTO"] = one(moto) if moto else out["AUTO"]
    return out

# ---------------------------------------------------------------- Autopista Central
# (código, tramo, km, cat 1 y 4 [TBFP,TBP,TS], cat 2, cat 3, bloques)
AC = [
    ("Sur → Norte", [
        ("PA2", "Los Guindos - La Capilla", "7,68", ["868,37"], ["1.736,74"], ["2.605,11"], ""),
        ("PA3", "La Capilla - Colón", "5,63", ["585,09", "1.170,18", "1.755,28"], ["1.170,18", "2.340,37", "3.510,56"], ["1.755,27", "3.510,56", "5.265,84"],
         "LABORAL TS 07:00-07:30; LABORAL TBP 06:30-07:00 / 07:30-08:00; DOMINGO TBP 18:00-20:00"),
        ("PA5", "Colón - Las Acacias", "3,22", ["334,63", "669,27", "1.003,90"], ["669,27", "1.338,54", "2.007,81"], ["1.003,90", "2.007,82", "3.011,72"],
         "LABORAL TS 07:00-08:00; LABORAL TBP 06:30-07:00 / 08:00-09:30; DOMINGO TBP 18:00-20:00"),
        ("PA7", "Las Acacias - Américo Vespucio", "4,35", ["452,06", "904,14"], ["904,13", "1.808,28"], ["1.356,20", "2.712,42"],
         "LABORAL TBP 07:30-09:30; DOMINGO TBP 18:30-20:30"),
        ("PA30", "Américo Vespucio - Departamental", "3,78", ["392,83", "785,66"], ["785,66", "1.571,33"], ["1.178,49", "2.357,00"],
         "LABORAL TBP 07:30-09:30; SABADO TBP 07:30-09:30; DOMINGO TBP 18:30-20:30"),
        ("PA10", "Departamental - Carlos Valdovinos", "2,75", ["285,79", "571,58"], ["571,58", "1.143,16"], ["857,37", "1.714,75"],
         "LABORAL TBP 07:30-09:30; SABADO TBP 07:30-09:30; DOMINGO TBP 18:30-20:30"),
        ("PA31", "Carlos Valdovinos - Alameda", "3,55", ["368,93", "737,86", "1.106,79"], ["737,86", "1.475,72", "2.213,58"], ["1.106,79", "2.213,59", "3.320,38"],
         "LABORAL TS 08:30-09:00; LABORAL TBP 06:30-08:30 / 09:00-14:00 / 17:00-19:00; SABADO TBP 10:00-13:00; DOMINGO TBP 18:30-20:30"),
        ("PA13", "Alameda - Río Mapocho", "1,75", ["181,86", "363,73", "545,60"], ["363,73", "727,47", "1.091,20"], ["545,60", "1.091,20", "1.636,80"],
         "LABORAL TS 08:30-09:00; LABORAL TBP 06:30-08:30 / 09:00-14:00 / 17:00-19:00; SABADO TBP 10:00-13:00; DOMINGO TBP 18:30-20:30"),
        ("PA16", "Río Mapocho - 14 de la Fama", "4,09", ["425,04", "850,10"], ["850,09", "1.700,20"], ["1.275,14", "2.550,30"], "LABORAL TBP 07:30-09:30"),
        ("PA17", "14 de la Fama - A. Vespucio Norte", "4,45", ["462,46", "924,92"], ["924,92", "1.849,85"], ["1.387,38", "2.774,78"],
         "LABORAL TBP 07:00-10:00 / 10:30-15:00 / 16:30-19:30"),
    ]),
    ("Norte → Sur", [
        ("PA18", "A. Vespucio Norte - 14 de la Fama", "4,45", ["462,46", "924,92", "1.387,38"], ["924,92", "1.849,85", "2.774,77"], ["1.387,38", "2.774,78", "4.162,16"],
         "LABORAL TS 17:30-18:00; LABORAL TBP 07:00-08:30 / 09:30-10:00"),
        ("PA15", "14 de la Fama - Río Mapocho", "4,09", ["425,04", "850,10"], ["850,09", "1.700,20"], ["1.275,14", "2.550,30"],
         "LABORAL TBP 07:30-08:00 / 08:30-09:00 / 18:30-20:30"),
        ("PA14", "Río Mapocho - Alameda", "1,75", ["181,86", "363,73", "545,60"], ["363,73", "727,47", "1.091,20"], ["545,60", "1.091,20", "1.636,80"],
         "LABORAL TS 10:00-10:30 / 11:00-11:30 / 15:30-16:00 / 19:30-20:00; LABORAL TBP 07:00-08:30 / 09:00-09:30 / 15:00-15:30 / 16:00-16:30 / 18:30-19:30 / 20:00-20:30; SABADO TBP 11:00-15:00"),
        ("PA12", "Alameda - Carlos Valdovinos", "3,55", ["368,93", "737,86", "1.106,79"], ["737,86", "1.475,72", "2.213,58"], ["1.106,79", "2.213,59", "3.320,38"],
         "LABORAL TS 10:00-10:30 / 11:00-11:30 / 15:30-16:00 / 19:30-20:00; LABORAL TBP 07:00-08:30 / 09:00-09:30 / 15:00-15:30 / 16:00-16:30 / 18:30-19:30 / 20:00-20:30; SABADO TBP 11:00-15:00"),
        ("PA11", "Carlos Valdovinos - Departamental", "2,75", ["285,79", "571,58"], ["571,58", "1.143,16"], ["857,37", "1.714,75"], "LABORAL TBP 18:00-20:30; SABADO TBP 11:00-15:00"),
        ("PA9", "Departamental - Américo Vespucio", "3,78", ["392,83", "785,66"], ["785,66", "1.571,33"], ["1.178,49", "2.357,00"], "LABORAL TBP 18:00-20:30; SABADO TBP 11:00-15:00"),
        ("PA8", "Américo Vespucio - Las Acacias", "4,35", ["452,06", "904,14"], ["904,13", "1.808,28"], ["1.356,20", "2.712,42"], "LABORAL TBP 18:30-20:30"),
        ("PA32", "Las Acacias - Lo Blanco", "1,70", ["176,67", "353,34", "530,01"], ["353,34", "706,68", "1.060,02"], ["530,01", "1.060,02", "1.590,04"],
         "LABORAL TS 17:30-19:30; LABORAL TBP 10:00-10:30 / 19:30-20:30"),
        ("PA6", "Lo Blanco - Colón", "1,52", ["157,96", "315,93", "473,89"], ["315,92", "631,86", "947,78"], ["473,89", "947,79", "1.421,68"],
         "LABORAL TS 17:30-19:30; LABORAL TBP 10:00-10:30 / 19:30-20:30"),
        ("PA37", "Colón - Calera de Tango", "4,38", ["455,18"], ["910,37"], ["1.365,56"], ""),
        ("PA4", "Calera de Tango - La Capilla", "1,25", ["129,90"], ["259,81"], ["389,71"], ""),
        ("PA1", "La Capilla - Los Guindos", "7,68", ["868,37"], ["1.736,74"], ["2.605,11"], ""),
    ]),
    ("General Velásquez, Sur → Norte", [
        ("PA19", "Ruta 5 Sur - Américo Vespucio", "3,97", ["412,57"], ["618,86"], ["825,15"], ""),
        ("PA21", "Américo Vespucio - Carlos Valdovinos", "4,93", ["512,34"], ["768,51"], ["1.024,69"], ""),
        ("PA23", "Carlos Valdovinos - Alameda", "2,77", ["287,86", "575,74"], ["431,80", "863,61"], ["575,73", "1.151,48"], "LABORAL TBP 07:00-10:00"),
        ("PA25", "Alameda - Río Mapocho", "4,06", ["421,93", "843,86"], ["632,89", "1.265,79"], ["843,86", "1.687,73"], "LABORAL TBP 07:00-09:30 / 14:30-15:00 / 19:00-19:30"),
        ("PA28", "Río Mapocho - Ruta 5 Norte", "4,93", ["512,34", "1.024,69", "1.537,04"], ["768,51", "1.537,04", "2.305,55"], ["1.024,69", "2.049,39", "3.074,08"],
         "LABORAL TS 07:30-08:30; LABORAL TBP 07:00-07:30 / 08:30-09:30 / 10:00-10:30 / 18:00-19:00"),
    ]),
    ("General Velásquez, Norte → Sur", [
        ("PA29", "Ruta 5 Norte - Río Mapocho", "4,93", ["512,34", "1.024,69"], ["768,51", "1.537,04"], ["1.024,69", "2.049,39"], "LABORAL TBP 17:00-20:30"),
        ("PA26", "Río Mapocho - Alameda", "4,06", ["421,93", "843,86"], ["632,89", "1.265,79"], ["843,86", "1.687,73"], "LABORAL TBP 18:30-20:30"),
        ("PA24", "Alameda - Carlos Valdovinos", "2,77", ["287,86", "575,74", "863,61"], ["431,80", "863,61", "1.295,41"], ["575,73", "1.151,48", "1.727,22"],
         "LABORAL TS 18:30-19:00; LABORAL TBP 18:00-18:30 / 19:00-20:30"),
        ("PA22", "Carlos Valdovinos - Américo Vespucio", "4,93", ["512,34"], ["768,51"], ["1.024,69"], ""),
        ("PA20", "Américo Vespucio - Ruta 5 Sur", "3,97", ["412,57"], ["618,86"], ["825,15"], ""),
    ]),
]

def ac():
    gs = []
    for direction, rows in AC:
        for code, name, km, c1, c2, c3, spec in rows:
            gs.append(gantry(code, name, direction, rates3(c1, c2, c3), spec, d(km)))
    return {"id": "autopista-central", "name": "Autopista Central", "region": "RM", "source": "src-ac-2026",
            "validFrom": "2026-03-17", "validTo": "2026-12-31", "holidayAs": "SABADO", "gantries": gs,
            "note": "Sábado y festivos comparten horario. Motos (cat. 4) pagan como cat. 1; el descuento de motos es un plan aparte."}

# ---------------------------------------------------------------- Vespucio Sur y Norte (tarifa por km)
def per_km(km, factor):
    base = [Decimal("100.489"), Decimal("200.978"), Decimal("301.467")]
    return {t: money(d(km) * r * factor) for t, r in zip(["TBFP", "TBP", "TS"], base)}

def km_rates(km, ts=True):
    out = {}
    for cat, f in (("AUTO", 1), ("BUS_CAMION", 2), ("CAMION_REMOLQUE", 3), ("MOTO", 1)):
        r = per_km(km, f)
        if not ts:
            r.pop("TS")
        out[cat] = r
    return out

VS = [
    ("Poniente → Oriente", [
        ("1.3", "2ª Transversal - Camino a Melipilla", "5,30", "LABORAL TBP 08:30-09:30; LABORAL TS 07:30-08:30; SABADO TBP 18:00-21:00; DOMINGO TBP 19:00-22:00"),
        ("2.2", "General Velásquez - Ruta 5", "2,50", "LABORAL TBP 17:00-17:30; LABORAL TS 18:30-19:30; SABADO TBP 18:00-21:00; DOMINGO TBP 19:00-22:00"),
        ("3.4", "Ruta 5 - Gran Avenida", "1,20", "LABORAL TBP 17:00-18:30 / 19:30-20:00; LABORAL TS 18:30-19:30; SABADO TBP 13:00-15:00 / 18:00-21:00; DOMINGO TBP 19:00-22:00"),
        ("3.2", "Gran Avenida - Santa Rosa", "4,70", "LABORAL TBP 17:00-18:30 / 19:30-20:00; LABORAL TS 18:30-19:30; SABADO TBP 13:00-15:00 / 18:00-21:00; DOMINGO TBP 19:00-22:00"),
        ("4.3", "Coronel - Santa Julia", "0,45", "LABORAL TBP 08:30-09:30 / 18:00-18:30 / 19:30-20:00; LABORAL TS 07:30-08:30 / 18:30-19:30; SABADO TBP 18:00-21:00; DOMINGO TBP 19:00-22:00"),
        ("4.2", "Gnmo. de Alderete - Vicuña Mackenna", "2,65", "LABORAL TBP 08:30-09:30 / 18:00-18:30 / 19:30-20:00; LABORAL TS 07:30-08:30 / 18:30-19:30; SABADO TBP 18:00-21:00; DOMINGO TBP 19:00-22:00"),
        ("5.4", "Las Torres - Quilín", "3,81", "LABORAL TBP 08:30-09:30; LABORAL TS 07:30-08:30"),
        ("5.2", "Quilín - Grecia", "2,89", "LABORAL TBP 08:30-09:30; LABORAL TS 07:30-08:30"),
    ]),
    ("Oriente → Poniente", [
        ("5.1", "Grecia - Quilín", "1,21", "LABORAL TBP 20:00-22:00; LABORAL TS 19:00-20:00; SABADO TBP 13:00-15:00 / 20:00-22:00"),
        ("5.3", "Quilín - Las Torres", "5,49", "LABORAL TBP 20:00-22:00; LABORAL TS 19:00-20:00; SABADO TBP 13:00-15:00 / 20:00-22:00"),
        ("4.1", "Gnmo. de Alderete - Santa Julia", "3,10", "SABADO TBP 13:00-15:00 / 20:00-22:00; DOMINGO TBP 21:00-23:00"),
        ("3.1", "Santa Rosa - Gran Avenida", "3,31", "LABORAL TBP 07:00-07:30 / 08:30-09:30; LABORAL TS 07:30-08:30; SABADO TBP 13:00-15:00 / 20:00-22:00; DOMINGO TBP 21:00-23:00"),
        ("3.3", "Gran Avenida - Ruta 5", "2,59", "LABORAL TBP 07:00-07:30 / 08:30-09:30; LABORAL TS 07:30-08:30; SABADO TBP 13:00-15:00 / 20:00-22:00; DOMINGO TBP 21:00-23:00"),
        ("2.1", "Ruta 5 - General Velásquez", "2,50", "LABORAL TBP 08:30-09:30; LABORAL TS 07:30-08:30"),
        ("1.1", "General Velásquez - Ruta 78", "5,30", "SABADO TBP 11:00-14:00 / 19:00-22:00"),
    ]),
]

AVN = [
    ("Oriente → Poniente", [
        ("P15", "El Salto - Recoleta", "1,40", True, "LABORAL TBP 17:30-18:30 / 19:00-22:00; SABADO TBP 13:00-15:00 / 20:00-22:00; LABORAL TS 18:30-19:00"),
        ("P13", "Recoleta - Pedro Fontova", "4,10", True, "LABORAL TBP 17:30-18:30 / 19:00-22:00; SABADO TBP 13:00-15:00 / 20:00-22:00; LABORAL TS 18:30-19:00"),
        ("P11", "Pedro Fontova - Ruta 5 Norte", "3,00", False, "LABORAL TBP 07:30-09:00 / 17:30-19:00; SABADO TBP 13:00-15:00 / 20:00-22:00; DOMINGO TBP 21:00-23:00"),
        ("P8", "Ruta 5 Norte - Condell", "6,50", False, "LABORAL TBP 07:30-09:30; SABADO TBP 13:00-15:00 / 20:00-22:00; DOMINGO TBP 21:00-23:00"),
        ("P6", "Condell - Costanera Norte", "4,50", False, "LABORAL TBP 07:30-09:30 / 17:30-18:30"),
        ("P4", "Costanera Norte - Ruta 68", "3,50", True, "LABORAL TBP 15:30-16:30 / 19:30-20:00; SABADO TBP 11:00-14:00 / 19:00-22:00; LABORAL TS 16:30-19:30"),
        ("P2", "Ruta 68 - Los Mares", "2,10", True, "LABORAL TBP 15:30-17:30 / 19:30-20:00; LABORAL TS 17:30-19:30"),
        ("P17", "Los Mares - Ruta 78", "3,90", True, "LABORAL TBP 15:30-17:30 / 19:30-20:00; LABORAL TS 17:30-19:30"),
    ]),
    ("Poniente → Oriente", [
        ("P1", "Ruta 78 - Santa Elena", "1,20", True, "LABORAL TBP 06:30-07:00 / 10:00-12:30; LABORAL TS 07:00-10:00"),
        ("P16", "Santa Elena - Ruta 68", "4,80", True, "LABORAL TBP 06:30-07:00 / 10:00-12:30; LABORAL TS 07:00-10:00"),
        ("P3", "Ruta 68 - Costanera Norte", "3,50", False, "LABORAL TBP 07:30-09:30; SABADO TBP 18:00-21:00; DOMINGO TBP 19:00-22:00"),
        ("P5", "Costanera Norte - Condell", "4,50", False, "LABORAL TBP 07:30-08:00; SABADO TBP 18:00-21:00; DOMINGO TBP 19:00-22:00"),
        ("P7", "Condell - Lo Echevers", "1,04", False, "LABORAL TBP 07:30-09:00 / 10:00-11:30 / 17:30-20:00; SABADO TBP 13:00-15:00 / 18:00-21:00; DOMINGO TBP 19:00-22:00"),
        ("P9", "Lo Echevers - Ruta 5 Norte", "5,46", False, "LABORAL TBP 07:30-09:00 / 10:00-11:30 / 17:30-20:00; SABADO TBP 13:00-15:00 / 18:00-21:00; DOMINGO TBP 19:00-22:00"),
        ("P10", "Ruta 5 Norte - Pedro Fontova", "3,00", True, "LABORAL TBP 07:30-08:00 / 09:00-09:30 / 17:30-20:00; SABADO TBP 18:00-21:00; DOMINGO TBP 19:00-22:00; LABORAL TS 08:00-09:00"),
        ("P12", "Pedro Fontova - Guanaco", "0,69", False, "LABORAL TBP 07:30-09:30"),
        ("P14", "Guanaco - El Salto", "4,81", False, "LABORAL TBP 07:30-09:30"),
    ]),
]

def vs():
    gs = [gantry(code, name, direction, km_rates(km, ts="TS" in spec), spec, d(km)) for direction, rows in VS for code, name, km, spec in rows]
    return {"id": "vespucio-sur", "name": "Vespucio Sur", "region": "RM", "source": "src-vs-2026",
            "validFrom": "2026-01-01", "validTo": "2026-12-31", "holidayAs": "DOMINGO", "gantries": gs,
            "note": "Monto = kilómetros del tramo x tarifa por km. Domingo y festivos comparten horario."}

def avn():
    gs = [gantry(code, name, direction, km_rates(km, ts), spec, d(km)) for direction, rows in AVN for code, name, km, ts, spec in rows]
    return {"id": "vespucio-norte", "name": "Vespucio Norte", "region": "RM", "source": "src-avn-2026",
            "validFrom": "2026-02-01", "validTo": "2026-12-31", "holidayAs": "SABADO", "gantries": gs,
            "note": "Monto = kilómetros del tramo x tarifa por km. Sábado y festivos comparten horario."}

# ---------------------------------------------------------------- Túnel San Cristóbal
def tsc():
    ek = {"TBFP": ("565", "1.696", "2.826"), "TBP": ("904", "2.713", "4.522"), "TS": ("1.131", "3.392", "5.653")}
    ke = {"TBFP": ("452", "1.357", "2.261"), "TBP": ("678", "2.035", "3.392")}
    def r(tbl):
        cats = ["AUTO", "BUS_CAMION", "CAMION_REMOLQUE"]
        out = {c: {t: money(d(v[i])) for t, v in tbl.items()} for i, c in enumerate(cats)}
        out["MOTO"] = out["AUTO"]
        return out
    gs = [
        gantry("TSC-EK", "El Salto - Kennedy", "El Salto → Kennedy", r(ek),
               "LABORAL TBP 07:00-07:30 / 10:00-11:00 / 15:30-17:30; LABORAL TS 07:30-10:00 / 17:30-20:30; SABADO TBP 10:00-14:00"),
        gantry("TSC-KE", "Kennedy - El Salto", "Kennedy → El Salto", r(ke),
               "LABORAL TBP 07:00-10:00 / 17:30-20:30; SABADO TBP 10:00-14:00; DOMINGO TBP 17:00-21:00"),
    ]
    return {"id": "tunel-san-cristobal", "name": "Túnel San Cristóbal", "region": "RM", "source": "src-tsc-2026",
            "validFrom": "2026-02-01", "validTo": "2026-12-31", "holidayAs": "SABADO", "gantries": gs,
            "note": "Los festivos usan la estructura del sábado (según el cuadro oficial)."}

# ---------------------------------------------------------------- Nororiente
def an():
    oriente = {"TBFP": ("4.116", "7.408", "13.170", "1.235"), "TBP": ("6.173", "11.112", "19.755", "1.852")}
    poniente = {"TBFP": ("2.744", "4.939", "8.780", "823"), "TBP": ("4.116", "7.408", "13.170", "1.235")}
    def r(tbl):
        cats = ["AUTO", "BUS_CAMION", "CAMION_REMOLQUE", "MOTO"]
        return {c: {t: money(d(v[i])) for t, v in tbl.items()} for i, c in enumerate(cats)}
    spec = "LABORAL TBP 07:00-09:00 / 19:00-21:00; SABADO TBP 08:00-10:00 / 17:00-21:00; DOMINGO TBP 08:00-10:00"
    gs = [
        gantry("P64", "Troncal Oriente", "Oriente → Poniente", r(oriente), spec),
        gantry("P65", "Troncal Oriente", "Poniente → Oriente", r(oriente), spec),
        gantry("P60", "Entrada Llano", "Poniente → Oriente", r(oriente), spec),
        gantry("P61", "Salida Llano", "Oriente → Poniente", r(oriente), spec),
        gantry("P62", "Troncal Poniente", "Oriente → Poniente", r(poniente), spec),
        gantry("P63", "Troncal Poniente", "Poniente → Oriente", r(poniente), spec),
    ]
    return {"id": "nororiente", "name": "Autopista Nororiente", "region": "RM", "source": "src-an-2026",
            "validFrom": "2026-01-01", "validTo": "2026-12-31", "holidayAs": "LABORAL", "gantries": gs,
            "note": "El cuadro no indica horario especial para festivos: se usa el de lunes a viernes (el más alto) para no marcar cobros correctos."}

# ---------------------------------------------------------------- AVO (tarifa entre pórtico de entrada y salida)
def avo():
    text = (ROOT / "tools" / "avo_2026.txt").read_text()
    gs, direction = [], ""
    row = re.compile(r"^(P\d{3}) (.+?)\s{2,}(?:(P\d{3}) (.+?)\s{2,})?(\d+,\d+)\s+((?:\$ [\d.]+\s+){6})")
    for line in text.splitlines():
        if "DIRECCIÓN PRÍNCIPE DE GALES - EL SALTO" in line: direction = "Príncipe de Gales → El Salto"
        if "LA PIRÁMIDE" in line: direction = "La Pirámide"
        if "DIRECCIÓN EL SALTO - PRÍNCIPE DE GALES" in line: direction = "El Salto → Príncipe de Gales"
        m = row.match(line.strip())
        if not m:
            continue
        p_in, n_in, p_out, n_out, km, amounts = m.groups()
        v = re.findall(r"\$ ([\d.]+)", amounts)
        rates = {
            "AUTO": {"TBFP": money(d(v[0])), "TBP": money(d(v[1]))},
            "BUS_CAMION": {"TBFP": money(d(v[2])), "TBP": money(d(v[3]))},
            "CAMION_REMOLQUE": {"TBFP": money(d(v[4])), "TBP": money(d(v[5]))},
        }
        rates["MOTO"] = rates["AUTO"]
        code = f"{p_in}-{p_out}" if p_out else p_in
        name = f"{n_in.strip()} a {n_out.strip()}" if p_out else n_in.strip()
        gs.append(gantry(code, name, direction, rates, "LABORAL TBP 07:30-09:30 / 17:30-19:30", d(km)))
    assert len(gs) == 40, len(gs)
    return {"id": "avo", "name": "AVO (Vespucio Oriente)", "region": "RM", "source": "src-avo-2026",
            "validFrom": "2026-01-01", "validTo": "2026-12-31", "holidayAs": "DOMINGO", "gantries": gs,
            "note": "Se cobra por tramo entre pórtico de entrada y de salida. Punta solo de lunes a viernes, excepto festivos."}

def amb():
    r = {"AUTO": {"TBFP": 889.0}, "MOTO": {"TBFP": 889.0}, "BUS_CAMION": {"TBFP": 1778.0}, "CAMION_REMOLQUE": {"TBFP": 2667.0}}
    return {"id": "amb", "name": "Acceso Vial AMB", "region": "RM", "source": "src-amb-2026",
            "validFrom": "2026-01-01", "validTo": "2026-12-31", "holidayAs": "DOMINGO",
            "gantries": [gantry("AMB", "Acceso al aeropuerto", "Ambos sentidos", r)],
            "note": "Tarifa única con TAG. Se cobra en la boleta de Costanera Norte."}

def r78():
    plazas = [
        ("Américo Vespucio", "215,40", "430,80", "718,00", "1.077,00", "1.436,00", "2.872,00", "2.513,00", "5.026,00"),
        ("Rinconada", "99,00", "198,00", "330,00", "495,00", "660,00", "1.320,00", "1.155,00", "2.310,00"),
        ("Padre Hurtado", "67,50", "135,00", "225,00", "337,50", "450,00", "900,00", "787,50", "1.575,00"),
        ("Malloco", "67,50", "135,00", "225,00", "337,50", "450,00", "900,00", "787,50", "1.575,00"),
        ("Talagante", "112,50", "225,00", "375,00", "562,50", "750,00", "1.500,00", "1.312,50", "2.625,00"),
        ("El Paico", "112,50", "225,00", "375,00", "562,50", "750,00", "1.500,00", "1.312,50", "2.625,00"),
        ("Pomaire", "179,70", "359,40", "599,00", "898,50", "1.198,00", "2.396,00", "2.096,50", "4.193,00"),
        ("Puangue", "348,30", "696,60", "1.161,00", "1.741,50", "2.322,00", "4.644,00", "4.063,50", "8.127,00"),
    ]
    gs = []
    for name, *v in plazas:
        p = [money(d(x)) for x in v]
        rates = {"MOTO": {"TBFP": p[0], "TBP": p[1]}, "AUTO": {"TBFP": p[2], "TBP": p[3]},
                 "BUS_CAMION": {"TBFP": p[4], "TBP": p[5]}, "CAMION_REMOLQUE": {"TBFP": p[6], "TBP": p[7]}}
        code = "R78-" + re.sub(r"[^A-Z]", "", name.upper())[:6]
        gs.append(gantry(code, name, "Ambos sentidos", rates))
    return {"id": "ruta-78", "name": "Autopista Ruta 78", "region": "RM y Valparaíso", "source": "src-r78-2026",
            "validFrom": "2026-01-01", "validTo": "2026-12-31", "holidayAs": "DOMINGO", "bandsComplete": False, "gantries": gs,
            "note": "Tarifa normal todo el año. La punta aplica en temporada alta (20-dic a 10-mar) y fines de semana largos: la revisión solo marca lo que supera la tarifa punta."}

# ---------------------------------------------------------------- Costanera Norte (2° semestre 2026)
# Tarifa = km x $/km (cat 1 y 4: 107 / 206 / 312; cat 2 = x2; cat 3 = x3). Domingos y festivos: TBFP todo el día.
# (código, tramo, km, sin TS, bloques LABORAL TBP | LABORAL TS | SABADO TBP | SABADO TS)
CN_A = "07:00-07:30 / 08:30-10:00 / 12:00-13:00 / 14:00-15:00 / 17:30-19:30", "07:30-08:30 / 13:00-14:00"
CN_B = "07:00-07:30 / 08:30-10:00 / 11:00-13:00 / 14:00-17:00 / 19:30-21:00", "07:30-08:30 / 13:00-14:00 / 17:00-19:30", "11:30-15:00 / 16:30-17:00 / 18:30-19:30"
CN_K = "07:00-07:30 / 08:30-10:00 / 12:00-13:00 / 14:00-15:00 / 17:30-19:00", "07:30-08:30 / 13:00-14:00"
CN_KP = "07:00-09:30 / 12:00-13:00 / 14:00-15:00 / 15:30-16:00 / 16:30-18:00 / 19:30-21:00", "13:00-14:00 / 18:00-19:30"
CN_W = "07:00-07:30 / 09:00-10:00 / 12:00-15:00 / 18:00-18:30", "07:30-09:00"
CN_T = "14:00-16:30 / 19:30-21:00", "07:00-14:00 / 16:30-19:30", "08:30-15:30 / 18:30-19:00"
CN_E = "12:00-13:00 / 14:00-15:00 / 18:00-18:30 / 19:30-21:00", "13:00-14:00 / 18:30-19:30"
CN = [
    ("Oriente → Poniente", "OP", [
        ("P0", "Puente Padre Arteaga - Puente San Francisco", "1,4000", False, CN_A),
        ("P1", "Puente San Francisco - Gran Vía", "4,2000", False, CN_A),
        ("P2.1", "Gran Vía - Centenario", "3,9800", False, CN_A),
        ("P2.2", "Centenario - Puente Lo Saldes", "2,4700", False, CN_A),
        ("SB", "Salida Bellavista", "2,1850", False, CN_B),
        ("P3", "Puente Lo Saldes - Vivaceta", "6,7200", False, CN_B),
        ("EP", "Entrada Purísima", "2,1100", False, CN_B),
        ("EV", "Entrada Vivaceta", "1,1160", False, CN_B),
        ("P5", "Vivaceta - Carrascal", "6,6900", True, ("12:00-15:00 / 18:00-21:00",)),
        ("P6.1", "Carrascal - Petersen", "2,2400", True, ("12:00-15:00 / 18:00-21:00",)),
        ("P6.2", "Petersen - Américo Vespucio Poniente", "3,4100", True, ("12:00-15:00 / 18:00-21:00",)),
        ("P9", "Américo Vespucio Poniente - Ruta 68", "5,0000", False, ("12:00-15:00 / 18:00-21:00", "", "11:00-11:30", "11:30-15:00")),
        ("P7", "Estoril - Las Tranqueras", "2,3385", False, CN_K),
        ("P8.0", "Las Tranqueras - Costanera Norte", "5,4565", False, CN_K),
        ("P8.1", "Las Tranqueras - Costanera Norte", "5,4565", False, CN_K),
    ]),
    ("Poniente → Oriente", "PO", [
        ("P8.3", "Costanera Norte - Las Tranqueras", "5,4565", False, CN_KP),
        ("P8.2", "Costanera Norte - Las Tranqueras", "5,4565", False, CN_KP),
        ("P8.1", "Costanera Norte - Las Tranqueras", "5,4565", False, CN_KP),
        ("P8.0", "Costanera Norte - Las Tranqueras", "5,4565", False, CN_KP),
        ("P7", "Las Tranqueras - Estoril", "2,3385", False, CN_KP),
        ("P9", "Ruta 68 - Américo Vespucio Poniente", "5,0000", True, ("07:00-10:00 / 12:00-15:00",)),
        ("P6.2", "Américo Vespucio Poniente - Petersen", "3,4100", False, CN_W),
        ("P6.1", "Petersen - Carrascal", "2,2400", False, CN_W),
        ("P5", "Carrascal - Vivaceta", "6,6900", False, CN_W),
        ("P4", "Vivaceta - Torres Tajamar", "3,8600", False, CN_T),
        ("P3", "Torres Tajamar - Puente Lo Saldes", "2,8600", False, CN_T),
        ("P2.2", "Puente Lo Saldes - Centenario", "2,4700", False, CN_E),
        ("P2.1", "Centenario - Gran Vía", "3,9800", False, CN_E),
        ("P1", "Gran Vía - Puente San Francisco", "4,2000", False, CN_E),
        ("P0", "Puente San Francisco - Puente Padre Arteaga", "1,4000", False, CN_E),
    ]),
]

def cn():
    base = [Decimal("107"), Decimal("206"), Decimal("312")]
    gs = []
    for direction, suffix, rows in CN:
        for code, name, km, no_ts, blocks in rows:
            blocks = list(blocks) + [""] * (4 - len(blocks))
            spec = "; ".join(f"{day} {kind} {r}" for (day, kind), r in
                             zip([("LABORAL", "TBP"), ("LABORAL", "TS"), ("SABADO", "TBP"), ("SABADO", "TS")], blocks) if r)
            rates = {}
            for cat, f in (("AUTO", 1), ("BUS_CAMION", 2), ("CAMION_REMOLQUE", 3), ("MOTO", 1)):
                r = {t: money(d(km) * b * f) for t, b in zip(["TBFP", "TBP", "TS"], base)}
                if no_ts:
                    r.pop("TS")
                rates[cat] = r
            gs.append(gantry(f"{code}-{suffix}", name, direction, rates, spec, km=d(km)))
    return {"id": "costanera-norte", "name": "Costanera Norte", "region": "RM", "source": "src-cn-2026",
            "validFrom": "2026-07-01", "validTo": "2026-12-31", "holidayAs": "DOMINGO", "gantries": gs,
            "note": "Cuadro del 2° semestre 2026. Domingos y festivos: tarifa base todo el día. El código del pórtico lleva el sentido (OP = oriente a poniente, PO = poniente a oriente)."}

def main():
    pack = {
        "schema": 1,
        "version": "2026.11.13",
        "fetched": FETCHED,
        "sources": [{"id": i, "owner": o, "url": u, "title": t} for i, o, u, t in SOURCES],
        "holidays": [{"date": a, "name": b} for a, b in HOLIDAYS],
        "concessions": [ac(), vs(), avn(), tsc(), an(), cn(), avo(), amb(), r78()],
        "pending": ["Ruta 68", "autopistas interurbanas fuera de la RM"],
    }
    # Coordenadas de OpenStreetMap (tools/build_osm.py): pos = [[lat, lon, rumbo que paga], ...]
    osm = ROOT / "osm" / "porticos_rm.json"
    if osm.exists():
        o = json.loads(osm.read_text())
        for c in pack["concessions"]:
            for g in c["gantries"]:
                pos = o["placed"].get(c["id"], {}).get(g["code"])
                if pos:
                    g["pos"] = pos
        pack["pendingGantries"] = o["pending"]
        pack["mapLicense"] = o["license"]
    out = ROOT / "tarifas" / "2026.json"
    out.write_text(json.dumps(pack, ensure_ascii=False, separators=(",", ":")))
    n = sum(len(c["gantries"]) for c in pack["concessions"])
    print(f"{out}: {len(pack['concessions'])} autopistas, {n} pórticos, {out.stat().st_size // 1024} KB")

if __name__ == "__main__":
    main()
