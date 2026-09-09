#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Caso 03 - La comprobación que se encuentra a sí misma.

    python ejemplos/03_se_encuentra_a_si_misma.py

Una prueba verifica que el informe destaca los hallazgos graves buscando la
palabra "GRAVE" en el texto generado. Esa palabra ya viene dentro del mensaje
que escribe el propio sistema auditado, así que la prueba pasa con el destacado
completamente desactivado.

La prueba no encuentra el destacado: se encuentra a sí misma, reflejada en el
texto que audita.
"""

import sys

# El arnés ejemplos/degradar.py sustituye este False por True desde fuera.
DEGRADAR = False

DEGRADACION = "se desactiva el destacado de los hallazgos graves"


# ---------------------------------------------------------------------------
# El sistema auditado
# ---------------------------------------------------------------------------

# La marca estructural: el informe la pone delante de cada hallazgo grave, y
# solo ahí. Es lo que hay que comprobar, porque es lo único que el destacado
# produce y que nadie más puede producir por accidente.
MARCA = "!! "
SANGRIA = "   "


class Hallazgo(object):
    def __init__(self, identificador, severidad, mensaje):
        self.id = identificador
        self.severidad = severidad
        self.mensaje = mensaje


HALLAZGOS = [
    Hallazgo("H-01", "GRAVE",
             "el equipo resuelve nombres sin pasar por el filtro de la empresa"),
    Hallazgo("H-02", "MENOR",
             "la version instalada no es la ultima publicada"),
    # Y aquí está la trampa. Este mensaje lo escribe el sistema auditado, no la
    # prueba, y contiene la palabra que la prueba busca. Nadie lo puso ahí para
    # engañar a nadie: es el texto natural de un aviso del verificador.
    Hallazgo("H-03", "MENOR",
             "el verificador no pudo confirmar si H-01 sigue siendo GRAVE tras el ultimo cambio"),
]


def generar_informe(hallazgos, destacar=True):
    lineas = ["INFORME DE VERIFICACION", ""]
    for hallazgo in hallazgos:
        marca = MARCA if (destacar and hallazgo.severidad == "GRAVE") else SANGRIA
        lineas.append("%s%s %s" % (marca, hallazgo.id, hallazgo.mensaje))
    return "\n".join(lineas)


def informe(degradado):
    return generar_informe(HALLAZGOS, destacar=not degradado)


# ---------------------------------------------------------------------------
# El control con el defecto
# ---------------------------------------------------------------------------

def destaca_los_graves_con_defecto(texto):
    """Comprueba que el informe destaca lo grave... buscando una palabra.

    Es la comprobación más natural del mundo y no verifica nada: la palabra
    puede llegar al texto por el destacado, por el mensaje de un hallazgo, por
    un encabezado, por una nota al pie o por un comentario. La prueba no
    distingue de dónde vino.
    """
    return "GRAVE" in texto


def suite_con_defecto(degradado):
    return [
        ("el informe debe destacar los hallazgos graves",
         lambda: destaca_los_graves_con_defecto(informe(degradado)) is True),

        ("el informe debe incluir todos los hallazgos",
         lambda: all(h.id in informe(degradado) for h in HALLAZGOS)),

        ("el informe debe llevar encabezado",
         lambda: informe(degradado).startswith("INFORME DE VERIFICACION")),
    ]


# ---------------------------------------------------------------------------
# El control corregido
# ---------------------------------------------------------------------------

def ids_marcados(texto):
    """Devuelve los identificadores de las líneas que llevan la marca.

    Mira la forma, no el contenido: la marca solo cuenta si está en la columna
    donde el generador la pone. Una línea que mencione "!!" en medio de su
    mensaje no queda marcada por eso.

    En un informe de texto la forma es la columna. En código sería la
    estructura de la llamada, el orden de las operaciones o las clases del
    resalte, y siempre sobre el texto sin comentarios, porque un comentario
    también contiene palabras.
    """
    marcados = []
    for linea in texto.splitlines():
        if linea.startswith(MARCA):
            resto = linea[len(MARCA):]
            marcados.append(resto.split(" ", 1)[0])
    return marcados


def destaca_los_graves_corregido(texto, hallazgos):
    """Exige que el conjunto marcado sea exactamente el conjunto grave.

    Igualdad de conjuntos, no pertenencia: así una prueba tampoco pasa porque
    se marque todo, que es la otra manera de no destacar nada.
    """
    esperados = set(h.id for h in hallazgos if h.severidad == "GRAVE")
    return set(ids_marcados(texto)) == esperados


def suite_corregida(degradado):
    return [
        ("cada hallazgo grave debe llevar la marca estructural",
         lambda: destaca_los_graves_corregido(informe(degradado), HALLAZGOS) is True),

        ("ningun hallazgo menor debe llevar la marca",
         lambda: not any(h.id in ids_marcados(informe(degradado))
                         for h in HALLAZGOS if h.severidad != "GRAVE")),

        # Esta prueba fija por escrito el fallo que se corrigió, para que no
        # vuelva: H-03 dice "GRAVE" en su mensaje y no debe quedar marcado.
        ("un mensaje que contiene la palabra no debe quedar marcado por eso",
         lambda: "H-03" not in ids_marcados(informe(degradado))),

        ("el informe debe incluir todos los hallazgos",
         lambda: all(h.id in informe(degradado) for h in HALLAZGOS)),
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


def resumen(pruebas, anotar=False):
    fallos = correr(pruebas)
    total = len(pruebas)
    if fallos:
        linea = "  pruebas: %d fallo%s de %d" % (
            len(fallos), "" if len(fallos) == 1 else "s", total)
    else:
        linea = "  pruebas: %d de %d en verde" % (total, total)
    if anotar:
        linea = linea.ljust(38) + ("<-- detectado" if fallos else "<-- no detecto nada")
    print(linea)
    for nombre in fallos:
        print("             - " + nombre)
    return fallos


def demo():
    print("CASO 03 - La comprobacion que se encuentra a si misma")
    print()
    print("CONTROL CON DEFECTO")
    resumen(suite_con_defecto(degradado=False))
    print("  degradacion aplicada: " + DEGRADACION)
    resumen(suite_con_defecto(degradado=True), anotar=True)
    print()
    print("CONTROL CORREGIDO")
    resumen(suite_corregida(degradado=False))
    print("  degradacion aplicada: " + DEGRADACION)
    resumen(suite_corregida(degradado=True), anotar=True)
    print()
    print("El informe sin destacado, tal como lo aprobaba la prueba con defecto:")
    for linea in informe(degradado=True).splitlines():
        print("  |" + linea)
    print()
    print("Ni un solo hallazgo destacado, y la palabra GRAVE aparece igual, en")
    print("el mensaje de H-03, que lo escribio el sistema auditado.")


def main(argv):
    if len(argv) > 1 and argv[1] == "--pruebas":
        cual = argv[2] if len(argv) > 2 else "corregido"
        suite = suite_corregida if cual == "corregido" else suite_con_defecto
        fallos = resumen(suite(degradado=DEGRADAR))
        return 1 if fallos else 0
    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
