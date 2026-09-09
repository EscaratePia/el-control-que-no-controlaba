# El control que no controlaba

Cinco formas en que un control de seguridad dice la verdad a medias, con el fallo
real que enseñó cada una.

Trabajo en ciberseguridad, construyendo servicios de monitoreo gestionado y
protección de datos para empresas pequeñas y medianas. Estos criterios salieron
de operar esos controles, no de leer sobre ellos: cada uno viene de un caso en
que el informe decía verde y el sistema no estaba protegido.

---

## Por qué existe esto

Un control que no existe es un riesgo conocido. Alguien puede decidir asumirlo.

Un control que existe y dice verde sin haber comprobado nada es peor, porque
produce confianza. Cierra la pregunta. Nadie vuelve a mirar ahí.

Los cinco casos de abajo tienen algo en común: ninguno estaba mal escrito. Todos
comprobaban algo. Simplemente no comprobaban lo que su mensaje afirmaba, y en los
cinco hizo falta romper el código a propósito para darse cuenta.

---

## 1. Sin respuesta no es evidencia de nada

**El fallo.** Un instalador tenía que comprobar que el equipo resolvía nombres a
través del filtro de la empresa y no del resolvedor de su red local. Para eso
consultaba un dominio de prueba por los dos caminos y comparaba.

La comprobación decía, en esencia: si el filtro no devuelve direcciones, es que
lo está bloqueando.

```
bloquea = (respuestas.length == 0) || respuestas.contiene("0.0.0.0")
```

El dominio de prueba elegido no existía. El filtro lo reenvió, le respondieron
que no existe, y devolvió cero direcciones. Cero direcciones se tomó por bloqueo.
Verde.

Peor: el dominio era de publicidad y las listas configuradas eran de suplantación
de identidad y programas maliciosos. Ninguna lo iba a bloquear jamás. La
comprobación estaba condenada desde el principio y llevaba semanas dando
conforme.

**El criterio.** Una ausencia de respuesta no distingue entre «bloqueado» y «no
existe». Si el verde de un control descansa en que algo *no* pasó, ese control no
está comprobando: está suponiendo.

El verde tiene que exigir una señal positiva. Y cuando esa señal no se puede
obtener, la respuesta correcta no es verde ni rojo: es **no concluyente**, dicho
con esas palabras y explicando por qué.

---

## 2. Una comprobación correcta en el momento equivocado

**El fallo.** Un servicio de red borraba la configuración de nombres de su
interfaz al cerrarla y no la reponía al abrirla. Una tarea programada la volvía a
poner en cada arranque, la leía de vuelta para confirmar, y anotaba el éxito.

Tras un reinicio del equipo, la bitácora mostraba dos reposiciones correctas. Y
el equipo estaba sin filtro.

```
23:08:39  tarea:   configuracion repuesta (estaba: vacia)
23:09:24  tarea:   configuracion repuesta (estaba: vacia)
23:10:41  sistema: el servicio entro en estado corriendo
23:12:07  a mano:  sin configuracion
```

La tarea se disparó antes de que el servicio terminara de arrancar. Fijó la
configuración —correctamente— y el servicio la borró un minuto después al
inicializarse. La lectura de vuelta no mentía: era verdadera cuando se hizo y
falsa noventa segundos más tarde.

**El criterio.** Verificar un estado que otro proceso todavía puede cambiar
exige volver a mirar, no mirar mejor.

La corrección no fue acertar el momento sino dejar de depender de él: vigilar
durante un rato después de actuar, y corregir cada vez que se pierda. Cuando hay
vigilancia, que el disparador llegue temprano deja de importar.

---

## 3. La comprobación que se encuentra a sí misma

**El fallo.** Un informe tenía que destacar visualmente los hallazgos más graves.
La prueba comprobaba que el texto generado contuviera la palabra que marca esa
gravedad.

Pero esa palabra ya venía dentro del mensaje que escribía el propio verificador,
mucho antes de llegar al informe. La prueba pasaba en verde con el destacado
completamente desactivado.

Apareció dos veces más en el mismo proyecto, y siempre igual: una comprobación
por búsqueda de texto encontrando el texto que ella misma —o el sistema que
audita— había puesto ahí.

**El criterio.** Comprobar la presencia de una palabra no comprueba nada si esa
palabra puede llegar por otro camino.

La comprobación tiene que exigir la **forma** de lo que verifica: la estructura
de la llamada, el orden de las operaciones, las clases del resalte. Y sobre el
código sin comentarios, porque un comentario también contiene palabras.

---

## 4. Verde por vacío

**El fallo.** Un control revisaba todos los equipos de una red y avisaba de los
que llevaban tiempo sin dar señales. Se le añadió, con buen criterio, una lista de
exenciones: ciertos roles no tienen por qué dar esa señal y aparecían como
hallazgo permanente, que es ruido.

El escenario de prueba tenía un solo equipo, y era justamente de uno de los roles
exentos. Al añadir la exención, la prueba se quedó sin sujetos que mirar y pasó a
dar verde por no encontrar nada.

Se detectó al implementarlo, por suerte. La corrección introducía el defecto.

