#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Caso 04 - Verde por vacío.

    python ejemplos/04_verde_por_vacio.py

Un control recorre el inventario de equipos y afirma que ninguno lleva
demasiado tiempo sin dar señales. Se le añade, con buen criterio, una exención
por rol: ciertos equipos no tienen por qué dar esa señal y aparecían como
hallazgo permanente.

El escenario de prueba tenía un solo equipo, y era justamente de un rol exento.
Al añadir la exención, la prueba se quedó sin sujetos que mirar y pasó a dar
verde por no haber revisado nada. La corrección introducía el defecto.
"""

import sys

# El arnés ejemplos/degradar.py sustituye este False por True desde fuera.
DEGRADAR = False

DEGRADACION = "todos los equipos dejan de dar senales (400 dias en silencio)"


# ---------------------------------------------------------------------------
# El inventario simulado
# ---------------------------------------------------------------------------

UMBRAL_DIAS = 14

# Las exenciones viven en la configuración declarada y traen su motivo escrito.
# Una exención sin motivo es una exención que nadie puede revisar. Ver el caso
# 05: lo excluido tiene que seguir siendo visible.
ROLES_EXENTOS = {
    "impresora": "no reporta estado por diseno",
    "sensor-ambiental": "solo transmite al despertar, cada varias semanas",
}


class Equipo(object):
    def __init__(self, identificador, rol, dias_sin_senal):
        self.id = identificador
        self.rol = rol
        self.dias_sin_senal = dias_sin_senal


def inventario(equipos, degradado):
    # La degradación deja a toda la flota en silencio. Es la avería que este
    # control existe para detectar; si las pruebas no se enteran, no lo detecta.
    if degradado:
        return [Equipo(e.id, e.rol, 400) for e in equipos]
    return list(equipos)


# El escenario de prueba real: un equipo, y del rol que acaba de quedar exento.
ESCENARIO_ORIGINAL = [
    Equipo("EQ-14", "impresora", 3),
]

FLOTA_SANA = [
    Equipo("EQ-14", "impresora", 3),
    Equipo("EQ-01", "portatil", 1),
    Equipo("EQ-02", "servidor", 0),
]

FLOTA_CON_UN_SILENCIOSO = [
    Equipo("EQ-14", "impresora", 3),
    Equipo("EQ-01", "portatil", 1),
    Equipo("EQ-07", "portatil", 62),
]


# ---------------------------------------------------------------------------
# El control con el defecto
# ---------------------------------------------------------------------------

def control_con_defecto(equipos):
    """CONFORME cuando ningún equipo revisado supera el umbral.

    La afirmación es universal —"ninguno de los equipos revisados tiene
    problemas"— y una afirmación universal es trivialmente cierta sobre un
    conjunto vacío. El control no distingue "los revisé todos y están bien" de
    "no revisé ninguno", y su mensaje de salida es el mismo en los dos casos.
    """
    revisados = [e for e in equipos if e.rol not in ROLES_EXENTOS]
    hallazgos = [e for e in revisados if e.dias_sin_senal > UMBRAL_DIAS]
    return {
        "estado": "NO CONFORME" if hallazgos else "CONFORME",
        "hallazgos": [e.id for e in hallazgos],
        "resumen": "equipos sin senal en mas de %d dias: %d" % (UMBRAL_DIAS, len(hallazgos)),
    }


def suite_con_defecto(degradado):
    """Las tres pruebas que existían, todas sobre el mismo escenario.

    Que las tres usen el único escenario disponible no es descuido: es lo
    normal. Por eso un cambio que reduce lo que se examina —una exención, un
    filtro, un umbral— puede vaciar de sujeto a la suite entera de una vez.
    """
    escenario = lambda: inventario(ESCENARIO_ORIGINAL, degradado)
    return [
        ("el control debe dar CONFORME en el escenario de prueba",
         lambda: control_con_defecto(escenario())["estado"] == "CONFORME"),

        ("el equipo exento no debe aparecer entre los hallazgos",
         lambda: "EQ-14" not in control_con_defecto(escenario())["hallazgos"]),

        ("el resumen debe mencionar el umbral configurado",
         lambda: str(UMBRAL_DIAS) in control_con_defecto(escenario())["resumen"]),
    ]


# ---------------------------------------------------------------------------
# El control corregido
# ---------------------------------------------------------------------------

def control_corregido(equipos):
    """Comprueba que hay sujeto antes de afirmar nada sobre él.

    Tres estados, no dos. SIN SUJETO no es un verde con matices: es la
    respuesta honesta a "revisé cero equipos", y hay que decirla con esas
    palabras porque de otro modo se lee como conforme.

    Los exentos van listados aparte con su motivo. Siguen visibles y
    auditables; simplemente no cuentan como hallazgo.
    """
    revisados = [e for e in equipos if e.rol not in ROLES_EXENTOS]
    exentos = [e for e in equipos if e.rol in ROLES_EXENTOS]
    excluidos = ["%s (%s): %s" % (e.id, e.rol, ROLES_EXENTOS[e.rol]) for e in exentos]

    if not revisados:
        # El recuento se redacta en singular o en plural segun el numero. Es la
        # linea que remata el informe, y un "1 elementos" invita a desconfiar
        # del control entero: ver el caso 05.
        if len(equipos) == 1:
            recuento = "el inventario trae un solo equipo y esta exento"
        else:
            recuento = "el inventario trae %d equipos y todos estan exentos" % len(equipos)
        return {
            "estado": "SIN SUJETO",
            "hallazgos": [],
            "excluidos": excluidos,
            "resumen": recuento + ": el control no reviso ninguno",
        }

    hallazgos = [e for e in revisados if e.dias_sin_senal > UMBRAL_DIAS]
    return {
        "estado": "NO CONFORME" if hallazgos else "CONFORME",
        "hallazgos": ["%s: %d dias sin senal" % (e.id, e.dias_sin_senal) for e in hallazgos],
        "excluidos": excluidos,
        "resumen": "equipos revisados: %d, umbral en dias: %d, hallazgos: %d" % (
            len(revisados), UMBRAL_DIAS, len(hallazgos)),
    }


def suite_corregida(degradado):
    """Cuatro pruebas. La primera es la que atrapa el verde por vacío; la
    segunda es la que se pone en rojo cuando la flota enmudece."""

    def escenario_sin_sujeto():
        resultado = control_corregido(inventario(ESCENARIO_ORIGINAL, degradado))
        return resultado["estado"] == "SIN SUJETO"

    def flota_sana_conforme():
        resultado = control_corregido(inventario(FLOTA_SANA, degradado))
        return resultado["estado"] == "CONFORME"

    def nombra_al_silencioso():
        resultado = control_corregido(inventario(FLOTA_CON_UN_SILENCIOSO, degradado))
        # El hallazgo nombra al equipo, no informa una cantidad: ver caso 05.
        return (resultado["estado"] == "NO CONFORME"
                and any(h.startswith("EQ-07") for h in resultado["hallazgos"]))

    def exentos_visibles_con_motivo():
        resultado = control_corregido(inventario(FLOTA_SANA, degradado))
        return any(e.startswith("EQ-14") and ROLES_EXENTOS["impresora"] in e
                   for e in resultado["excluidos"])

    return [
        ("un inventario donde todo esta exento debe dar SIN SUJETO, no CONFORME",
         escenario_sin_sujeto),
        ("una flota sana con equipos revisables debe dar CONFORME", flota_sana_conforme),
        ("un equipo silencioso debe aparecer nombrado en los hallazgos", nombra_al_silencioso),
        ("los exentos deben listarse aparte con su motivo", exentos_visibles_con_motivo),
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
    print("CASO 04 - Verde por vacio")
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
    print("Sobre el mismo inventario en silencio total, lo que dice cada uno:")
    silencioso = inventario(ESCENARIO_ORIGINAL, degradado=True)
    con_defecto = control_con_defecto(silencioso)
    corregido = control_corregido(silencioso)
    print("  con defecto: %-11s  %s" % (con_defecto["estado"], con_defecto["resumen"]))
    print("  corregido:   %-11s  %s" % (corregido["estado"], corregido["resumen"]))


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
