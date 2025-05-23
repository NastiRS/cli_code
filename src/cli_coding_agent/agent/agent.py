import uuid
import os
import sqlite3
import datetime
from typing import Dict, Any, List, Optional, Generator

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.storage.sqlite import SqliteStorage

from src.cli_coding_agent.agent.agent_config import agent_config
from src.cli_coding_agent.agent.tools.tools import ALL_TOOLS


class CodeAgent:
    """
    Agente de código que encapsula toda la lógica de interacción con el modelo de IA.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
        instructions: Optional[str] = None,
        db_file: Optional[str] = None,
        table_name: Optional[str] = None,
        with_tools: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
    ):
        """
        Inicializa el agente de código.

        Args:
            session_id: ID de sesión opcional. Si no se proporciona, se crea uno nuevo.
            model_id: ID del modelo a utilizar. Si no se proporciona, se usa el predeterminado.
            api_key: Clave API para el modelo. Si no se proporciona, se toma de la configuración.
            instructions: Instrucciones personalizadas para el agente.
            db_file: Ruta al archivo de base de datos SQLite.
            table_name: Nombre de la tabla en la base de datos.
            with_tools: Si se deben habilitar las herramientas para el agente.
            temperature: Temperatura del modelo.
            max_tokens: Máximo número de tokens.
            top_p: Valor top_p para el modelo.
        """

        self.session_id = session_id or str(uuid.uuid4())
        self.session_name = None

        self.model_id = agent_config.DEFAULT_MODEL_ID
        self.instructions = agent_config.AGENT_INSTRUCTIONS
        self.db_file = agent_config.DB_FILE
        self.table_name = agent_config.TABLE_NAME
        self.temperature = agent_config.TEMPERATURE
        self.max_tokens = agent_config.MAX_TOKENS
        self.top_p = agent_config.TOP_P
        self.api_key = agent_config.ANTHROPIC_API_KEY

        if not self.api_key:
            raise ValueError(
                "Se requiere una clave API para el modelo. Proporcione api_key o configure ANTHROPIC_API_KEY en el archivo .env"
            )

        self.with_tools = with_tools

        self._initialize_agent()

    def _initialize_agent(self):
        """Inicializa el agente interno de Agno con la configuración adecuada."""
        model = Claude(
            id=self.model_id,
            api_key=self.api_key,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
        )

        storage = SqliteStorage(db_file=self.db_file, table_name=self.table_name)

        tools = ALL_TOOLS if self.with_tools else None

        # Crear el agente usando todas las configuraciones de agent_config
        self.agent = Agent(
            name="Asistente de Código",
            instructions=self.instructions,
            model=model,
            storage=storage,
            session_id=self.session_id,
            tools=tools,
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
        # Utilizar directamente el agente de Agno sin procesamiento complejo
        # Agno maneja automáticamente las tool calls y el formateo
        for response in self.agent.run(message=message, stream=stream):
            yield response

    def set_session_name(self, name: str) -> None:
        """
        Establece el nombre de la sesión actual.

        Args:
            name: Nombre para la sesión.
        """
        # Guardar el nombre en el objeto
        self.session_name = name
        self.agent.session_name = name

        # Guardar el nombre directamente en la base de datos
        try:
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)

            # Conectar a la base de datos
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Obtener la fecha actual
            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Verificar si la tabla existe
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                (f"{self.table_name}_sessions",),
            )
            table_exists = cursor.fetchone() is not None

            if table_exists:
                # Verificar la estructura de la tabla
                cursor.execute(f"PRAGMA table_info({self.table_name}_sessions)")
                columns = [info[1] for info in cursor.fetchall()]

                # Recrear la tabla con la estructura correcta si no tiene las columnas necesarias
                if "session_id" not in columns:
                    # La tabla existe pero no tiene la estructura correcta
                    # Guardar datos antiguos
                    try:
                        cursor.execute(
                            f"SELECT session_name FROM {self.table_name}_sessions"
                        )
                        old_names = cursor.fetchall()
                    except Exception:
                        old_names = []

                    # Eliminar tabla antigua
                    cursor.execute(f"DROP TABLE {self.table_name}_sessions")

                    # Crear nueva tabla
                    cursor.execute(f"""
                        CREATE TABLE {self.table_name}_sessions (
                            session_id TEXT PRIMARY KEY,
                            session_name TEXT,
                            created_at TEXT
                        )
                    """)

                    # Guardar el nombre actual
                    cursor.execute(
                        f"""
                        INSERT INTO {self.table_name}_sessions (session_id, session_name, created_at)
                        VALUES (?, ?, ?)
                    """,
                        (self.session_id, name, current_date),
                    )

                    print(
                        f"Tabla {self.table_name}_sessions recreada con la estructura correcta"
                    )
                elif "created_at" not in columns:
                    # La tabla existe pero no tiene la columna created_at
                    try:
                        # Modificar la tabla para añadir created_at
                        cursor.execute(
                            f"ALTER TABLE {self.table_name}_sessions ADD COLUMN created_at TEXT"
                        )

                        # Insertar o actualizar el registro
                        cursor.execute(
                            f"""
                            INSERT OR REPLACE INTO {self.table_name}_sessions (session_id, session_name, created_at)
                            VALUES (?, ?, ?)
                        """,
                            (self.session_id, name, current_date),
                        )
                    except sqlite3.OperationalError as e:
                        # Si no se puede modificar, usar la estructura existente
                        print(f"No se pudo añadir la columna created_at: {str(e)}")
                        cursor.execute(
                            f"""
                            INSERT OR REPLACE INTO {self.table_name}_sessions (session_id, session_name)
                            VALUES (?, ?)
                        """,
                            (self.session_id, name),
                        )
                else:
                    # La tabla tiene la estructura correcta
                    cursor.execute(
                        f"""
                        INSERT OR REPLACE INTO {self.table_name}_sessions (session_id, session_name, created_at)
                        VALUES (?, ?, ?)
                    """,
                        (self.session_id, name, current_date),
                    )
            else:
                # La tabla no existe, crearla
                cursor.execute(f"""
                    CREATE TABLE {self.table_name}_sessions (
                        session_id TEXT PRIMARY KEY,
                        session_name TEXT,
                        created_at TEXT
                    )
                """)

                cursor.execute(
                    f"""
                    INSERT INTO {self.table_name}_sessions (session_id, session_name, created_at)
                    VALUES (?, ?, ?)
                """,
                    (self.session_id, name, current_date),
                )

            # Guardar cambios
            conn.commit()
        except Exception as e:
            print(f"Error al guardar el nombre de la sesión: {str(e)}")
        finally:
            if "conn" in locals():
                conn.close()

    def set_session_name_from_message(self, message: str) -> None:
        """
        Establece el nombre de la sesión basado en el mensaje del usuario.

        Args:
            message: Mensaje del usuario.
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

        # Establecer el nombre

        self.set_session_name(session_name)

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

        # Guardar fecha de creación en la base de datos
        try:
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)

            # Conectar a la base de datos
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Obtener la fecha actual
            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                # Crear tabla si no existe
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name}_sessions (
                        session_id TEXT PRIMARY KEY,
                        session_name TEXT,
                        created_at TEXT
                    )
                """)

                # Insertar registro con fecha de creación
                cursor.execute(
                    f"""
                    INSERT INTO {self.table_name}_sessions (session_id, created_at)
                    VALUES (?, ?)
                """,
                    (self.session_id, current_date),
                )

                conn.commit()
            except Exception as e:
                print(f"Error al guardar fecha de creación: {str(e)}")
            finally:
                conn.close()
        except Exception:
            # Ignorar errores, esto no debería impedir la creación de la sesión
            pass

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
        try:
            # Conectar a la base de datos
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Buscar el nombre en la tabla de sesiones
            try:
                cursor.execute(
                    f"""
                    SELECT session_name FROM {self.table_name}_sessions
                    WHERE session_id = ?
                """,
                    (session_id,),
                )

                result = cursor.fetchone()
                if result and result[0]:
                    self.session_name = result[0]
                    self.agent.session_name = result[0]
                    print(f"Nombre de sesión cargado: '{result[0]}'")
            except Exception as e:
                print(f"Error al cargar el nombre de la sesión: {str(e)}")
        finally:
            if "conn" in locals():
                conn.close()

    def delete_session(self, session_id: str) -> None:
        """
        Elimina una sesión.

        Args:
            session_id: ID de la sesión a eliminar.
        """
        # Eliminar también el nombre de la sesión de la base de datos
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            try:
                cursor.execute(
                    f"""
                    DELETE FROM {self.table_name}_sessions
                    WHERE session_id = ?
                """,
                    (session_id,),
                )
                conn.commit()
            except sqlite3.OperationalError:
                # La tabla podría no existir, lo cual está bien
                pass
        except Exception:
            # Ignorar errores en la eliminación del nombre
            pass
        finally:
            if "conn" in locals():
                conn.close()

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
        try:
            # Consultar directamente la base de datos SQLite
            # Asegurarse de que el directorio existe
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Verificar si la tabla de sesiones existe
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                (f"{self.table_name}_sessions",),
            )
            table_exists = cursor.fetchone() is not None

            if table_exists:
                # Verificar columnas disponibles
                cursor.execute(f"PRAGMA table_info({self.table_name}_sessions)")
                columns = [info[1] for info in cursor.fetchall()]

                # Determinar qué datos buscar
                has_session_id = "session_id" in columns
                has_session_name = "session_name" in columns
                has_created_at = "created_at" in columns

                if has_session_id:
                    # Si tiene session_id, usamos esa tabla
                    if has_created_at and has_session_name:
                        query = f"SELECT session_id, session_name, created_at FROM {self.table_name}_sessions"
                    elif has_session_name:
                        query = f"SELECT session_id, session_name FROM {self.table_name}_sessions"
                    else:
                        query = f"SELECT session_id FROM {self.table_name}_sessions"

                    cursor.execute(query)
                    session_rows = cursor.fetchall()

                    sessions = []
                    for row in session_rows:
                        session_data = {"session_id": row[0]}

                        if has_session_name and len(row) > 1:
                            session_data["session_name"] = (
                                row[1] if row[1] else "Sin nombre"
                            )
                        else:
                            session_data["session_name"] = "Sin nombre"

                        if has_created_at and len(row) > 2:
                            session_data["created_at"] = (
                                row[2] if row[2] else "Fecha desconocida"
                            )
                        else:
                            session_data["created_at"] = "Fecha desconocida"

                        sessions.append(session_data)

                    return sessions
                else:
                    # La tabla tiene una estructura incorrecta, intentar usar la tabla principal
                    return self._get_sessions_from_main_table(cursor)
            else:
                # La tabla no existe, intentar usar la tabla principal
                return self._get_sessions_from_main_table(cursor)

        except Exception as e:
            print(f"Error al listar sesiones: {str(e)}")
            return []
        finally:
            if "conn" in locals():
                conn.close()

    def _get_sessions_from_main_table(self, cursor) -> List[Dict[str, Any]]:
        """
        Obtiene las sesiones de la tabla principal.

        Args:
            cursor: Cursor de SQLite.

        Returns:
            Lista de diccionarios con información de las sesiones.
        """
        try:
            # Intentar obtener sesiones de la tabla principal
            cursor.execute(f"SELECT DISTINCT session_id FROM {self.table_name}")
            session_rows = cursor.fetchall()

            sessions = []
            for row in session_rows:
                session_id = row[0]

                # Intentar obtener fecha de creación
                try:
                    cursor.execute(
                        f"SELECT created_at FROM {self.table_name} WHERE session_id = ? LIMIT 1",
                        (session_id,),
                    )
                    created_data = cursor.fetchone()

                    if created_data and created_data[0]:
                        # Convertir timestamp a formato legible
                        try:
                            timestamp = int(created_data[0])
                            created_at = datetime.datetime.fromtimestamp(
                                timestamp
                            ).strftime("%Y-%m-%d %H:%M:%S")
                        except (ValueError, TypeError):
                            created_at = str(created_data[0])
                    else:
                        created_at = "Fecha desconocida"
                except Exception:
                    created_at = "Fecha desconocida"

                sessions.append(
                    {
                        "session_id": session_id,
                        "session_name": "Sin nombre",
                        "created_at": created_at,
                    }
                )

            return sessions
        except Exception as e:
            print(f"Error al obtener sesiones de la tabla principal: {str(e)}")
            return []

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

        # Método 1: Usar directamente el agente (necesitamos cargar primero la sesión)
        try:
            # Si estamos pidiendo mensajes para una sesión que no es la actual,
            # guardamos la sesión actual, cargamos la solicitada, y luego restauramos
            current_session = self.session_id
            if sid != current_session:
                # Cargar temporalmente la sesión solicitada
                print(f"Cargando temporalmente la sesión {sid}...")
                self.agent.session_id = sid
                self.agent.load_session()

            # Intentar obtener mensajes usando la API del agente
            try:
                # Usar el método get_messages() que devuelve todo el historial en lugar de get_messages_for_session
                # que puede tener implementación diferente según la versión de Agno
                messages = self.agent.get_messages()

                # Aquí tenemos acceso a todos los mensajes, limitarlos si es necesario
                if limit is not None and limit > 0 and messages:
                    messages = messages[-limit:]

                print(
                    f"Se encontraron {len(messages)} mensajes a través de la API del agente."
                )

                # Restaurar la sesión original si cambiamos
                if sid != current_session:
                    self.agent.session_id = current_session
                    self.agent.load_session()

                if messages:
                    return messages
            except Exception as e:
                print(
                    f"Error al obtener mensajes a través de la API del agente: {str(e)}"
                )

                # Restaurar la sesión original si cambiamos
                if sid != current_session:
                    self.agent.session_id = current_session
                    self.agent.load_session()
        except Exception as e:
            print(f"Error general en el primer método: {str(e)}")

        # Método 2: Intentar con la API antigua (para compatibilidad)
        try:
            try:
                # Verificar si el método get_messages_for_session existe
                if hasattr(self.agent, "get_messages_for_session"):
                    print("Intentando con get_messages_for_session...")
                    messages = self.agent.get_messages_for_session(sid)

                    if limit is not None and limit > 0 and messages:
                        messages = messages[-limit:]

                    if messages:
                        print(
                            f"Se encontraron {len(messages)} mensajes con get_messages_for_session."
                        )
                        return messages
            except Exception as e:
                print(f"Error con get_messages_for_session: {str(e)}")
        except Exception as e:
            print(f"Error general en el segundo método: {str(e)}")

        # Método 3: Acceder directamente a la base de datos como último recurso
        print("Intentando acceder directamente a la base de datos...")
        return self._get_messages_from_db(sid, limit)

    def _get_messages_from_db(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene los mensajes directamente de la base de datos.

        Args:
            session_id: ID de la sesión.
            limit: Número máximo de mensajes a retornar.

        Returns:
            Lista de mensajes de la sesión.
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # Verificar si existe la tabla principal
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                (self.table_name,),
            )
            if cursor.fetchone() is None:
                print(f"No existe la tabla {self.table_name} en la base de datos.")
                return []

            # Verificar la estructura de la tabla
            cursor.execute(f"PRAGMA table_info({self.table_name})")
            columns = [info[1] for info in cursor.fetchall()]

            # Reportar las columnas encontradas
            print(
                f"Columnas encontradas en la tabla {self.table_name}: {', '.join(columns)}"
            )

            # Verificar si la sesión existe
            cursor.execute(
                f"SELECT COUNT(*) FROM {self.table_name} WHERE session_id = ?",
                (session_id,),
            )
            count = cursor.fetchone()[0]
            if count == 0:
                print(
                    f"No se encontró la sesión {session_id} en la tabla {self.table_name}."
                )
                return []
            else:
                print(f"Sesión {session_id} encontrada en la tabla {self.table_name}.")

            # Obtener todos los datos de la sesión para diagnóstico
            cursor.execute(
                f"SELECT * FROM {self.table_name} WHERE session_id = ?", (session_id,)
            )
            row = cursor.fetchone()

            # Obtener los nombres de columna
            cursor.execute(f"PRAGMA table_info({self.table_name})")
            col_names = [info[1] for info in cursor.fetchall()]

            # Diagnosticar qué columnas tienen datos
            for i, col in enumerate(col_names):
                if col in ["memory", "session_data", "extra_data", "agent_data"]:
                    if row[i]:
                        print(f"La columna '{col}' tiene datos.")
                        try:
                            import json

                            json_data = json.loads(row[i])
                            if col == "memory":
                                # Diagnosticar estructura de memory
                                if "messages" in json_data:
                                    print(
                                        f"  - Encontrados {len(json_data['messages'])} mensajes en memory.messages"
                                    )
                                if (
                                    "history" in json_data
                                    and isinstance(json_data["history"], dict)
                                    and "messages" in json_data["history"]
                                ):
                                    print(
                                        f"  - Encontrados {len(json_data['history']['messages'])} mensajes en memory.history.messages"
                                    )
                                if "runs" in json_data and isinstance(
                                    json_data["runs"], list
                                ):
                                    print(
                                        f"  - Encontrados {len(json_data['runs'])} runs en memory.runs"
                                    )
                                    for i, run in enumerate(json_data["runs"]):
                                        if "messages" in run and isinstance(
                                            run["messages"], list
                                        ):
                                            print(
                                                f"  - Run {i}: {len(run['messages'])} mensajes"
                                            )
                        except Exception as e:
                            print(f"Error al parsear JSON en columna '{col}': {str(e)}")
                    else:
                        print(f"La columna '{col}' está vacía.")

            # Ver si hay mensajes en la API de Agno en otras tablas
            try:
                # Buscar en la tabla de mensajes directamente si existe
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?;",
                    (f"{self.table_name}%",),
                )
                tables = [t[0] for t in cursor.fetchall()]
                print(f"Tablas relacionadas encontradas: {', '.join(tables)}")

                # Buscar en otras tablas posibles
                for table in tables:
                    if table != self.table_name and "messages" in table.lower():
                        try:
                            cursor.execute(
                                f"SELECT COUNT(*) FROM {table} WHERE session_id = ?",
                                (session_id,),
                            )
                            msg_count = cursor.fetchone()[0]
                            print(
                                f"Encontrados {msg_count} mensajes en la tabla {table} para la sesión {session_id}"
                            )

                            if msg_count > 0:
                                cursor.execute(
                                    f"SELECT * FROM {table} WHERE session_id = ? LIMIT 5",
                                    (session_id,),
                                )
                                sample = cursor.fetchall()
                                print(f"Muestra de mensajes en {table}: {sample}")
                        except Exception as e:
                            print(f"Error al buscar en tabla {table}: {str(e)}")
            except Exception as e:
                print(f"Error al buscar mensajes en otras tablas: {str(e)}")

            # Obtener el registro para la sesión con column memory
            if "memory" in columns:
                cursor.execute(
                    f"SELECT memory FROM {self.table_name} WHERE session_id = ?",
                    (session_id,),
                )
                memory_row = cursor.fetchone()

                if not memory_row or not memory_row[0]:
                    print(f"No hay datos de memory para la sesión {session_id}.")
                    return []

                # Parsear el JSON de la memoria
                import json

                memory_data = json.loads(memory_row[0])

                # Extraer mensajes de la memoria
                messages = []
                memory_structure = "desconocida"

                # Buscar mensajes en diferentes estructuras posibles
                if isinstance(memory_data, dict):
                    # Estructura 1: Objeto memory con messages
                    if "messages" in memory_data and isinstance(
                        memory_data["messages"], list
                    ):
                        messages = memory_data["messages"]
                        memory_structure = "memory.messages"
                    # Estructura 2: Objeto memory con history.messages
                    elif (
                        "history" in memory_data
                        and isinstance(memory_data["history"], dict)
                        and "messages" in memory_data["history"]
                    ):
                        messages = memory_data["history"]["messages"]
                        memory_structure = "memory.history.messages"
                    # Estructura 3: Objeto memory con runs que contienen messages
                    elif "runs" in memory_data and isinstance(
                        memory_data["runs"], list
                    ):
                        memory_structure = "memory.runs[].messages"
                        for run in memory_data["runs"]:
                            if "messages" in run and isinstance(run["messages"], list):
                                messages.extend(run["messages"])

                print(f"Estructura de memoria encontrada: {memory_structure}")
                print(f"Total de mensajes encontrados: {len(messages)}")

                # Limitar el número de mensajes si se especificó
                if limit is not None and limit > 0 and messages:
                    messages = messages[-limit:]

                # Formatear los mensajes para mostrarlos
                formatted_messages = []
                for msg in messages:
                    if isinstance(msg, dict):
                        # Extraer role y content
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")

                        # Si content es una lista (formato de Claude), extraer el texto
                        if isinstance(content, list):
                            text_content = ""
                            for item in content:
                                if isinstance(item, dict) and "text" in item:
                                    text_content += item["text"]
                            content = text_content if text_content else str(content)

                        formatted_messages.append({"role": role, "content": content})

                return formatted_messages
            else:
                print(f"La columna 'memory' no existe en la tabla {self.table_name}.")
                return []

        except Exception as e:
            print(f"Error al obtener mensajes de la base de datos: {str(e)}")
            return []
        finally:
            if "conn" in locals():
                conn.close()

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
        # Combinar configuración personalizada con la predeterminada
        config = {}
        if custom_config:
            config.update(custom_config)

        # Crear instancia usando todas las configuraciones disponibles
        return cls(
            session_id=session_id,
            model_id=config.get("model_id", agent_config.DEFAULT_MODEL_ID),
            api_key=api_key or config.get("api_key", agent_config.ANTHROPIC_API_KEY),
            instructions=config.get("instructions", agent_config.AGENT_INSTRUCTIONS),
            db_file=config.get("db_file", agent_config.DB_FILE),
            table_name=config.get("table_name", agent_config.TABLE_NAME),
            with_tools=config.get("with_tools", False),
            temperature=config.get("temperature", agent_config.TEMPERATURE),
            max_tokens=config.get("max_tokens", agent_config.MAX_TOKENS),
            top_p=config.get("top_p", agent_config.TOP_P),
        )
