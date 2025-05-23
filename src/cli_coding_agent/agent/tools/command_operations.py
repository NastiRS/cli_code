"""
Herramientas de operaciones de comandos para el CLI agent - Inspiradas en Cline
"""

import asyncio
import platform
import shlex
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from .base import BaseTool, ToolResult, ToolParameter, ToolType


class ExecuteCommandTool(BaseTool):
    """Herramienta para ejecutar comandos CLI con aprobación automática configurable"""

    def __init__(self):
        super().__init__()
        self.name = "execute_command"
        self.description = (
            "Ejecuta comandos CLI en el sistema con control de aprobación automática"
        )
        self.tool_type = ToolType.COMMAND_OPERATION
        self.parameters = [
            ToolParameter(
                name="command", type=str, description="Comando CLI a ejecutar"
            ),
            ToolParameter(
                name="requires_approval",
                type=bool,
                description="Si el comando requiere aprobación explícita del usuario",
            ),
            ToolParameter(
                name="timeout",
                type=int,
                description="Tiempo límite en segundos para la ejecución del comando",
                required=False,
                default=30,
            ),
            ToolParameter(
                name="capture_output",
                type=bool,
                description="Si capturar la salida del comando",
                required=False,
                default=True,
            ),
        ]
        self.requires_approval = True  # Por defecto requiere aprobación

        # Comandos seguros que no requieren aprobación
        self.safe_commands = {
            "ls",
            "dir",
            "pwd",
            "cd",
            "cat",
            "type",
            "head",
            "tail",
            "less",
            "more",
            "find",
            "grep",
            "wc",
            "sort",
            "uniq",
            "echo",
            "which",
            "where",
            "whoami",
            "ps",
            "top",
            "df",
            "du",
            "free",
            "uptime",
            "date",
            "cal",
            "env",
            "printenv",
            "python",
            "python3",
            "node",
            "npm",
            "yarn",
            "pip",
            "git",
            "mvn",
            "gradle",
            "cargo",
            "dotnet",
            "go",
            "rustc",
            "javac",
            "gcc",
            "make",
            "cmake",
        }

        # Comandos peligrosos que siempre requieren aprobación
        self.dangerous_commands = {
            "rm",
            "del",
            "rmdir",
            "rd",
            "mv",
            "move",
            "cp",
            "copy",
            "chmod",
            "chown",
            "sudo",
            "su",
            "admin",
            "runas",
            "format",
            "fdisk",
            "mkfs",
            "dd",
            "kill",
            "killall",
            "pkill",
            "shutdown",
            "reboot",
            "halt",
            "poweroff",
            "systemctl",
            "service",
            "crontab",
            "at",
            "schtasks",
            "reg",
            "regedit",
            "netsh",
        }

    async def execute(self, **kwargs) -> ToolResult:
        command = kwargs["command"]
        requires_approval = kwargs["requires_approval"]
        timeout = kwargs.get("timeout", 30)
        capture_output = kwargs.get("capture_output", True)

        # Validar el comando
        validation_result = self._validate_command(command)
        if not validation_result[0]:
            return ToolResult(success=False, content="", error=validation_result[1])

        # Determinar si es un comando seguro
        is_safe = self._is_safe_command(command)

        try:
            # Ejecutar el comando
            if platform.system() == "Windows":
                result = await self._execute_windows_command(
                    command, timeout, capture_output
                )
            else:
                result = await self._execute_unix_command(
                    command, timeout, capture_output
                )

            return ToolResult(
                success=result["success"],
                content=result["output"],
                metadata={
                    "command": command,
                    "exit_code": result["exit_code"],
                    "execution_time": result["execution_time"],
                    "is_safe": is_safe,
                    "requires_approval": requires_approval,
                    "timeout": timeout,
                    "working_directory": self.working_directory,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error ejecutando comando '{command}': {str(e)}",
            )

    def _validate_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """Valida si el comando es seguro de ejecutar"""
        if not command or not command.strip():
            return False, "El comando no puede estar vacío"

        command = command.strip()

        # Verificar caracteres peligrosos
        dangerous_chars = ["|", "&", ";", "$(", "`", ">", ">>", "<", "<<"]
        for char in dangerous_chars:
            if char in command:
                # Permitir algunos casos específicos
                if char in [">", ">>"] and any(
                    safe in command.lower() for safe in ["echo", "cat", "print"]
                ):
                    continue
                return False, f"Comando contiene carácter peligroso: {char}"

        # Verificar longitud
        if len(command) > 1000:
            return False, "Comando demasiado largo"

        return True, None

    def _is_safe_command(self, command: str) -> bool:
        """Determina si un comando es seguro"""
        command_parts = shlex.split(command.lower())
        if not command_parts:
            return False

        base_command = command_parts[0]

        # Extraer el nombre del comando sin ruta
        if "/" in base_command or "\\" in base_command:
            base_command = Path(base_command).name

        # Verificar si es un comando peligroso
        if base_command in self.dangerous_commands:
            return False

        # Verificar si es un comando seguro
        if base_command in self.safe_commands:
            return True

        # Verificar patrones específicos de comandos seguros
        safe_patterns = [
            "python -m",
            "python3 -m",
            "npm run",
            "npm start",
            "npm test",
            "yarn run",
            "yarn start",
            "yarn test",
            "git status",
            "git log",
            "git diff",
            "git show",
            "git branch",
            "pip list",
            "pip show",
        ]

        for pattern in safe_patterns:
            if command.lower().startswith(pattern):
                return True

        return False

    async def _execute_windows_command(
        self, command: str, timeout: int, capture_output: bool
    ) -> Dict[str, Any]:
        """Ejecuta comando en Windows"""
        import time

        start_time = time.time()

        try:
            # Usar PowerShell para comandos complejos
            if any(char in command for char in ["|", "&", "&&", "||"]):
                full_command = ["powershell", "-Command", command]
            else:
                full_command = ["cmd", "/c", command]

            if capture_output:
                process = await asyncio.create_subprocess_exec(
                    *full_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.working_directory,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                output = stdout.decode("utf-8", errors="ignore")
                if stderr:
                    error_output = stderr.decode("utf-8", errors="ignore")
                    output += f"\n[STDERR]: {error_output}"

            else:
                process = await asyncio.create_subprocess_exec(
                    *full_command, cwd=self.working_directory
                )

                await asyncio.wait_for(process.wait(), timeout=timeout)
                output = "Comando ejecutado (salida no capturada)"

            execution_time = time.time() - start_time

            return {
                "success": process.returncode == 0,
                "output": output,
                "exit_code": process.returncode,
                "execution_time": execution_time,
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "output": f"Comando excedió el tiempo límite de {timeout} segundos",
                "exit_code": -1,
                "execution_time": timeout,
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Error ejecutando comando: {str(e)}",
                "exit_code": -1,
                "execution_time": time.time() - start_time,
            }

    async def _execute_unix_command(
        self, command: str, timeout: int, capture_output: bool
    ) -> Dict[str, Any]:
        """Ejecuta comando en sistemas Unix-like"""
        import time

        start_time = time.time()

        try:
            if capture_output:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.working_directory,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                output = stdout.decode("utf-8", errors="ignore")
                if stderr:
                    error_output = stderr.decode("utf-8", errors="ignore")
                    output += f"\n[STDERR]: {error_output}"

            else:
                process = await asyncio.create_subprocess_shell(
                    command, cwd=self.working_directory
                )

                await asyncio.wait_for(process.wait(), timeout=timeout)
                output = "Comando ejecutado (salida no capturada)"

            execution_time = time.time() - start_time

            return {
                "success": process.returncode == 0,
                "output": output,
                "exit_code": process.returncode,
                "execution_time": execution_time,
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "output": f"Comando excedió el tiempo límite de {timeout} segundos",
                "exit_code": -1,
                "execution_time": timeout,
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Error ejecutando comando: {str(e)}",
                "exit_code": -1,
                "execution_time": time.time() - start_time,
            }

    def get_safe_commands_list(self) -> List[str]:
        """Retorna la lista de comandos seguros"""
        return sorted(list(self.safe_commands))

    def get_dangerous_commands_list(self) -> List[str]:
        """Retorna la lista de comandos peligrosos"""
        return sorted(list(self.dangerous_commands))

    def add_safe_command(self, command: str) -> None:
        """Agrega un comando a la lista de comandos seguros"""
        self.safe_commands.add(command.lower())

    def add_dangerous_command(self, command: str) -> None:
        """Agrega un comando a la lista de comandos peligrosos"""
        self.dangerous_commands.add(command.lower())

    def is_command_safe(self, command: str) -> bool:
        """Verifica si un comando es considerado seguro"""
        return self._is_safe_command(command)


# Instancia de la herramienta
execute_command_tool = ExecuteCommandTool()
