from abc import ABC, abstractmethod
from scipy import stats
import math

class Distribucion(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def calcular_frecuencia_esperada(self, intervalos, cantidad_total):
        pass

class Uniforme(Distribucion):
    def __init__(self, a, b):
        super().__init__()
        self.a = a
        self.b = b

    def calcular_frecuencia_esperada(self, intervalos, cantidad_total):
        frecuencias_esperadas = {}
        num_intervalos = len(intervalos)
        if num_intervalos > 0:
            frecuencia_esperada_por_intervalo = cantidad_total / num_intervalos
            for intervalo in intervalos:
                frecuencias_esperadas[intervalo] = frecuencia_esperada_por_intervalo
        return frecuencias_esperadas

class Exponencial(Distribucion):
    def __init__(self, media):
        super().__init__()
        self.media = media

    def calcular_frecuencia_esperada(self, intervalos, cantidad_total):
        frecuencias_esperadas = {}

        dist_esperada = stats.expon(scale=self.media)
        for intervalo in intervalos:
            limite_inf, limite_sup = intervalo
            probabilidad = dist_esperada.cdf(limite_sup) - dist_esperada.cdf(limite_inf)
            frecuencia_esperada = cantidad_total * probabilidad
            frecuencias_esperadas[intervalo] = frecuencia_esperada
        return frecuencias_esperadas

class Normal(Distribucion):
    def __init__(self, mu, sigma):
        super().__init__()
        self.mu = mu
        self.sigma = sigma

    def calcular_frecuencia_esperada(self, intervalos, cantidad_total):
        frecuencias_esperadas = {}
        dist_esperada = stats.norm(loc=self.mu, scale=self.sigma)
        for intervalo in intervalos:
            limite_inf, limite_sup = intervalo
            probabilidad = dist_esperada.cdf(limite_sup) - dist_esperada.cdf(limite_inf)
            frecuencia_esperada = cantidad_total * probabilidad
            frecuencias_esperadas[intervalo] = frecuencia_esperada
        return frecuencias_esperadas

class Poisson(Distribucion):
    def __init__(self, media):
        self.media = media

    def _pmf(self, k):
        if k < 0:
            return 0
        return (math.exp(-self.media) * (self.media ** k)) / math.factorial(k)

    def calcular_frecuencia_esperada(self, valores_unicos, cantidad_total):
        frecuencias_esperadas = {}
        for valor in valores_unicos:
            prob = self._pmf(valor)
            frecuencia_esperada = cantidad_total * prob
            frecuencias_esperadas[valor] = frecuencia_esperada
        return frecuencias_esperadas