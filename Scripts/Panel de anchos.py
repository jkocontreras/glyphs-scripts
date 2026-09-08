#MenuTitle: Panel de anchos
# -*- coding: utf-8 -*-
"""
Panel de anchos para trabajar familias Uniwidth.

Medir (no modifica nada, informa en la ventana de macros):
  - Rango de anchos dentro del master: linea de info, automatica.
  - Similares en el master: agrupa glifos de ancho parecido hacia los
    picos mas poblados, hasta una distancia maxima que eliges.
  - Comparar masters: lista los glifos cuyo ancho no coincide entre
    todos los masters (tolerancia 0), que es lo que rompe el Uniwidth.

Modificar (cambia la fuente, no guarda el archivo):
  - Fijar mono: pone un ancho unico a todas las capas del master elegido.
  - Unificar desde este master: copia el ancho de cada glifo del master
    elegido hacia los demas masters.

Todo respeta el alcance (toda la fuente / seleccionados) y, cuando
corresponde, el master elegido arriba.
"""

import vanilla
from GlyphsApp import Glyphs, Message

DOMINIO = "contrafonts.anchos."


class PanelDeAnchos(object):

	def __init__(self):
		ancho, alto, margen, col, fila = 380, 372, 15, 62, 26
		campo = ancho - margen - col

		self.w = vanilla.FloatingWindow((ancho, alto), "Panel de anchos")

		# ---- controles compartidos ----
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

		y += fila
		self.w.info = vanilla.TextBox((margen, y, -margen, 30), "", sizeStyle="mini")

		# ---- seccion Medir ----
		y += 34
		self.w.lineaMedir = vanilla.HorizontalLine((margen, y, -margen, 1))
		y += 6
		self.w.tituloMedir = vanilla.TextBox((margen, y, -margen, 16), "Medir  (no modifica nada)", sizeStyle="small")

		y += 22
		self.w.btnSimilares = vanilla.Button((margen, y, 168, 20), "Similares en el master", sizeStyle="small", callback=self.medirSimilares)
		self.w.etiquetaLimite = vanilla.TextBox((margen + 178, y + 3, 34, 17), "hasta", sizeStyle="small")
		self.w.valorLimite = vanilla.EditText((margen + 214, y, 44, 20), "10", sizeStyle="small", callback=self.guardarPrefs)
		self.w.etiquetaPts = vanilla.TextBox((margen + 262, y + 3, 30, 17), "pts", sizeStyle="small")

		y += fila
		self.w.btnComparar = vanilla.Button((margen, y, 168, 20), "Comparar masters", sizeStyle="small", callback=self.compararMasters)

		# ---- seccion Modificar ----
		y += fila + 6
		self.w.lineaMod = vanilla.HorizontalLine((margen, y, -margen, 1))
		y += 6
		self.w.tituloMod = vanilla.TextBox((margen, y, -margen, 16), "Modificar  (no guarda el archivo)", sizeStyle="small")

		y += 22
		self.w.etiquetaAncho = vanilla.TextBox((margen, y + 3, col, 17), "Ancho:", sizeStyle="small")
		self.w.valorAncho = vanilla.EditText((col, y, 62, 20), "560", sizeStyle="small", callback=self.guardarPrefs)
		self.w.usarMaximo = vanilla.Button((col + 70, y, campo - 70, 20), "usar el mas ancho", sizeStyle="small", callback=self.ponerMaximo)

		y += fila
		self.w.centrar = vanilla.CheckBox((margen, y, -margen, 20), "Centrar el dibujo en la caja", value=False, sizeStyle="small", callback=self.guardarPrefs)

		y += 22
		self.w.saltarMarcas = vanilla.CheckBox((margen, y, -margen, 20), "Conservar marcas y glifos de ancho 0", value=True, sizeStyle="small", callback=self.actualizarInfo)

		y += 28
		self.w.btnFijarMono = vanilla.Button((margen, y, 108, 20), "Fijar mono", sizeStyle="small", callback=self.aplicar)
		self.w.btnUnificar = vanilla.Button((margen + 118, y, ancho - margen - (margen + 118), 20), "Unificar desde este master", sizeStyle="small", callback=self.unificarDesdeReferencia)

		# Enter dispara una medicion inofensiva, nunca una modificacion.
		self.w.setDefaultButton(self.w.btnComparar)

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
		"""Capas del master elegido que si van a recibir el ancho (Fijar mono)."""
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

	def conteoAnchos(self):
		"""Histograma del master elegido: ancho (entero) -> lista de nombres.
		Ignora los glifos de ancho 0 (marcas), que no aportan al analisis."""
		master = self.masterElegido()
		if master is None:
			return {}
		conteo = {}
		for glyph in self.glifosObjetivo():
			capa = glyph.layers[master.id]
			if capa is None:
				continue
			w = int(round(capa.width))
			if w == 0:
				continue
			conteo.setdefault(w, []).append(glyph.name)
		return conteo

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
		texto = "%i capas en el master   ·   anchos de %i a %i" % (len(capas), round(min(anchos)), round(max(anchos)))
		if omitidas:
			texto += "\n%i sin contar (marcas / ancho 0)" % omitidas
		self.w.info.set(texto)

	def ponerMaximo(self, sender):
		capas, _ = self.capasObjetivo()
		if not capas:
			return
		maximo = max(c.width for c in capas)
		self.w.valorAncho.set(str(int(-(-maximo // 10) * 10)))
		self.actualizarInfo(None)

	def anchoPedido(self):
		try:
			return float(self.w.valorAncho.get().replace(",", "."))
		except ValueError:
			return None

	def limitePedido(self):
		try:
			return int(round(float(self.w.valorLimite.get().replace(",", "."))))
		except ValueError:
			return None

	# ------------------------------------------------------ preferencias

	def cargarPrefs(self):
		Glyphs.registerDefault(DOMINIO + "ancho", "560")
		Glyphs.registerDefault(DOMINIO + "limite", "10")
		Glyphs.registerDefault(DOMINIO + "centrar", False)
		Glyphs.registerDefault(DOMINIO + "saltarMarcas", True)
		Glyphs.registerDefault(DOMINIO + "alcance", 0)
		self.w.valorAncho.set(Glyphs.defaults[DOMINIO + "ancho"])
		self.w.valorLimite.set(Glyphs.defaults[DOMINIO + "limite"])
		self.w.centrar.set(bool(Glyphs.defaults[DOMINIO + "centrar"]))
		self.w.saltarMarcas.set(bool(Glyphs.defaults[DOMINIO + "saltarMarcas"]))
		self.w.alcance.set(int(Glyphs.defaults[DOMINIO + "alcance"]))

	def guardarPrefs(self, sender):
		Glyphs.defaults[DOMINIO + "ancho"] = self.w.valorAncho.get()
		Glyphs.defaults[DOMINIO + "limite"] = self.w.valorLimite.get()
		Glyphs.defaults[DOMINIO + "centrar"] = self.w.centrar.get()
		Glyphs.defaults[DOMINIO + "saltarMarcas"] = self.w.saltarMarcas.get()
		Glyphs.defaults[DOMINIO + "alcance"] = self.w.alcance.get()

	# --------------------------------------------------------- medir

	def medirSimilares(self, sender):
		font = self.fuente()
		if font is None:
			Message(title="No hay fuente abierta", message="Abre primero un archivo .glyphs.")
			return
		master = self.masterElegido()
		if master is None:
			Message(title="Sin master", message="No pude identificar el master elegido.")
			return

		limite = self.limitePedido()
		if limite is None or limite < 1:
			Message(title="Distancia invalida", message="Escribe un numero de 1 o mas en el campo de distancia.")
			return

		conteo = self.conteoAnchos()
		if not conteo:
			Glyphs.showMacroWindow()
			print("No hay anchos que analizar con estos ajustes.")
			return

		# Ordena los anchos por poblacion (mas glifos primero); en empate, por valor.
		anchos = sorted(conteo.keys(), key=lambda w: (-len(conteo[w]), w))

		# Los mas poblados anclan como centros. Cada ancho se pega al centro
		# mas cercano dentro del limite; si no hay ninguno cerca, es un centro nuevo.
		centros = []
		asignacion = {}
		for w in anchos:
			mejor, mejorDist = None, None
			for c in centros:
				d = abs(w - c)
				if d <= limite and (mejorDist is None or d < mejorDist):
					mejor, mejorDist = c, d
			if mejor is None:
				centros.append(w)
				asignacion[w] = w
			else:
				asignacion[w] = mejor

		grupos = {}
		for w, c in asignacion.items():
			grupos.setdefault(c, []).append(w)

		colapsables = {c: ms for c, ms in grupos.items() if len(ms) > 1}
		solos = {c: ms for c, ms in grupos.items() if len(ms) == 1}

		Glyphs.clearLog()
		Glyphs.showMacroWindow()
		print("Similares en el master -- %s / %s" % (font.familyName or "sin nombre", master.name))
		print("Distancia maxima: %i pts" % limite)
		print("=" * 60)

		if colapsables:
			print("Grupos con anchos parecidos (candidatos a un valor comun):")
			orden = sorted(colapsables, key=lambda c: -sum(len(conteo[w]) for w in colapsables[c]))
			for c in orden:
				miembros = sorted(colapsables[c])
				total = sum(len(conteo[w]) for w in miembros)
				print("")
				print("  pico %i  (%i glifos en el grupo)" % (c, total))
				for w in miembros:
					marca = "   <- pico" if w == c else ""
					print("      %i pts : %i glifos%s" % (w, len(conteo[w]), marca))
		else:
			print("No hay anchos parecidos dentro de %i pts." % limite)

		print("")
		print("=" * 60)
		print("Anchos distintos: %i    Grupos colapsables: %i" % (len(conteo), len(colapsables)))
		if solos:
			sueltos = sorted(solos.keys())
			print("Anchos sin vecinos cercanos: %s" % ", ".join(str(w) for w in sueltos))

	def compararMasters(self, sender):
		font = self.fuente()
		if font is None:
			Message(title="No hay fuente abierta", message="Abre primero un archivo .glyphs.")
			return

		masters = font.masters
		if len(masters) < 2:
			Glyphs.showMacroWindow()
			print("La fuente tiene un solo master; no hay nada que comparar.")
			return

		inconsistentes, faltantes, revisados = [], [], 0
		for glyph in self.glifosObjetivo():
			anchos, falta = [], False
			for m in masters:
				capa = glyph.layers[m.id]
				if capa is None:
					falta = True
					break
				anchos.append(capa.width)
			revisados += 1
			if falta:
				faltantes.append(glyph.name)
				continue
			# tolerancia 0: distintos si no coinciden al redondear a entero
			if len(set(int(round(a)) for a in anchos)) > 1:
				detalle = ", ".join("%s=%g" % (m.name, w) for m, w in zip(masters, anchos))
				inconsistentes.append((glyph.name, detalle))

		Glyphs.clearLog()
		Glyphs.showMacroWindow()
		print("Comparar masters (Uniwidth) -- %s" % (font.familyName or "sin nombre"))
		print("Masters: %s" % ", ".join(m.name for m in masters))
		print("=" * 60)
		if inconsistentes:
			print("Glifos con ancho distinto entre masters (%i):" % len(inconsistentes))
			for name, detalle in inconsistentes:
				print("  %s  ->  %s" % (name, detalle))
		else:
			print("Todos los glifos tienen el mismo ancho en todos los masters.")
		if faltantes:
			print("")
			print("Glifos sin capa en algun master (%i):" % len(faltantes))
			for name in faltantes:
				print("  %s" % name)
		print("=" * 60)
		print("Revisados: %i    Inconsistentes: %i    Sin capa: %i" % (revisados, len(inconsistentes), len(faltantes)))

	# --------------------------------------------------------- modificar

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
		print("Fijar mono")
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

	def unificarDesdeReferencia(self, sender):
		font = self.fuente()
		if font is None:
			Message(title="No hay fuente abierta", message="Abre primero un archivo .glyphs.")
			return

		masters = font.masters
		if len(masters) < 2:
			Message(title="Un solo master", message="La fuente tiene un solo master; no hay hacia donde unificar.")
			return

		referencia = self.masterElegido()
		if referencia is None:
			Message(title="Sin master", message="No pude identificar el master de referencia.")
			return

		centrar = self.w.centrar.get()
		saltar = self.w.saltarMarcas.get()
		otros = [m for m in masters if m.id != referencia.id]

		Glyphs.clearLog()
		print("Unificar desde este master")
		print("Fuente: %s   ·   referencia: %s" % (font.familyName, referencia.name))
		print("Hacia: %s" % ", ".join(m.name for m in otros))
		print("")

		modificadas, omitidas = 0, 0
		font.disableUpdateInterface()
		try:
			for glyph in self.glifosObjetivo():
				capaRef = glyph.layers[referencia.id]
				if capaRef is None:
					continue
				esMarca = (glyph.category == "Mark" and glyph.subCategory == "Nonspacing")
				if saltar and (esMarca or capaRef.width == 0):
					omitidas += 1
					continue
				anchoRef = capaRef.width
				glyph.beginUndo()
				try:
					for m in otros:
						capa = glyph.layers[m.id]
						if capa is None:
							continue
						if int(round(capa.width)) == int(round(anchoRef)):
							continue
						if centrar:
							caja = capa.bounds
							anchoDibujo = caja.size.width
							if anchoDibujo > 0:
								destino = (anchoRef - anchoDibujo) / 2.0
								dx = destino - caja.origin.x
								if abs(dx) > 0.001:
									capa.applyTransform([1, 0, 0, 1, dx, 0])
						capa.width = anchoRef
						modificadas += 1
				finally:
					glyph.endUndo()
		finally:
			font.enableUpdateInterface()

		print("Capas ajustadas: %i" % modificadas)
		print("Glifos omitidos (marcas / ancho 0): %i" % omitidas)
		print("")
		print("El archivo no se guardo. Revisa y guarda tu mismo.")

		self.guardarPrefs(None)
		self.actualizarInfo(None)


PanelDeAnchos()
