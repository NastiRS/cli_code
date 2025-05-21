from typing import List, Generator, Dict, Any

from agno.models.anthropic import Claude

from src.cli_coding_agent.domain.schemas import Message
from src.cli_coding_agent.ports.ai_model_port import AIModelPort


class ClaudeAdapter(AIModelPort):
    """Adaptador que implementa el modelo de IA usando Claude de Anthropic."""

    def __init__(self, model_id: str = "claude-3-7-sonnet-latest", api_key: str = None):
        """
        Inicializa el adaptador para Claude.

        Args:
            model_id: ID del modelo de Claude a utilizar.
            api_key: Clave API de Anthropic.
        """
        self.model = Claude(id=model_id, api_key=api_key)
        self.model_id = model_id
        self.api_key = api_key

    def generate_response(
        self, messages: List[Message], stream: bool = True
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Genera una respuesta usando el modelo de Claude.

        Args:
            messages: Lista de mensajes de la conversación.
            stream: Si es True, retorna la respuesta en streaming.

        Returns:
            Un generador que produce fragmentos de la respuesta.
        """
        # Convertir mensajes al formato que espera Claude
        system_message = None
        claude_messages = []

        # Extraer mensaje de sistema si existe
        for msg in messages:
            if msg.role == "system" and system_message is None:
                system_message = msg.content
            elif msg.content.strip():  # Solo incluir mensajes no vacíos
                claude_messages.append({"role": msg.role, "content": msg.content})

        # Generar la respuesta
        try:
            # Si hay un mensaje de sistema, usarlo como system prompt
            if system_message:
                for response in self.model.chat(
                    messages=claude_messages, system=system_message, stream=stream
                ):
                    yield response
            else:
                # De lo contrario, solo pasar los mensajes
                for response in self.model.chat(
                    messages=claude_messages, stream=stream
                ):
                    yield response
        except Exception as e:
            # En caso de error, lanzar una excepción más informativa
            error_msg = f"Error en la API de Claude: {str(e)}"
            raise ValueError(error_msg)

    def get_model_id(self) -> str:
        """Retorna el ID del modelo utilizado."""
        return self.model_id

    def get_api_key(self) -> str:
        """Retorna la clave API utilizada."""
        return self.api_key
