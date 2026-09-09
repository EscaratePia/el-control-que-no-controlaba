#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Caso 02 - Una comprobación correcta en el momento equivocado.

    python ejemplos/02_momento_equivocado.py

Un componente fija una configuración, la lee de vuelta —correctamente— y
declara éxito. Otro proceso la borra un instante después. La lectura de vuelta
no mentía: era verdadera cuando se hizo y falsa noventa segundos más tarde.

El tiempo aquí es un reloj falso. Todo el ejemplo es instantáneo: una prueba
que necesita esperar para comprobar algo es una prueba que nadie va a correr.
"""

import sys

# El arnés ejemplos/degradar.py sustituye este False por True desde fuera.
DEGRADAR = False

DEGRADACION = "la configuracion deja de persistir (se borra tras cada escritura)"


# ---------------------------------------------------------------------------
# El reloj falso
# ---------------------------------------------------------------------------

class Reloj(object):
    """Un reloj que avanza porque alguien se lo pide, no porque pase el tiempo.

    Los eventos programados se disparan al avanzar. Así se puede escribir "y
    noventa segundos después el servicio borró la configuración" sin que la
    prueba tarde noventa segundos, ni dependa de la carga de la máquina que la
    corre.
    """

    def __init__(self):
        self.ahora = 0
        self._eventos = []   # [instante, orden, funcion]
        self._orden = 0

    def programar(self, dentro_de, funcion):
        self._orden += 1
        self._eventos.append([self.ahora + dentro_de, self._orden, funcion])

    def avanzar(self, segundos):
        destino = self.ahora + segundos
        while True:
            listos = [e for e in self._eventos if e[0] <= destino]
            if not listos:
                break
            # El orden de llegada desempata: dos eventos en el mismo segundo
            # tienen que ocurrir siempre en el mismo orden, o la prueba deja de
            # ser reproducible.
            evento = min(listos, key=lambda e: (e[0], e[1]))
            self._eventos.remove(evento)
            self.ahora = evento[0]
            evento[2]()
        self.ahora = destino


# ---------------------------------------------------------------------------
# El equipo simulado
# ---------------------------------------------------------------------------

ARRANQUE_DEL_SERVICIO = 90     # segundos que tarda el servicio de red en arrancar
RETARDO_DEGRADADO = 5          # cuánto tarda en borrar, ya degradado

CONFIGURACION = "192.0.2.53"   # la dirección del filtro que hay que dejar puesta


class Equipo(object):
    def __init__(self, reloj, degradado=False, rechaza_escritura=False):
        self.reloj = reloj
        self.configuracion = None
        self.bitacora = []
        self.degradado = degradado
        self.rechaza_escritura = rechaza_escritura

    def escribir(self, valor, motivo="configuracion escrita"):
        if self.rechaza_escritura:
            raise PermissionError("el almacen rechazo la escritura")
        self.configuracion = valor
        self.bitacora.append((self.reloj.ahora, motivo))
        if self.degradado:
            # DEGRADACIÓN: el borrado deja de ser un episodio del arranque y
            # pasa a ocurrir tras cada escritura. Es exactamente lo que este
            # componente dice garantizar —que la configuración queda puesta— y
            # por eso es lo que hay que romper para probarlo.
            self.reloj.programar(RETARDO_DEGRADADO, self._borrar)

    def leer(self):
        return self.configuracion

    def _borrar(self):
        self.configuracion = None
        self.bitacora.append((self.reloj.ahora, "borrada por el servicio de red"))


def equipo_que_arranca(reloj, degradado, rechaza_escritura=False):
    """El equipo del caso real: el servicio borra la configuración al arrancar.

    La tarea programada se dispara antes de que el servicio termine de
    inicializarse. Nadie hizo nada mal; simplemente el orden no está
    garantizado, y no lo va a estar nunca.
    """
    equipo = Equipo(reloj, degradado=degradado, rechaza_escritura=rechaza_escritura)
    reloj.programar(ARRANQUE_DEL_SERVICIO, equipo._borrar)
    return equipo


def equipo_estable(reloj, degradado):
    """Un equipo donde nadie más toca la configuración."""
    return Equipo(reloj, degradado=degradado)


# ---------------------------------------------------------------------------
# El componente con el defecto
# ---------------------------------------------------------------------------

def componente_con_defecto(equipo, valor=CONFIGURACION):
    """Escribe, lee de vuelta y declara éxito.

    La lectura de vuelta es correcta: comprueba de verdad que la escritura
    llegó. El problema es que responde una pregunta más pequeña de la que el
    mensaje de éxito da a entender. Comprueba "la escritura llegó", y se lee
    como "la configuración está puesta".
    """
    try:
        equipo.escribir(valor)
    except PermissionError as error:
        return {"exito": False, "motivo": str(error)}

    if equipo.leer() != valor:
        return {"exito": False, "motivo": "la lectura de vuelta no coincide"}

    return {"exito": True, "motivo": "configuracion repuesta y verificada"}


def suite_con_defecto(degradado):
    """Tres pruebas honestas sobre una afirmación demasiado grande."""

    def declara_exito():
        reloj = Reloj()
        equipo = equipo_que_arranca(reloj, degradado)
        return componente_con_defecto(equipo)["exito"] is True

    def lectura_de_vuelta():
        reloj = Reloj()
        equipo = equipo_que_arranca(reloj, degradado)
        componente_con_defecto(equipo)
        return equipo.leer() == CONFIGURACION

    def escritura_rechazada():
        reloj = Reloj()
        equipo = equipo_que_arranca(reloj, degradado, rechaza_escritura=True)
        return componente_con_defecto(equipo)["exito"] is False

    return [
        ("tras fijar la configuracion, el componente debe declarar exito", declara_exito),
        ("la lectura de vuelta debe devolver lo que se escribio", lectura_de_vuelta),
        ("si el almacen rechaza la escritura, debe declarar fallo", escritura_rechazada),
    ]


# ---------------------------------------------------------------------------
# El componente corregido
# ---------------------------------------------------------------------------

VENTANA = 300        # cuánto se vigila después de actuar, en segundos
INTERVALO = 30       # cada cuánto se vuelve a mirar
CHEQUEOS_ESTABLES = 2  # cuántas miradas seguidas sin reponer hacen falta


def componente_corregido(equipo, reloj, valor=CONFIGURACION):
    """Escribe y vigila una ventana, reponiendo cada vez que se pierde.

    La corrección no fue acertar el momento sino dejar de depender de él. Con
    vigilancia, que el disparador llegue temprano deja de importar.

    El éxito exige además que la configuración se haya quedado quieta: si en
    las últimas miradas seguía haciendo falta reponerla, el equipo no está
    configurado, está siendo sostenido a pulso. Eso es un fallo, y el mensaje
    lo dice.
    """
    try:
        equipo.escribir(valor)
    except PermissionError as error:
        return {"exito": False, "reposiciones": 0, "motivo": str(error)}

    reposiciones = 0
    seguidas_sin_reponer = 0

    for _ in range(VENTANA // INTERVALO):
        reloj.avanzar(INTERVALO)
        if equipo.leer() == valor:
            seguidas_sin_reponer += 1
            continue
        try:
            equipo.escribir(valor, motivo="configuracion repuesta por la vigilancia")
        except PermissionError as error:
            return {"exito": False, "reposiciones": reposiciones, "motivo": str(error)}
        reposiciones += 1
        seguidas_sin_reponer = 0

    if equipo.leer() != valor:
        return {"exito": False, "reposiciones": reposiciones,
                "motivo": "al cerrar la ventana la configuracion no estaba puesta"}

    if seguidas_sin_reponer < CHEQUEOS_ESTABLES:
        return {"exito": False, "reposiciones": reposiciones,
                "motivo": "la configuracion se sigue perdiendo al cerrar la ventana y "
                          "no llego a quedarse quieta; reposiciones: %d" % reposiciones}

    return {"exito": True, "reposiciones": reposiciones,
            "motivo": "configuracion estable durante la ventana de vigilancia"}


def suite_corregida(degradado):
    """Cuatro pruebas. Las dos primeras miran el final de la ventana, no el
    instante siguiente a la escritura."""

    def equipo_sin_interferencia():
        reloj = Reloj()
        equipo = equipo_estable(reloj, degradado)
        return componente_corregido(equipo, reloj)["exito"] is True

    def repone_lo_que_el_servicio_borra():
        reloj = Reloj()
        equipo = equipo_que_arranca(reloj, degradado)
        return componente_corregido(equipo, reloj)["exito"] is True

    def deja_rastro_de_cada_reposicion():
        reloj = Reloj()
        equipo = equipo_que_arranca(reloj, degradado)
        resultado = componente_corregido(equipo, reloj)
        repuestas = [m for _, m in equipo.bitacora if "repuesta" in m]
        # Que el número de líneas coincida con lo que el resultado declara: una
        # bitácora que no cuadra con el informe es otra forma de verde falso.
        return len(repuestas) == resultado["reposiciones"] >= 1

    def escritura_rechazada():
        reloj = Reloj()
        equipo = equipo_que_arranca(reloj, degradado, rechaza_escritura=True)
        return componente_corregido(equipo, reloj)["exito"] is False

    return [
        ("en un equipo estable, debe cerrar la ventana con exito", equipo_sin_interferencia),
        ("si el servicio borra la configuracion, debe reponerla y cerrar con exito",
         repone_lo_que_el_servicio_borra),
        ("la bitacora debe registrar cada reposicion", deja_rastro_de_cada_reposicion),
        ("si el almacen rechaza la escritura, debe declarar fallo", escritura_rechazada),
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
        linea = linea.ljust(38) + ("<-- detectado" if fallos else "<-- no detecto nada")
    print(linea)
    for nombre in fallos:
        print("             - " + nombre)
    return fallos


def bitacora_del_caso_real():
    """La bitácora que se veía: dos reposiciones correctas y el equipo sin filtro."""
    reloj = Reloj()
    equipo = equipo_que_arranca(reloj, degradado=False)
    componente_con_defecto(equipo)          # la tarea, disparada temprano
    reloj.avanzar(ARRANQUE_DEL_SERVICIO + 60)
    return equipo


def demo():
    print("CASO 02 - Una comprobacion correcta en el momento equivocado")
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
    print("Lo que el componente con defecto declaraba, y lo que quedaba despues:")
    equipo = bitacora_del_caso_real()
    for instante, mensaje in equipo.bitacora:
        print("  t+%3ds  %s" % (instante, mensaje))
    print("  t+%3ds  configuracion actual: %s" % (
        equipo.reloj.ahora, equipo.leer() or "ninguna"))


def main(argv):
    if len(argv) > 1 and argv[1] == "--pruebas":
        cual = argv[2] if len(argv) > 2 else "corregido"
        suite = suite_corregida if cual == "corregido" else suite_con_defecto
        fallos = informe(suite(degradado=DEGRADAR))
        return 1 if fallos else 0
    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
