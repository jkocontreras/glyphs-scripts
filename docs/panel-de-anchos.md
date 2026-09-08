# Panel de anchos — manual

Script de Glyphs 3 (`Script ▸ Panel de anchos`). Abre una ventana flotante que
se queda encima mientras trabajas en la fuente.

Sirve para una cosa concreta: **mantener el ancho bajo control en familias
Uniwidth y monoespaciadas**. Uniwidth significa que un mismo glifo mide igual en
todos los masters — cambia el peso, no el avance — y eso se rompe con facilidad
al dibujar. El panel primero te deja *mirar* dónde se rompió y solo después
*arreglarlo*.

La ventana está partida en dos mitades a propósito:

- **Medir** — no toca la fuente. Escribe informes en la ventana de macros.
- **Modificar** — cambia anchos en la fuente abierta, pero **nunca guarda el archivo**.

---

## Los tres controles de arriba (afectan a todo lo demás)

**Master**
Se llena con los masters de la fuente abierta y arranca en el que tienes activo.
Es el master sobre el que se mide y sobre el que se escribe. Excepción:
*Comparar masters* recorre todos los masters y no le hace caso a este menú
(aunque sí lo usa *Unificar*, como master de referencia).

**Glifos: Toda la fuente / Solo los seleccionados**
El alcance. "Solo los seleccionados" toma los glifos de las capas seleccionadas
en la ventana de fuente o en la pestaña de edición, sin repetir. Aplica a las
cuatro operaciones.

**Línea de información**
Se actualiza sola al cambiar master, alcance o la casilla de marcas. Dice cuántas
capas entran con esos ajustes y entre qué anchos se mueven, más cuántas quedaron
fuera. Es tu confirmación de que estás apuntando a lo que crees.

La casilla **Conservar marcas y glifos de ancho 0** (en la mitad de abajo, pero
manda también arriba) excluye las marcas combinantes — categoría `Mark`,
subcategoría `Nonspacing` — y cualquier capa que ya mida 0. Encendida por defecto:
una marca con ancho 560 rompe el posicionamiento.

---

## Medir

### Similares en el master  ·  hasta N pts

Contesta: *¿cuántos anchos distintos tengo en realidad, y cuáles son casi el mismo?*

Arma el histograma de anchos del master elegido (redondeando a entero e ignorando
siempre los de ancho 0), ordena los anchos **por población** y usa los más poblados
como picos. Cada ancho se pega al pico más cercano que esté dentro de la distancia
que escribiste; si no hay ninguno cerca, se vuelve un pico nuevo.

El informe trae los grupos con más de un ancho — los candidatos a colapsar a un
valor común — con el pico marcado y cuántos glifos hay en cada escalón, y al final
el total de anchos distintos y la lista de los que no tienen vecinos.

El campo **hasta N pts** es la distancia máxima; por defecto 10. Con un número
chico ves solo los desajustes finos (el glifo que quedó en 558 en vez de 560);
subiéndolo empiezas a ver la retícula real de la fuente. Tiene que ser 1 o más.

Es la herramienta de diagnóstico: no toca nada, solo te dice qué tan pareja está
la fuente antes de que decidas un valor para *Fijar mono*.

### El mapa: picos a la izquierda, glifos a la derecha

Medir también llena las dos tablas del centro de la ventana, que es donde se
trabaja de verdad.

**Izquierda — los picos.** Un renglón por pico, con cuántos glifos tiene el grupo
y cuántos colapsarían hacia él. Están los picos de todos los grupos, también los
anchos aislados (colapsan 0), así que la lista es el paisaje completo de anchos
del master, ordenado del más poblado al menos. El punto marca los grupos que
tienen algo que revisar.

**Derecha — los glifos de ese pico.** Al elegir un pico aparecen sus desviados
**dibujados**, con el nombre, su ancho, la diferencia en puntos y el pico hacia
el que irían. La miniatura sale de la capa del master elegido, así que estás
mirando el dibujo real, no un carácter de sistema. *Incluir los del pico* suma
los que ya están bien, para comparar.

Debajo, tres formas de sacar el grupo del panel:

