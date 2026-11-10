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
