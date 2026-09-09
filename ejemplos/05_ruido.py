#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Caso 05 - Un control que reporta ruido deja de leerse.

    python ejemplos/05_ruido.py

Dos partes en el mismo archivo, porque son el mismo problema visto dos veces.

Parte A: un hallazgo compara contenido pero informa cantidades, y acaba
diciendo "1 regla en el sistema, esperada 1 declarada". El mismo número a
ambos lados, marcado como problema. Quien lo lee concluye que el control está
roto.

Parte B: un servidor que por su función nunca va a generar el tráfico que el
control busca aparece como hallazgo todos los días. Comportamiento esperado
reportado como anomalía, indefinidamente.

El ruido no es un defecto estético. Un informe que trae siempre el mismo
hallazgo esperable deja de leerse, y entonces tampoco sirve para el hallazgo
real.
"""

import sys

# El arnés ejemplos/degradar.py sustituye este False por True desde fuera.
DEGRADAR = False

DEGRADACION = "el comparador deja de mirar el contenido y solo compara cantidades"


# ---------------------------------------------------------------------------
# El sistema simulado
# ---------------------------------------------------------------------------

REGLAS_DECLARADAS = [
    "bloquear:suplantacion-de-identidad",
    "permitir:actualizaciones-del-sistema",
]

# Misma cantidad que lo declarado, distinto contenido: una regla cambió de
# nombre en el sistema y nadie actualizó lo declarado. Este es el desvío que
# hay que poder leer en el informe.
REGLAS_EN_EL_SISTEMA = [
    "bloquear:programas-maliciosos",
    "permitir:actualizaciones-del-sistema",
]

REGLAS_QUE_COINCIDEN = list(REGLAS_DECLARADAS)

REGLAS_CON_UNA_DE_MAS = REGLAS_DECLARADAS + ["permitir:todo-lo-demas"]


class Servidor(object):
    def __init__(self, identificador, rol, consultas_al_filtro):
        self.id = identificador
        self.rol = rol
        self.consultas_al_filtro = consultas_al_filtro


# La exención vive en la configuración declarada, con su motivo escrito, y no
# en una heurística dentro del código ("si el nombre empieza por SRV y no tiene
# consultas, callarlo"). Una heurística no se puede auditar ni discutir: hay
# que leer el código para saber qué se está ocultando.
EXENCIONES_DECLARADAS = {
    "SRV-03": "retransmisor de correo: no resuelve nombres por el filtro",
}

SERVIDORES = [
    Servidor("SRV-01", "puesto de trabajo", 4120),
    Servidor("SRV-02", "puesto de trabajo", 3880),
    Servidor("SRV-03", "retransmisor de correo", 0),
]


# ---------------------------------------------------------------------------
# El control con el defecto
# ---------------------------------------------------------------------------

def comparar_reglas(en_el_sistema, declaradas, degradado):
    """Devuelve (sobran, faltan) mirando el contenido.

    Degradado, compara cantidades: dos listas del mismo tamaño le parecen
    iguales aunque no tengan una sola regla en común. Es la avería que el
    control existe para detectar.
    """
    if degradado:
        if len(en_el_sistema) == len(declaradas):
            return ([], [])
        return (en_el_sistema[len(declaradas):], declaradas[len(en_el_sistema):])
    sobran = [r for r in en_el_sistema if r not in declaradas]
    faltan = [r for r in declaradas if r not in en_el_sistema]
    return (sobran, faltan)


def informe_con_defecto(en_el_sistema, declaradas, servidores, degradado):
    """Detecta bien y comunica mal, que también deja al control sin función.

    El desvío se detecta comparando contenido —eso está bien— pero el hallazgo
    se redacta con cantidades. Cuando el contenido difiere y la cantidad
    coincide, el informe dice "1 y 1" y marca eso como problema: el lector
    concluye que el roto es el control, y deja de mirarlo.

    Y abajo, el segundo hallazgo: SRV-03 no consulta al filtro porque es un
    retransmisor de correo y nunca lo va a hacer. Aparece todos los días.
    """
    lineas = ["DESVIOS DE CONFIGURACION"]

    sobran, faltan = comparar_reglas(en_el_sistema, declaradas, degradado)
    if sobran or faltan:
        lineas.append("  desvio de reglas: %d en el sistema, esperadas %d declaradas"
                      % (len(en_el_sistema), len(declaradas)))

    for servidor in servidores:
        if servidor.consultas_al_filtro == 0:
            lineas.append("  el servidor %s no envio consultas al filtro" % servidor.id)

    if len(lineas) == 1:
        lineas.append("  sin desvios")
    return "\n".join(lineas)


def suite_con_defecto(degradado):
    """Tres pruebas verdes que nunca ejercitan el caso interesante.

    Ninguna prueba el desvío de contenido con la misma cantidad a ambos lados,
    que es justamente el único caso donde comparar cantidades y comparar
    contenido dan respuestas distintas. Por eso un comparador que solo cuente
    las pasa las tres.
    """
    coinciden = lambda: informe_con_defecto(
        REGLAS_QUE_COINCIDEN, REGLAS_DECLARADAS, SERVIDORES, degradado)
    con_una_de_mas = lambda: informe_con_defecto(
        REGLAS_CON_UNA_DE_MAS, REGLAS_DECLARADAS, SERVIDORES, degradado)

    return [
        ("si el sistema coincide con lo declarado, no debe haber desvio de reglas",
         lambda: "desvio de reglas" not in coinciden()),

        ("si sobra una regla, el informe debe reportar el desvio",
         lambda: "desvio de reglas" in con_una_de_mas()),

        ("el informe debe reportar los servidores sin consultas al filtro",
         lambda: "SRV-03" in coinciden()),
    ]


# ---------------------------------------------------------------------------
# El control corregido
# ---------------------------------------------------------------------------

def informe_corregido(en_el_sistema, declaradas, servidores, degradado):
    """Nombra lo que sobra y lo que falta, y declara lo que excluye.

    Dos cambios, uno por cada parte del caso:

    - Los hallazgos citan el texto exacto de cada regla. Un número no permite
      actuar; un nombre sí. Y de paso desaparece el hallazgo "1 contra 1", que
      sonaba a control averiado.

    - Las exenciones salen de la configuración declarada y viajan en el
      informe, en su propia sección y con su motivo. Un control que calla lo
      que excluye es peor que uno que no excluye nada: el lector no tiene
      manera de saber que SRV-03 quedó fuera, ni de discutirlo.
    """
    hallazgos = []

    sobran, faltan = comparar_reglas(en_el_sistema, declaradas, degradado)
    for regla in sobran:
        hallazgos.append('  regla presente en el sistema y no declarada: "%s"' % regla)
    for regla in faltan:
        hallazgos.append('  regla declarada y ausente del sistema: "%s"' % regla)

    for servidor in servidores:
        if servidor.id in EXENCIONES_DECLARADAS:
            continue
        if servidor.consultas_al_filtro == 0:
            hallazgos.append("  el servidor %s no envio consultas al filtro" % servidor.id)

    lineas = ["DESVIOS DE CONFIGURACION"]
    lineas.extend(hallazgos or ["  sin desvios"])

    excluidos = [s for s in servidores if s.id in EXENCIONES_DECLARADAS]
    if excluidos:
        lineas.append("")
        lineas.append("EXCLUIDOS (declarados en la configuracion, no cuentan como hallazgo)")
        for servidor in excluidos:
            lineas.append("  %s: %s" % (servidor.id, EXENCIONES_DECLARADAS[servidor.id]))
    return "\n".join(lineas)


def suite_corregida(degradado):
    """Cuatro pruebas. La primera es la que faltaba: mismo número de reglas a
    ambos lados y contenido distinto."""

    mismo_numero = lambda: informe_corregido(
        REGLAS_EN_EL_SISTEMA, REGLAS_DECLARADAS, SERVIDORES, degradado)
    coinciden = lambda: informe_corregido(
        REGLAS_QUE_COINCIDEN, REGLAS_DECLARADAS, SERVIDORES, degradado)

    def nombra_lo_que_sobra_y_lo_que_falta():
        texto = mismo_numero()
        return ('"bloquear:programas-maliciosos"' in texto
                and '"bloquear:suplantacion-de-identidad"' in texto)

    def sin_desvios_cuando_coincide():
        return "sin desvios" in coinciden()

    def el_exento_no_es_hallazgo():
        texto = coinciden()
        desvios = texto.split("EXCLUIDOS")[0]
        return "SRV-03" not in desvios

    def el_exento_aparece_con_su_motivo():
        texto = coinciden()
        return "EXCLUIDOS" in texto and EXENCIONES_DECLARADAS["SRV-03"] in texto

    return [
        ("con la misma cantidad y distinto contenido, debe nombrar ambas reglas",
         nombra_lo_que_sobra_y_lo_que_falta),
        ("si el sistema coincide con lo declarado, debe decir sin desvios",
         sin_desvios_cuando_coincide),
        ("el servidor exento no debe aparecer entre los desvios", el_exento_no_es_hallazgo),
        ("el servidor exento debe aparecer en excluidos con su motivo",
         el_exento_aparece_con_su_motivo),
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
    print("CASO 05 - Un control que reporta ruido deja de leerse")
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
    print("El mismo desvio, contado de las dos maneras:")
    print()
    for linea in informe_con_defecto(REGLAS_EN_EL_SISTEMA, REGLAS_DECLARADAS,
                                     SERVIDORES, degradado=False).splitlines():
        print("  |" + linea)
    print()
    for linea in informe_corregido(REGLAS_EN_EL_SISTEMA, REGLAS_DECLARADAS,
                                   SERVIDORES, degradado=False).splitlines():
        print("  |" + linea)


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
