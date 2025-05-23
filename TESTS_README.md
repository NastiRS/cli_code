# Tests para CLI Code Agent

Este directorio contiene los tests automatizados para las herramientas del CLI Code Agent.

## Estructura de archivos

- **`conftest.py`** - Configuración y fixtures compartidas para pytest
- **`sandbox.py`** - Archivo de ejemplo que las herramientas pueden leer/editar
- **`test_agno_tools.py`** - Tests principales que usan las herramientas REALES (extrae funciones de decorador `@tool`)

## Herramientas probadas

Los tests cubren las siguientes 7 herramientas:

1. **`system_status`** - Obtiene información del sistema operativo
2. **`read_file`** - Lee contenido de archivos
3. **`write_to_file`** - Escribe contenido a archivos
4. **`list_files`** - Lista archivos y directorios
5. **`execute_command`** - Ejecuta comandos en el terminal
6. **`search_files`** - Busca patrones en archivos
7. **`attempt_completion`** - Marca tareas como completadas

## Ejecutar los tests

### Prerequisitos

Asegúrate de tener pytest instalado:

```bash
pip install pytest
```

### Ejecutar todos los tests

```bash
# Desde la raíz del proyecto
pytest tests/

# O con más detalle
pytest tests/ -v

### Ejecutar tests específicos

```bash
# Solo tests de una herramienta específica
pytest tests/test_agno_tools.py::TestSystemStatus -v

# Solo un test específico
pytest tests/test_agno_tools.py::TestReadFile::test_read_existing_file -v

# Tests de integración
pytest tests/test_agno_tools.py::TestIntegration -v
```

### Opciones útiles

```bash

# Parar en el primer fallo
pytest tests/ -x


## Tipos de tests

### Tests unitarios
Cada herramienta tiene tests que verifican:
- ✅ Funcionalidad básica
- ✅ Manejo de errores
- ✅ Casos edge
- ✅ Validación de parámetros

### Tests de integración
Combinan múltiples herramientas:
- ✅ Escribir → Leer archivo
- ✅ Escribir → Listar → Buscar
- ✅ Operaciones → Completion

### Tests de seguridad
Verifican que comandos peligrosos sean rechazados:
- ❌ `rm -rf /`
- ❌ `del /f C:\*`
- ❌ `format C:`
- ❌ `sudo shutdown`

## Fixtures disponibles

- **`temp_dir`** - Directorio temporal que se limpia automáticamente
- **`sandbox_file_path`** - Ruta al archivo sandbox.py
- **`test_file_content`** - Contenido de ejemplo para archivos
- **`test_directory_structure`** - Estructura de directorios con archivos de prueba
- **`safe_commands`** - Lista de comandos seguros para testing
- **`dangerous_commands`** - Lista de comandos peligrosos que deben ser rechazados

## Archivo Sandbox

El archivo `sandbox.py` contiene:
- Funciones de Python de ejemplo
- Clases con métodos
- Variables globales
- Texto para búsquedas
- Código ejecutable

Las herramientas pueden usar este archivo para:
- Practicar lectura de código
- Buscar patrones específicos
- Analizar estructura de código
- Testing de funcionalidades

## Contribuir

Para añadir nuevos tests:

1. Añade el test en la clase correspondiente en `test_agno_tools.py`
2. Usa las fixtures existentes cuando sea posible
3. Sigue el patrón Arrange-Act-Assert
4. Incluye docstrings descriptivos
5. Maneja tanto casos exitosos como de error
