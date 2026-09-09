#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arnés de degradación: rompe algo a propósito y comprueba si las pruebas se
enteran.

    python ejemplos/degradar.py \
        --archivo src/control.py \
        --buscar  "if respuestas == []:" \
        --poner   "if False:" \
        --comando "pytest tests/test_control.py"

No sabe nada de Python ni de este repositorio. Necesita tres cosas: un archivo
de texto, una sustitución que rompa algo de verdad, y un comando que devuelva
cero cuando las pruebas pasan. Sirve igual para un proyecto en cualquier
lenguaje.

La pregunta que responde es una sola, y no se responde de ninguna otra forma:
¿esta prueba detecta el fallo que dice detectar?

Códigos de salida
    0  la degradación fue detectada: las pruebas se pusieron en rojo
    1  NO detectada: las pruebas siguieron en verde sobre código roto
    2  error de uso
    3  no se encontró qué degradar: el texto a sustituir no está en el archivo
    4  no concluyente: las pruebas fallaron, pero por lo que parece un error de
       carga o compilación, no por una comprobación
"""

import argparse
import os
import signal
import subprocess
import sys
import time

DETECTADO = 0
NO_DETECTADO = 1
ERROR_DE_USO = 2
NADA_QUE_DEGRADAR = 3
NO_CONCLUYENTE = 4

# Señales de que el comando ni siquiera llegó a ejecutar comprobaciones. Si la
# sustitución rompió la sintaxis, las pruebas fallan sin haber detectado nada:
# el rojo es del compilador, no de una aserción, y confundirlos es creer que la
# prueba vigila algo que no vigila.
SENALES_DE_CARGA = (
    "syntaxerror",
    "indentationerror",
    "taberror",
    "modulenotfounderror",
    "importerror",
    "cannot import name",
    "unexpected token",
    "unexpected end of input",
    "parse error",
    "error collecting",
    "collection error",
    "compilation terminated",
    "compilation failed",
    "cannot find symbol",
    "cannot find module",
    "command not found",
    "is not recognized as",
    "no such file or directory",
    "segmentation fault",
    # El intérprete de comandos traduce sus errores, y un comando mal escrito
    # devuelve un código distinto de cero igual que una prueba en rojo. Sin
    # estas líneas, un comando que ni siquiera existe se informaría como
    # degradación detectada.
    "no se reconoce como un comando",
    "orden no encontrada",
    "no se encuentra el archivo",
    "error de sintaxis",
)

SUFIJO_RESPALDO = ".degradar-respaldo"


class Degradacion(object):
    """Aplica la sustitución y garantiza la vuelta atrás.

    El original se guarda en memoria y también en un archivo de respaldo junto
    al degradado. El respaldo es redundante a propósito: si el proceso muere
    de una forma que no se puede interceptar, queda a la vista qué archivo
    quedó tocado y con qué contenido volver. Dejar el código degradado es peor
    que no tener la herramienta.
    """

    def __init__(self, ruta, buscar, poner, codificacion):
        self.ruta = ruta
        self.buscar = buscar
        self.poner = poner
        self.codificacion = codificacion
        self.original = None
        self.respaldo = ruta + SUFIJO_RESPALDO
        self.aplicada = False

    def aplicar(self):
        with open(self.ruta, "rb") as archivo:
            self.original = archivo.read()

        texto = self.original.decode(self.codificacion)
        ocurrencias = texto.count(self.buscar)

        # Sin esta comprobación la herramienta tendría el defecto que existe
        # para encontrar. Si el texto a sustituir ya no está —porque el código
        # cambió, o porque hay un espacio de más— no se rompió nada, el comando
        # pasa en verde, y ese verde se leería como "la prueba no detecta el
        # fallo" cuando en realidad no hubo fallo que detectar. Sería la sexta
        # trampa, dentro del arnés escrito para cazar las cinco.
        if ocurrencias == 0:
            return 0

        # El respaldo se escribe antes de tocar el archivo, no después.
        with open(self.respaldo, "wb") as archivo:
            archivo.write(self.original)

        degradado = texto.replace(self.buscar, self.poner)
        with open(self.ruta, "wb") as archivo:
            archivo.write(degradado.encode(self.codificacion))
        self.aplicada = True
        return ocurrencias

    def restaurar(self):
        if not self.aplicada:
            return
        with open(self.ruta, "wb") as archivo:
            archivo.write(self.original)
        self.aplicada = False
        if os.path.exists(self.respaldo):
            os.remove(self.respaldo)


def parece_fallo_de_carga(salida):
    minuscula = salida.lower()
    return [senal for senal in SENALES_DE_CARGA if senal in minuscula]


def ultimas_lineas(texto, cuantas):
    lineas = texto.rstrip().splitlines()
    if len(lineas) <= cuantas:
        return lineas
    return ["[...%d lineas omitidas...]" % (len(lineas) - cuantas)] + lineas[-cuantas:]


def analizar_argumentos(argv):
    analizador = argparse.ArgumentParser(
        prog="degradar.py",
        description="Rompe algo a proposito y comprueba si las pruebas se enteran.")
    analizador.add_argument("--archivo", "-a", required=True,
                            help="archivo de texto donde aplicar la degradacion")
    analizador.add_argument("--buscar", "-b", required=True,
                            help="texto exacto a sustituir; si no esta, el arnes falla")
    analizador.add_argument("--poner", "-p", default="",
                            help="texto que lo reemplaza (por omision, se borra)")
    analizador.add_argument("--comando", "-c", required=True,
                            help="comando de pruebas; debe devolver cero si pasan")
    analizador.add_argument("--directorio", "-d", default=None,
                            help="directorio desde donde ejecutar el comando")
    analizador.add_argument("--codificacion", default="utf-8")
    analizador.add_argument("--tiempo-limite", type=int, default=600,
                            help="segundos antes de abandonar el comando (por omision 600)")
    analizador.add_argument("--lineas", type=int, default=20,
                            help="cuantas lineas finales de la salida mostrar")
    return analizador.parse_args(argv)


def main(argv):
    opciones = analizar_argumentos(argv)

    if not os.path.isfile(opciones.archivo):
        print("ERROR: no existe el archivo %s" % opciones.archivo)
        return ERROR_DE_USO

    respaldo_previo = opciones.archivo + SUFIJO_RESPALDO
    if os.path.exists(respaldo_previo):
        # Un respaldo huérfano significa que una corrida anterior no llegó a
        # restaurar. Seguir adelante sobrescribiría el original bueno con uno
        # ya degradado, así que aquí se para.
        print("ERROR: hay un respaldo sin restaurar en %s" % respaldo_previo)
        print("       el archivo puede estar degradado de una corrida anterior;")
        print("       revisar y restaurar a mano antes de seguir.")
        return ERROR_DE_USO

    degradacion = Degradacion(opciones.archivo, opciones.buscar,
                              opciones.poner, opciones.codificacion)

    # Ctrl+C durante las pruebas es lo normal, no la excepción. Sin esto, la
    # forma más habitual de usar la herramienta es también la que deja el
    # código roto en el disco.
    def al_recibir_senal(numero, marco):
        degradacion.restaurar()
        print("")
        print("interrumpido: el archivo quedo restaurado")
        sys.exit(ERROR_DE_USO)

    for nombre in ("SIGINT", "SIGTERM", "SIGBREAK"):
        if hasattr(signal, nombre):
            try:
                signal.signal(getattr(signal, nombre), al_recibir_senal)
            except (ValueError, OSError):
                pass  # hay entornos donde no se puede registrar; el finally sigue ahí

    print("ARNES DE DEGRADACION")
    print("  archivo:  %s" % opciones.archivo)
    print("  sustituye: %r" % opciones.buscar)
    print("  por:       %r" % opciones.poner)
    print("  comando:  %s" % opciones.comando)
    print("")

    try:
        ocurrencias = degradacion.aplicar()

        if ocurrencias == 0:
            print("  NO SE ENCONTRO QUE DEGRADAR")
            print("  el texto a sustituir no aparece en el archivo.")
            print("  no se rompio nada, asi que el resultado del comando no")
            print("  significaria nada: se aborta sin ejecutarlo.")
            return NADA_QUE_DEGRADAR

        print("  degradacion aplicada: %d ocurrencia%s sustituida%s" % (
            ocurrencias, "" if ocurrencias == 1 else "s", "" if ocurrencias == 1 else "s"))

        inicio = time.time()
        try:
            proceso = subprocess.run(
                opciones.comando, shell=True, cwd=opciones.directorio,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=opciones.tiempo_limite)
            salida = proceso.stdout.decode("utf-8", "replace")
            codigo = proceso.returncode
            expiro = False
        except subprocess.TimeoutExpired as agotado:
            salida = (agotado.stdout or b"").decode("utf-8", "replace")
            codigo = None
            expiro = True
        duracion = time.time() - inicio
    finally:
        # Pase lo que pase: comando que revienta, excepción del propio arnés,
        # tiempo agotado. El bloque de restauración no depende de haber llegado
        # a ninguna conclusión.
        degradacion.restaurar()

    print("  archivo restaurado")
    print("")

    if salida.strip():
        print("  salida del comando (ultimas lineas):")
        for linea in ultimas_lineas(salida, opciones.lineas):
            print("    | " + linea)
        print("")

    if expiro:
        print("  NO CONCLUYENTE")
        print("  el comando no termino en %d segundos. No se sabe si detecto"
              % opciones.tiempo_limite)
        print("  la degradacion o si se quedo colgado por ella.")
        return NO_CONCLUYENTE

    print("  el comando tardo %.1fs y devolvio %d" % (duracion, codigo))
    print("")

    if codigo == 0:
        print("  NO DETECTADO")
        print("  las pruebas pasaron sobre codigo roto a proposito.")
        print("  no verifican lo que la degradacion rompio.")
        return NO_DETECTADO

    senales = parece_fallo_de_carga(salida)
    if senales:
        print("  NO CONCLUYENTE")
        print("  las pruebas fallaron, pero la salida sugiere un fallo de carga")
        print("  o compilacion (%s)." % ", ".join(senales))
        print("  puede que ninguna comprobacion haya llegado a ejecutarse: la")
        print("  sustitucion tiene que romper el comportamiento, no el archivo.")
        return NO_CONCLUYENTE

    print("  DETECTADO")
    print("  las pruebas se pusieron en rojo con la degradacion aplicada.")
    return DETECTADO


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
