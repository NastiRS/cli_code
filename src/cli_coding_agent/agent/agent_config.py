from typing import Dict, Any, Optional, List
from pydantic_settings import BaseSettings


class AgentConfigSettings(BaseSettings):
    """Configuración del agente de código utilizando Pydantic Settings"""

    # API keys
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Configuración de base de datos
    DB_FILE: str = "database/code_agent.db"
    TABLE_NAME: str = "code_agent"

    # Modelo base a utilizar
    DEFAULT_MODEL_ID: str = "claude-sonnet-4-20250514"

    # Número de interacciones de historial a incluir en cada consulta
    NUM_HISTORY_RUNS: int = 10

    # Temperatura para el modelo (determinismo vs. creatividad)
    TEMPERATURE: float = 0.7

    # Instrucciones generales para el agente
    AGENT_INSTRUCTIONS: str = """Eres un asistente de programación experto que ayuda con código Python.
    
    Reglas a seguir:
    1. Responde de manera concisa y clara a preguntas sobre programación.
    2. Cuando te pidan código, muestra ejemplos prácticos con explicaciones breves.
    3. Si el usuario necesita ayuda con librerías o frameworks específicos, proporciona ejemplos de uso adecuados.
    4. Utiliza el formateo markdown apropiado para resaltar código y conceptos importantes.
    5. Mantén tus respuestas enfocadas en resolver el problema del usuario.
    6. Sugiere enfoques alternativos cuando sea apropiado, explicando brevemente las ventajas y desventajas.
    7. Cuando analices código, explica claramente cómo funciona y sugiere mejoras si es necesario.
    8. Cuando uses herramientas, NO anuncies que vas a utilizarlas (evita frases como "voy a utilizar la herramienta X"). Simplemente úsalas y responde directamente con el resultado obtenido.
    """

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class AgentConfig(AgentConfigSettings):
    """Clase que extiende la configuración con métodos adicionales"""

    # Configuración adicional que se puede pasar al modelo
    def get_model_config(self) -> Dict[str, Any]:
        """Retorna la configuración completa para el modelo"""
        return {
            "model_id": self.DEFAULT_MODEL_ID,
            "temperature": self.TEMPERATURE,
            "max_tokens": 4096,
            "top_p": 1.0,
            "add_history_to_messages": True,
            "add_datetime_to_instructions": True,
            "num_history_runs": self.NUM_HISTORY_RUNS,
            "markdown": True,
        }

    def get_agent_config(
        self,
        session_id: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Retorna la configuración completa para el agente

        Args:
            session_id: ID de sesión opcional para el agente
            tools: Lista de herramientas a habilitar para el agente

        Returns:
            Configuración completa para inicializar un agente
        """
        config = {
            "name": "Asistente de Código",
            "instructions": self.AGENT_INSTRUCTIONS,
            **self.get_model_config(),
        }

        if session_id:
            config["session_id"] = session_id

        if tools:
            config["tools"] = tools

        return config


# Instancia global de la configuración del agente
agent_config = AgentConfig()
