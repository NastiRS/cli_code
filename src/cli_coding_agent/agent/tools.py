from typing import Dict, Any, List, Optional, Callable, TypeVar, cast
import os
import platform
import sys
import socket
import time
import functools

from agno.tools import tool as agno_tool
from rich.console import Console


# Tipo para funciones que retornan diccionarios
T = TypeVar("T", bound=Callable[..., Dict[str, Any]])

# Consola para mostrar output formateado
console = Console()


# Decorador personalizado que mejora la visualización
def tool(show_result: bool = True):
    """
    Decorador que mejora la visualización de las herramientas.

    Args:
        show_result: Si se debe mostrar el resultado de la herramienta en la consola.
    """

    def decorator(func: T) -> T:
        # Aplicar el decorador de Agno primero
        agno_decorated = agno_tool(show_result=True)(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            # Obtener el nombre de la función
            func_name = func.__name__

            # Mostrar solo una vez el indicador visual de llamada a herramienta
            console.print("\n" + "─" * 80, style="bold magenta")
            console.print(
                f"[bold magenta]🔧 HERRAMIENTA: [bold cyan]{func_name.upper()}[/bold cyan][/bold magenta]"
            )
            console.print("─" * 80, style="bold magenta")

            # Ejecutar la función original
            result = func(*args, **kwargs)

            # Mostrar la información en formato más claro sin repetir en la salida del modelo
            if show_result:
                console.print("[bold green]Resultado:[/bold green]")
                console.print(result)
                console.print("─" * 80, style="bold magenta")

            # Devolver solo el resultado sin formateo adicional para que el modelo lo use
            return result

        # Mantener atributos necesarios para Agno
        wrapper.__agno_schema__ = getattr(agno_decorated, "__agno_schema__", None)

        return cast(T, wrapper)

    return decorator


SYSTEM_INFO_NAME = "get_system_info"
COUNT_LINES_NAME = "count_lines_of_code"
INTERNET_CHECK_NAME = "check_internet_connection"


@tool()
def get_system_info() -> Dict[str, str]:
    """
    Obtiene información del sistema operativo, versión de Python, etc.

    Returns:
        Diccionario con información detallada del sistema.
    """
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }

    # Formatear el resultado para mejor visualización
    result = f"""## Información del Sistema

* **Sistema Operativo**: {info["os"]}
* **Versión del SO**: {info["os_version"]}
* **Plataforma**: {info["platform"]}
* **Arquitectura**: {info["machine"]}
* **Procesador**: {info["processor"]}

## Información de Python

* **Versión**: {info["python_version"].split()[0]}
* **Implementación**: {info["python_implementation"]}
"""

    # Incluir tanto el texto formateado como los datos para que el modelo tenga acceso a ambos
    return {"data": info, "formatted_result": result}


