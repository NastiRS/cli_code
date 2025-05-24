import typer
import sys
from typing import Optional, Literal

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table
from rich.live import Live
from rich.text import Text

from src.cli_coding_agent.utils.env_checker import check_env_file
from src.cli_coding_agent.agent.agent import CodeAgent


app = typer.Typer(help="Chat con el agente de código")
console = Console()


def get_code_agent(
    session_id: Optional[str] = None,
    nuevo: bool = False,
    with_tools: bool = False,
    command_type: Literal["chat", "other"] = "other",
) -> CodeAgent:
    """
    Obtiene una instancia del agente de código.
    """
    # Manejar nuevo: crear nueva sesión o usar existente
    if nuevo:
        session_id = None  # Forzar nueva sesión

    # Si no es chat y no hay session_id, crear agente temporal
    if command_type != "chat" and not session_id:
        session_id = "temp_" + str(sys.maxsize)  # ID temporal

    # Crear agente
    agent = CodeAgent(
        session_id=session_id,
        with_tools=with_tools,
    )

    return agent


@app.command()
def chat(
    session_id: Optional[str] = typer.Option(
        None, "--session", "-s", help="ID de sesión"
    ),
    nuevo: bool = typer.Option(False, "--nuevo", "-n", help="Iniciar nueva sesión"),
    with_tools: bool = typer.Option(
        False, "--tools", help="Habilitar herramientas para el agente"
    ),
):
    """
    Inicia un chat con el asistente de código.
    """
    # Usar el nuevo CodeAgent en lugar de ChatService
    agent = get_code_agent(
        session_id=session_id,
        nuevo=nuevo,
        with_tools=with_tools,
        command_type="chat",
    )

    # Comandos especiales
    comandos = {
        "/ayuda": "Muestra esta ayuda",
        "/bye": "Salir del chat",
        "/id": "Muestra el ID de la sesión actual",
        "/switch ID_SESION": "Cambia a la sesión especificada",
    }

    console.print(
        Panel.fit(
            f"[bold]Asistente de Código[/bold]\n"
            f"ID de sesión: {agent.session_id}\n"
            f"Escribe '/ayuda' para ver comandos disponibles\n"
            f"Escribe '/bye' para terminar el chat\n"
            f"Usa '/switch ID_SESION' para cambiar a otra sesión",
            title="Bienvenido",
            border_style="green",
        )
    )

    # Variable para controlar si este es el primer mensaje del usuario
    es_primer_mensaje = True

    try:
        while True:
            # Mostrar prompt y obtener entrada del usuario
            message = Prompt.ask("\n[bold blue]Tú[/bold blue]")

            # Procesar comandos especiales
            if message.startswith("/"):
                comando_completo = message.lower()
                comando = comando_completo.split()[0].lower()

                if comando == "/ayuda":
                    table = Table(title="Comandos disponibles")
                    table.add_column("Comando", style="cyan")
                    table.add_column("Descripción", style="green")

                    for cmd, desc in comandos.items():
                        table.add_row(cmd, desc)

                    console.print(table)
                    continue

                elif comando == "/bye":
                    console.print("[bold green]¡Hasta luego![/bold green]")
                    break

                elif comando == "/id":
                    console.print(f"[bold]ID de sesión:[/bold] {agent.session_id}")
                    continue

                elif comando == "/switch" and len(message.split()) > 1:
                    # Obtener el ID de sesión
                    target_session_id = message.split()[1]

                    try:
                        # Cargar la sesión
                        agent.load_session(target_session_id)
                        console.print(
                            f"[bold green]Cambiado a la sesión:[/bold green] {target_session_id}"
                        )

                        # Verificar que se haya cargado correctamente
                        if agent.session_id != target_session_id:
                            console.print(
                                "[bold red]¡Error! No se actualizó el ID de sesión correctamente.[/bold red]"
                            )
                            continue

                        # Obtener mensajes para confirmar que se cargó la memoria
                        try:
                            # Usar get_messages_for_session en lugar de get_messages
                            mensajes = agent.agent.get_messages_for_session(
                                target_session_id
                            )
                            if mensajes and len(mensajes) > 0:
                                console.print(
                                    "[bold green]Memoria del agente actualizada correctamente.[/bold green]"
                                )
                                console.print(
                                    f"[bold]Mensajes cargados:[/bold] {len(mensajes)}"
                                )
                            else:
                                console.print(
                                    "[bold yellow]Sesión cargada, pero no contiene mensajes previos.[/bold yellow]"
                                )
                        except Exception as e:
                            console.print(
                                f"[bold yellow]Sesión cargada, pero no se pudieron verificar los mensajes: {str(e)}[/bold yellow]"
                            )

                        if agent.session_name:
                            console.print(
                                f"[bold]Nombre de la sesión:[/bold] {agent.session_name}"
                            )

                        continue
                    except Exception as e:
                        console.print(
                            f"[bold red]Error al cambiar de sesión: {str(e)}[/bold red]"
                        )
                        continue

                else:
                    console.print(
                        f"[bold red]Comando desconocido: {comando}[/bold red]"
                    )
                    continue

            # Si es el primer mensaje, establecer el nombre de la sesión
            if es_primer_mensaje:
                agent.set_session_name_from_message(message)
                es_primer_mensaje = False

            # Mostrar respuesta
            console.print("\n[bold green]Asistente[/bold green]")

            # Usar streaming para mostrar la respuesta a medida que se genera
            with Live("", refresh_per_second=4, console=console) as live_display:
                try:
                    # Usar nuestra función personalizada para procesar la respuesta
                    process_agent_response_stream(
                        agent.chat(message, stream=True), live_display
                    )
                except Exception as e:
                    console.print(
                        f"[bold red]Error al obtener respuesta: {str(e)}[/bold red]"
                    )

    except KeyboardInterrupt:
        console.print("\n[bold red]Chat interrumpido.[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")


