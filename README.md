# tagme-datos

Datos públicos y páginas legales de **TagMe v1**, la app Android para conocer el costo de los peajes en todo Chile ([código de la app](https://github.com/2010CR7/tagme-android)). La app solo descarga estos archivos y nunca envía información de las personas.

**Páginas públicas** (GitHub Pages, carpeta `docs/`): [inicio](https://2010cr7.github.io/tagme-datos/), [política de privacidad](https://2010cr7.github.io/tagme-datos/privacidad.html), [términos de uso](https://2010cr7.github.io/tagme-datos/terminos.html) y [eliminar cuenta y datos](https://2010cr7.github.io/tagme-datos/eliminar-datos.html). Son las direcciones que se informan en Google Play.

## Qué hay

| Archivo | Contenido | Se actualiza |
|---|---|---|
| `tarifas/2026.json` | Cuadros tarifarios 2026 de las autopistas urbanas de Santiago, Ruta 68 y Ruta 78, con fuente, vigencia, feriados y pórticos | A mano con `tools/build_tarifas.py` (subir `version`, formato `AAAA.MM.DD`) |
| `osm/peajes_cl.json` | 195 peajes y pórticos de regiones con su concesión y plaza (174 con tarifa exacta) y las tarifas 2026 del MOP | `tools/build_peajes.py` |
| `osm/porticos_rm.json` | Coordenadas y sentido de cobro de cada pórtico urbano | `tools/build_osm.py` |
| `tarifas/rutas_rm.json` | Red vial detallada de Santiago para calcular rutas | `tools/build_osm.py` |
| `tarifas/rutas_cl.bin` | Red de autopistas, troncales y rutas principales de Chile (87.703 nodos, 24.735 km) | `tools/build_red_cl.py` |
| `osm/peajes_vias.json` | Tipo de vía de cada caseta (en la ruta o en un enlace) | `tools/build_red_cl.py` |
| rama `vivo`: `noticias.json` | 15 titulares recientes de medios chilenos | Cada 30 min |
| rama `vivo`: `bencinas.json` | Precios de combustibles de todas las estaciones del país | Cada 3 h |
| `ticker.json` | Avisos fijos de la barra "EN VIVO" | A mano |
| `docs/` | Páginas públicas: inicio, privacidad, términos y eliminación de datos | A mano |

## Flujos automáticos (GitHub Actions)

- **Datos en vivo** (`datos-vivos.yml`, cada 30 min): `tools/build_noticias.py` lee Google News filtrado a medios chilenos; `tools/build_bencinas.py` consulta la API de la Comisión Nacional de Energía cada 3 horas. Publica ambos en la rama `vivo`. Las credenciales de la CNE viven solo como secretos del repositorio (`CNE_EMAIL`, `CNE_PASSWORD`). Si llegan menos de 50 estaciones, no se publica nada.
- **Pórticos desde OpenStreetMap** (`osm-porticos.yml`, manual): descarga pórticos, casetas y autopistas de la RM desde Overpass a la rama `osm`.
- **Vigilar tarifas nuevas** (`vigilar-tarifas.yml`, lunes y jueves): `tools/vigilar_tarifas.py` revisa las páginas de tarifas de las concesionarias y del MOP; si aparecen documentos del año siguiente, abre un issue con los enlaces. Lo visto se guarda en la rama `vigilancia`.
- **Red vial de Chile** (`red-vial-chile.yml`, manual): baja el extracto de Chile de Geofabrik, lo filtra con osmium y arma `rutas_cl.bin` y `peajes_vias.json` en la rama `osm`.

## Cómo se asigna cada peaje de regiones

`tools/peajes_regiones.py` tiene las tarifas transcritas de los 28 PDF interurbanos del MOP (https://concesiones.mop.gob.cl/peajes-y-porticos/). Cada peaje se asigna a su concesión por nombre o zona, y a su plaza por nombre, por un punto conocido o por la vía donde está la caseta: en la carretera es troncal y en un enlace es lateral.

## Reajuste de enero

Los cuadros cambian cada 1 de enero. El flujo "Vigilar tarifas nuevas" avisa con un issue cuando se publican. Para 2027: actualizar los montos en `tools/build_tarifas.py` y `tools/peajes_regiones.py`, subir `version`, regenerar y copiar los archivos a `app/src/main/resources` de la app.

## Formato de `ticker.json`

| Campo | Obligatorio | Valores |
|---|---|---|
| `kind` | sí | `precio`, `aviso` o `noticia` |
| `text` | sí | máximo 160 caracteres |
| `date` | no | `AAAA-MM-DD` |
| `url` | no | solo `https://`, fuente oficial o de prensa |

## Reportes de la comunidad

Los cobros mayores a la tarifa oficial llegan como issues con la etiqueta `reporte-tarifa`, sin patente, RUT ni fecha exacta. Se revisan contra el cuadro oficial antes de confirmarlos.

## Reglas

Solo información pública y verificable, con fuente. Lenguaje neutro ("posible inconsistencia", nunca acusaciones).

## Licencias

Datos de mapa, pórticos y red vial © colaboradores de OpenStreetMap, licencia [ODbL](https://www.openstreetmap.org/copyright). Tarifas: documentos públicos de cada concesionaria y del MOP.
