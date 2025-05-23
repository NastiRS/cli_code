"""
Herramientas de operaciones de sistema para el CLI agent - Inspiradas en Cline
"""

import os
import asyncio
from typing import Dict, Any
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from .base import BaseTool, ToolResult, ToolParameter, ToolType


class AskFollowupQuestionTool(BaseTool):
    """Herramienta para hacer preguntas al usuario usando selector CLI"""

    def __init__(self):
        super().__init__()
        self.name = "ask_followup_question"
        self.description = "Hace una pregunta de seguimiento al usuario usando selector CLI interactivo"
        self.tool_type = ToolType.SYSTEM_OPERATION
        self.parameters = [
            ToolParameter(
                name="question", type=str, description="Pregunta a hacer al usuario"
            ),
            ToolParameter(
                name="options",
                type=str,
                description="Opciones disponibles separadas por comas (opcional)",
                required=False,
                default="",
            ),
            ToolParameter(
                name="question_type",
                type=str,
                description="Tipo de pregunta: 'text', 'confirm', 'choice'",
                required=False,
                default="text",
            ),
        ]
        self.requires_approval = False
        self.console = Console()

    async def execute(self, **kwargs) -> ToolResult:
        question = kwargs["question"]
        options = kwargs.get("options", "")
        question_type = kwargs.get("question_type", "text")

        try:
            # Mostrar pregunta formateada
            self._display_question_header(question)

            # Procesar según el tipo de pregunta
            if question_type == "confirm":
                response = await self._ask_confirmation(question)
            elif question_type == "choice" and options:
                response = await self._ask_choice(question, options)
            else:
                response = await self._ask_text(question)

            # Mostrar respuesta seleccionada
            self._display_response(response)

            return ToolResult(
                success=True,
                content=response,
                metadata={
                    "question": question,
                    "question_type": question_type,
                    "options": options,
                    "response_length": len(str(response)),
                },
            )

        except KeyboardInterrupt:
            return ToolResult(
                success=False, content="", error="Pregunta cancelada por el usuario"
            )
        except Exception as e:
            return ToolResult(
                success=False, content="", error=f"Error procesando pregunta: {str(e)}"
            )

    def _display_question_header(self, question: str) -> None:
        """Muestra el encabezado de la pregunta"""
        self.console.print()
        self.console.print(
            Panel(
                Text(question, style="bold cyan"),
                title="🤖 Pregunta del Agente",
                title_align="left",
                border_style="cyan",
            )
        )

    async def _ask_text(self, question: str) -> str:
        """Pregunta de texto libre"""
        self.console.print("📝 [yellow]Ingrese su respuesta:[/yellow]")
        response = Prompt.ask("")
        return response

    async def _ask_confirmation(self, question: str) -> str:
        """Pregunta de confirmación sí/no"""
        self.console.print("❓ [yellow]Confirme su respuesta:[/yellow]")
        response = Confirm.ask("", default=False)
        return "sí" if response else "no"

    async def _ask_choice(self, question: str, options: str) -> str:
        """Pregunta de selección múltiple"""
        option_list = [opt.strip() for opt in options.split(",")]

        if len(option_list) <= 1:
            return await self._ask_text(question)

        # Mostrar opciones en tabla
        table = Table(
            title="Opciones disponibles", show_header=True, header_style="bold magenta"
        )
        table.add_column("Nº", style="cyan", width=3)
        table.add_column("Opción", style="white")

        for i, option in enumerate(option_list, 1):
            table.add_row(str(i), option)

        self.console.print(table)
        self.console.print()

        # Solicitar selección
        while True:
            try:
                choice = Prompt.ask(
                    "🔢 [yellow]Seleccione una opción (número)[/yellow]",
                    choices=[str(i) for i in range(1, len(option_list) + 1)],
                )
                selected_option = option_list[int(choice) - 1]
                return selected_option
            except (ValueError, IndexError):
                self.console.print(
                    "❌ [red]Selección inválida. Intente nuevamente.[/red]"
                )
                continue

    def _display_response(self, response: str) -> None:
        """Muestra la respuesta seleccionada"""
        self.console.print()
        self.console.print(
            Panel(
                Text(f"✅ Respuesta: {response}", style="bold green"),
                title="Respuesta del Usuario",
                title_align="left",
                border_style="green",
            )
        )
        self.console.print()


