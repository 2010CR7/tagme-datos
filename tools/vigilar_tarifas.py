"""Vigila si las concesionarias o el MOP publicaron cuadros tarifarios nuevos (por ejemplo, los de 2027).

Lee páginas públicas, junta los enlaces a PDF o imágenes que mencionan el año siguiente al de los cuadros
cargados y los compara con los ya vistos (archivo vistos.json en la rama `vigilancia`). Si aparece algo nuevo,
lo escribe en nuevos.md para que el flujo abra un aviso (issue) en el repositorio. No descarga los archivos.
"""
import json
import re
import sys
import urllib.parse
import urllib.request

PAGINAS = [
    "https://concesiones.mop.gob.cl/peajes-y-porticos/",
    "https://www.autopistacentral.cl/tarifas/",
    "https://www.vespuciosur.cl/tarifas/",
    "https://www.vespucionorte.cl/tarifas",
    "https://www.tunelsancristobal.cl/tarifas",
    "https://www.autopistanororiente.cl/tarifas/",
    "https://www.avo.cl/tarifas/",
    "https://www.accesovialamb.cl/tarifas/",
    "https://www.autopistaruta78.cl/tarifas",
    "https://web.costaneranorte.cl/tarifas/",
    "https://ruta68.cl/tarifas/",
]
ENLACE = re.compile(r'href=["\']([^"\']+\.(?:pdf|jpg|jpeg|png))["\']', re.I)


def enlaces(url: str, anio: str) -> set[str]:
    req = urllib.request.Request(url, headers={"User-Agent": "tagme-datos/1.0 (datos publicos)"})
    try:
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    except Exception as e:  # una página caída no detiene la revisión
        print(f"  sin respuesta: {url} ({e.__class__.__name__})")
        return set()
    out = set()
    for href in ENLACE.findall(html):
        full = urllib.parse.urljoin(url, href)
        if anio in urllib.parse.unquote(full):
            out.add(full)
    return out


def main(vistos_path: str, anio: str) -> None:
    try:
        vistos = set(json.load(open(vistos_path)))
    except FileNotFoundError:
        vistos = set()
    encontrados = set()
    for p in PAGINAS:
        e = enlaces(p, anio)
        print(f"{p}: {len(e)} enlaces con {anio}")
        encontrados |= e
    nuevos = sorted(encontrados - vistos)
    json.dump(sorted(vistos | encontrados), open(vistos_path, "w"), indent=1)
    if nuevos:
        with open("nuevos.md", "w") as f:
            f.write(f"Aparecieron documentos tarifarios {anio} en sitios oficiales. Hay que transcribirlos en "
                    "`tools/build_tarifas.py` y `tools/peajes_regiones.py`, subir `version` y copiar los archivos a la app.\n\n")
            f.writelines(f"- {u}\n" for u in nuevos)
    print(f"Nuevos: {len(nuevos)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
