"""
Wrappers con decorador @tool de agno para las herramientas fragmentadas potentes
Mantiene toda la funcionalidad avanzada pero en formato compatible con agno
"""

import asyncio
from typing import Optional

from agno.tools import tool

# Importar las herramientas fragmentadas potentes
from . import (
    read_file_tool,
    write_to_file_tool,
    replace_in_file_tool,
    list_files_tool,
    list_code_definition_names_tool,
    search_files_tool,
    file_search_tool,
    search_workspace_files_tool,
    execute_command_tool,
    ask_followup_question_tool,
    attempt_completion_tool,
    system_status_tool,
)


def _run_async_tool(tool_instance, **kwargs):
    """Helper para ejecutar herramientas asíncronas en formato síncrono"""
    try:
        # Ejecutar la herramienta fragmentada
        result = asyncio.run(tool_instance.execute(**kwargs))

        if result.success:
            # Si el contenido es un dict/list, formatearlo como string
            if isinstance(result.content, (dict, list)):
                import json

                return json.dumps(result.content, indent=2, ensure_ascii=False)
            return str(result.content)
        else:
            return f"Error: {result.error}"
    except Exception as e:
        return f"Error ejecutando herramienta: {str(e)}"


@tool(show_result=True)
def system_status() -> str:
    """Obtiene información completa del sistema operativo y herramientas de desarrollo."""
    result = _run_async_tool(system_status_tool)
    # Para system_status, formatear mejor el resultado si es JSON
    try:
        import json

        data = json.loads(result)
        if isinstance(data, dict):
            formatted = "## Estado del Sistema\n\n"
            for key, value in data.items():
                formatted += f"**{key.replace('_', ' ').title()}:** {value}\n"
            return formatted
    except Exception:
        pass
    return result


@tool(show_result=True)
def read_file(file_path: str) -> str:
    """Lee el contenido de un archivo (soporta texto, PDF, DOCX) con análisis avanzado."""
    return _run_async_tool(read_file_tool, path=file_path)


@tool(show_result=True)
def write_to_file(file_path: str, content: str) -> str:
    """Escribe contenido a un archivo, creando directorios si es necesario."""
    return _run_async_tool(write_to_file_tool, path=file_path, content=content)


@tool(show_result=True)
def replace_in_file(file_path: str, old_str: str, new_str: str) -> str:
    """Reemplaza contenido específico en un archivo usando búsqueda y reemplazo exacto."""
    return _run_async_tool(
        replace_in_file_tool, path=file_path, old_str=old_str, new_str=new_str
    )


@tool(show_result=True)
def list_files(
    directory_path: str = ".", recursive: bool = False, limit: int = 1000
) -> str:
    """Lista archivos y directorios con información detallada."""
    return _run_async_tool(
        list_files_tool, path=directory_path, recursive=recursive, limit=limit
    )


@tool(show_result=True)
def list_code_definitions(path: str) -> str:
    """Lista definiciones de código (clases, funciones, métodos) usando tree-sitter para análisis AST."""
    return _run_async_tool(list_code_definition_names_tool, path=path)


@tool(show_result=True)
def search_files(
    directory_path: str, pattern: str, file_extension: Optional[str] = None
) -> str:
    """Busca archivos que contengan un patrón de texto específico."""
    kwargs = {"path": directory_path, "pattern": pattern}
    if file_extension:
        kwargs["file_extension"] = file_extension
    return _run_async_tool(search_files_tool, **kwargs)


@tool(show_result=True)
def file_search(query: str) -> str:
    """Búsqueda rápida de archivos por nombre usando patrones fuzzy."""
    return _run_async_tool(file_search_tool, query=query)


@tool(show_result=True)
def search_workspace_files(query: str, max_results: int = 20) -> str:
    """Búsqueda avanzada en todo el workspace con indexación inteligente."""
    return _run_async_tool(
        search_workspace_files_tool, query=query, max_results=max_results
    )


@tool(show_result=True)
def execute_command(command: str, working_directory: Optional[str] = None) -> str:
    """Ejecuta un comando en el terminal de forma segura con protecciones."""
    kwargs = {"command": command}
    if working_directory:
        kwargs["working_directory"] = working_directory
    return _run_async_tool(execute_command_tool, **kwargs)


@tool(show_result=True)
def ask_followup_question(
    question: str, question_type: str = "text", options: Optional[str] = None
) -> str:
    """Permite al agente hacer preguntas de seguimiento al usuario."""
    kwargs = {"question": question, "question_type": question_type}
    if options:
        kwargs["options"] = options
    return _run_async_tool(ask_followup_question_tool, **kwargs)


@tool(show_result=True, stop_after_tool_call=True)
def attempt_completion(
    result: str,
    command: Optional[str] = None,
    files_created: Optional[str] = None,
    files_modified: Optional[str] = None,
) -> str:
    """Marca la tarea como completada y muestra el resultado final con información detallada."""
    kwargs = {"result": result}
    if command:
        kwargs["command"] = command
    if files_created:
        kwargs["files_created"] = files_created
    if files_modified:
        kwargs["files_modified"] = files_modified
    return _run_async_tool(attempt_completion_tool, **kwargs)


# Lista de todas las herramientas para agno
ALL_TOOLS = [
    system_status,
    read_file,
    write_to_file,
    replace_in_file,
    list_files,
    list_code_definitions,
    search_files,
    file_search,
    search_workspace_files,
    execute_command,
    # ask_followup_question,
    attempt_completion,
]