class AttemptCompletionTool(BaseTool):
    """Herramienta para marcar tarea como completada con display resaltado"""

    def __init__(self):
        super().__init__()
        self.name = "attempt_completion"
        self.description = (
            "Marca la tarea como completada y muestra resultado resaltado en CLI"
        )
        self.tool_type = ToolType.SYSTEM_OPERATION
        self.parameters = [
            ToolParameter(
                name="result",
                type=str,
                description="Descripción del resultado de la tarea completada",
            ),
            ToolParameter(
                name="command",
                type=str,
                description="Comando opcional para demostrar el resultado",
                required=False,
                default="",
            ),
            ToolParameter(
                name="files_created",
                type=str,
                description="Lista de archivos creados separados por comas",
                required=False,
                default="",
            ),
            ToolParameter(
                name="files_modified",
                type=str,
                description="Lista de archivos modificados separados por comas",
                required=False,
                default="",
            ),
        ]
        self.requires_approval = False
        self.console = Console()

    async def execute(self, **kwargs) -> ToolResult:
        result = kwargs["result"]
        command = kwargs.get("command", "")
        files_created = kwargs.get("files_created", "")
        files_modified = kwargs.get("files_modified", "")

        try:
            # Mostrar mensaje de finalización prominente
            await self._display_completion_banner()

            # Mostrar resultado principal
            self._display_main_result(result)

            # Mostrar comando si se proporcionó
            if command:
                self._display_demonstration_command(command)

            # Mostrar archivos afectados
            if files_created or files_modified:
                self._display_affected_files(files_created, files_modified)

            # Mostrar footer de finalización
            self._display_completion_footer()

            return ToolResult(
                success=True,
                content=result,
                metadata={
                    "result": result,
                    "command": command,
                    "files_created": files_created.split(",") if files_created else [],
                    "files_modified": files_modified.split(",")
                    if files_modified
                    else [],
                    "completion_timestamp": asyncio.get_event_loop().time(),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error mostrando finalización: {str(e)}",
            )

    async def _display_completion_banner(self) -> None:
        """Muestra banner de finalización"""
        self.console.print("\n" * 2)

        # Banner principal con emoji y efectos
        banner_text = Text()
        banner_text.append("🎉 ", style="bold yellow")
        banner_text.append("TAREA COMPLETADA EXITOSAMENTE", style="bold green on black")
        banner_text.append(" 🎉", style="bold yellow")

        self.console.print(
            Panel(banner_text, style="bold green", border_style="green", padding=(1, 2))
        )

    def _display_main_result(self, result: str) -> None:
        """Muestra el resultado principal"""
        self.console.print()
        self.console.print(
            Panel(
                Text(result, style="white"),
                title="📋 Resultado de la Tarea",
                title_align="left",
                border_style="blue",
                padding=(1, 2),
            )
        )

    def _display_demonstration_command(self, command: str) -> None:
        """Muestra comando de demostración"""
        self.console.print()
        command_text = Text()
        command_text.append("💻 Comando para probar: ", style="bold cyan")
        command_text.append(command, style="bold white on dark_blue")

        self.console.print(
            Panel(
                command_text,
                title="Demostración",
                title_align="left",
                border_style="cyan",
                padding=(0, 1),
            )
        )

    def _display_affected_files(self, files_created: str, files_modified: str) -> None:
        """Muestra archivos creados y modificados"""
        self.console.print()

        table = Table(
            title="📁 Archivos Afectados", show_header=True, header_style="bold magenta"
        )
        table.add_column("Estado", style="bold", width=12)
        table.add_column("Archivo", style="white")

        # Archivos creados
        if files_created:
            for file_path in files_created.split(","):
                file_path = file_path.strip()
                if file_path:
                    table.add_row("✨ CREADO", file_path)

        # Archivos modificados
        if files_modified:
            for file_path in files_modified.split(","):
                file_path = file_path.strip()
                if file_path:
                    table.add_row("📝 MODIFICADO", file_path)

        if table.rows:
            self.console.print(Panel(table, border_style="magenta"))

    def _display_completion_footer(self) -> None:
        """Muestra footer de finalización"""
        self.console.print()

        footer_text = Text()
        footer_text.append("✅ ", style="bold green")
        footer_text.append("El agente ha completado su tarea. ", style="green")
        footer_text.append("¿Necesita algo más?", style="bold green")

        self.console.print(
            Panel(footer_text, style="green", border_style="green", padding=(0, 1))
        )
        self.console.print("\n")


class SystemStatusTool(BaseTool):
    """Herramienta para mostrar estado del sistema y herramientas disponibles"""

    def __init__(self):
        super().__init__()
        self.name = "system_status"
        self.description = "Muestra el estado del sistema y herramientas disponibles"
        self.tool_type = ToolType.SYSTEM_OPERATION
        self.parameters = []
        self.requires_approval = False
        self.console = Console()

    async def execute(self, **kwargs) -> ToolResult:
        try:
            # Mostrar información del sistema
            system_info = self._get_system_info()

            # Mostrar estado en CLI
            self._display_system_status(system_info)

            return ToolResult(
                success=True,
                content=system_info,
                metadata={
                    "working_directory": self.working_directory,
                    "system_platform": os.name,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error obteniendo estado del sistema: {str(e)}",
            )

    def _get_system_info(self) -> Dict[str, Any]:
        """Obtiene información del sistema"""
        import platform
        import psutil

        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "working_directory": self.working_directory,
            "cpu_count": os.cpu_count(),
            "memory_total": psutil.virtual_memory().total // (1024**3)
            if "psutil" in globals()
            else "N/A",
            "disk_free": psutil.disk_usage(self.working_directory).free // (1024**3)
            if "psutil" in globals()
            else "N/A",
        }

    def _display_system_status(self, system_info: Dict[str, Any]) -> None:
        """Muestra estado del sistema en CLI"""
        self.console.print()

        # Información del sistema
        table = Table(
            title="🖥️ Estado del Sistema", show_header=True, header_style="bold cyan"
        )
        table.add_column("Propiedad", style="bold white", width=20)
        table.add_column("Valor", style="green")

        table.add_row("Sistema Operativo", str(system_info.get("platform", "N/A")))
        table.add_row("Versión Python", str(system_info.get("python_version", "N/A")))
        table.add_row(
            "Directorio de Trabajo", str(system_info.get("working_directory", "N/A"))
        )
        table.add_row("CPUs", str(system_info.get("cpu_count", "N/A")))

        memory = system_info.get("memory_total", "N/A")
        if memory != "N/A":
            table.add_row("Memoria Total", f"{memory} GB")

        disk = system_info.get("disk_free", "N/A")
        if disk != "N/A":
            table.add_row("Espacio Libre", f"{disk} GB")

        self.console.print(Panel(table, border_style="cyan"))
        self.console.print()


# Instancias de las herramientas
ask_followup_question_tool = AskFollowupQuestionTool()
attempt_completion_tool = AttemptCompletionTool()
system_status_tool = SystemStatusTool()
