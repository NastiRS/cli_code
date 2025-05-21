import os
import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime

from agno.storage.sqlite import SqliteStorage
from agno.agent import Agent

from src.cli_coding_agent.domain.schemas import Session, Message
from src.cli_coding_agent.ports.storage_port import StoragePort


class SQLiteAdapter(StoragePort):
    """Adaptador que implementa el almacenamiento usando SQLite a través de Agno."""

    def __init__(
        self, db_file: str = "database/code_agent.db", table_name: str = "code_agent"
    ):
        """
        Inicializa el adaptador de SQLite.

        Args:
            db_file: Ruta al archivo de base de datos SQLite.
            table_name: Nombre de la tabla en la base de datos.
        """
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        # Crear el almacenamiento SQLite de Agno
        self.storage = SqliteStorage(db_file=db_file, table_name=table_name)
        self.db_file = db_file
        self.table_name = table_name

        # Crear un agente temporal para operaciones que requieren un agente
        self.agent = Agent(
            name="StorageAgent", instructions="", model=None, storage=self.storage
        )

    def save_session(self, session: Session) -> None:
        """
        Guarda una sesión en el almacenamiento.
        """
        # En Agno, configuramos el ID y nombre de la sesión en el agente
        self.agent.session_id = session.session_id
        if session.name:
            self.agent.session_name = session.name

    def load_session(self, session_id: str) -> Session:
        """
        Carga una sesión desde el almacenamiento.
        """
        try:
            # Configurar el agente con el ID de sesión
            self.agent.session_id = session_id
            # Cargar la sesión
            self.agent.load_session()

            # Obtener mensajes
            messages = self.get_messages(session_id)

            return Session(
                session_id=session_id,
                name=self.agent.session_name,
                created_at=datetime.now(),  # No tenemos la fecha original, usamos la actual
                messages=messages,
            )
        except Exception as e:
            raise ValueError(f"Error al cargar la sesión: {str(e)}")

    def delete_session(self, session_id: str) -> None:
        """
        Elimina una sesión del almacenamiento.
        """
        # La API de Agno proporciona un método directo para esto
        self.storage.delete_session(session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        Lista todas las sesiones disponibles.
        """
        try:
            # Consultar directamente la base de datos SQLite
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Intentar obtener las sesiones directamente de la base de datos
            try:
                cursor.execute(
                    f"SELECT DISTINCT session_id FROM {self.table_name}_sessions"
                )
                sessions_rows = cursor.fetchall()

                sessions = []
                for row in sessions_rows:
                    session_id = row[0]
                    # Intentar obtener el nombre de la sesión si existe
                    try:
                        cursor.execute(
                            f"SELECT session_name FROM {self.table_name}_sessions WHERE session_id = ? LIMIT 1",
                            (session_id,),
                        )
                        session_name_row = cursor.fetchone()
                        session_name = (
                            session_name_row[0] if session_name_row else "Sin nombre"
                        )
                    except Exception:
                        session_name = "Sin nombre"

                    sessions.append(
                        {"session_id": session_id, "session_name": session_name}
                    )

                return sessions

            except sqlite3.OperationalError:
                # Si la tabla no existe, probamos con otra estructura
                try:
                    cursor.execute(f"SELECT DISTINCT session_id FROM {self.table_name}")
                    sessions_rows = cursor.fetchall()

                    sessions = []
                    for row in sessions_rows:
                        session_id = row[0]
                        sessions.append(
                            {"session_id": session_id, "session_name": "Sin nombre"}
                        )

                    return sessions
                except Exception:
                    return []

        except Exception as e:
            print(f"Error al listar sesiones: {str(e)}")
            return []
        finally:
            if "conn" in locals():
                conn.close()

    def add_message(self, session_id: str, message: Message) -> None:
        """
        Añade un mensaje a una sesión existente.
        """
        # Para usuario, podemos usar directamente el método run del agente
        if message.role == "user":
            self.agent.session_id = session_id
            try:
                # Para evitar la generación de respuestas, usamos un modelo None temporal
                original_model = self.agent.model
                self.agent.model = None
                # Ejecutar sin stream y sin esperar respuesta
                self.agent.run(message=message.content, stream=False)
                # Restaurar el modelo original
                self.agent.model = original_model
            except Exception:
                # Si falla, no hacer nada especial, simplemente continuar
                pass
        # Para mensajes del asistente, no hay una API directa fácil de usar
        # en este adaptador simplificado, así que no hacemos nada

    def get_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Message]:
        """
        Obtiene los mensajes de una sesión específica.
        """
        try:
            # Configurar el agente para la sesión
            self.agent.session_id = session_id
            # Obtener mensajes a través del agente
            agno_messages = self.agent.get_messages_for_session(session_id)

            # Convertir al formato de nuestras entidades
            messages = []
            for msg in agno_messages:
                if hasattr(msg, "role") and hasattr(msg, "content"):
                    # Crear mensaje en nuestro formato
                    messages.append(
                        Message(
                            role=msg.role,
                            content=msg.content,
                            timestamp=getattr(msg, "created_at", datetime.now()),
                            message_id=getattr(msg, "id", None),
                        )
                    )

            # Aplicar límite si es necesario
            if limit and len(messages) > limit:
                messages = messages[-limit:]

            return messages
        except Exception:
            # Si hay algún error, retornar lista vacía
            return []