**El criterio.** Un conjunto vacío satisface cualquier afirmación universal.
«Ninguno de los equipos revisados tiene problemas» es trivialmente cierto cuando
no se revisó ninguno.

Toda prueba que recorra una colección debería comprobar además que la colección
no está vacía. Y todo cambio que reduzca lo que se examina —una exención, un
filtro, un umbral— obliga a revisar si las pruebas existentes siguen teniendo
sujeto.

---

## 5. Un control que reporta ruido deja de leerse

**El fallo.** Dos casos del mismo proyecto.

Un control informaba un desvío comparando cantidades donde comparaba contenido:
«1 regla en el sistema, esperada 1 regla declarada». El mismo número a ambos
lados, marcado como problema. Quien lo leía concluía que el control estaba roto.

Otro marcaba como hallazgo, todos los días, a servidores que por su función nunca
iban a generar el tráfico que el control buscaba. Comportamiento esperado
reportado como anomalía, indefinidamente.

**El criterio.** Un informe que trae siempre el mismo hallazgo esperable deja de
leerse, y entonces tampoco sirve para el hallazgo real. El ruido no es un defecto
estético: destruye la función del control.

Dos consecuencias prácticas. Los hallazgos deben **nombrar** lo que sobra o falta,
con su texto exacto, no informar cantidades. Y las exenciones legítimas deben
declararse en la configuración, no filtrarse con una heurística en el código.

Con un matiz que importa: **un control que calla lo que excluye es peor que uno
que no excluye nada.** Los exentos van listados en una sección aparte, con su
motivo. Siguen visibles y auditables; simplemente no cuentan como hallazgo.

---

## Cómo se encuentran estos fallos

Ninguno de los cinco se detectó leyendo el código. Los cinco aparecieron
rompiendo algo a propósito y comprobando si la prueba se enteraba.

El procedimiento es simple y vale la pena tenerlo como herramienta y no como
buena intención:

1. Elegir un comportamiento que la prueba dice verificar.
2. Romperlo deliberadamente en el código.
3. Ejecutar la prueba.
4. Si sigue en verde, la prueba no verificaba eso.

Cada degradación tarda minutos y responde una pregunta que de otro modo no se
responde nunca: *¿esta prueba detecta el fallo que dice detectar?*

En el proyecto del que salen estos casos, el arnés de degradación encontró huecos
reales en cuatro ocasiones distintas —incluido uno en la comprobación escrita
específicamente para evitar este problema.

---

## Lo que un informe tiene que declarar

Si un informe puede llegar a un cliente, a un auditor o simplemente a alguien que
no estuvo cuando se escribió, viaja solo. Tiene que decir en su propia cara qué
alcance tiene.

Cuatro cosas, siempre:

**Qué verifica.** La lista concreta, no una descripción general.

**Qué no verifica.** Esta es la que se omite, y es la que hace honesto al resto.
«Un resultado sin desvíos significa que la configuración coincide con lo
declarado al momento de la consulta. No significa que el sistema esté bien
configurado ni que nadie lo haya evadido.»

**Qué excluye y por qué.** Si el control ignora ciertos elementos, listarlos con
su motivo.

**De dónde salen sus umbrales.** Un número que vive en una bandera de línea de
comandos no es un compromiso: depende de quién ejecutó el comando, y dos personas
con distinto criterio obtienen resultados distintos sobre el mismo sistema. Los
umbrales pertenecen a la configuración declarada, y el informe debe decir si
fueron sobrescritos en esa corrida.

---

## Un corolario sobre los números medidos

Cuando un control declara un tiempo —cuánto tarda en detectar algo, cuánta ventana
de exposición hay— ese número acaba citado ante alguien.

Tres reglas que salieron de equivocarse en las tres:

- **Si lo medido no coincide con lo declarado, manda lo medido.** Hay que corregir
  el documento, no el número.
- **Un número medido en laboratorio es un piso, no un techo.** Y debe declarar
  dónde se midió: un servidor sin carga no predice un equipo de oficina
  arrancando con antivirus y actualizaciones.
- **La documentación no puede despegarse del código.** Si el umbral vive en una
  constante, la prueba debe comprobar que el texto declarado cita esa misma
  constante. Un número documentado que dejó de ser cierto es peor que no
  documentarlo.

---

## Y el criterio más general

Entre «el control existe», «el control se ejecuta» y «alguien se entera del
resultado» hay tres pasos.

Hasta el tercero, no protege a nadie.

---

## Sobre quien escribe esto

Trabajo en ciberseguridad: diseño y opero servicios de monitoreo gestionado y de
protección de datos para empresas pequeñas y medianas, en entornos sujetos a
normativa de tratamiento de datos personales.

Los casos de arriba vienen de construir controles de configuración y de uso para
infraestructura de red y filtrado de nombres de dominio, y de romperlos después
para comprobar que las pruebas los detectaban. Los ejemplos están anonimizados;
los fallos son reales y todos aparecieron en un sistema que ya estaba en
funcionamiento.

Hay mucho escrito sobre cómo construir controles. Bastante menos sobre cómo saber
si el que ya tienes está comprobando lo que dice comprobar.
