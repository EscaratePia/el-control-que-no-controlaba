#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Caso 01 - Sin respuesta no es evidencia de nada.

    python ejemplos/01_sin_respuesta.py

Un comprobador de resolución de nombres que trata "cero respuestas" como
"bloqueado". El dominio elegido para la prueba no existe, así que ninguna de
las dos vías devuelve direcciones y el control da conforme sin haber
comprobado nada.

El fallo no está en el código, que hace exactamente lo que dice. Está en que la
evidencia elegida —una ausencia— no distingue entre las dos explicaciones
posibles: el filtro lo bloqueó, o el dominio no existe.
"""

import sys

# El arnés ejemplos/degradar.py sustituye este False por True desde fuera, para
# comprobar que las pruebas del control corregido se ponen en rojo cuando el
# filtro deja de bloquear. Ver ejemplos/README.md.
DEGRADAR = False

DEGRADACION = "el filtro deja de bloquear (su lista de dominios queda vacia)"


# ---------------------------------------------------------------------------
# El mundo simulado
# ---------------------------------------------------------------------------

CENTINELA = "0.0.0.0"  # dirección que algunos filtros devuelven al bloquear

# El dominio que se eligió para la prueba. Es de publicidad, y las listas
# cargadas en el filtro son de suplantación de identidad y programas
# maliciosos: ninguna lo iba a bloquear jamás. Además no existe, así que
# tampoco resuelve por la vía de referencia.
DOMINIO_DE_PRUEBA = "anuncios-de-prueba.invalido"

# Un dominio que sí existe y sí está en una lista cargada. Es el señuelo que la
# comprobación necesitaba desde el principio: sin un dominio que exista, el
# bloqueo no se puede distinguir de la inexistencia.
DOMINIO_SENUELO = "senuelo-listado.invalido"

# Un dominio corriente: existe y nadie lo bloquea.
DOMINIO_CORRIENTE = "sitio-cualquiera.invalido"


class TiempoAgotado(Exception):
    """El resolvedor no contestó. No es lo mismo que contestar "nada"."""


class Mundo(object):
    def __init__(self, bloqueados, filtro_responde=True):
        # dominio -> direcciones reales, iguales por cualquier vía legítima
        self.existentes = {
            DOMINIO_SENUELO: ["203.0.113.10"],
            DOMINIO_CORRIENTE: ["203.0.113.20"],
        }
        self.bloqueados = set(bloqueados)
        self.filtro_responde = filtro_responde

    def consultar(self, dominio, via):
        if via == "filtro":
            if not self.filtro_responde:
                raise TiempoAgotado("el filtro no contesto")
            if dominio in self.bloqueados:
                # Este filtro bloquea respondiendo que el dominio no existe, que
                # es lo más común. Es decir: bloquea devolviendo cero
                # direcciones, exactamente lo mismo que devuelve un dominio que
                # de verdad no existe. De ahí viene todo el problema.
                return []
            return list(self.existentes.get(dominio, []))
        # Vía de referencia: un resolvedor público, sin filtrar.
        return list(self.existentes.get(dominio, []))


def mundo(degradado, filtro_responde=True):
    # La degradación deja la lista de bloqueo vacía: el filtro sigue en pie,
    # sigue respondiendo, y ya no bloquea nada. Es la avería que este control
    # existe para detectar.
    bloqueados = [] if degradado else [DOMINIO_SENUELO]
    return Mundo(bloqueados, filtro_responde=filtro_responde)


# ---------------------------------------------------------------------------
# El control con el defecto
# ---------------------------------------------------------------------------

def control_con_defecto(mundo, dominio):
    """Da CONFORME cuando el filtro no devuelve direcciones.

    La línea que decide se lee como una comprobación: si el filtro no me
    entrega direcciones, es que lo está bloqueando. Pero "no me entrega
    direcciones" es también lo que pasa cuando el dominio no existe, cuando hay
    un error de configuración y cuando la consulta se pierde. El control no
    comprueba: supone.
    """
    try:
        respuestas = mundo.consultar(dominio, via="filtro")
    except TiempoAgotado:
        return "NO CONFORME"
    bloquea = len(respuestas) == 0 or CENTINELA in respuestas
    return "CONFORME" if bloquea else "NO CONFORME"


def suite_con_defecto(degradado):
    """Las pruebas que existían. Las tres pasan, y las tres seguirán pasando.

    Ninguna es tonta: comprueban el camino feliz, el camino contrario y el
    error. Lo que no hace ninguna es preguntarse si el verde del camino feliz
    tiene alguna causa además del bloqueo.
    """
    return [
        ("con el filtro activo, el dominio de prueba debe dar CONFORME",
         lambda: control_con_defecto(mundo(degradado), DOMINIO_DE_PRUEBA) == "CONFORME"),

        ("un dominio corriente que si resuelve debe dar NO CONFORME",
         lambda: control_con_defecto(mundo(degradado), DOMINIO_CORRIENTE) == "NO CONFORME"),

        ("si el filtro no responde, el control no debe dar CONFORME",
         lambda: control_con_defecto(mundo(degradado, filtro_responde=False),
                                     DOMINIO_DE_PRUEBA) != "CONFORME"),
    ]


# ---------------------------------------------------------------------------
# El control corregido
# ---------------------------------------------------------------------------

def control_corregido(mundo, dominio):
    """Exige una señal positiva de bloqueo, y admite no poder concluir.

    La señal positiva puede ser el centinela, o el contraste entre las dos
    vías: el dominio resuelve por la referencia y el filtro no lo entrega. Eso
    ya no es una ausencia.

    Cuando no hay contraste posible —el dominio no resuelve por ninguna vía— la
    respuesta correcta no es verde ni rojo: es NO CONCLUYENTE, dicho con esas
    palabras y con el motivo al lado, porque un no concluyente silencioso se
    lee como un verde.
    """
    try:
        por_el_filtro = mundo.consultar(dominio, via="filtro")
        por_referencia = mundo.consultar(dominio, via="referencia")
    except TiempoAgotado:
        return ("NO CONCLUYENTE", "el filtro no respondio: no hay evidencia de nada")

    if CENTINELA in por_el_filtro:
        return ("CONFORME", "el filtro devolvio la direccion centinela")

    # Antes de interpretar un silencio del filtro hay que saber si el dominio
    # habla. Si no resuelve ni por la vía sin filtrar, su silencio no dice nada
    # sobre el filtro.
    if not por_referencia:
        return ("NO CONCLUYENTE",
                "el dominio de prueba no resuelve por ninguna via: no se puede "
                "distinguir un bloqueo de un dominio que no existe")

    if not por_el_filtro:
        return ("CONFORME",
                "el dominio resuelve por la via de referencia y el filtro no lo entrega")

    return ("NO CONFORME",
            "el filtro entrego las mismas direcciones que la via de referencia")


def suite_corregida(degradado):
    """Cuatro pruebas. La segunda es la que faltaba."""
    return [
        ("un dominio que existe y esta en la lista debe dar CONFORME",
         lambda: control_corregido(mundo(degradado), DOMINIO_SENUELO)[0] == "CONFORME"),

        # Este es el caso que el control con defecto llamaba CONFORME durante
        # semanas: el dominio de prueba original, que no existe.
        ("un dominio que no resuelve por ninguna via debe dar NO CONCLUYENTE",
         lambda: control_corregido(mundo(degradado), DOMINIO_DE_PRUEBA)[0] == "NO CONCLUYENTE"),

        ("un dominio corriente debe dar NO CONFORME",
         lambda: control_corregido(mundo(degradado), DOMINIO_CORRIENTE)[0] == "NO CONFORME"),

        ("si el filtro no responde, debe dar NO CONCLUYENTE y explicar por que",
         lambda: control_corregido(mundo(degradado, filtro_responde=False),
                                   DOMINIO_SENUELO) ==
                 ("NO CONCLUYENTE", "el filtro no respondio: no hay evidencia de nada")),
    ]


# ---------------------------------------------------------------------------
# Arnés de pruebas escrito a mano, para que se vea lo que hace
# ---------------------------------------------------------------------------

def correr(pruebas):
    fallos = []
    for nombre, prueba in pruebas:
        try:
            paso = bool(prueba())
        except Exception as error:  # una prueba que revienta es una prueba que falla
            paso = False
            nombre = "%s [excepcion: %s]" % (nombre, error)
        if not paso:
            fallos.append(nombre)
    return fallos


def informe(pruebas, anotar=False):
    fallos = correr(pruebas)
    total = len(pruebas)
    if fallos:
        linea = "  pruebas: %d fallo%s de %d" % (
            len(fallos), "" if len(fallos) == 1 else "s", total)
    else:
        linea = "  pruebas: %d de %d en verde" % (total, total)
    if anotar:
        # La anotación se decide leyendo el resultado real, nunca se escribe a
        # mano: un demo que afirma "detectado" sin comprobarlo es el caso 03.
        linea = linea.ljust(38) + ("<-- detectado" if fallos else "<-- no detecto nada")
    print(linea)
    for nombre in fallos:
        print("             - " + nombre)
    return fallos


def demo():
    print("CASO 01 - Sin respuesta no es evidencia de nada")
    print()
    print("CONTROL CON DEFECTO")
    informe(suite_con_defecto(degradado=False))
    print("  degradacion aplicada: " + DEGRADACION)
    informe(suite_con_defecto(degradado=True), anotar=True)
    print()
    print("CONTROL CORREGIDO")
    informe(suite_corregida(degradado=False))
    print("  degradacion aplicada: " + DEGRADACION)
    informe(suite_corregida(degradado=True), anotar=True)
    print()
    print("El control con defecto sobrevive a que el filtro deje de bloquear")
    print("porque su verde nunca dependio del bloqueo: dependia de una ausencia")
    print("de respuesta que el dominio de prueba producia por si solo.")


def main(argv):
    # Modo para el arnés externo: corre una sola suite y devuelve 0 o 1.
    if len(argv) > 1 and argv[1] == "--pruebas":
        cual = argv[2] if len(argv) > 2 else "corregido"
        suite = suite_corregida if cual == "corregido" else suite_con_defecto
        fallos = informe(suite(degradado=DEGRADAR))
        return 1 if fallos else 0
    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