@app.command()
def session(
    list_sessions: bool = typer.Option(
        False, "--list", "-l", help="Listar todas las sesiones"
    ),
    delete_id: Optional[str] = typer.Option(
        None, "--delete", "-d", help="ID de sesión a eliminar"
    ),
    delete_all: bool = typer.Option(
        False, "--delete-all", "-a", help="Eliminar todas las sesiones"
    ),
    messages_id: Optional[str] = typer.Option(
        None, "--messages", "-m", help="Ver mensajes de una sesión"
    ),
    limit: int = typer.Option(
        10, "--limit", help="Número de mensajes a mostrar (con --messages)"
    ),
    confirm: bool = typer.Option(
        False, "--yes", "-y", help="Confirmar operaciones destructivas sin preguntar"
    ),
):
    """
    Gestiona las sesiones de chat almacenadas.

    Este comando permite listar, eliminar y ver mensajes de sesiones de chat.

    Ejemplos:
        clicode session --list
        clicode session --delete ID
        clicode session --delete-all --yes
        clicode session --messages ID --limit 20
    """
    agent = get_code_agent(command_type="other")

    # Validar que al menos se proporcione una acción
    if not any([list_sessions, delete_id, delete_all, messages_id]):
        console.print(
            "[yellow]Debes especificar una acción. Usa --help para ver las opciones disponibles.[/yellow]"
        )
        return

    # Listar sesiones
    if list_sessions:
        try:
            sessions = agent.list_sessions()

            if not sessions:
                console.print("[yellow]No hay sesiones disponibles.[/yellow]")
                return

            console.print("[bold]Sesiones disponibles:[/bold]\n")

            # Mostrar cada sesión en formato de texto simple
            for i, session in enumerate(sessions, 1):
                session_id = session.get("session_id", "Desconocido")
                session_name = session.get("session_name", "Sin nombre")
                created_at = session.get("created_at", "Fecha desconocida")

                console.print(f"[bold cyan]Sesión #{i}[/bold cyan]")
                console.print(f"[bold]ID:[/bold] {session_id}")
                console.print(f"[bold]Nombre:[/bold] {session_name}")
                console.print(f"[bold]Fecha de creación:[/bold] {created_at}")
                console.print("─" * 50)  # Línea divisoria

        except Exception as e:
            console.print(f"[bold red]Error al listar sesiones: {e}[/bold red]")

    # Eliminar una sesión específica
    if delete_id:
        try:
            # Confirmación del usuario si no se ha proporcionado el flag
            if not confirm:
                confirmacion = Prompt.ask(
                    f"¿Estás seguro de que deseas eliminar la sesión [bold red]{delete_id}[/bold red]?",
                    choices=["s", "n"],
                    default="n",
                )

                if confirmacion.lower() != "s":
                    console.print("[yellow]Operación cancelada.[/yellow]")
                    return

            # Eliminar la sesión
            agent.delete_session(delete_id)

            console.print(
                f"[bold green]Sesión {delete_id} eliminada correctamente.[/bold green]"
            )
        except Exception as e:
            console.print(f"[bold red]Error al eliminar la sesión: {e}[/bold red]")

    # Eliminar todas las sesiones
    if delete_all:
        try:
            # Obtener todas las sesiones
            sessions = agent.list_sessions()

            if not sessions:
                console.print(
                    "[yellow]No hay sesiones disponibles para eliminar.[/yellow]"
                )
                return

            # Mostrar cuántas sesiones se eliminarán
            num_sessions = len(sessions)

            # Confirmación del usuario si no se ha proporcionado el flag
            if not confirm:
                confirmacion = Prompt.ask(
                    f"¿Estás seguro de que deseas eliminar [bold red]TODAS[/bold red] las sesiones ({num_sessions} en total)?",
                    choices=["s", "n"],
                    default="n",
                )

                if confirmacion.lower() != "s":
                    console.print("[yellow]Operación cancelada.[/yellow]")
                    return

            # Eliminar cada sesión
            for session in sessions:
                session_id = session.get("session_id")
                if session_id:
                    agent.delete_session(session_id)

            console.print(
                f"[bold green]Se han eliminado todas las sesiones ({num_sessions} en total).[/bold green]"
            )
        except Exception as e:
            console.print(f"[bold red]Error al eliminar las sesiones: {e}[/bold red]")

    # Ver mensajes de una sesión
    if messages_id:
        try:
            # Cargar la sesión
            agent.load_session(messages_id)

            # Obtener los mensajes
            mensajes = agent.get_messages(messages_id, limit)

            if not mensajes:
                console.print("[yellow]No hay mensajes en esta sesión.[/yellow]")
                return

            # Mostrar ID de la sesión
            console.print(f"[bold]Mensajes de la sesión:[/bold] {messages_id}\n")

            # Mostrar cada mensaje en formato de texto simple
            for i, mensaje in enumerate(mensajes, 1):
                role = mensaje.get("role", "unknown")
                content = mensaje.get("content", "")

                # Determinar el color según el rol
                if role == "user":
                    role_text = "[bold blue]Usuario[/bold blue]"
                elif role == "assistant":
                    role_text = "[bold green]Asistente[/bold green]"
                elif role == "system":
                    role_text = "[bold yellow]Sistema[/bold yellow]"
                else:
                    role_text = f"[bold]{role.capitalize()}[/bold]"

                # Mostrar encabezado del mensaje
                console.print(f"{role_text} - Mensaje #{i}")

                # Mostrar contenido del mensaje
                # Para mensajes del sistema, mostramos el texto tal cual
                # Para otros, usamos Markdown para formateo
                if role == "system":
                    console.print(content)
                else:
                    console.print(Markdown(content))

                # Línea divisoria entre mensajes
                console.print("─" * 50)

        except Exception as e:
            console.print(f"[bold red]Error al mostrar mensajes: {e}[/bold red]")


