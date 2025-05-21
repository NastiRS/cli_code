import typer
import sys
from typing import Optional, List, Literal

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table
from rich.live import Live

from src.cli_coding_agent.config import settings
from src.cli_coding_agent.utils.env_checker import check_env_file
from src.cli_coding_agent.adapters.storage.sqlite_adapter import SQLiteAdapter
from src.cli_coding_agent.adapters.claude_adapter import ClaudeAdapter
from src.cli_coding_agent.application.chat_service import ChatService
from src.cli_coding_agent.agent import CodeAgent


app = typer.Typer(help="Chat con el agente de código")
console = Console()


def get_chat_service(
    session_id: Optional[str] = None,
    nuevo: bool = False,
    db_file: str = settings.DB_FILE,
    table_name: str = settings.TABLE_NAME,
    command_type: Literal["chat", "other"] = "other",
) -> ChatService:
    """
    Obtiene una instancia de ChatService configurada.

    Args:
        session_id: ID de sesión opcional.
        nuevo: Si es True, crea una nueva sesión incluso si se proporciona un ID.
        db_file: Ruta al archivo de base de datos.
        table_name: Nombre de la tabla en la base de datos.
        command_type: Tipo de comando que está solicitando el servicio.
            - "chat": Permite crear nuevas sesiones si session_id es None.
            - "other": No crea nuevas sesiones, solo utiliza sesiones existentes.

    Returns:
        Una instancia configurada de ChatService.
    """
    storage = SQLiteAdapter(db_file=db_file, table_name=table_name)
    model = ClaudeAdapter(
        model_id=settings.MODEL_ID, api_key=settings.ANTHROPIC_API_KEY
    )

    # Si es una solicitud para una nueva sesión, ignoramos cualquier ID previo
    if nuevo:
        session_id = None

    # Crear y retornar el servicio con los parámetros adecuados
    return ChatService(
        storage=storage,
        ai_model=model,
        instructions=settings.AGENT_INSTRUCTIONS,
        session_id=session_id,
        num_history_runs=settings.NUM_HISTORY_RUNS,
        command_type=command_type,
    )


def get_code_agent(
    session_id: Optional[str] = None,
    nuevo: bool = False,
    db_file: str = settings.DB_FILE,
    table_name: str = settings.TABLE_NAME,
    with_tools: bool = False,
    command_type: Literal["chat", "other"] = "other",
) -> CodeAgent:
    """
    Obtiene una instancia de CodeAgent configurada.

    Args:
        session_id: ID de sesión opcional.
        nuevo: Si es True, crea una nueva sesión incluso si se proporciona un ID.
        db_file: Ruta al archivo de base de datos.
        table_name: Nombre de la tabla en la base de datos.
        with_tools: Si se deben habilitar las herramientas para el agente.
        command_type: Tipo de comando que está solicitando el agente.
            - "chat": Permite crear nuevas sesiones si session_id es None.
            - "other": No crea nuevas sesiones, solo utiliza sesiones existentes.

    Returns:
        Una instancia configurada de CodeAgent.
    """
    # Si es una solicitud para una nueva sesión, ignoramos cualquier ID previo
    if nuevo:
        session_id = None

    # Si no es chat y no hay session_id, no crear un agent
    if command_type != "chat" and not session_id:
        # En este caso, creamos un agente con una sesión temporal
        # Solo para acceder a sus métodos, pero no para chatear
        agent = CodeAgent(
            session_id="temp_"
            + str(sys.maxsize),  # ID temporal que no debería colisionar
            model_id=settings.MODEL_ID,
            api_key=settings.ANTHROPIC_API_KEY,
            instructions=settings.AGENT_INSTRUCTIONS,
            db_file=db_file,
            table_name=table_name,
            with_tools=with_tools,
        )
    else:
        # Crear un agente normal
        agent = CodeAgent(
            session_id=session_id,
            model_id=settings.MODEL_ID,
            api_key=settings.ANTHROPIC_API_KEY,
            instructions=settings.AGENT_INSTRUCTIONS,
            db_file=db_file,
            table_name=table_name,
            with_tools=with_tools,
        )

    return agent


@app.command()
def chat(
    session_id: Optional[str] = typer.Option(
        None, "--session", "-s", help="ID de sesión"
    ),
    nuevo: bool = typer.Option(False, "--nuevo", "-n", help="Iniciar nueva sesión"),
    db_file: str = typer.Option(
        settings.DB_FILE, "--db", help="Archivo de base de datos"
    ),
    table_name: str = typer.Option(
        settings.TABLE_NAME, "--table", help="Nombre de tabla"
    ),
    exit_words: List[str] = typer.Option(
        ["salir", "exit", "quit"], help="Palabras para salir"
    ),
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
        db_file=db_file,
        table_name=table_name,
        with_tools=with_tools,
        command_type="chat",
    )

    # Comandos especiales
    comandos = {
        "/ayuda": "Muestra esta ayuda",
        "/salir": "Salir del chat",
        "/id": "Muestra el ID de la sesión actual",
    }

    console.print(
        Panel.fit(
            f"[bold]Asistente de Código[/bold]\n"
            f"ID de sesión: {agent.session_id}\n"
            f"Escribe '/ayuda' para ver comandos disponibles\n"
            f"Escribe 'exit', 'quit' o 'salir' para terminar el chat",
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
                comando = message.split()[0].lower()

                if comando == "/ayuda":
                    table = Table(title="Comandos disponibles")
                    table.add_column("Comando", style="cyan")
                    table.add_column("Descripción", style="green")

                    for cmd, desc in comandos.items():
                        table.add_row(cmd, desc)

                    console.print(table)
                    continue

                elif comando == "/salir":
                    console.print("[bold green]¡Hasta luego![/bold green]")
                    break

                elif comando == "/id":
                    console.print(f"[bold]ID de sesión:[/bold] {agent.session_id}")
                    continue

                else:
                    console.print(
                        f"[bold red]Comando desconocido: {comando}[/bold red]"
                    )
                    continue

            # Salir si se usa una palabra de salida
            if message.lower() in exit_words:
                console.print("[bold green]¡Hasta luego![/bold green]")
                break

            # Si es el primer mensaje, establecer el nombre de la sesión
            if es_primer_mensaje:
                agent.set_session_name_from_message(message)
                es_primer_mensaje = False

            # Mostrar respuesta
            console.print("\n[bold green]Asistente[/bold green]")

            # Usar streaming para mostrar la respuesta a medida que se genera
            respuesta_completa = ""

            # Usar un único contexto Live para toda la respuesta con markdown
            with Live("", refresh_per_second=4, console=console) as live_display:
                try:
                    for respuesta in agent.chat(message, stream=True):
                        if respuesta.content:
                            fragmento = respuesta.content
                            respuesta_completa += fragmento
                            # Actualizar la visualización con el contenido completo hasta ahora
                            live_display.update(Markdown(respuesta_completa))
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
    db_file: str = typer.Option(
        settings.DB_FILE, "--db", help="Archivo de base de datos"
    ),
    table_name: str = typer.Option(
        settings.TABLE_NAME, "--table", help="Nombre de tabla"
    ),
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
    agent = get_code_agent(db_file=db_file, table_name=table_name, command_type="other")

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
