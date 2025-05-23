"""
Tests para las herramientas del CLI Code Agent (agno_tools.py)

Este archivo contiene tests para cada una de las 7 herramientas:
1. system_status
2. read_file
3. write_to_file
4. list_files
5. execute_command
6. search_files
7. attempt_completion
"""

import os
import platform

# Importar las herramientas REALES con decorador @tool
from src.cli_coding_agent.agent.tools.agno_tools import (
    system_status as _system_status,
    read_file as _read_file,
    write_to_file as _write_to_file,
    list_files as _list_files,
    execute_command as _execute_command,
    search_files as _search_files,
    attempt_completion as _attempt_completion,
)

# Extraer las funciones originales del decorador @tool
system_status = _system_status.entrypoint
read_file = _read_file.entrypoint
write_to_file = _write_to_file.entrypoint
list_files = _list_files.entrypoint
execute_command = _execute_command.entrypoint
search_files = _search_files.entrypoint
attempt_completion = _attempt_completion.entrypoint


class TestSystemStatus:
    """Tests para la herramienta system_status"""

    def test_system_status_returns_string(self):
        """Test que verifica que system_status retorna un string"""
        result = system_status()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_system_status_contains_basic_info(self):
        """Test que verifica que system_status contiene información básica del sistema"""
        result = system_status()

        # Verificar que contiene información básica
        assert "Sistema Operativo" in result
        assert "Python" in result
        assert "Directorio de trabajo" in result

        # Verificar que contiene información del sistema real
        assert platform.system() in result
        assert platform.python_version() in result

    def test_system_status_contains_memory_info(self):
        """Test que verifica que system_status contiene información de memoria"""
        result = system_status()
        assert (
            "Memoria RAM" in result or "N/A" in result
        )  # Puede fallar en algunos entornos

    def test_system_status_contains_disk_info(self):
        """Test que verifica que system_status contiene información de disco"""
        result = system_status()
        assert "Disco" in result or "N/A" in result


