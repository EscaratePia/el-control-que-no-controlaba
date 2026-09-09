# Ejemplos ejecutables

Cinco casos, uno por cada trampa del [README principal](../README.md), más el
arnés de degradación.

Los casos son reales; el código que los ilustra está escrito desde cero para
este repositorio. Sin dependencias fuera de la biblioteca estándar y sin marco
de pruebas: la comprobación se hace a mano para que se vea lo que hace.

## Los cinco casos

```
python ejemplos/01_sin_respuesta.py            Sin respuesta no es evidencia de nada
python ejemplos/02_momento_equivocado.py       Una comprobación correcta en el momento equivocado
python ejemplos/03_se_encuentra_a_si_misma.py  La comprobación que se encuentra a sí misma
python ejemplos/04_verde_por_vacio.py          Verde por vacío
python ejemplos/05_ruido.py                    Un control que reporta ruido
```

Cada archivo tiene la misma estructura: un control con el defecto y sus pruebas,
que pasan; la degradación, que rompe a propósito lo que el control dice
verificar; y el control corregido con sus pruebas, que ahora sí se ponen en rojo
con la misma degradación.

La salida es el contraste:

```
CONTROL CON DEFECTO
  pruebas: 3 de 3 en verde
  degradacion aplicada: el filtro deja de bloquear (su lista de dominios queda vacia)
  pruebas: 3 de 3 en verde            <-- no detecto nada

CONTROL CORREGIDO
  pruebas: 4 de 4 en verde
  degradacion aplicada: el filtro deja de bloquear (su lista de dominios queda vacia)
  pruebas: 1 fallo de 4               <-- detectado
             - un dominio que existe y esta en la lista debe dar CONFORME
```

Los comentarios de cada archivo explican por qué, no qué. Se pueden leer sin
haber leído el README.

## El arnés

`ejemplos/degradar.py` no sabe nada de este repositorio ni de Python. Necesita
tres cosas: un archivo de texto, una sustitución que rompa algo, y un comando
que devuelva cero cuando las pruebas pasan.

```
python ejemplos/degradar.py \
    --archivo  src/control.py \
    --buscar   "if respuestas == []:" \
    --poner    "if False:" \
    --comando  "pytest tests/test_control.py"
```

Aplica la degradación, corre el comando, comprueba que ahora falla, y restaura
el archivo pase lo que pase. Sirve para cualquier proyecto y cualquier lenguaje:
el comando puede ser `go test ./...`, `npm test`, `dotnet test` o un guion
propio.

Códigos de salida, pensados para encadenarlo en una tubería:

| código | significado |
| --- | --- |
| `0` | **detectado**: las pruebas se pusieron en rojo |
| `1` | **no detectado**: pasaron en verde sobre código roto a propósito |
| `2` | error de uso |
| `3` | **no se encontró qué degradar**: el texto a sustituir no está en el archivo |
| `4` | **no concluyente**: fallaron, pero por lo que parece un error de carga o compilación |

Los tres últimos vienen de fallos reales usándolo:

- Restaura siempre —también si el comando revienta o si se interrumpe con
  Ctrl+C— y escribe un respaldo junto al archivo mientras dura la degradación.
  Dejar el código degradado es peor que no tener la herramienta.
- Si el texto a sustituir no aparece, no se rompió nada, y el verde del comando
  no significaría nada. Sería la sexta trampa, dentro de la herramienta escrita
  para encontrar las cinco. Por eso falla en vez de seguir.
- Un rojo por error de sintaxis no es un rojo por detección. Cuando la salida
  sugiere un fallo de carga o compilación, lo dice en vez de anotarse el punto.

## Los ejemplos, con el arnés por fuera

Cada caso lleva una constante `DEGRADAR = False` justamente para esto, y un modo
`--pruebas` que devuelve cero o uno según la suite elegida:

```
# el control corregido detecta la degradación: código 0
python ejemplos/degradar.py -a ejemplos/01_sin_respuesta.py \
    -b "DEGRADAR = False" -p "DEGRADAR = True" \
    -c "python ejemplos/01_sin_respuesta.py --pruebas corregido"

# el control con defecto no se entera: código 1
python ejemplos/degradar.py -a ejemplos/01_sin_respuesta.py \
    -b "DEGRADAR = False" -p "DEGRADAR = True" \
    -c "python ejemplos/01_sin_respuesta.py --pruebas defectuoso"
```

Es el mismo procedimiento que encontró los cinco fallos originales, corriendo
sobre los cinco fallos originales.
