import uuid
from typing import Dict, Any, List, Optional, Generator

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.openrouter import OpenRouter
from agno.storage.sqlite import SqliteStorage
from agno.tools.reasoning import ReasoningTools

from src.cli_coding_agent.agent.agent_config import agent_config
from src.cli_coding_agent.agent.tools.agno_wrappers import ALL_TOOLS
from src.cli_coding_agent.agent.db_and_session import DatabaseSessionManager


class CodeAgent:
    """
    Agente de código que encapsula toda la lógica de interacción con el modelo de IA.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        with_tools: bool = False,
    ):
        """
        Inicializa el agente de código.

        Args:
            session_id: ID de sesión opcional. Si no se proporciona, se crea uno nuevo.
            with_tools: Si se deben habilitar las herramientas para el agente.
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.session_name = None

        # Configuración del agente
        self.instructions = agent_config.AGENT_INSTRUCTIONS
        self.db_file = agent_config.DB_FILE
        self.table_name = agent_config.TABLE_NAME
        self.temperature = agent_config.TEMPERATURE
        self.max_tokens = agent_config.MAX_TOKENS
        self.top_p = agent_config.TOP_P
        self.reasoning = agent_config.REASONING
        self.max_mode = agent_config.MAX_MODE

        # Configuración del modelo según el modo
        if self.max_mode:
            self.api_key = agent_config.ANTHROPIC_API_KEY
            self.model_id = agent_config.ANTHROPIC_MODEL_ID
        else:
            self.api_key = agent_config.OPENROUTER_API_KEY
            self.model_id = agent_config.OPENROUTER_MODEL_ID

        if not self.api_key:
            raise ValueError(
                "Se requiere una clave API para el modelo. Proporcione api_key o configurela en el archivo .env"
            )

        self.with_tools = with_tools

        # Inicializar el manejador de base de datos y sesiones
        self.db_manager = DatabaseSessionManager(self.db_file, self.table_name)

        self._initialize_agent()

    def _initialize_agent(self):
        """Inicializa el agente interno de Agno con la configuración adecuada."""
        if self.max_mode:
            model = Claude(
                id=self.model_id,
                api_key=self.api_key,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
            )
        else:
            model = OpenRouter(
                id=self.model_id,
                api_key=self.api_key,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
            )

        storage = SqliteStorage(db_file=self.db_file, table_name=self.table_name)

        agent_tools = []
        if self.with_tools:
            agent_tools.extend(ALL_TOOLS)
        if self.with_tools and self.reasoning:
            agent_tools.append(ReasoningTools(add_instructions=True, add_few_shot=True))

        self.agent = Agent(
            name="Asistente de Código",
            instructions=self.instructions,
            model=model,
            storage=storage,
            session_id=self.session_id,
            tools=agent_tools,
            add_datetime_to_instructions=agent_config.ADD_DATETIME_TO_INSTRUCTIONS,
            add_history_to_messages=agent_config.ADD_HISTORY_TO_MESSAGES,
            num_history_runs=agent_config.NUM_HISTORY_RUNS,
            markdown=agent_config.MARKDOWN,
            show_tool_calls=agent_config.SHOW_TOOL_CALLS,
        )

    def chat(
        self, message: str, stream: bool = True
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Envía un mensaje al agente y obtiene su respuesta.

        Args:
            message: Mensaje del usuario.
            stream: Si la respuesta debe ser transmitida en tiempo real.

        Returns:
            Generador que produce fragmentos de la respuesta.
        """
        for response in self.agent.run(message=message, stream=stream):
            yield response

    def set_session_name(self, name: str) -> None:
        """
        Establece el nombre de la sesión actual.

        Args:
            name: Nombre para la sesión.
        """
        self.session_name = name
        self.agent.session_name = name
        self.db_manager.set_session_name(self.session_id, name)

    def set_session_name_from_message(self, message: str) -> None:
        """
        Establece el nombre de la sesión basado en el mensaje del usuario.

        Args:
            message: Mensaje del usuario.
        """
        session_name = self.db_manager.set_session_name_from_message(
            self.session_id, message
        )
        self.session_name = session_name
        self.agent.session_name = session_name

    def new_session(self) -> str:
        """
        Crea una nueva sesión.

        Returns:
            ID de la nueva sesión.
        """
        self.session_id = str(uuid.uuid4())
        self.agent.session_id = self.session_id
        self.agent.new_session()
        self.session_name = None

        # Crear registro en la base de datos
        self.db_manager.create_new_session_record(self.session_id)

        return self.session_id

    def load_session(self, session_id: str) -> None:
        """
        Carga una sesión existente.

        Args:
            session_id: ID de la sesión a cargar.
        """
        self.session_id = session_id
        self.agent.session_id = session_id
        self.agent.load_session()

        # Recuperar nombre de la sesión si existe
        session_name = self.db_manager.get_session_name(session_id)
        if session_name:
            self.session_name = session_name
            self.agent.session_name = session_name
            print(f"Nombre de sesión cargado: '{session_name}'")

    def delete_session(self, session_id: str) -> None:
        """
        Elimina una sesión.

        Args:
            session_id: ID de la sesión a eliminar.
        """
        # Eliminar registro de la base de datos
        self.db_manager.delete_session_record(session_id)

        # Eliminar la sesión a través de la API de Agno
        self.agent.delete_session(session_id)

        # Si era la sesión actual, crear una nueva
        if self.session_id == session_id:
            self.new_session()

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        Lista todas las sesiones disponibles.

        Returns:
            Lista de diccionarios con información de las sesiones.
        """
        return self.db_manager.list_sessions()

    def get_messages(
        self, session_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene los mensajes de una sesión.

        Args:
            session_id: ID de la sesión. Si no se proporciona, se usa la sesión actual.
            limit: Número máximo de mensajes a retornar.

        Returns:
            Lista de mensajes de la sesión.
        """
        sid = session_id or self.session_id

        # Método 1: Usar directamente el agente
        try:
            current_session = self.session_id
            if sid != current_session:
                self.agent.session_id = sid
                self.agent.load_session()

            try:
                messages = self.agent.get_messages()
                if limit is not None and limit > 0 and messages:
                    messages = messages[-limit:]

                if sid != current_session:
                    self.agent.session_id = current_session
                    self.agent.load_session()

                if messages:
                    return messages
            except Exception as e:
                print(
                    f"Error al obtener mensajes a través de la API del agente: {str(e)}"
                )
                if sid != current_session:
                    self.agent.session_id = current_session
                    self.agent.load_session()
        except Exception as e:
            print(f"Error general en el primer método: {str(e)}")

        # Método 2: Intentar con la API antigua
        try:
            if hasattr(self.agent, "get_messages_for_session"):
                messages = self.agent.get_messages_for_session(sid)
                if limit is not None and limit > 0 and messages:
                    messages = messages[-limit:]
                if messages:
                    return messages
        except Exception as e:
            print(f"Error con get_messages_for_session: {str(e)}")

        # Método 3: Acceder directamente a la base de datos
        print("Intentando acceder directamente a la base de datos...")
        return self.db_manager.get_messages_from_db(sid, limit)

    @classmethod
    def create_with_config(
        cls,
        api_key: Optional[str] = None,
        session_id: Optional[str] = None,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> "CodeAgent":
        """
        Crea una instancia del agente con configuración personalizada.

        Args:
            api_key: Clave API para el modelo. Si no se proporciona, se toma de la configuración.
            session_id: ID de sesión opcional.
            custom_config: Configuración personalizada para sobrescribir valores predeterminados.

        Returns:
            Una instancia configurada del agente.
        """
        # Para mantener compatibilidad, pero la configuración se maneja en agent_config
        return cls(
            session_id=session_id,
            with_tools=custom_config.get("with_tools", False)
            if custom_config
            else False,
        )
