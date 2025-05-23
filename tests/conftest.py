import pytest
import os
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """
    Fixture que crea un directorio temporal para las pruebas.
    Se limpia automáticamente después de cada test.
    """
    temp_directory = tempfile.mkdtemp()
    yield temp_directory
    shutil.rmtree(temp_directory, ignore_errors=True)


@pytest.fixture
def sandbox_file_path():
    """
    Fixture que retorna la ruta al archivo sandbox.py.
    """
    return os.path.join(os.path.dirname(__file__), "sandbox.py")


@pytest.fixture
def test_file_content():
    """
    Fixture con contenido de prueba para archivos.
    """
    return """# Archivo de prueba
def funcion_test():
    return "Hello World"

variable_test = 42
lista_test = [1, 2, 3, 4, 5]
"""


@pytest.fixture
def test_directory_structure(temp_dir):
    """
    Fixture que crea una estructura de directorios de prueba.
    """
    # Crear subdirectorios
    subdir1 = os.path.join(temp_dir, "subdir1")
    subdir2 = os.path.join(temp_dir, "subdir2")
    os.makedirs(subdir1)
    os.makedirs(subdir2)

    # Crear archivos de prueba
    files = {
        "archivo1.txt": "Contenido del archivo 1\nBUSCAR esta palabra",
        "archivo2.py": "def funcion():\n    return 'BUSCAR'\n",
        "subdir1/archivo3.txt": "Contenido anidado\nTexto para encontrar",
        "subdir2/archivo4.py": "import os\nprint('Hello World')\n",
    }

    for file_path, content in files.items():
        full_path = os.path.join(temp_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    return temp_dir


@pytest.fixture
def safe_commands():
    """
    Fixture con comandos seguros para testing.
    """
    if os.name == "nt":  # Windows
        return ["echo Hello World", "dir", "cd", "python --version"]
    else:  # Unix/Linux/Mac
        return ["echo Hello World", "ls", "pwd", "python --version"]


@pytest.fixture
def dangerous_commands():
    """
    Fixture con comandos peligrosos que deben ser rechazados.
    """
    return [
        "rm -rf /",
        "del /f C:\\*",
        "format C:",
        "sudo shutdown now",
        "dd if=/dev/zero of=/dev/sda",
    ]
