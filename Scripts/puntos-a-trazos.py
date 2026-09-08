# MenuTitle: Añadir Puntos a Trazos
# -*- coding: utf-8 -*-
"""
Añade una cantidad personalizada de puntos a los trazos (paths) seleccionados,
sin modificar la forma de la figura.

Instalación:
1. Copia este archivo en:
   ~/Library/Application Support/Glyphs 3/Scripts/
2. En Glyphs: Script > Reload Scripts (Cmd+Opt+Shift+Y)
3. Selecciona un trazo (o nodos de un trazo) en la vista de edición
4. Ejecuta: Script > Añadir Puntos a Trazos
"""

from GlyphsApp import *
from AppKit import NSPoint
import vanilla


# ---------------------------------------------------------------------------
# Matemática de subdivisión (garantiza que la forma NO cambia)
# ---------------------------------------------------------------------------

def lerp(p0, p1, t=0.5):
	"""Interpolación lineal entre dos puntos."""
	return NSPoint(p0.x + (p1.x - p0.x) * t, p0.y + (p1.y - p0.y) * t)


def deCasteljau(p0, p1, p2, p3, t=0.5):
	"""
	Subdivide una curva cúbica de Bézier en el parámetro t.
	Devuelve los 5 puntos nuevos necesarios para reconstruir
	las dos mitades de la curva original de forma EXACTA:
	(offA, onA_control, midOnCurve, onB_control, offB)
	Curva 1: p0, offA, onA_control, midOnCurve
	Curva 2: midOnCurve, onB_control, offB, p3
	"""
	p01 = lerp(p0, p1, t)
	p12 = lerp(p1, p2, t)
	p23 = lerp(p2, p3, t)
	p012 = lerp(p01, p12, t)
	p123 = lerp(p12, p23, t)
	p0123 = lerp(p012, p123, t)
	return p01, p012, p0123, p123, p23


# ---------------------------------------------------------------------------
# Segmentación de un GSPath
# ---------------------------------------------------------------------------

def getSegments(path):
	"""
	Devuelve una lista de segmentos del path.
	Cada segmento es un dict con:
	  - 'onCurveStartIndex': índice del nodo on-curve inicial
	  - 'offIndices': lista de índices de nodos off-curve (0, o 2 para cúbicas)
	  - 'onCurveEndIndex': índice del nodo on-curve final
	"""
	nodes = path.nodes
	n = len(nodes)
	segments = []
	offBuffer = []

	# Recorremos el path de forma circular (los paths en Glyphs son cerrados
	# salvo casos especiales; si es abierto igual funciona, solo no cierra el último tramo)
	startIdx = 0
	for i in range(n):
		node = nodes[i]
		if node.type == OFFCURVE:
			offBuffer.append(i)
			continue
		else:
			# node es LINE o CURVE (on-curve): cierra el segmento
			segments.append({
				"onCurveStartIndex": startIdx,
				"offIndices": list(offBuffer),
				"onCurveEndIndex": i,
			})
			offBuffer = []
			startIdx = i

	if not path.closed and segments:
		# quitamos el segmento "fantasma" que cerraría el último punto con el primero
		segments.pop()

	return segments


def segmentLength(path, seg):
	"""Longitud aproximada de un segmento (para elegir cuál subdividir)."""
	nodes = path.nodes
	p0 = nodes[seg["onCurveStartIndex"]].position
	p3 = nodes[seg["onCurveEndIndex"]].position
	if len(seg["offIndices"]) == 2:
		p1 = nodes[seg["offIndices"][0]].position
		p2 = nodes[seg["offIndices"][1]].position
		# longitud del polígono de control, más precisa que la cuerda directa
		return dist(p0, p1) + dist(p1, p2) + dist(p2, p3)
	else:
		return dist(p0, p3)


def dist(a, b):
	dx = a.x - b.x
	dy = a.y - b.y
	return (dx * dx + dy * dy) ** 0.5


# ---------------------------------------------------------------------------
# Inserción de un punto en un segmento (sin alterar la forma)
# ---------------------------------------------------------------------------

