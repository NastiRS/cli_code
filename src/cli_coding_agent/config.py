from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuración de la aplicación."""

    # API keys
    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY: Optional[str] = None

    # Configuración de base de datos
    DB_FILE: str = "database/code_agent.db"
    TABLE_NAME: str = "code_agent"

    # Configuración del modelo
    MODEL_ID: str = "claude-3-7-sonnet-latest"
    NUM_HISTORY_RUNS: int = 10

    # Instrucciones para el agente
    AGENT_INSTRUCTIONS: str = """Eres un asistente de programación experto que ayuda con código Python.
    
    Reglas a seguir:
    1. Responde de manera concisa y clara a preguntas sobre programación.
    2. Cuando te pidan código, muestra ejemplos prácticos con explicaciones breves.
    3. Si el usuario necesita ayuda con librerías o frameworks específicos, proporciona ejemplos de uso adecuados.
    4. Utiliza el formateo markdown apropiado para resaltar código y conceptos importantes.
    5. Mantén tus respuestas enfocadas en resolver el problema del usuario.
    """

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instancia global de configuración
settings = Settings()
