"""
Herramientas del CLI Agent usando el decorador @tool nativo de Agno
"""

import os
import platform
import subprocess
import psutil
from typing import Optional

from agno.tools import tool


@tool(show_result=True)
def system_status() -> str:
    """Obtiene información completa del sistema operativo y herramientas de desarrollo."""
    try:
        # Información básica del sistema
        system_info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "working_directory": os.getcwd(),
        }

        # Información de memoria y disco
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(os.getcwd())

            system_info.update(
                {
                    "memory_total_gb": round(memory.total / (1024**3), 1),
                    "memory_available_gb": round(memory.available / (1024**3), 1),
                    "disk_total_gb": round(disk.total / (1024**3), 1),
                    "disk_free_gb": round(disk.free / (1024**3), 1),
                    "disk_free_percent": round((disk.free / disk.total) * 100, 1),
                }
            )
        except Exception:
            system_info.update(
                {
                    "memory_total_gb": "N/A",
                    "memory_available_gb": "N/A",
                    "disk_total_gb": "N/A",
                    "disk_free_gb": "N/A",
                    "disk_free_percent": "N/A",
                }
            )

        # Detectar herramientas de desarrollo
        dev_tools = {}
        tools_to_check = {
            "python": ["python", "--version"],
            "node": ["node", "--version"],
            "npm": ["npm", "--version"],
            "git": ["git", "--version"],
            "docker": ["docker", "--version"],
            "java": ["java", "--version"],
        }

        for tool_name, cmd in tools_to_check.items():
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    version = result.stdout.strip().split("\n")[0]
                    dev_tools[tool_name] = version
            except Exception:
                pass

        # Formatear respuesta
        response = f"""## Información de tu Sistema Operativo

**Sistema Operativo:** {system_info["os"]}
- Versión: {system_info["os_version"]}
- Plataforma: {system_info["platform"]}
- Arquitectura: {system_info["architecture"]}

**Hardware:**
- Procesador: {system_info["processor"]}
- Memoria RAM: {system_info["memory_total_gb"]} GB total, {system_info["memory_available_gb"]} GB disponible
- Disco: {system_info["disk_total_gb"]} GB total, {system_info["disk_free_gb"]} GB libre ({system_info["disk_free_percent"]}% disponible)

**Información del Usuario:**
- Directorio de trabajo actual: {system_info["working_directory"]}
- Python: {system_info["python_version"]}

**Herramientas de Desarrollo Instaladas:**"""

        for tool_name, version in dev_tools.items():
            response += f"\n- {tool_name.title()}: {version}"

        if not dev_tools:
            response += "\n- No se detectaron herramientas de desarrollo comunes"

        return response

    except Exception as e:
        return f"Error obteniendo información del sistema: {str(e)}"


@tool(show_result=True)
def read_file(file_path: str) -> str:
    """Lee el contenido de un archivo de texto."""
    try:
        # Convertir a ruta absoluta si es relativa
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.getcwd(), file_path)

        # Verificar que el archivo existe
        if not os.path.exists(file_path):
            return f"Error: El archivo '{file_path}' no existe."

        # Verificar que es un archivo (no directorio)
        if not os.path.isfile(file_path):
            return f"Error: '{file_path}' no es un archivo."

        # Intentar leer el archivo con diferentes codificaciones
        encodings = ["utf-8", "utf-16", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()

                # Información del archivo
                file_size = os.path.getsize(file_path)
                lines_count = content.count("\n") + 1 if content else 0

                return f"""## Contenido de {os.path.basename(file_path)}

**Archivo:** {file_path}
**Tamaño:** {file_size} bytes
**Líneas:** {lines_count}

```
{content}
```"""

            except UnicodeDecodeError:
                continue

        return f"Error: No se pudo leer el archivo '{file_path}' con ninguna codificación compatible."

    except Exception as e:
        return f"Error leyendo archivo: {str(e)}"


@tool(show_result=True)
def write_to_file(file_path: str, content: str) -> str:
    """Escribe contenido a un archivo."""
    try:
        # Convertir a ruta absoluta si es relativa
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.getcwd(), file_path)

        # Crear directorios padre si no existen
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Escribir archivo
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Información del archivo creado
        file_size = os.path.getsize(file_path)
        lines_count = content.count("\n") + 1 if content else 0

        return f"✅ Archivo '{os.path.basename(file_path)}' creado exitosamente.\n- Ruta: {file_path}\n- Tamaño: {file_size} bytes\n- Líneas: {lines_count}"

    except Exception as e:
        return f"Error escribiendo archivo: {str(e)}"


@tool(show_result=True)
def list_files(
    directory_path: str = ".", recursive: bool = False, limit: int = 50
) -> str:
    """Lista archivos y directorios en una ruta especificada."""
    try:
        # Convertir a ruta absoluta si es relativa
        if not os.path.isabs(directory_path):
            directory_path = os.path.join(os.getcwd(), directory_path)

        # Verificar que el directorio existe
        if not os.path.exists(directory_path):
            return f"Error: El directorio '{directory_path}' no existe."

        # Verificar que es un directorio
        if not os.path.isdir(directory_path):
            return f"Error: '{directory_path}' no es un directorio."

        files = []
        directories = []
        count = 0

        if recursive:
            # Listado recursivo
            for root, dirs, file_list in os.walk(directory_path):
                if count >= limit:
                    break

                # Agregar directorios
                for d in dirs:
                    if count >= limit:
                        break
                    full_path = os.path.join(root, d)
                    rel_path = os.path.relpath(full_path, directory_path)
                    directories.append(rel_path)
                    count += 1

                # Agregar archivos
                for f in file_list:
                    if count >= limit:
                        break
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, directory_path)
                    file_size = os.path.getsize(full_path)
                    files.append(f"{rel_path} ({file_size} bytes)")
                    count += 1
        else:
            # Solo nivel superior
            items = os.listdir(directory_path)
            for item in items:
                if count >= limit:
                    break

                item_path = os.path.join(directory_path, item)

                if os.path.isdir(item_path):
                    directories.append(item + "/")
                else:
                    file_size = os.path.getsize(item_path)
                    files.append(f"{item} ({file_size} bytes)")

                count += 1

        # Formatear respuesta
        response = f"## Contenido de {directory_path}\n\n"

        if directories:
            response += "**📁 Directorios:**\n"
            for d in sorted(directories):
                response += f"- {d}\n"
            response += "\n"

        if files:
            response += "**📄 Archivos:**\n"
            for f in sorted(files):
                response += f"- {f}\n"
            response += "\n"

        if not directories and not files:
            response += "El directorio está vacío.\n"

        response += f"**Total:** {len(directories)} directorios, {len(files)} archivos"

        if count >= limit:
            response += f" (limitado a {limit} elementos)"

        return response

    except Exception as e:
        return f"Error listando archivos: {str(e)}"


