import uuid
from typing import List, Generator, Dict, Any, Optional, Literal

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.storage.sqlite import SqliteStorage

from src.cli_coding_agent.domain.schemas import Message
from src.cli_coding_agent.ports.storage_port import StoragePort
from src.cli_coding_agent.ports.ai_model_port import AIModelPort


class ChatService:
    """Servicio principal para gestionar las conversaciones con el agente."""

    def __init__(
        self,
        storage: StoragePort,
        ai_model: AIModelPort,
        instructions: str,
        session_id: Optional[str] = None,
        num_history_runs: int = 10,
        command_type: Literal["chat", "other"] = "other",
    ):
        """
        Inicializa el servicio de chat.

        Args:
            storage: Adaptador para el almacenamiento.
            ai_model: Adaptador para el modelo de IA.
            instructions: Instrucciones para el agente.
            session_id: ID de sesión opcional. Si no se proporciona, se crea uno nuevo solo en modo chat.
            num_history_runs: Número de intercambios previos a incluir en cada consulta.
            command_type: Tipo de comando que está utilizando este servicio.
        """
        self.storage = storage
        self.ai_model = ai_model
        self.instructions = instructions
        self.num_history_runs = num_history_runs
        self.command_type = command_type

        # Crear agente de Agno directamente para simplificar
        self.agent = Agent(
            name="Asistente de Código",
            instructions=instructions,
            model=Claude(id=ai_model.get_model_id(), api_key=ai_model.get_api_key()),
            storage=SqliteStorage(
                table_name="code_agent", db_file="database/code_agent.db"
            ),
            add_datetime_to_instructions=True,
            add_history_to_messages=True,
            num_history_runs=num_history_runs,
            markdown=True,
        )

        # Solo manejar sesiones cuando:
        # 1. Nos proporcionan un session_id específico, o
        # 2. Estamos en modo chat
        if session_id:
            # Si nos proporcionan un ID específico, intentamos cargarlo
            self.session_id = session_id
            try:
                self.agent.session_id = session_id
                self.agent.load_session()
            except Exception:
                if command_type == "chat":
                    # Solo creamos una nueva sesión en modo chat
                    self.session_id = str(uuid.uuid4())
                    self.agent.session_id = self.session_id
                    self.agent.new_session()
        elif command_type == "chat":
            # Solo creamos una nueva sesión en modo chat si no tenemos ID
            self.session_id = str(uuid.uuid4())
            self.agent.session_id = self.session_id
            self.agent.new_session()
        else:
            # Para otros comandos sin session_id, no creamos ni asignamos nada
            self.session_id = None

    def new_session(self) -> str:
        """
        Crea una nueva sesión.

        Returns:
            El ID de la nueva sesión.
        """
        self.session_id = str(uuid.uuid4())
        self.agent.session_id = self.session_id
        self.agent.new_session()
        return self.session_id

    def send_message(
        self, content: str, stream: bool = True
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Envía un mensaje al agente y retorna su respuesta.
        """
        # Usar directamente el agente de Agno
        for response in self.agent.run(message=content, stream=stream):
            yield response

    def load_session(self, session_id: str) -> None:
        """
        Carga una sesión existente.
        """
        self.session_id = session_id
        self.agent.session_id = session_id
        self.agent.load_session()

    def delete_session(self, session_id: str) -> None:
        """
        Elimina una sesión.
        """
        self.agent.delete_session(session_id)
        if self.session_id == session_id:
            self.new_session()

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        Lista todas las sesiones disponibles.
        """
        # Delegar en el adaptador de almacenamiento
        return self.storage.list_sessions()

    def get_messages(
        self, session_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Message]:
        """
        Obtiene los mensajes de una sesión.
        """
        sid = session_id or self.session_id
        # Obtener mensajes directamente del agente
        agno_messages = self.agent.get_messages_for_session(sid)

        # Convertir al formato de nuestro dominio
        messages = []
        for msg in agno_messages:
            if hasattr(msg, "role") and hasattr(msg, "content"):
                messages.append(Message(role=msg.role, content=msg.content))

        # Aplicar límite
        if limit and len(messages) > limit:
            messages = messages[-limit:]

        return messages

    def set_session_name_from_message(self, message: str) -> None:
        """
        Establece el nombre de la sesión basado en el primer mensaje del usuario.

        Args:
            message: El mensaje del usuario.
        """
        # Dividir el mensaje en palabras
        words = message.split()

        # Tomar las primeras 10 palabras (o menos si el mensaje es más corto)
        session_name_words = words[:10]

        # Crear el nombre de la sesión
        if len(words) > 10:
            session_name = " ".join(session_name_words) + "..."
        else:
            session_name = " ".join(session_name_words)

        # Limitar el nombre a un máximo de 100 caracteres (para seguridad)
        if len(session_name) > 100:
            session_name = session_name[:97] + "..."

        # Asignar el nombre a la sesión
        self.agent.session_name = session_name