@tool()
def count_lines_of_code(
    path: str, extensions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Cuenta las líneas de código en un directorio, organizado por tipo de archivo.

    Args:
        path: Ruta al directorio a analizar.
        extensions: Lista opcional de extensiones de archivo a considerar.
                   Por defecto: ['.py', '.js', '.ts', '.html', '.css']

    Returns:
        Estadísticas sobre las líneas de código.
    """
    if not os.path.exists(path):
        return {"error": f"La ruta '{path}' no existe."}

    if extensions is None:
        extensions = [".py", ".js", ".ts", ".html", ".css"]

    stats = {
        "total_files": 0,
        "total_lines": 0,
        "lines_by_extension": {},
        "files_by_extension": {},
    }

    # Inicializar contadores para cada extensión
    for ext in extensions:
        stats["lines_by_extension"][ext] = 0
        stats["files_by_extension"][ext] = 0

    # Recorrer directorios y archivos
    for root, _, files in os.walk(path):
        for file in files:
            _, ext = os.path.splitext(file)

            if ext.lower() in extensions:
                file_path = os.path.join(root, file)
                stats["total_files"] += 1
                stats["files_by_extension"][ext.lower()] += 1

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        line_count = sum(1 for _ in f)
                        stats["total_lines"] += line_count
                        stats["lines_by_extension"][ext.lower()] += line_count
                except Exception as e:
                    stats["error_reading"] = stats.get("error_reading", []) + [
                        f"Error al leer {file_path}: {str(e)}"
                    ]

    # Formatear el resultado para mejor visualización
    formatted_result = f"""## Estadísticas de Código en '{path}'

* **Total de archivos**: {stats["total_files"]}
* **Total de líneas de código**: {stats["total_lines"]}

## Desglose por extensión
"""

    for ext in extensions:
        if stats["files_by_extension"][ext] > 0:
            formatted_result += f"* **{ext}**: {stats['files_by_extension'][ext]} archivos, {stats['lines_by_extension'][ext]} líneas\n"

    if "error_reading" in stats:
        formatted_result += "\n## Errores\n"
        for error in stats["error_reading"]:
            formatted_result += f"* {error}\n"

    # Incluir tanto el texto formateado como los datos para que el modelo tenga acceso a ambos
    return {"data": stats, "formatted_result": formatted_result}


@tool()
def check_internet_connection(
    host: str = "8.8.8.8", port: int = 53, timeout: int = 3
) -> Dict[str, Any]:
    """
    Verifica la conexión a internet intentando conectarse a un servidor específico.

    Args:
        host: Host al que intentar conectarse (por defecto: 8.8.8.8, DNS de Google)
        port: Puerto a usar (por defecto: 53, puerto DNS)
        timeout: Tiempo de espera en segundos (por defecto: 3 segundos)

    Returns:
        Diccionario con información sobre la conexión.
    """
    start_time = time.time()

    try:
        # Intentar crear un socket IPv4 TCP
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()

        # Calcular tiempo de respuesta
        response_time = time.time() - start_time

        result = {
            "status": "connected",
            "message": f"Conexión establecida con {host}:{port}",
            "response_time_ms": round(response_time * 1000, 2),
        }

        # Formatear el resultado para mejor visualización
        formatted_result = f"""## Estado de la Conexión a Internet

* **Estado**: ✅ Conectado
* **Host**: {host}:{port}
* **Tiempo de respuesta**: {result["response_time_ms"]} ms
"""

    except socket.error as e:
        result = {
            "status": "disconnected",
            "message": f"No se pudo conectar a {host}:{port}",
            "error": str(e),
        }

        # Formatear el resultado para mejor visualización
        formatted_result = f"""## Estado de la Conexión a Internet

* **Estado**: ❌ Desconectado
* **Host**: {host}:{port}
* **Error**: {str(e)}
"""

    # Incluir tanto el texto formateado como los datos para que el modelo tenga acceso a ambos
    return {"data": result, "formatted_result": formatted_result}


# Lista de herramientas disponibles con sus nombres originales
TOOLS_INFO = [
    (SYSTEM_INFO_NAME, get_system_info),
    (COUNT_LINES_NAME, count_lines_of_code),
    (INTERNET_CHECK_NAME, check_internet_connection),
]

# Lista de herramientas disponibles para Agno
AVAILABLE_TOOLS = [tool_func for _, tool_func in TOOLS_INFO]

# Para compatibilidad con el código antiguo
TOOL_SCHEMAS = [
    tool_func.__agno_schema__
    for tool_func in AVAILABLE_TOOLS
    if hasattr(tool_func, "__agno_schema__")
]

# Diccionario de herramientas por nombre para ejecución
TOOLS_BY_NAME = {name: tool_func for name, tool_func in TOOLS_INFO}


def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Ejecuta una herramienta por su nombre con los argumentos proporcionados.

    Args:
        tool_name: Nombre de la herramienta a ejecutar.
        **kwargs: Argumentos para la herramienta.

    Returns:
        Resultado de la ejecución de la herramienta.
    """
    if tool_name not in TOOLS_BY_NAME:
        return {
            "error": f"Herramienta '{tool_name}' no encontrada. Herramientas disponibles: {list(TOOLS_BY_NAME.keys())}"
        }

    try:
        tool_func = TOOLS_BY_NAME[tool_name]
        result = tool_func(**kwargs)
        return result
    except Exception as e:
        return {"error": f"Error al ejecutar la herramienta '{tool_name}': {str(e)}"}