def show_commands_help():
    """Muestra información de ayuda sobre los comandos disponibles."""
    table = Table(
        title="Comandos disponibles", show_header=True, header_style="bold magenta"
    )
    table.add_column("Comando", style="cyan")
    table.add_column("Descripción", style="green")

    table.add_row("chat", "Inicia un chat con el asistente de código")
    table.add_row(
        "session --list, -l",
        "Lista todas las sesiones disponibles mostrando su ID y nombre",
    )
    table.add_row(
        "session --delete ID, -d ID", "Elimina una sesión específica por su ID"
    )
    table.add_row("session --delete-all, -a", "Elimina TODAS las sesiones existentes")
    table.add_row(
        "session --messages ID, -m ID", "Muestra los mensajes de una sesión específica"
    )

    console.print(table)


def display_tool_call_elegantly(tool_name: str, tool_args: dict = None) -> None:
    """
    Muestra la llamada a una herramienta de forma elegante.

    Args:
        tool_name: Nombre de la herramienta
        tool_args: Argumentos de la herramienta (opcional)
    """
    # Mapeo de nombres técnicos a nombres amigables
    tool_names_friendly = {
        "system_status": "Estado del Sistema",
        "read_file": "Leer Archivo",
        "write_to_file": "Escribir Archivo",
        "list_files": "Listar Archivos",
        "search_files": "Buscar en Archivos",
        "execute_command": "Ejecutar Comando",
        "list_code_definition_names": "Analizar Código",
        "file_search": "Buscar Archivos",
        "search_workspace_files": "Buscar en Workspace",
        "replace_in_file": "Reemplazar en Archivo",
        "ask_followup_question": "Hacer Pregunta",
        "attempt_completion": "Finalizar Tarea",
        "think": "Pensar",
    }

    # Emojis para cada tipo de herramienta
    tool_emojis = {
        "system_status": "ℹ️",
        "read_file": "📖",
        "write_to_file": "📝",
        "list_files": "📁",
        "search_files": "🔍",
        "execute_command": "⚙️",
        "list_code_definition_names": "🔬",
        "file_search": "🗂️",
        "search_workspace_files": "🔎",
        "replace_in_file": "✏️",
        "ask_followup_question": "❓",
        "attempt_completion": "✅",
        "think": "🧠",
    }

    friendly_name = tool_names_friendly.get(
        tool_name, tool_name.replace("_", " ").title()
    )
    emoji = tool_emojis.get(tool_name, "🔧")

    # Crear el texto del mensaje
    message_text = Text()
    message_text.append(f"{emoji} ", style="bold yellow")
    message_text.append("Llamando a la herramienta ", style="cyan")
    message_text.append(friendly_name, style="bold cyan")
    message_text.append("...", style="cyan")

    # Mostrar el panel
    console.print()
    console.print(
        Panel(message_text, style="cyan", border_style="cyan", padding=(0, 1))
    )


