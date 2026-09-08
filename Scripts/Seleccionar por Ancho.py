#MenuTitle: Seleccionar por Ancho
# -*- coding: utf-8 -*-
"""
Lista los anchos que existen en un master y selecciona en la ventana de
fuente todos los glifos de los anchos que elijas.

Pensado para leer consistencias en monoespaciadas: la columna "x base"
muestra cada ancho como multiplo del ancho dominante, y marca con un
punto los que se salen de la reticula.

Seleccionas, aplicas, y etiquetas con color tu mismo en la ventana.
"""

import collections
import vanilla
from GlyphsApp import Glyphs, Message, UPDATEINTERFACE
from AppKit import NSPasteboard, NSStringPboardType

DOMINIO = "org.contrafonts.selporancho."


class SeleccionarPorAncho(object):

	def __init__(self):
		ancho, alto, margen = 340, 348, 15
		self.w = vanilla.FloatingWindow((ancho, alto), "Seleccionar por ancho")
		col = 52
		campo = ancho - margen - col

		y = 12
		self.w.etiquetaMaster = vanilla.TextBox((margen, y + 3, col, 17), "Master:", sizeStyle="small")
		self.w.master = vanilla.PopUpButton((col, y, campo, 20), [], sizeStyle="small", callback=self.recargar)

		y += 28
		self.w.soloExportables = vanilla.CheckBox((margen, y, -margen, 20), "Solo glifos que exportan", value=True, sizeStyle="small", callback=self.recargar)

		y += 26
		columnas = [
			{"title": "Ancho",  "key": "ancho",  "width": 64},
			{"title": "Glifos", "key": "conteo", "width": 54},
			{"title": "x base", "key": "ratio",  "width": 62},
			{"title": "",       "key": "aviso",  "width": 26},
		]
		self.w.lista = vanilla.List(
			(margen, y, -margen, 176), [],
			columnDescriptions=columnas,
			selectionCallback=self.actualizarInfo,
			doubleClickCallback=self.aplicar,
			allowsMultipleSelection=True,
			allowsEmptySelection=True,
			drawFocusRing=True,
		)

		y += 184
		self.w.info = vanilla.TextBox((margen, y, -margen, 28), "", sizeStyle="mini")

		self.w.copiar = vanilla.Button((margen, -32, 118, 20), "Copiar nombres", sizeStyle="small", callback=self.copiarNombres)
		self.w.aplicar = vanilla.Button((-margen - 130, -32, 130, 20), "Seleccionar", sizeStyle="small", callback=self.aplicar)
		self.w.setDefaultButton(self.w.aplicar)

		self.filas = []       # [(ancho, [nombres...])]
		self._font = None     # para detectar cambios de fuente/master en la grilla
		self._masterID = None
		self.poblarMasters()
		self.recargar(None)
		# Sigue al master que tienes al frente en la ventana de fuente:
		# si lo cambias en la grilla, este panel se actualiza solo.
		Glyphs.addCallback(self.seguirGrilla, UPDATEINTERFACE)
		self.w.bind("close", self.alCerrar)
		self.w.open()
		self.w.makeKey()

	# ------------------------------------------------------------- datos

	def poblarMasters(self):
		font = Glyphs.font
		if font is None:
			self.w.master.setItems(["(sin fuente abierta)"])
			return
		self.w.master.setItems([m.name for m in font.masters])
		activo = font.selectedFontMaster
		if activo is not None:
			for i, m in enumerate(font.masters):
				if m.id == activo.id:
					self.w.master.set(i)
					break

	def masterElegido(self):
		font = Glyphs.font
		if font is None or not len(font.masters):
			return None
		i = self.w.master.get()
		return font.masters[i] if 0 <= i < len(font.masters) else None

	def seguirGrilla(self, sender):
		"""Se dispara cuando Glyphs refresca su interfaz. Si cambiaste de
		master (o de fuente) en la grilla, sincroniza el menu y recarga.
		Sale barato cuando no hubo cambios relevantes."""
		font = Glyphs.font
		if font is None:
			return
		activo = font.selectedFontMaster
		if activo is None:
			return
		# Nada cambio: no recargar (este callback es muy frecuente).
		if self._font is font and self._masterID == activo.id:
			return
		cambioFuente = self._font is not font
		self._font = font
		self._masterID = activo.id
		if cambioFuente:
			self.w.master.setItems([m.name for m in font.masters])
		idx = next((i for i, m in enumerate(font.masters) if m.id == activo.id), 0)
		self.w.master.set(idx)
		self.recargar(None)

	def alCerrar(self, sender):
		"""Quita el callback al cerrar la ventana, para no dejarlo colgado."""
		try:
			Glyphs.removeCallback(self.seguirGrilla)
		except Exception:
			pass

	def recargar(self, sender):
		font = Glyphs.font
		master = self.masterElegido()
		if font is None or master is None:
			self.w.lista.set([])
			self.w.info.set("Abre un archivo .glyphs para empezar.")
			return

		soloExp = self.w.soloExportables.get()
		porAncho = collections.defaultdict(list)

		for glyph in font.glyphs:
			if soloExp and not glyph.export:
				continue
			capa = glyph.layers[master.id]
			if capa is None:
				continue
			porAncho[round(capa.width, 1)].append(glyph.name)

		if not porAncho:
			self.w.lista.set([])
			self.w.info.set("Este master no tiene capas.")
			self.filas = []
			return

		# el ancho dominante define la reticula
		base = max(porAncho, key=lambda w: len(porAncho[w]))
		self.base = base

		# de mayor a menor cantidad: lo raro queda abajo, a la vista
		self.filas = sorted(porAncho.items(), key=lambda kv: (-len(kv[1]), kv[0]))

		items = []
		for w, nombres in self.filas:
			ratio = (w / base) if base else 0
			enReticula = abs(ratio * 4 - round(ratio * 4)) < 0.01
			items.append({
				"ancho": ("%g" % w),
				"conteo": str(len(nombres)),
				"ratio": ("%.3f" % ratio).rstrip("0").rstrip("."),
				"aviso": "" if enReticula else "•",
			})
		self.w.lista.set(items)
		self.actualizarInfo(None)

	# ---------------------------------------------------------- interfaz

	def glifosElegidos(self):
		indices = self.w.lista.getSelection()
		nombres = []
		for i in indices:
			if 0 <= i < len(self.filas):
				nombres.extend(self.filas[i][1])
		return nombres

	def actualizarInfo(self, sender):
		if not self.filas:
			return
		fuera = sum(1 for w, n in self.filas if abs((w / self.base) * 4 - round((w / self.base) * 4)) >= 0.01)
		total = sum(len(n) for _, n in self.filas)
		texto = "Base: %g   ·   %i anchos distintos en %i glifos" % (self.base, len(self.filas), total)
		if fuera:
			texto += "   ·   %i fuera de la reticula (•)" % fuera
		elegidos = self.glifosElegidos()
		if elegidos:
			texto += "\nVas a seleccionar %i glifos." % len(elegidos)
		self.w.info.set(texto)

	# -------------------------------------------------------- acciones

	def aplicar(self, sender):
		font = Glyphs.font
		if font is None:
			Message(title="Sin fuente", message="Abre primero un archivo .glyphs.")
			return

		nombres = self.glifosElegidos()
		if not nombres:
			Message(title="Nada elegido", message="Elige al menos un ancho en la lista.")
			return

		# Resuelve nombres a glifos y anota los que no existan, en vez de
		# dejarlos desaparecer en silencio.
		glifos, faltantes = [], []
		for n in nombres:
			g = font.glyphs[n]
			if g is None:
				faltantes.append(n)
			else:
				glifos.append(g)

		if not glifos:
			Message(title="No pude seleccionar", message="Ninguno de esos glifos existe en la fuente.")
			return

		# Selecciona en la grilla. Si la API falla, muestra el error real.
		try:
			font.selection = glifos
		except Exception as e:
			Message(title="No pude seleccionar", message="La API rechazo la seleccion:\n%s" % e)
			return

		# Cuenta cuantos quedaron seleccionados de verdad, no cuantos pedimos.
		realmente = len(font.selection)
		pedidos = len(glifos)

		aviso = "%i glifos seleccionados." % realmente
		if realmente != pedidos:
			aviso += "\nOjo: pedi %i, la fuente marco %i." % (pedidos, realmente)
		if faltantes:
			muestra = ", ".join(faltantes[:5]) + ("..." if len(faltantes) > 5 else "")
			aviso += "\n%i no existen: %s" % (len(faltantes), muestra)
		if realmente == pedidos and not faltantes:
			aviso += "\nEtiquetalos con color desde la ventana de fuente."
		self.w.info.set(aviso)

	def copiarNombres(self, sender):
		nombres = self.glifosElegidos()
		if not nombres:
			Message(title="Nada elegido", message="Elige al menos un ancho en la lista.")
			return
		pb = NSPasteboard.generalPasteboard()
		pb.declareTypes_owner_([NSStringPboardType], None)
		pb.setString_forType_(" ".join(nombres), NSStringPboardType)
		self.w.info.set("%i nombres copiados.\nSirven para pegar en un List Filter." % len(nombres))


SeleccionarPorAncho()
