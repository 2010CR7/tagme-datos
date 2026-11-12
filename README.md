# tagme-datos

Datos públicos que la app TagMe descarga sin enviar información de las personas.

- `ticker.json`: noticias de la barra "EN VIVO". Editar este archivo actualiza la barra de todos los usuarios en máximo 30 minutos, sin publicar una nueva versión de la app.

Formato de cada elemento de `items`:

| Campo | Obligatorio | Valores |
|---|---|---|
| `kind` | sí | `precio`, `aviso` o `noticia` |
| `text` | sí | máximo 160 caracteres |
| `date` | no | `AAAA-MM-DD` |
| `url` | no | solo `https://`, fuente oficial o de prensa |

Reglas: solo información pública y verificable; lenguaje neutral ("posible inconsistencia", nunca acusaciones).

## Tarifas oficiales

- `tarifas/2026.json`: cuadros tarifarios 2026 de cada autopista, transcritos de los PDF oficiales (ver `sources`). La app lo trae incluido y descarga la versión nueva cuando cambia `version`.
- `tools/build_tarifas.py`: genera el archivo. Para actualizar: corregir los datos en el script y ejecutar `python3 tools/build_tarifas.py`. Subir `version` (formato `AAAA.MM.DD`).
- Pendientes: Costanera Norte, Ruta 68 y autopistas interurbanas fuera de la RM.

## Reportes de la comunidad

Los reportes de cobros mayores a la tarifa oficial llegan como issues con la etiqueta `reporte-tarifa`. No contienen patente, RUT ni fecha exacta. Antes de confirmarlos se revisan contra el cuadro oficial; el lenguaje es siempre neutral ("posible cobro a revisar").

## Mapa de pórticos y red de rutas (OpenStreetMap)

- `osm/porticos_rm.json`: coordenadas y rumbo de cobro de cada pórtico, cruzados con `tarifas/2026.json` por su código.
- `tarifas/rutas_rm.json`: red simplificada de autopistas, troncales y enlaces de la RM para calcular rutas en el teléfono.
- Se generan con el flujo **Pórticos desde OpenStreetMap** (descarga desde Overpass a la rama `osm`) y `python3 tools/build_osm.py <rm_gantries.json> <rm_roads.json>`; luego `python3 tools/build_tarifas.py` agrega las coordenadas al paquete.
- Datos © colaboradores de OpenStreetMap, licencia [ODbL](https://www.openstreetmap.org/copyright).