def process_agent_response_stream(agent_response_stream, live_display):
    """
    Procesa el stream de respuestas del agente con soporte nativo para tool calls de Agno.
    Maneja las respuestas duplicadas que Agno puede enviar y muestra las tool calls.

    Args:
        agent_response_stream: Stream de respuestas del agente
        live_display: Objeto Live para actualizar la pantalla

    Returns:
        str: Respuesta completa del agente
    """
    seen_tool_calls = set()  # Para evitar mostrar tool calls duplicadas
    accumulated_content = ""  # Contenido acumulado de RunResponse
    has_tools = False  # Flag para detectar si esta sesión usa herramientas

    for respuesta in agent_response_stream:
        # Detectar y mostrar tool calls cuando comienzan
        if (
            hasattr(respuesta, "event")
            and respuesta.event == "ToolCallStarted"
            and hasattr(respuesta, "tools")
            and respuesta.tools
        ):
            has_tools = True  # Marcar que esta sesión tiene herramientas
            for tool in respuesta.tools:
                if isinstance(tool, dict) and "tool_name" in tool:
                    tool_name = tool["tool_name"]
                    tool_args = tool.get("tool_args", {})
                    tool_id = tool.get("tool_call_id", "")

                    # Evitar mostrar la misma tool call múltiples veces
                    tool_signature = f"{tool_name}:{tool_id}"
                    if tool_signature not in seen_tool_calls:
                        seen_tool_calls.add(tool_signature)

                        # Pausar la visualización live para mostrar la tool call
                        live_display.stop()
                        display_tool_call_elegantly(tool_name, tool_args)
                        live_display.start()

        # Procesar contenido: concatenar fragmentos de RunResponse
        if hasattr(respuesta, "content") and respuesta.content:
            content = respuesta.content
            event = getattr(respuesta, "event", "RunResponse")

            # Solo procesar RunResponse (respuestas del modelo)
            # Ignorar ToolCallCompleted (resultados crudos de herramientas)
            if event == "RunResponse":
                # Concatenar todos los fragmentos de RunResponse
                accumulated_content += content

                # Solo actualizar en tiempo real si NO hay herramientas
                # Para chat con herramientas: mostrar solo al final para evitar duplicación
                if not has_tools:
                    try:
                        live_display.update(Markdown(accumulated_content))
                    except Exception:
                        live_display.update(accumulated_content)

    # Mostrar el contenido final para sesiones con herramientas
    if has_tools and accumulated_content:
        try:
            live_display.update(Markdown(accumulated_content))
        except Exception:
            live_display.update(accumulated_content)

    # SEGURIDAD: Nunca retornar una cadena vacía para evitar errores de API
    # Si por alguna razón no hay contenido, retornar un mensaje mínimo
    if not accumulated_content.strip():
        return "..."  # Mensaje mínimo para evitar errores de API

    return accumulated_content


def main():
    """Función principal que inicia la aplicación CLI."""
    try:
        # Mostrar un encabezado bonito
        console.print(
            Panel.fit(
                "[bold cyan]CLI de Chat con Agente de Código[/bold cyan]\n"
                "[green]Usa clicode --help para ver los comandos disponibles[/green]",
                border_style="blue",
            )
        )

        # Verificar configuración del entorno
        if not check_env_file():
            return

        # Si se llama sin argumentos o solo con --help, mostrar ayuda personalizada
        if len(sys.argv) <= 2 and (len(sys.argv) == 1 or sys.argv[1] == "--help"):
            show_commands_help()
            console.print(
                "\nPara más información sobre un comando específico, usa: [cyan]clicode COMANDO --help[/cyan]"
            )
            return

        # Ejecutar la aplicación
        app()

    except KeyboardInterrupt:
        console.print("\n[bold red]Aplicación interrumpida.[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]Error fatal: {e}[/bold red]")
