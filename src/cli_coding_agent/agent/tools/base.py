"""
Clases base para las herramientas del agente CLI - Inspiradas en Cline
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path


class ToolType(Enum):
    """Tipos de herramientas disponibles"""

    FILE_OPERATION = "file_operation"
    SEARCH_OPERATION = "search_operation"
    COMMAND_OPERATION = "command_operation"
    SYSTEM_OPERATION = "system_operation"


@dataclass
class ToolParameter:
    """Definición de un parámetro de herramienta"""

    name: str
    type: type
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolResult:
    """Resultado de la ejecución de una herramienta"""

    success: bool
    content: Union[str, Dict[str, Any], List[Any]]
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseTool(ABC):
    """Clase base abstracta para todas las herramientas del CLI agent"""

    def __init__(self):
        self.name: str = ""
        self.description: str = ""
        self.tool_type: ToolType = ToolType.SYSTEM_OPERATION
        self.parameters: List[ToolParameter] = []
        self.requires_approval: bool = False
        self.working_directory: str = os.getcwd()

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Ejecuta la herramienta con los parámetros dados"""
        pass

    def validate_parameters(self, **kwargs) -> Tuple[bool, Optional[str]]:
        """Valida que los parámetros requeridos estén presentes y sean del tipo correcto"""
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                return False, f"Parámetro requerido '{param.name}' no encontrado"

            if param.name in kwargs:
                value = kwargs[param.name]
                if not isinstance(value, param.type) and value is not None:
                    # Intentar conversión automática para tipos básicos
                    try:
                        if param.type is str:
                            kwargs[param.name] = str(value)
                        elif param.type is int:
                            kwargs[param.name] = int(value)
                        elif param.type is bool:
                            kwargs[param.name] = bool(value)
                        elif param.type is float:
                            kwargs[param.name] = float(value)
                    except (ValueError, TypeError):
                        return (
                            False,
                            f"Parámetro '{param.name}' debe ser de tipo {param.type.__name__}",
                        )

        return True, None

    def get_absolute_path(self, relative_path: str) -> str:
        """Convierte una ruta relativa en absoluta basada en el directorio de trabajo"""
        if os.path.isabs(relative_path):
            return relative_path
        return os.path.join(self.working_directory, relative_path)

    def get_relative_path(self, absolute_path: str) -> str:
        """Convierte una ruta absoluta en relativa al directorio de trabajo"""
        try:
            return os.path.relpath(absolute_path, self.working_directory)
        except ValueError:
            return absolute_path

    def is_path_safe(self, path: str) -> bool:
        """Verifica si una ruta es segura para acceder"""
        absolute_path = self.get_absolute_path(path)

        # Verificar que no contenga .. para evitar path traversal
        if ".." in Path(absolute_path).parts:
            return False

        # Verificar que esté dentro del directorio de trabajo o sus subdirectorios
        try:
            Path(absolute_path).resolve().relative_to(
                Path(self.working_directory).resolve()
            )
            return True
        except ValueError:
            # Permitir algunos directorios específicos fuera del workspace
            allowed_dirs = [Path.home(), Path.cwd(), Path("/tmp"), Path("/var/tmp")]

            for allowed_dir in allowed_dirs:
                try:
                    Path(absolute_path).resolve().relative_to(allowed_dir.resolve())
                    return True
                except ValueError:
                    continue

            return False

    def get_tool_info(self) -> Dict[str, Any]:
        """Retorna información sobre la herramienta"""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.tool_type.value,
            "parameters": [
                {
                    "name": param.name,
                    "type": param.type.__name__,
                    "description": param.description,
                    "required": param.required,
                    "default": param.default,
                }
                for param in self.parameters
            ],
            "requires_approval": self.requires_approval,
        }


class ToolRegistry:
    """Registro central de todas las herramientas disponibles para el CLI agent"""

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.tool_categories: Dict[ToolType, List[str]] = {
            tool_type: [] for tool_type in ToolType
        }

    def register_tool(self, tool: BaseTool) -> None:
        """Registra una herramienta en el registro"""
        self.tools[tool.name] = tool
        if tool.tool_type not in self.tool_categories:
            self.tool_categories[tool.tool_type] = []
        if tool.name not in self.tool_categories[tool.tool_type]:
            self.tool_categories[tool.tool_type].append(tool.name)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Obtiene una herramienta por nombre"""
        return self.tools.get(name)

    def get_tools_by_type(self, tool_type: ToolType) -> List[BaseTool]:
        """Obtiene todas las herramientas de un tipo específico"""
        tool_names = self.tool_categories.get(tool_type, [])
        return [self.tools[name] for name in tool_names if name in self.tools]

    def list_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """Lista información de todas las herramientas registradas"""
        return {name: tool.get_tool_info() for name, tool in self.tools.items()}

    def get_all_tools(self) -> List[BaseTool]:
        """Obtiene todas las herramientas registradas como lista"""
        return list(self.tools.values())

    async def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Ejecuta una herramienta por nombre"""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False, content="", error=f"Herramienta '{name}' no encontrada"
            )

        # Validar parámetros
        valid, error_msg = tool.validate_parameters(**kwargs)
        if not valid:
            return ToolResult(success=False, content="", error=error_msg)

        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error ejecutando herramienta '{name}': {str(e)}",
            )


# Decorador para crear herramientas de forma más simple
def create_tool(
    name: str,
    description: str,
    tool_type: ToolType,
    parameters: List[ToolParameter],
    requires_approval: bool = False,
):
    """Decorador para crear herramientas de forma simplificada"""

    def decorator(func: Callable) -> BaseTool:
        class DecoratedTool(BaseTool):
            def __init__(self):
                super().__init__()
                self.name = name
                self.description = description
                self.tool_type = tool_type
                self.parameters = parameters
                self.requires_approval = requires_approval

            async def execute(self, **kwargs) -> ToolResult:
                return await func(**kwargs)

        return DecoratedTool()

    return decorator
