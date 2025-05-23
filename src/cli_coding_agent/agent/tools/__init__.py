"""
Herramientas del agente de código CLI - Inspiradas en Cline
Todas las herramientas adaptadas específicamente para funcionar con CLI
"""

# Importar herramientas de archivos
from .file_operations import (
    read_file_tool,
    write_to_file_tool,
    replace_in_file_tool,
    list_files_tool,
    list_code_definition_names_tool,
)

# Importar herramientas de búsqueda
from .search_operations import (
    search_files_tool,
    file_search_tool,
    search_workspace_files_tool,
)

# Importar herramientas de comandos
from .command_operations import execute_command_tool

# Importar herramientas de sistema
from .system_operations import (
    ask_followup_question_tool,
    attempt_completion_tool,
    system_status_tool,
)

# Importar clase base y registro
from .base import ToolRegistry, BaseTool, ToolResult, ToolType

# Crear registro global de herramientas
tool_registry = ToolRegistry()

# Registrar todas las herramientas de archivos
tool_registry.register_tool(read_file_tool)
tool_registry.register_tool(write_to_file_tool)
tool_registry.register_tool(replace_in_file_tool)
tool_registry.register_tool(list_files_tool)
tool_registry.register_tool(list_code_definition_names_tool)

# Registrar herramientas de búsqueda
tool_registry.register_tool(search_files_tool)
tool_registry.register_tool(file_search_tool)
tool_registry.register_tool(search_workspace_files_tool)

# Registrar herramientas de comandos
tool_registry.register_tool(execute_command_tool)

# Registrar herramientas de sistema
tool_registry.register_tool(ask_followup_question_tool)
tool_registry.register_tool(attempt_completion_tool)
tool_registry.register_tool(system_status_tool)

# Exportar todo lo necesario
__all__ = [
    # Herramientas individuales
    "read_file_tool",
    "write_to_file_tool",
    "replace_in_file_tool",
    "list_files_tool",
    "list_code_definition_names_tool",
    "search_files_tool",
    "file_search_tool",
    "search_workspace_files_tool",
    "execute_command_tool",
    "ask_followup_question_tool",
    "attempt_completion_tool",
    "system_status_tool",
    # Clases base
    "BaseTool",
    "ToolResult",
    "ToolType",
    "ToolRegistry",
    # Registro global
    "tool_registry",
]


def get_available_tools():
    """
    Retorna información sobre todas las herramientas disponibles
    """
    return tool_registry.list_all_tools()


def get_tools_by_category():
    """
    Retorna herramientas organizadas por categoría
    """
    categories = {}

    for tool_type in ToolType:
        tools = tool_registry.get_tools_by_type(tool_type)
        categories[tool_type.value] = [
            {
                "name": tool.name,
                "description": tool.description,
                "requires_approval": tool.requires_approval,
            }
            for tool in tools
        ]

    return categories


def execute_tool(tool_name: str, **kwargs):
    """
    Ejecuta una herramienta por nombre
    """
    return tool_registry.execute_tool(tool_name, **kwargs)


def display_tools_summary():
    """
    Muestra un resumen de todas las herramientas disponibles
    """
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

    console = Console()

    # Título principal
    console.print()
    console.print(
        Panel(
            "[bold cyan]🛠️ Herramientas del CLI Agent[/bold cyan]",
            style="cyan",
            padding=(1, 2),
        )
    )

    # Obtener herramientas por categoría
    categories = get_tools_by_category()

    for category_name, tools in categories.items():
        if not tools:
            continue

        # Crear tabla para cada categoría
        table = Table(
            title=f"📂 {category_name.replace('_', ' ').title()}",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Herramienta", style="cyan", width=25)
        table.add_column("Descripción", style="white")
        table.add_column("Aprobación", style="yellow", width=12)

        for tool in tools:
            approval_status = (
                "✅ Requerida" if tool["requires_approval"] else "⚡ Automática"
            )
            table.add_row(tool["name"], tool["description"], approval_status)

        console.print(table)
        console.print()

    # Estadísticas
    total_tools = sum(len(tools) for tools in categories.values())
    tools_requiring_approval = sum(
        1
        for tools in categories.values()
        for tool in tools
        if tool["requires_approval"]
    )

    stats_text = f"📊 Total: {total_tools} herramientas | ✅ Requieren aprobación: {tools_requiring_approval} | ⚡ Automáticas: {total_tools - tools_requiring_approval}"

    console.print(Panel(stats_text, style="green", title="Estadísticas"))
    console.print()


# Función de conveniencia para mostrar herramientas disponibles
def show_tools():
    """Muestra todas las herramientas disponibles"""
    display_tools_summary()
