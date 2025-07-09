import random
import math
from abc import ABC, abstractmethod

def get_rnd():
    """Genera un número aleatorio en el intervalo [0, 1) con una precisión de dos decimales."""
    while True:
        rnd = round(random.random(), 16)
        if rnd < 1.0:
            return rnd

def generar_numeros(generador, cantidad_total):
    numeros = []
    for _ in range(cantidad_total):
        numero = generador.generar_numero()
        numeros.append(numero)
    return numeros

def generar_numperos_de_a_pares(generador, cantidad_total):
    numeros = []
    numeros_generados = 0
    for _ in range(cantidad_total // 2):
        numero1, numero2 = generador.generar_numero()
        numeros.append(numero1)
        numeros.append(numero2)
        numeros_generados += 2
    if numeros_generados < cantidad_total:
        numero1, _ = generador.generar_numero()
        numeros.append(numero1)
    return numeros

class GeneradorDistribucion(ABC):
    """Clase abstracta base para los generadores de distribuciones."""
    @abstractmethod
    def generar_numero(self):
        """Genera un número aleatorio siguiendo la distribución."""
        pass

    def generar_numeros(self, cantidad):
        """Genera una lista de números aleatorios."""
        return generar_numeros(self, cantidad)

class GeneradorUniforme(GeneradorDistribucion):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def generar_numero(self):
        rnd = get_rnd()
        return self.a + rnd * (self.b - self.a)

    def generar_numeros(self, cantidad):
        return generar_numeros(self, cantidad)

class GeneradorExponencial(GeneradorDistribucion):
    def __init__(self, media):
        self.media = media

    def generar_numero(self):
        rnd = get_rnd()
        return -self.media * math.log(1 - rnd)

    def generar_numeros(self, cantidad):
        return generar_numeros(self, cantidad)

class GeneradorPoisson(GeneradorDistribucion):
    def __init__(self, media):
        self.media = media

    def generar_numero(self):
        p = 1
        x = -1
        a = math.exp(-self.media)
        u = get_rnd()
        p = p * u
        x = x + 1
        while p >= a:
            u = get_rnd()
            p = p * u
            x = x + 1
        return x
    
    def generar_numeros(self, cantidad):
        return generar_numeros(self,cantidad)

class GeneradorNormal(GeneradorDistribucion):
    def __init__(self, media, devest):
        self.media = media
        self.devest = devest

    def generar_numero(self):
        rnd1 = get_rnd()
        rnd2 = get_rnd()

        loge = math.log(1 - rnd1)
        a = math.sqrt(-2 * loge)
        b = 2 * math.pi * rnd2

        z1 = a * math.cos(b)
        z2 = a * math.sin(b)

        return self.media + self.devest * z1 , self.media + self.devest * z2

    def generar_numeros(self, cantidad):
        return generar_numperos_de_a_pares(self, cantidad)