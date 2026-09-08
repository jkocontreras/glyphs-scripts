# MenuTitle: Palabras desde Wikipedia
# -*- coding: utf-8 -*-
__doc__ = """
Busca palabras en Wikipedia (un idioma al azar por ejecución) que usen SOLO
los glifos seleccionados en la fuente actual, y las abre en una pestaña nueva.
"""

import json
import random
import ssl
import time
import urllib.request
from GlyphsApp import Glyphs

# Contexto SSL sin verificación de certificados. Necesario porque el Python
# de Glyphs en macOS no siempre encuentra los certificados del sistema.
# Es seguro aquí: solo leemos páginas públicas de Wikipedia.
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# AJUSTES (puedes cambiar estos valores)
# ---------------------------------------------------------------------------

TARGET_WORDS = 30      # cuántas palabras juntar (aproximado)
MAX_TRIES = 40         # cuántos artículos consultar como máximo
MIN_WORD_LENGTH = 2    # ignora palabras más cortas que esto
MAX_SHORT_WORDS = 4    # cuántas palabras "cortas" se permiten
SHORT_WORD_LENGTH = 3  # qué se considera "corta"
PAUSE_SECONDS = 0.4    # pausa entre peticiones, evita el bloqueo 429 de Wikipedia
CASE_SENSITIVE = True  # True = respeta mayúsculas/minúsculas de lo seleccionado
                       # False = "a" también acepta "A"

# Idiomas (mismos que la web): sudamericanos + europeos de alfabeto latino
LANGUAGES = [
    'es', 'en', 'de',
    'qu', 'gn', 'ay', 'nah',
    'pt', 'fr', 'it', 'nl', 'sv', 'no', 'da', 'fi',
    'pl', 'cs', 'sk', 'hu', 'ro', 'hr', 'sl', 'lt', 'lv', 'et',
    'tr', 'id', 'ms', 'tl', 'sw',
    'eu', 'ca', 'gl', 'af', 'ga', 'cy', 'is',
]

LANGUAGE_NAMES = {
    'es': 'Español', 'en': 'Inglés', 'de': 'Alemán',
    'qu': 'Quechua', 'gn': 'Guaraní', 'ay': 'Aymara', 'nah': 'Náhuatl',
    'pt': 'Portugués', 'fr': 'Francés', 'it': 'Italiano', 'nl': 'Neerlandés',
    'sv': 'Sueco', 'no': 'Noruego', 'da': 'Danés', 'fi': 'Finlandés',
    'pl': 'Polaco', 'cs': 'Checo', 'sk': 'Eslovaco', 'hu': 'Húngaro',
    'ro': 'Rumano', 'hr': 'Croata', 'sl': 'Esloveno', 'lt': 'Lituano',
    'lv': 'Letón', 'et': 'Estonio', 'tr': 'Turco', 'id': 'Indonesio',
    'ms': 'Malayo', 'tl': 'Tagalo', 'sw': 'Suajili', 'eu': 'Euskera',
    'ca': 'Catalán', 'gl': 'Gallego', 'af': 'Afrikáans', 'ga': 'Irlandés',
    'cy': 'Galés', 'is': 'Islandés',
}

# ---------------------------------------------------------------------------
# LÓGICA
# ---------------------------------------------------------------------------

def selected_characters(font):
    """Caracteres de los glifos seleccionados. Funciona en vista de Fuente
    y de Edición: en ambas toma el carácter real, nunca el nombre del glifo."""
    # selectedLayers funciona en las dos vistas; de cada capa sacamos su glifo.
    layers = font.selectedLayers or []
    glyphs = [layer.parent for layer in layers if layer.parent is not None]
    # Respaldo por si la vista de Fuente no entrega capas.
    if not glyphs:
        glyphs = list(font.selection)

    chars = set()
    for glyph in glyphs:
        s = glyph.string  # carácter unicode del glifo, o None si no tiene
        if not s:
            continue
        for ch in s:
            chars.add(ch)
            if not CASE_SENSITIVE:
                chars.add(ch.lower())
                chars.add(ch.upper())
    return chars


def fetch_one_paragraph(lang):
    """Trae el resumen de un artículo aleatorio de Wikipedia en ese idioma."""
    url = "https://%s.wikipedia.org/api/rest_v1/page/random/summary" % lang
    req = urllib.request.Request(url, headers={"User-Agent": "GlyphsTester/1.0"})
    with urllib.request.urlopen(req, timeout=8, context=SSL_CONTEXT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return (data.get("extract") or "").strip()


def words_in_text(text):
    """Separa el texto en palabras (secuencias de letras)."""
    out = []
    current = ""
    for ch in text:
        if ch.isalpha():
            current += ch
        else:
            if current:
                out.append(current)
            current = ""
    if current:
        out.append(current)
    return out


def matching_words(text, allowed):
    result = []
    for word in words_in_text(text):
        if len(word) < MIN_WORD_LENGTH:
            continue
        if all(ch in allowed for ch in word):
            result.append(word)
    return result


def main():
    font = Glyphs.font
    if font is None:
        Glyphs.showMacroWindow()
        print("Abre una fuente primero.")
        return

    allowed = selected_characters(font)
    if not allowed:
        Glyphs.showMacroWindow()
        print("Selecciona al menos un glifo con carácter unicode.")
        return

    # Un solo idioma por ejecución. Ejecuta de nuevo para otro idioma.
    lang = random.choice(LANGUAGES)

    found = []
    seen = set()
    short_count = 0
    failures = 0
    last_error = None

    for _ in range(MAX_TRIES):
        if len(found) >= TARGET_WORDS:
            break
        try:
            extract = fetch_one_paragraph(lang)
        except Exception as err:
            failures += 1
            last_error = err
            time.sleep(PAUSE_SECONDS)
            continue
        for word in matching_words(extract, allowed):
            if word in seen:
                continue
            is_short = len(word) <= SHORT_WORD_LENGTH
            if is_short and short_count >= MAX_SHORT_WORDS:
                continue
            seen.add(word)
            found.append(word)
            if is_short:
                short_count += 1
        time.sleep(PAUSE_SECONDS)

    if not found:
        Glyphs.showMacroWindow()
        if failures >= MAX_TRIES:
            print("No se pudo conectar con Wikipedia.")
            if last_error is not None:
                print("Detalle del error: %s" % last_error)
        else:
            print("No se encontraron palabras con esos glifos. Prueba con otros.")
        return

    # Abre una pestaña nueva con las palabras
    text = " ".join(found)
    font.newTab(text)

    # Informe en la ventana de macros
    lang_name = LANGUAGE_NAMES.get(lang, lang)
    print("%s: %d palabras" % (lang_name, len(found)))


main()