- **Copiar nombres** — al portapapeles, uno por línea; sirve para un List Filter.
- **Seleccionar** — los marca en la ventana de fuente, para etiquetarlos con color.
- **Abrir en pestaña** — los abre en una pestaña de edición, dibujados y con su
  avance real, que es donde se corrigen.

Los tres trabajan sobre las filas que tengas marcadas a la derecha; si no marcas
ninguna, sobre todas las del grupo. Nada de esto modifica la fuente.

### Comparar masters

Contesta: *¿dónde se me rompió el Uniwidth?*

Recorre todos los masters con **tolerancia 0** — anchos distintos si no coinciden
al redondear a entero — y lista cada glifo cuyo ancho no calza en todos, con el
detalle master por master. Aparte lista los glifos que no tienen capa en algún
master, que es el otro modo de romperse.

Con un solo master te avisa y no hace nada. Es el botón por defecto de la ventana:
**Enter dispara esta medición**, nunca una modificación. Eso es deliberado.

---

## Modificar

Las dos operaciones de abajo cambian la fuente en memoria y **no guardan**. Revisa
y guarda tú. El deshacer se registra glifo por glifo, así que Cmd+Z no revierte
una pasada completa de un golpe: si vas a correrlo sobre toda la fuente, guarda antes.

### Ancho  ·  "usar el más ancho"

El valor que va a escribir *Fijar mono*. El botón lo llena con el ancho máximo de
las capas que hay en el alcance actual, **redondeado hacia arriba al múltiplo de 10**
— o sea, ninguna letra queda apretada y el número queda limpio.

### Centrar el dibujo en la caja

Al escribir el ancho nuevo, corre el dibujo horizontalmente para dejarlo centrado
en la caja resultante (desplazamiento puro, no deforma ni escala). Solo mueve las
capas que tienen dibujo. Afecta tanto a *Fijar mono* como a *Unificar*.

Ojo: centrar tira a la basura el espaciado que hayas hecho a mano. Úsalo al pasar
un diseño proporcional a mono, no sobre una mono ya espaciada.

### Fijar mono

Escribe el mismo ancho en todas las capas del alcance, dentro del master elegido.
Solo ese master. Es el paso de "esta fuente ahora es monoespaciada a N".

Informa cuántas capas modificó y cuántas dejó fuera por marcas o ancho 0.

### Unificar desde este master

El arreglo del Uniwidth. Toma el master elegido arriba como **referencia** y copia
el ancho de cada glifo hacia todos los demás masters. Salta las capas que ya
coinciden, así que solo mueve lo que estaba mal.

Es la contraparte de *Comparar masters*: primero miras la lista de inconsistentes,
decides qué master tiene el espaciado bueno, lo eliges arriba y unificas desde ahí.
Con un solo master te avisa y no hace nada.

---

## Un flujo que funciona

1. **Comparar masters** — ¿está roto el Uniwidth? ¿dónde?
2. Si está roto: elegir el master con el espaciado correcto y **Unificar desde este master**.
3. **Comparar masters** otra vez — debería quedar limpio.
4. **Similares en el master** con 5–10 pts — ¿quedan anchos que son casi el mismo?
5. Si hay que aplanar: seleccionar esos glifos, **usar el más ancho**, **Fijar mono**.
6. Revisar en la fuente y **guardar tú**.

## Los informes

Las cuatro operaciones abren la ventana de macros y escriben ahí su informe, así que
después de apretar cualquier botón tienes el resultado a la vista. Las dos que
modifican terminan siempre recordándote que el archivo no se guardó.

## Preferencias

Ancho, distancia, las dos casillas y el alcance se guardan en los defaults de
Glyphs bajo `contrafonts.anchos.` y vuelven como los dejaste la próxima vez.
El master no se guarda: siempre arranca en el que tengas activo.

## Relación con los otros dos scripts

- **Seleccionar por Ancho** — lee y selecciona en la ventana de fuente para
  etiquetar a mano; el panel informa en la ventana de macros y además modifica.
- **Volver Mono el Master** — es el antecesor de *Fijar mono*, con un solo master
  y sin la parte de medición.