def splitSegment(path, seg):
	nodes = path.nodes
	startIdx = seg["onCurveStartIndex"]
	endIdx = seg["onCurveEndIndex"]

	if len(seg["offIndices"]) == 2:
		# --- Segmento curvo: subdividimos con De Casteljau ---
		i1, i2 = seg["offIndices"]
		p0 = nodes[startIdx].position
		p1 = nodes[i1].position
		p2 = nodes[i2].position
		p3 = nodes[endIdx].position

		offA, onA_ctrl, midOn, onB_ctrl, offB = deCasteljau(p0, p1, p2, p3, 0.5)

		# Reasignamos las posiciones de los off-curve existentes
		nodes[i1].position = offA
		nodes[i2].position = offB  # ojo: se reasigna después de insertar, ver abajo

		# Insertamos, en orden, después de i1: onA_ctrl (off), midOn (on-curve nuevo), onB_ctrl (off)
		# Construimos los nodos nuevos
		newOffA = GSNode(onA_ctrl, OFFCURVE)
		newOn = GSNode(midOn, CURVE)
		newOffB = GSNode(onB_ctrl, OFFCURVE)

		# Insertamos en orden inverso para no desordenar índices
		path.nodes.insert(i2, newOffB)
		path.nodes.insert(i2, newOn)
		path.nodes.insert(i2, newOffA)

	else:
		# --- Segmento recto: el nuevo punto queda exactamente sobre la línea ---
		p0 = nodes[startIdx].position
		p1 = nodes[endIdx].position
		mid = lerp(p0, p1, 0.5)
		newNode = GSNode(mid, LINE)
		path.nodes.insert(endIdx, newNode)


# ---------------------------------------------------------------------------
# Lógica principal
# ---------------------------------------------------------------------------

def pathsWithSelection(layer):
	"""Devuelve los GSPath que tienen al menos un nodo seleccionado."""
	selectedPaths = []
	for path in layer.paths:
		for node in path.nodes:
			if node.selected:
				selectedPaths.append(path)
				break
	return selectedPaths


def countPoints(paths):
	return sum(len(p.nodes) for p in paths)


def addPointsToPath(path, amount):
	for _ in range(amount):
		segments = getSegments(path)
		if not segments:
			break
		longest = max(segments, key=lambda s: segmentLength(path, s))
		splitSegment(path, longest)


# ---------------------------------------------------------------------------
# Interfaz (Vanilla)
# ---------------------------------------------------------------------------

class AddPointsUI(object):
	def __init__(self):
		self.layer = Glyphs.font.selectedLayers[0] if Glyphs.font.selectedLayers else None
		self.targetPaths = pathsWithSelection(self.layer) if self.layer else []

		w = vanilla.FloatingWindow((300, 140), "Añadir Puntos a Trazos")
		self.w = w

		if not self.targetPaths:
			w.msg = vanilla.TextBox((15, 15, -15, 40),
				"⚠️ No hay ningún trazo seleccionado.\nSelecciona un trazo (o sus nodos) y vuelve a intentar.")
			w.open()
			return

		total = countPoints(self.targetPaths)
		w.info = vanilla.TextBox((15, 15, -15, 20),
			"Trazos seleccionados: %d — Puntos actuales: %d" % (len(self.targetPaths), total))

		w.label = vanilla.TextBox((15, 45, 180, 20), "Cantidad de puntos a añadir:")
		w.amount = vanilla.EditText((200, 43, -15, 22), "1")

		w.applyButton = vanilla.Button((15, 85, -15, 22), "Aplicar", callback=self.apply)

		w.open()

	def apply(self, sender):
		try:
			amount = int(self.w.amount.get())
		except ValueError:
			Message("Valor inválido", "Ingresa un número entero.", OKButton="Ok")
			return

		if amount <= 0:
			self.w.close()
			return

		font = Glyphs.font
		font.disableUpdateInterface()
		try:
			for path in self.targetPaths:
				addPointsToPath(path, amount)
		finally:
			font.enableUpdateInterface()

		self.w.close()


AddPointsUI()
