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

Despues de medir, la tabla de la izquierda muestra el paisaje de picos y la
de la derecha los glifos que podrian colapsar hacia el pico elegido, dibujados
y con su diferencia en puntos. Desde ahi se seleccionan en la ventana de
fuente, se copian sus nombres o se abren en una pestana para corregirlos.

Todo respeta el alcance (toda la fuente / seleccionados) y, cuando
corresponde, el master elegido arriba.
"""

import textwrap

import vanilla
from AppKit import NSAffineTransform, NSColor, NSImage, NSPasteboard, NSStringPboardType
from GlyphsApp import Glyphs, Message

DOMINIO = "contrafonts.anchos."


class PanelDeAnchos(object):

	def __init__(self):
		ancho, alto, margen, col, fila = 560, 640, 15, 62, 26

		self.w = vanilla.FloatingWindow(
			(ancho, alto), "Panel de anchos",
			minSize=(520, 560), maxSize=(1200, 1400),
		)

		# El mapa que dejan las mediciones: lista de grupos, cada uno con su
		# pico, sus anchos y los glifos que se le podrian pegar.
		self.mapa = []

		# ---- controles compartidos ----
		y = 12
		self.w.etiquetaMaster = vanilla.TextBox((margen, y + 3, col, 17), "Master:", sizeStyle="small")
		self.w.master = vanilla.PopUpButton((col, y, 200, 20), [], sizeStyle="small", callback=self.actualizarInfo)

		y += fila
		self.w.etiquetaAlcance = vanilla.TextBox((margen, y + 3, col, 17), "Glifos:", sizeStyle="small")
		self.w.alcance = vanilla.PopUpButton(
			(col, y, 200, 20),
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
		self.w.etiquetaLimite = vanilla.TextBox((margen + 176, y + 3, 34, 17), "hasta", sizeStyle="small")
		self.w.valorLimite = vanilla.EditText((margen + 212, y, 44, 20), "10", sizeStyle="small", callback=self.guardarPrefs)
		self.w.etiquetaPts = vanilla.TextBox((margen + 260, y + 3, 24, 17), "pts", sizeStyle="small")
		self.w.btnComparar = vanilla.Button((margen + 292, y, 168, 20), "Comparar masters", sizeStyle="small", callback=self.compararMasters)

		# ---- el mapa: picos a la izquierda, desviados a la derecha ----
		y += 30
		self.w.tituloMapa = vanilla.TextBox((margen, y, -margen, 16), "Picos del master   ·   a la derecha, los que podrian colapsar hacia el pico", sizeStyle="mini")

		y += 18
		columnasPicos = [
			{"title": "Pico",    "key": "pico",    "width": 54},
			{"title": "Glifos",  "key": "glifos",  "width": 48},
			{"title": "Colapsan", "key": "revisar", "width": 58},
			{"title": "",        "key": "aviso",   "width": 18},
		]
		self.w.picos = vanilla.List(
			(margen, y, 196, -206), [],
			columnDescriptions=columnasPicos,
			selectionCallback=self.alElegirPico,
			allowsMultipleSelection=False,
			allowsEmptySelection=True,
			drawFocusRing=True,
		)

		columnasDesviados = [
			{"title": "",       "key": "dibujo", "width": 46, "cell": vanilla.ImageListCell()},
			{"title": "Glifo",  "key": "nombre", "width": 140},
			{"title": "Ancho",  "key": "anchoTexto", "width": 54},
			{"title": "Dif",    "key": "dif",    "width": 44},
			{"title": "Hacia",  "key": "hacia",  "width": 54},
		]
		self.w.desviados = vanilla.List(
			(margen + 206, y, -margen, -206), [],
			columnDescriptions=columnasDesviados,
			allowsMultipleSelection=True,
			allowsEmptySelection=True,
			drawFocusRing=True,
			rowHeight=24,
		)

		self.w.conPico = vanilla.CheckBox((margen, -178, 196, 20), "Incluir los del pico", value=False, sizeStyle="small", callback=self.alElegirPico)
		self.w.btnCopiar = vanilla.Button((margen + 206, -176, 120, 20), "Copiar nombres", sizeStyle="small", callback=self.copiarNombres)
		self.w.btnSeleccionar = vanilla.Button((-300, -176, 130, 20), "Seleccionar", sizeStyle="small", callback=self.seleccionarDesviados)
		self.w.btnPestana = vanilla.Button((-160, -176, 145, 20), "Abrir en pestana", sizeStyle="small", callback=self.abrirPestana)

		# ---- seccion Modificar ----
		self.w.lineaMod = vanilla.HorizontalLine((margen, -146, -margen, 1))
		self.w.tituloMod = vanilla.TextBox((margen, -138, -margen, 16), "Modificar  (no guarda el archivo)", sizeStyle="small")

		self.w.etiquetaAncho = vanilla.TextBox((margen, -109, col, 17), "Ancho:", sizeStyle="small")
		self.w.valorAncho = vanilla.EditText((col, -112, 62, 20), "560", sizeStyle="small", callback=self.guardarPrefs)
		self.w.usarMaximo = vanilla.Button((col + 70, -112, 140, 20), "usar el mas ancho", sizeStyle="small", callback=self.ponerMaximo)

		self.w.centrar = vanilla.CheckBox((margen, -84, -margen, 20), "Centrar el dibujo en la caja", value=False, sizeStyle="small", callback=self.guardarPrefs)
		self.w.saltarMarcas = vanilla.CheckBox((margen, -62, -margen, 20), "Conservar marcas y glifos de ancho 0", value=True, sizeStyle="small", callback=self.actualizarInfo)

		self.w.btnFijarMono = vanilla.Button((margen, -34, 108, 20), "Fijar mono", sizeStyle="small", callback=self.aplicar)
		self.w.btnUnificar = vanilla.Button((margen + 118, -34, 190, 20), "Unificar desde este master", sizeStyle="small", callback=self.unificarDesdeReferencia)

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

	# -------------------------------------------------------------- mapa

	def imagenDeCapa(self, capa, alto=20):
		"""Dibuja la capa en una imagen chica para la tabla. Si algo falla
		devuelve una imagen vacia: la fila queda sin dibujo, pero la tabla vive."""
		vacia = NSImage.alloc().initWithSize_((1, alto))
		try:
			ruta = capa.completeBezierPath
		except Exception:
			ruta = None
		if ruta is None:
			try:
				ruta = capa.bezierPath
			except Exception:
				ruta = None
		if ruta is None or ruta.isEmpty():
			return vacia
		try:
			font = self.fuente()
			upm = float(font.upm or 1000)
			escala = float(alto) / upm
			anchoImagen = max(int(round(capa.width * escala)) + 2, 4)
			imagen = NSImage.alloc().initWithSize_((anchoImagen, alto))
			imagen.lockFocus()
			transformacion = NSAffineTransform.transform()
			# La linea de base queda a un cuarto de la altura: entra el descendente.
			transformacion.translateXBy_yBy_(1.0, alto * 0.25)
			transformacion.scaleBy_(escala)
			copia = ruta.copy()
			copia.transformUsingAffineTransform_(transformacion)
			NSColor.textColor().set()
			copia.fill()
			imagen.unlockFocus()
			return imagen
		except Exception:
			return vacia

	def cargarMapa(self, conteo, grupos):
		"""Guarda el resultado de la medicion y llena la tabla de picos."""
		self.mapa = []
		for pico, miembros in grupos.items():
			anchos = sorted(miembros)
			desviados = [(w, n) for w in anchos if w != pico for n in sorted(conteo[w])]
			self.mapa.append({
				"pico": pico,
				"anchos": anchos,
				"total": sum(len(conteo[w]) for w in anchos),
				"desviados": desviados,
				"delPico": sorted(conteo[pico]),
			})

		# Los grupos mas poblados primero: el ancho dominante encabeza la lista.
		self.mapa.sort(key=lambda g: (-g["total"], g["pico"]))

		filas = []
		for g in self.mapa:
			filas.append({
				"pico": str(g["pico"]),
				"glifos": g["total"],
				"revisar": len(g["desviados"]),
				"aviso": "•" if g["desviados"] else "",
			})
		self.w.picos.set(filas)
		self.w.desviados.set([])
		if filas:
			self.w.picos.setSelection([0])

	def grupoElegido(self):
		if not self.mapa:
			return None
		indices = self.w.picos.getSelection()
		if not indices:
			return None
		i = indices[0]
		if i < 0 or i >= len(self.mapa):
			return None
		return self.mapa[i]

	def alElegirPico(self, sender):
		grupo = self.grupoElegido()
		if grupo is None:
			self.w.desviados.set([])
			return

		master = self.masterElegido()
		font = self.fuente()
		if master is None or font is None:
			return

		pares = list(grupo["desviados"])
		if self.w.conPico.get():
			pares += [(grupo["pico"], n) for n in grupo["delPico"]]
		pares.sort(key=lambda par: (par[0], par[1]))

		filas = []
		for w, nombre in pares:
			glyph = font.glyphs[nombre]
			capa = glyph.layers[master.id] if glyph is not None else None
			filas.append({
				"dibujo": self.imagenDeCapa(capa) if capa is not None else NSImage.alloc().initWithSize_((1, 20)),
				"nombre": nombre,
				"anchoTexto": str(w),
				"dif": "pico" if w == grupo["pico"] else "%+i" % (w - grupo["pico"]),
				"hacia": str(grupo["pico"]),
			})
		self.w.desviados.set(filas)

	def nombresElegidos(self):
		"""Las filas marcadas en la tabla de la derecha; si no hay ninguna,
		todas las que se estan mostrando."""
		filas = self.w.desviados.get()
		if not filas:
			return []
		indices = self.w.desviados.getSelection()
		if indices:
			return [filas[i]["nombre"] for i in indices if 0 <= i < len(filas)]
		return [f["nombre"] for f in filas]

	def glifosElegidos(self):
		font = self.fuente()
		if font is None:
			return [], []
		glifos, faltantes = [], []
		for n in self.nombresElegidos():
			g = font.glyphs[n]
			if g is None:
				faltantes.append(n)
			else:
				glifos.append(g)
		return glifos, faltantes

	def seleccionarDesviados(self, sender):
		font = self.fuente()
		if font is None:
			Message(title="No hay fuente abierta", message="Abre primero un archivo .glyphs.")
			return
		glifos, faltantes = self.glifosElegidos()
		if not glifos:
			Message(title="Nada que seleccionar", message="Mide primero, y elige un pico en la lista.")
			return
		try:
			font.selection = glifos
		except Exception as e:
			Message(title="No pude seleccionar", message="La API rechazo la seleccion:\n%s" % e)
			return
		aviso = "%i glifos seleccionados en la ventana de fuente." % len(font.selection)
		if faltantes:
			aviso += "   %i no existen." % len(faltantes)
		self.w.info.set(aviso)

	def abrirPestana(self, sender):
		"""Abre los glifos del grupo en una pestana de edicion, que es donde
		se corrigen de verdad."""
		font = self.fuente()
		if font is None:
			Message(title="No hay fuente abierta", message="Abre primero un archivo .glyphs.")
			return
		glifos, _ = self.glifosElegidos()
		if not glifos:
			Message(title="Nada que abrir", message="Mide primero, y elige un pico en la lista.")
			return
		texto = "".join("/" + g.name for g in glifos)
		try:
			pestana = font.newTab(texto)
		except Exception as e:
			Message(title="No pude abrir la pestana", message="La API rechazo la pestana:\n%s" % e)
			return
		master = self.masterElegido()
		if master is not None and pestana is not None:
			try:
				font.masterIndex = list(font.masters).index(master)
			except Exception:
				pass
		self.w.info.set("%i glifos abiertos en una pestana nueva." % len(glifos))

	def copiarNombres(self, sender):
		nombres = self.nombresElegidos()
		if not nombres:
			Message(title="Nada que copiar", message="Mide primero, y elige un pico en la lista.")
			return
		tablero = NSPasteboard.generalPasteboard()
		tablero.declareTypes_owner_([NSStringPboardType], None)
		tablero.setString_forType_("\n".join(nombres), NSStringPboardType)
		self.w.info.set("%i nombres copiados al portapapeles." % len(nombres))

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
			self.mapa = []
			self.w.picos.set([])
			self.w.desviados.set([])
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

		# La tabla se queda con todo el paisaje, no solo con los colapsables.
		self.cargarMapa(conteo, grupos)

		# Cuentas del resumen: lo que importa es cuantos glifos hay que tocar.
		medidos = sum(len(nombres) for nombres in conteo.values())
		desviados = {}
		for c, miembros in colapsables.items():
			for w in miembros:
				if w != c:
					desviados[w] = c
		glifosDesviados = sum(len(conteo[w]) for w in desviados)
		anchosEnGrupos = sum(len(ms) for ms in colapsables.values())

		alcance = "toda la fuente" if self.w.alcance.get() == 0 else "los seleccionados"

		Glyphs.clearLog()
		Glyphs.showMacroWindow()
		print("SIMILARES EN EL MASTER -- %s / %s" % (font.familyName or "sin nombre", master.name))
		print("Alcance: %s   ·   distancia maxima: %i pts" % (alcance, limite))
		print("=" * 72)
		print("")
		print("  Glifos medidos                  %i" % medidos)
		print("  Anchos distintos                %i" % len(conteo))
		if colapsables:
			print("  Anchos que se pueden juntar     %i, repartidos en %i grupos" % (anchosEnGrupos, len(colapsables)))
			print("")
			print("  GLIFOS A REVISAR                %i" % glifosDesviados)
			print("  (los que no estan en el ancho mas poblado de su grupo)")
		else:
			print("")
			print("  No hay anchos parecidos dentro de %i pts: nada que juntar." % limite)

		if solos:
			sueltos = sorted(solos.keys())
			print("")
			print("  Anchos aislados (sin ningun vecino a menos de %i pts): %i" % (limite, len(sueltos)))
			print(textwrap.fill(
				", ".join(str(w) for w in sueltos),
				width=72,
				initial_indent="    ",
				subsequent_indent="    ",
			))

		if not colapsables:
			return

		print("")
		print("=" * 72)
		print("GRUPO POR GRUPO")
		print("El pico es el ancho con mas glifos; debajo van los que se le parecen,")
		print("con su diferencia en puntos y los glifos que hay que revisar.")

		orden = sorted(colapsables, key=lambda c: -sum(len(conteo[w]) for w in colapsables[c]))
		for i, c in enumerate(orden, 1):
			miembros = sorted(colapsables[c])
			total = sum(len(conteo[w]) for w in miembros)
			aRevisar = sum(len(conteo[w]) for w in miembros if w != c)
			print("")
			print("-" * 72)
			print("%i.  pico %i pts   ·   %i glifos en el grupo   ·   %i a revisar" % (i, c, total, aRevisar))
			for w in miembros:
				if w == c:
					print("      %5i         %4i glifos   pico" % (w, len(conteo[w])))
					continue
				prefijo = "      %5i  %+4i   %4i glifos   " % (w, w - c, len(conteo[w]))
				print(textwrap.fill(
					", ".join(sorted(conteo[w])),
					width=86,
					initial_indent=prefijo,
					subsequent_indent=" " * len(prefijo),
				))

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
		Glyphs.showMacroWindow()
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
		Glyphs.showMacroWindow()
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
