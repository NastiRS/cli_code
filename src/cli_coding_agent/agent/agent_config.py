from typing import Optional
from pydantic_settings import BaseSettings
from src.cli_coding_agent.agent.agent_instructions import instructions


class AgentConfigSettings(BaseSettings):
    """Configuración del agente de código utilizando Pydantic Settings"""

    # API keys
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None

    # Configuración de base de datos
    DB_FILE: str = "database/code_agent.db"
    TABLE_NAME: str = "code_agent"

    # Modelo base a utilizar
    ANTHROPIC_MODEL_ID: str = "claude-sonnet-4-20250514"
    OPENROUTER_MODEL_ID: str = "gpt-4.1-mini"
    MAX_MODE: bool = False
    REASONING: bool = True

    # Número de interacciones de historial a incluir en cada consulta
    NUM_HISTORY_RUNS: int = 15

    # Temperatura para el modelo (determinismo vs. creatividad)
    TEMPERATURE: float = 0.7

    # Configuración adicional del modelo
    MAX_TOKENS: int = 4096
    TOP_P: float = 1.0
    ADD_HISTORY_TO_MESSAGES: bool = True
    ADD_DATETIME_TO_INSTRUCTIONS: bool = True
    MARKDOWN: bool = True
    SHOW_TOOL_CALLS: bool = True

    # Instrucciones generales para el agente
    AGENT_INSTRUCTIONS: str = instructions

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


agent_config = AgentConfigSettings()
