#MenuTitle: Volver Mono el Master
# -*- coding: utf-8 -*-
"""
Fija un ancho unico en todas las capas de un master, con la opcion de
centrar el dibujo dentro de la caja resultante.

Sirve para cualquier fuente: elige el master, el alcance (toda la fuente
o solo los glifos seleccionados) y el ancho. No guarda el archivo.
"""

import vanilla
from GlyphsApp import Glyphs, Message

DOMINIO = "org.contrafonts.volvermono."


class VolverMono(object):

	def __init__(self):
		ancho, alto, margen, fila = 330, 232, 15, 26
		self.w = vanilla.FloatingWindow((ancho, alto), "Volver mono el master")
		col = 62
		campo = ancho - margen - col

		y = 12
		self.w.etiquetaMaster = vanilla.TextBox((margen, y + 3, col, 17), "Master:", sizeStyle="small")
		self.w.master = vanilla.PopUpButton((col, y, campo, 20), [], sizeStyle="small", callback=self.actualizarInfo)

		y += fila
		self.w.etiquetaAlcance = vanilla.TextBox((margen, y + 3, col, 17), "Glifos:", sizeStyle="small")
		self.w.alcance = vanilla.PopUpButton(
			(col, y, campo, 20),
			["Toda la fuente", "Solo los seleccionados"],
			sizeStyle="small",
			callback=self.actualizarInfo,
		)

		y += fila + 4
		self.w.etiquetaAncho = vanilla.TextBox((margen, y + 3, col, 17), "Ancho:", sizeStyle="small")
		self.w.valorAncho = vanilla.EditText((col, y, 62, 20), "560", sizeStyle="small", callback=self.guardarPrefs)
		self.w.usarMaximo = vanilla.Button((col + 70, y, campo - 70, 20), "usar el mas ancho", sizeStyle="small", callback=self.ponerMaximo)

		y += fila + 4
		self.w.centrar = vanilla.CheckBox((margen, y, -margen, 20), "Centrar el dibujo en la caja", value=False, sizeStyle="small", callback=self.guardarPrefs)

		y += 22
		self.w.saltarMarcas = vanilla.CheckBox((margen, y, -margen, 20), "Conservar marcas y glifos de ancho 0", value=True, sizeStyle="small", callback=self.actualizarInfo)

		y += 26
		self.w.info = vanilla.TextBox((margen, y, -margen, 32), "", sizeStyle="mini")

		self.w.aplicar = vanilla.Button((-margen - 110, -32, 110, 20), "Aplicar", sizeStyle="small", callback=self.aplicar)
		self.w.setDefaultButton(self.w.aplicar)

		self.cargarPrefs()
		self.poblarMasters()
		self.actualizarInfo(None)
		self.w.open()
		self.w.makeKey()

	# ------------------------------------------------------------- estado

	def fuente(self):
		return Glyphs.font

	def poblarMasters(self):
		font = self.fuente()
		if font is None:
			self.w.master.setItems(["(sin fuente abierta)"])
			return
		nombres = [m.name for m in font.masters]
		self.w.master.setItems(nombres)
		activo = font.selectedFontMaster
		if activo is not None:
			for i, m in enumerate(font.masters):
				if m.id == activo.id:
					self.w.master.set(i)
					break

	def masterElegido(self):
		font = self.fuente()
		if font is None or not len(font.masters):
			return None
		indice = self.w.master.get()
		if indice < 0 or indice >= len(font.masters):
			return None
		return font.masters[indice]

	def glifosObjetivo(self):
		"""Devuelve los glifos segun el alcance elegido."""
		font = self.fuente()
		if font is None:
			return []
		if self.w.alcance.get() == 1:
			glifos, vistos = [], set()
			for capa in (font.selectedLayers or []):
				glyph = capa.parent
				if glyph is not None and glyph.name not in vistos:
					vistos.add(glyph.name)
					glifos.append(glyph)
			return glifos
		return list(font.glyphs)

	def capasObjetivo(self):
		"""Capas del master elegido que si van a recibir el ancho."""
		master = self.masterElegido()
		if master is None:
			return [], 0

		saltar = self.w.saltarMarcas.get()
		capas, omitidas = [], 0

		for glyph in self.glifosObjetivo():
			capa = glyph.layers[master.id]
			if capa is None:
				continue
			esMarca = (glyph.category == "Mark" and glyph.subCategory == "Nonspacing")
			if saltar and (esMarca or capa.width == 0):
				omitidas += 1
				continue
			capas.append(capa)

		return capas, omitidas

	# ---------------------------------------------------------- interfaz

	def actualizarInfo(self, sender):
		self.guardarPrefs(None)
		font = self.fuente()
		if font is None:
			self.w.info.set("Abre un archivo .glyphs para empezar.")
			return

		capas, omitidas = self.capasObjetivo()
		if not capas:
			self.w.info.set("No hay capas que modificar con estos ajustes.")
			return

		anchos = [c.width for c in capas]
		texto = "%i capas a modificar   ·   anchos actuales de %i a %i" % (len(capas), round(min(anchos)), round(max(anchos)))
		if omitidas:
			texto += "\n%i sin tocar (marcas / ancho 0)" % omitidas
		self.w.info.set(texto)

	def ponerMaximo(self, sender):
		capas, _ = self.capasObjetivo()
		if not capas:
			return
		# el ancho de la capa mas ancha, redondeado hacia arriba a la decena
		maximo = max(c.width for c in capas)
		self.w.valorAncho.set(str(int(-(-maximo // 10) * 10)))
		self.actualizarInfo(None)

	def anchoPedido(self):
		try:
			return float(self.w.valorAncho.get().replace(",", "."))
		except ValueError:
			return None

	# ------------------------------------------------------ preferencias

	def cargarPrefs(self):
		Glyphs.registerDefault(DOMINIO + "ancho", "560")
		Glyphs.registerDefault(DOMINIO + "centrar", False)
		Glyphs.registerDefault(DOMINIO + "saltarMarcas", True)
		Glyphs.registerDefault(DOMINIO + "alcance", 0)
		self.w.valorAncho.set(Glyphs.defaults[DOMINIO + "ancho"])
		self.w.centrar.set(bool(Glyphs.defaults[DOMINIO + "centrar"]))
		self.w.saltarMarcas.set(bool(Glyphs.defaults[DOMINIO + "saltarMarcas"]))
		self.w.alcance.set(int(Glyphs.defaults[DOMINIO + "alcance"]))

	def guardarPrefs(self, sender):
		Glyphs.defaults[DOMINIO + "ancho"] = self.w.valorAncho.get()
		Glyphs.defaults[DOMINIO + "centrar"] = self.w.centrar.get()
		Glyphs.defaults[DOMINIO + "saltarMarcas"] = self.w.saltarMarcas.get()
		Glyphs.defaults[DOMINIO + "alcance"] = self.w.alcance.get()

	# --------------------------------------------------------- aplicacion

	def aplicar(self, sender):
		font = self.fuente()
		if font is None:
			Message(title="No hay fuente abierta", message="Abre primero un archivo .glyphs.")
			return

		master = self.masterElegido()
		if master is None:
			Message(title="Sin master", message="No pude identificar el master elegido.")
			return

		ancho = self.anchoPedido()
		if ancho is None or ancho <= 0:
			Message(title="Ancho invalido", message="Escribe un numero mayor que cero en el campo Ancho.")
			return

		capas, omitidas = self.capasObjetivo()
		if not capas:
			Message(title="Nada que hacer", message="Con estos ajustes no queda ninguna capa por modificar.")
			return

		centrar = self.w.centrar.get()

		Glyphs.clearLog()
		print("Volver mono el master")
		print("Fuente: %s   ·   master: %s" % (font.familyName, master.name))
		print("Ancho: %s   ·   centrado: %s" % (ancho, "si" if centrar else "no"))
		print("")

		font.disableUpdateInterface()
		try:
			for capa in capas:
				glyph = capa.parent
				glyph.beginUndo()
				try:
					if centrar:
						caja = capa.bounds
						anchoDibujo = caja.size.width
						if anchoDibujo > 0:
							destino = (ancho - anchoDibujo) / 2.0
							dx = destino - caja.origin.x
							if abs(dx) > 0.001:
								capa.applyTransform([1, 0, 0, 1, dx, 0])
					capa.width = ancho
				finally:
					glyph.endUndo()
		finally:
			font.enableUpdateInterface()

		print("Capas modificadas: %i" % len(capas))
		print("Capas sin tocar (marcas / ancho 0): %i" % omitidas)
		print("")
		print("El archivo no se guardo. Revisa y guarda tu mismo.")

		self.guardarPrefs(None)
		self.actualizarInfo(None)


VolverMono()
