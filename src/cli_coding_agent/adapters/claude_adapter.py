from typing import List, Generator, Dict, Any

from agno.models.anthropic import Claude
from agno.models.message import Message as AgnoFormatMessage

from src.cli_coding_agent.domain.schemas import Message
from src.cli_coding_agent.ports.ai_model_port import AIModelPort


class ClaudeAdapter(AIModelPort):
    def __init__(self, model_id: str, api_key: str = None):
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
        Genera una respuesta usando el modelo de Claude con streaming.

        Args:
            messages: Lista de mensajes de la conversación.
            stream: Parámetro mantenido por compatibilidad, siempre usa streaming.

        Returns:
            Un generador que produce fragmentos de la respuesta.
        """
        try:
            agno_messages = [
                AgnoFormatMessage(role=msg.role, content=msg.content)
                for msg in messages
                if msg.content.strip()
            ]

            for response_chunk in self.model.response_stream(messages=agno_messages):
                if response_chunk.content:
                    yield {"content": response_chunk.content, "role": "assistant"}

        except Exception as e:
            raise ValueError(f"Error en la API de Claude: {str(e)}")

    def get_model_id(self) -> str:
        """Retorna el ID del modelo utilizado."""
        return self.model_id

    def get_api_key(self) -> str:
        """Retorna la clave API utilizada."""
        return self.api_key