class TestReadFile:
    """Tests para la herramienta read_file"""

    def test_read_existing_file(self, sandbox_file_path):
        """Test que lee un archivo existente (sandbox.py)"""
        result = read_file(sandbox_file_path)

        assert isinstance(result, str)
        assert "Contenido de sandbox.py" in result
        assert "def saludar" in result
        assert "CalculadoraSimple" in result

    def test_read_nonexistent_file(self):
        """Test que maneja archivos inexistentes"""
        result = read_file("archivo_que_no_existe.txt")

        assert isinstance(result, str)
        assert "Error" in result
        assert "no existe" in result

    def test_read_file_with_relative_path(self, temp_dir, test_file_content):
        """Test que lee un archivo con ruta relativa"""
        # Crear archivo de prueba
        test_file = os.path.join(temp_dir, "test_relative.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_file_content)

        # Cambiar directorio temporalmente
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = read_file("test_relative.py")

            assert isinstance(result, str)
            assert "Contenido de test_relative.py" in result
            assert "funcion_test" in result
        finally:
            os.chdir(original_cwd)

    def test_read_directory_instead_of_file(self, temp_dir):
        """Test que maneja cuando se intenta leer un directorio"""
        result = read_file(temp_dir)

        assert isinstance(result, str)
        assert "Error" in result
        assert "no es un archivo" in result


class TestWriteToFile:
    """Tests para la herramienta write_to_file"""

    def test_write_new_file(self, temp_dir):
        """Test que crea un archivo nuevo"""
        test_content = "# Archivo de prueba\nprint('Hello World')\n"
        test_file = os.path.join(temp_dir, "nuevo_archivo.py")

        result = write_to_file(test_file, test_content)

        assert isinstance(result, str)
        assert "✅" in result
        assert "creado exitosamente" in result
        assert os.path.exists(test_file)

        # Verificar contenido
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == test_content

    def test_write_creates_directories(self, temp_dir):
        """Test que crea directorios padre si no existen"""
        test_content = "Contenido de prueba"
        test_file = os.path.join(temp_dir, "nivel1", "nivel2", "archivo.txt")

        result = write_to_file(test_file, test_content)

        assert isinstance(result, str)
        assert "✅" in result
        assert os.path.exists(test_file)
        assert os.path.exists(os.path.dirname(test_file))

    def test_write_overwrites_existing_file(self, temp_dir):
        """Test que sobrescribe un archivo existente"""
        test_file = os.path.join(temp_dir, "existente.txt")

        # Crear archivo inicial
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("Contenido original")

        # Sobrescribir
        new_content = "Contenido nuevo"
        result = write_to_file(test_file, new_content)

        assert isinstance(result, str)
        assert "✅" in result

        # Verificar que se sobrescribió
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == new_content


class TestListFiles:
    """Tests para la herramienta list_files"""

    def test_list_current_directory(self):
        """Test que lista el directorio actual"""
        result = list_files(".")

        assert isinstance(result, str)
        assert "Contenido de" in result
        assert "src/" in result or "src" in result  # Debería encontrar la carpeta src

    def test_list_specific_directory(self, test_directory_structure):
        """Test que lista un directorio específico"""
        result = list_files(test_directory_structure)

        assert isinstance(result, str)
        assert "archivo1.txt" in result
        assert "archivo2.py" in result
        assert "subdir1/" in result
        assert "subdir2/" in result

    def test_list_nonexistent_directory(self):
        """Test que maneja directorios inexistentes"""
        result = list_files("directorio_que_no_existe")

        assert isinstance(result, str)
        assert "Error" in result
        assert "no existe" in result

    def test_list_files_recursive(self, test_directory_structure):
        """Test del listado recursivo"""
        result = list_files(test_directory_structure, recursive=True)

        assert isinstance(result, str)
        assert "archivo3.txt" in result  # Archivo en subdirectorio
        assert "archivo4.py" in result  # Archivo en subdirectorio

    def test_list_files_with_limit(self, test_directory_structure):
        """Test del límite de archivos"""
        result = list_files(test_directory_structure, limit=2)

        assert isinstance(result, str)
        assert "limitado a 2 elementos" in result


class TestExecuteCommand:
    """Tests para la herramienta execute_command"""

    def test_execute_safe_command(self, safe_commands):
        """Test que ejecuta comandos seguros"""
        for command in safe_commands[:2]:  # Solo probar los primeros 2
            result = execute_command(command)

            assert isinstance(result, str)
            assert "Resultado del comando" in result
            assert command in result

    def test_reject_dangerous_commands(self, dangerous_commands):
        """Test que rechaza comandos peligrosos"""
        for command in dangerous_commands:
            result = execute_command(command)

            assert isinstance(result, str)
            assert "⚠️" in result
            assert "rechazado por seguridad" in result

    def test_execute_command_with_working_directory(self, temp_dir):
        """Test que ejecuta comando en directorio específico"""
        if os.name == "nt":  # Windows
            command = "cd"
        else:  # Unix/Linux/Mac
            command = "pwd"

        result = execute_command(command, working_directory=temp_dir)

        assert isinstance(result, str)
        assert "Resultado del comando" in result
        assert temp_dir in result or "Directorio:" in result

    def test_execute_nonexistent_command(self):
        """Test que maneja comandos inexistentes"""
        result = execute_command("comando_que_no_existe_xyz123")

        assert isinstance(result, str)
        assert "Error" in result or "❌" in result or "Código de salida" in result


class TestSearchFiles:
    """Tests para la herramienta search_files"""

    def test_search_pattern_found(self, test_directory_structure):
        """Test que encuentra un patrón en archivos"""
        result = search_files(test_directory_structure, "BUSCAR")

        assert isinstance(result, str)
        assert "Búsqueda: 'BUSCAR'" in result
        assert "archivo1.txt" in result
        assert "archivo2.py" in result
        assert "Coincidencias encontradas" in result

    def test_search_pattern_not_found(self, test_directory_structure):
        """Test cuando no se encuentra el patrón"""
        result = search_files(test_directory_structure, "PATRON_QUE_NO_EXISTE_XYZ")

        assert isinstance(result, str)
        assert "No se encontraron coincidencias" in result

    def test_search_with_file_extension_filter(self, test_directory_structure):
        """Test de búsqueda con filtro de extensión"""
        result = search_files(test_directory_structure, "BUSCAR", file_extension=".py")

        assert isinstance(result, str)
        assert "Solo archivos .py" in result
        assert "archivo2.py" in result
        # No debería encontrar archivo1.txt
        assert "archivo1.txt" not in result

    def test_search_nonexistent_directory(self):
        """Test de búsqueda en directorio inexistente"""
        result = search_files("directorio_que_no_existe", "cualquier_cosa")

        assert isinstance(result, str)
        assert "Error" in result
        assert "no existe" in result


class TestAttemptCompletion:
    """Tests para la herramienta attempt_completion"""

    def test_attempt_completion_basic(self):
        """Test básico de attempt_completion"""
        test_result = "Tarea completada con éxito"
        result = attempt_completion(test_result)

        assert isinstance(result, str)
        assert "🎉" in result
        assert "TAREA COMPLETADA EXITOSAMENTE" in result
        assert test_result in result
        assert "✅" in result

    def test_attempt_completion_with_long_result(self):
        """Test de attempt_completion con resultado largo"""
        test_result = "Este es un resultado muy largo " * 10
        result = attempt_completion(test_result)

        assert isinstance(result, str)
        assert test_result in result
        assert "TAREA COMPLETADA" in result

    def test_attempt_completion_with_empty_result(self):
        """Test de attempt_completion con resultado vacío"""
        result = attempt_completion("")

        assert isinstance(result, str)
        assert "TAREA COMPLETADA" in result


class TestIntegration:
    """Tests de integración que combinan múltiples herramientas"""

    def test_write_read_cycle(self, temp_dir):
        """Test que escribe un archivo y luego lo lee"""
        content = "# Archivo de integración\nprint('Testing integration')\n"
        file_path = os.path.join(temp_dir, "integration_test.py")

        # Escribir archivo
        write_result = write_to_file(file_path, content)
        assert "✅" in write_result

        # Leer archivo
        read_result = read_file(file_path)
        assert content in read_result
        assert "integration_test.py" in read_result

    def test_write_list_search_cycle(self, temp_dir):
        """Test que escribe, lista y busca en archivos"""
        # Escribir archivo con contenido específico
        content = "PALABRA_CLAVE_ESPECIAL para búsqueda\nOtro contenido"
        file_path = os.path.join(temp_dir, "busqueda_test.txt")

        write_result = write_to_file(file_path, content)
        assert "✅" in write_result

        # Listar archivos para verificar que existe
        list_result = list_files(temp_dir)
        assert "busqueda_test.txt" in list_result

        # Buscar el contenido
        search_result = search_files(temp_dir, "PALABRA_CLAVE_ESPECIAL")
        assert "busqueda_test.txt" in search_result
        assert "Coincidencias encontradas:** 1" in search_result

    def test_completion_with_file_operations(self, temp_dir):
        """Test que realiza operaciones de archivo y marca como completado"""
        # Crear archivo
        file_path = os.path.join(temp_dir, "completion_test.py")
        content = "def test_function():\n    return 'completed'\n"

        write_result = write_to_file(file_path, content)
        assert "✅" in write_result

        # Leer para verificar
        read_result = read_file(file_path)
        assert "test_function" in read_result

        # Marcar como completado
        completion_result = attempt_completion(
            f"Archivo {file_path} creado y verificado exitosamente"
        )
        assert "🎉" in completion_result
        assert file_path in completion_result
