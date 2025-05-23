"""
Archivo Sandbox para Testing

Este archivo es utilizado por las herramientas del CLI Code Agent
para realizar pruebas de lectura, escritura y manipulación de archivos.

Contenido de ejemplo:
- Funciones de Python
- Comentarios
- Diferentes tipos de datos
"""


def saludar(nombre: str) -> str:
    """
    Función que saluda a una persona.

    Args:
        nombre: Nombre de la persona a saludar

    Returns:
        Mensaje de saludo personalizado
    """
    return f"¡Hola, {nombre}! Bienvenido al sandbox."


def calcular_suma(a: int, b: int) -> int:
    """
    Calcula la suma de dos números.

    Args:
        a: Primer número
        b: Segundo número

    Returns:
        La suma de a y b
    """
    return a + b


class CalculadoraSimple:
    """Clase simple para operaciones matemáticas básicas."""

    def __init__(self):
        self.historial = []

    def sumar(self, a: float, b: float) -> float:
        """Suma dos números y guarda en el historial."""
        resultado = a + b
        self.historial.append(f"{a} + {b} = {resultado}")
        return resultado

    def restar(self, a: float, b: float) -> float:
        """Resta dos números y guarda en el historial."""
        resultado = a - b
        self.historial.append(f"{a} - {b} = {resultado}")
        return resultado

    def obtener_historial(self) -> list:
        """Retorna el historial de operaciones."""
        return self.historial.copy()


# Variables globales de ejemplo
CONSTANTE_PI = 3.14159
lista_numeros = [1, 2, 3, 4, 5]
diccionario_ejemplo = {"nombre": "Sandbox", "version": "1.0", "activo": True}

# Texto para búsquedas
texto_busqueda = """
Este es un texto de ejemplo para las pruebas de búsqueda.
Contiene palabras clave como: BUSCAR, encontrar, localizar.
También tiene números: 123, 456, 789.
Y algunos símbolos especiales: @#$%&*
"""

if __name__ == "__main__":
    # Código de ejemplo para ejecutar
    calc = CalculadoraSimple()
    print(saludar("Usuario de Prueba"))
    print(f"2 + 3 = {calc.sumar(2, 3)}")
    print(f"10 - 4 = {calc.restar(10, 4)}")
    print("Historial:", calc.obtener_historial())
