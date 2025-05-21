from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class Message:
    """Entidad que representa un mensaje en una conversación."""

    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: Optional[str] = None


@dataclass
class Session:
    """Entidad que representa una sesión de chat."""

    session_id: str
    name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)
