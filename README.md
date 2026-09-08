# glyphs-scripts

Scripts propios para Glyphs 3, escritos para el trabajo tipográfico de
contrafonts (Joaquín Contreras Soto).

## Contenido

| Script | Qué hace |
|---|---|
| **Panel de anchos** | Ventana flotante para familias Uniwidth y monoespaciadas: mide el reparto de anchos, compara masters y unifica o fija anchos. [Manual](docs/panel-de-anchos.md) |
| **Seleccionar por Ancho** | Lista los anchos existentes de un master con su conteo y su proporción respecto al ancho dominante, y selecciona esos glifos en la ventana de fuente para etiquetarlos a mano. |
| **Volver Mono el Master** | Fija un ancho único en todas las capas de un master, con opción de centrar el dibujo y de tomar el más ancho. Antecesor de *Fijar mono* del panel. |
| **Palabras desde Wikipedia** | Busca en Wikipedia palabras que usen solo los glifos seleccionados y las abre en una pestaña nueva. |
| **Añadir Puntos a Trazos** (`puntos-a-trazos.py`) | Añade una cantidad de puntos a los trazos seleccionados sin cambiar la forma. |

Ninguno guarda el archivo: los que modifican dejan los cambios en memoria para
que revises y guardes tú.

## Instalación

Los scripts se enlazan desde la carpeta de Glyphs a este repo, así se editan
aquí y Glyphs los ve al instante:

```sh
cd ~/Library/Application\ Support/Glyphs\ 3/Scripts/
for f in ~/Documents/GitHub/glyphs-scripts/Scripts/*.py; do ln -sf "$f" .; done
```

Después, en Glyphs: `Script ▸ Reload Scripts` (Cmd+Opt+Shift+Y).

Requieren `vanilla` (ya viene enlazada en la carpeta Scripts de Glyphs).

## Notas

- Los archivos fuente `.glyphs` no viven aquí: están en Dropbox, que ya los versiona.
- Los scripts de terceros instalados (Cape Weightor, Dirt) quedan fuera del repo.

## Scripts de 2017

La primera tanda (2017–2022) también vive en `Scripts/`, con la extensión `.py`
que les faltaba. Son de una línea y sin diálogo:

- `Add sufix to selected glyphs.py`
- `enable automatic alignment.py`
- `insert anchors in all layers, in position xy.py`
- `just print glyph names.py`

Tres de ellos están escritos en Python 2 (`print` sin paréntesis) y fallan tal
cual en Glyphs 3; el único que corre hoy es *insert anchors in all layers*.

## features/

Lo que no es script y estaba suelto en la raíz: `Opentype init` (código de una
feature `init`), `randomCycles` (un plist con clases y features) y el archivo de
prueba `random-feature.glyphs`.

Licencia: GPL-3.0.
