from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any

from src.cli_coding_agent.domain.schemas import Session, Message


class StoragePort(ABC):
    """Puerto que define las operaciones de almacenamiento."""

    @abstractmethod
    def save_session(self, session: Session) -> None:
        """Guarda una sesión en el almacenamiento."""
        pass

    @abstractmethod
    def load_session(self, session_id: str) -> Session:
        """Carga una sesión desde el almacenamiento."""
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Elimina una sesión del almacenamiento."""
        pass

    @abstractmethod
    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lista todas las sesiones disponibles."""
        pass

    @abstractmethod
    def add_message(self, session_id: str, message: Message) -> None:
        """Añade un mensaje a una sesión existente."""
        pass

    @abstractmethod
    def get_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Message]:
        """Obtiene los mensajes de una sesión específica."""
        pass
