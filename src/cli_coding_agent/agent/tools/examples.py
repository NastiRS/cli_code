"""
Ejemplos de uso de las herramientas del CLI agent
"""

import asyncio
from . import (
    tool_registry,
    read_file_tool,
    write_to_file_tool,
    search_files_tool,
    execute_command_tool,
    ask_followup_question_tool,
    attempt_completion_tool,
    show_tools,
)


async def example_file_operations():
    """Ejemplo de operaciones con archivos"""
    print("=== Ejemplo: Operaciones con Archivos ===")

    # Escribir un archivo
    result = await write_to_file_tool.execute(
        path="ejemplo.py",
        content='''def saludo(nombre):
    """Función para saludar"""
    return f"Hola, {nombre}!"

if __name__ == "__main__":
    print(saludo("Mundo"))
''',
    )
    print(f"Escribir archivo: {result.success}")

    # Leer el archivo
    result = await read_file_tool.execute(path="ejemplo.py")
    print(f"Leer archivo: {result.success}")
    if result.success:
        print("Contenido:", result.content[:50] + "...")


async def example_search_operations():
    """Ejemplo de operaciones de búsqueda"""
    print("\n=== Ejemplo: Operaciones de Búsqueda ===")

    # Buscar archivos Python
    result = await search_files_tool.execute(
        path=".", regex="def\\s+\\w+", file_pattern="*.py", context_lines=1
    )
    print(f"Búsqueda en archivos: {result.success}")


async def example_command_execution():
    """Ejemplo de ejecución de comandos"""
    print("\n=== Ejemplo: Ejecución de Comandos ===")

    # Ejecutar comando seguro
    result = await execute_command_tool.execute(
        command="python --version", requires_approval=False
    )
    print(f"Comando ejecutado: {result.success}")
    if result.success:
        print("Salida:", result.content.strip())


async def example_user_interaction():
    """Ejemplo de interacción con usuario"""
    print("\n=== Ejemplo: Interacción con Usuario ===")

    # Pregunta de texto
    result = await ask_followup_question_tool.execute(
        question="¿Cuál es tu lenguaje de programación favorito?", question_type="text"
    )
    print(f"Respuesta recibida: {result.content}")

    # Pregunta de selección múltiple
    result = await ask_followup_question_tool.execute(
        question="¿Qué tipo de proyecto quieres crear?",
        options="Web App,API REST,CLI Tool,Desktop App",
        question_type="choice",
    )
    print(f"Opción seleccionada: {result.content}")


async def example_task_completion():
    """Ejemplo de finalización de tarea"""
    print("\n=== Ejemplo: Finalización de Tarea ===")

    result = await attempt_completion_tool.execute(
        result="Se ha implementado exitosamente el sistema de herramientas CLI inspirado en Cline. "
        "Todas las herramientas están funcionando correctamente y adaptadas para CLI.",
        command="python -m src.cli_coding_agent.agent.tools.examples",
        files_created="ejemplo.py,src/cli_coding_agent/agent/tools/examples.py",
        files_modified="pyproject.toml",
    )
    print(f"Tarea completada: {result.success}")


async def demonstrate_tool_registry():
    """Demuestra el uso del registro de herramientas"""
    print("\n=== Ejemplo: Registro de Herramientas ===")

    # Mostrar todas las herramientas
    show_tools()

    # Ejecutar herramienta usando el registro
    result = await tool_registry.execute_tool(
        "list_files", path=".", recursive=False, limit=5
    )

    if result.success:
        files_data = result.content
        print(f"\nArchivos encontrados: {files_data['total_items']}")
        for file_info in files_data["files"][:3]:
            print(f"  📄 {file_info['name']} ({file_info['size']} bytes)")


async def main():
    """Función principal de ejemplos"""
    print("🚀 Demostrando las herramientas del CLI Agent")
    print("=" * 50)

    try:
        # Mostrar herramientas disponibles
        show_tools()

        # Ejecutar ejemplos
        await example_file_operations()
        await example_search_operations()
        await example_command_execution()

        # Ejemplos interactivos (comentados para demo automática)
        # await example_user_interaction()
        # await example_task_completion()

        await demonstrate_tool_registry()

        print("\n✅ Todos los ejemplos completados exitosamente!")

    except Exception as e:
        print(f"❌ Error en los ejemplos: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
