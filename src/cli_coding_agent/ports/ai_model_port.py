from abc import ABC, abstractmethod
from typing import List, Generator, Dict, Any

from src.cli_coding_agent.domain.schemas import Message


class AIModelPort(ABC):
    """Puerto que define las operaciones para el modelo de IA."""

    @abstractmethod
    def generate_response(
        self, messages: List[Message], stream: bool = True
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Genera una respuesta del modelo de IA.

        Args:
            messages: Lista de mensajes de la conversación.
            stream: Si es True, retorna la respuesta en streaming.

        Returns:
            Un generador que produce fragmentos de la respuesta.
        """
        pass

    @abstractmethod
    def get_model_id(self) -> str:
        """Retorna el ID del modelo utilizado."""
        pass

    @abstractmethod
    def get_api_key(self) -> str:
        """Retorna la clave API utilizada."""
        pass