@tool(show_result=True)
def execute_command(command: str, working_directory: Optional[str] = None) -> str:
    """Ejecuta un comando en el terminal."""
    try:
        # Comandos peligrosos que no se deben ejecutar
        dangerous_commands = [
            "rm -rf",
            "del /f",
            "format",
            "fdisk",
            "mkfs",
            "dd if=",
            "shutdown",
            "reboot",
            "halt",
            "poweroff",
            "sudo rm",
            "sudo shutdown",
            "sudo reboot",
        ]

        # Verificar si el comando es peligroso
        for dangerous in dangerous_commands:
            if dangerous.lower() in command.lower():
                return f"⚠️ Comando rechazado por seguridad: '{command}' contiene '{dangerous}'"

        # Establecer directorio de trabajo
        cwd = working_directory if working_directory else os.getcwd()

        # Ejecutar comando
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30, cwd=cwd
        )

        # Formatear respuesta
        response = f"## Resultado del comando: `{command}`\n\n"
        response += f"**Directorio:** {cwd}\n"
        response += f"**Código de salida:** {result.returncode}\n\n"

        if result.stdout:
            response += "**Salida estándar:**\n```\n" + result.stdout + "\n```\n\n"

        if result.stderr:
            response += "**Errores:**\n```\n" + result.stderr + "\n```\n\n"

        if result.returncode == 0:
            response += "✅ Comando ejecutado exitosamente."
        else:
            response += f"❌ Comando falló con código {result.returncode}."

        return response

    except subprocess.TimeoutExpired:
        return f"⏰ Timeout: El comando '{command}' tardó más de 30 segundos."
    except Exception as e:
        return f"Error ejecutando comando: {str(e)}"


@tool(show_result=True)
def search_files(
    directory_path: str, pattern: str, file_extension: Optional[str] = None
) -> str:
    """Busca archivos que contengan un patrón de texto específico."""
    try:
        import re

        # Convertir a ruta absoluta si es relativa
        if not os.path.isabs(directory_path):
            directory_path = os.path.join(os.getcwd(), directory_path)

        # Verificar que el directorio existe
        if not os.path.exists(directory_path):
            return f"Error: El directorio '{directory_path}' no existe."

        results = []
        files_searched = 0
        matches_found = 0

        # Buscar archivos
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                # Filtrar por extensión si se especifica
                if file_extension and not file.endswith(file_extension):
                    continue

                file_path = os.path.join(root, file)

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        files_searched += 1

                        # Buscar patrón
                        if re.search(pattern, content, re.IGNORECASE):
                            rel_path = os.path.relpath(file_path, directory_path)

                            # Encontrar líneas que coinciden
                            lines = content.split("\n")
                            matching_lines = []

                            for i, line in enumerate(lines, 1):
                                if re.search(pattern, line, re.IGNORECASE):
                                    matching_lines.append(
                                        f"  Línea {i}: {line.strip()}"
                                    )
                                    if (
                                        len(matching_lines) >= 3
                                    ):  # Limitar a 3 líneas por archivo
                                        break

                            results.append(
                                {"file": rel_path, "matches": matching_lines}
                            )
                            matches_found += 1

                            # Limitar resultados
                            if len(results) >= 20:
                                break

                except Exception:
                    # Ignorar archivos que no se pueden leer
                    continue

            if len(results) >= 20:
                break

        # Formatear respuesta
        response = f"## Búsqueda: '{pattern}' en {directory_path}\n\n"

        if file_extension:
            response += f"**Filtro:** Solo archivos {file_extension}\n"

        response += f"**Archivos analizados:** {files_searched}\n"
        response += f"**Coincidencias encontradas:** {matches_found}\n\n"

        if results:
            response += "**Resultados:**\n\n"
            for result in results:
                response += f"📄 **{result['file']}**\n"
                for match in result["matches"]:
                    response += f"{match}\n"
                response += "\n"
        else:
            response += "No se encontraron coincidencias."

        if len(results) >= 20:
            response += "\n⚠️ Resultados limitados a 20 archivos."

        return response

    except Exception as e:
        return f"Error en búsqueda: {str(e)}"


@tool(show_result=True)
def attempt_completion(result: str) -> str:
    """Marca la tarea como completada y muestra el resultado final."""
    return f"""🎉 **TAREA COMPLETADA EXITOSAMENTE**

{result}

✅ El agente ha completado su tarea. ¿Necesita algo más?"""


# Lista de todas las herramientas para facilitar el registro
ALL_TOOLS = [
    system_status,
    read_file,
    write_to_file,
    list_files,
    execute_command,
    search_files,
    attempt_completion,
]
