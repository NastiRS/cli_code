import os
import sqlite3
import datetime
import json
from typing import Dict, Any, List, Optional


class DatabaseSessionManager:
    """
    Maneja toda la lógica de sesiones y base de datos.
    """

    def __init__(self, db_file: str, table_name: str):
        """
        Inicializa el manejador de sesiones y base de datos.

        Args:
            db_file: Ruta al archivo de base de datos SQLite.
            table_name: Nombre de la tabla en la base de datos.
        """
        self.db_file = db_file
        self.table_name = table_name

    def set_session_name(self, session_id: str, name: str) -> None:
        """
        Establece el nombre de una sesión.

        Args:
            session_id: ID de la sesión.
            name: Nombre para la sesión.
        """
        try:
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                (f"{self.table_name}_sessions",),
            )
            table_exists = cursor.fetchone() is not None

            if table_exists:
                cursor.execute(f"PRAGMA table_info({self.table_name}_sessions)")
                columns = [info[1] for info in cursor.fetchall()]

                if "session_id" not in columns:
                    cursor.execute(f"DROP TABLE {self.table_name}_sessions")
                    self._create_sessions_table(cursor)
                    cursor.execute(
                        f"""
                        INSERT INTO {self.table_name}_sessions (session_id, session_name, created_at)
                        VALUES (?, ?, ?)
                    """,
                        (session_id, name, current_date),
                    )
                elif "created_at" not in columns:
                    try:
                        cursor.execute(
                            f"ALTER TABLE {self.table_name}_sessions ADD COLUMN created_at TEXT"
                        )
                        cursor.execute(
                            f"""
                            INSERT OR REPLACE INTO {self.table_name}_sessions (session_id, session_name, created_at)
                            VALUES (?, ?, ?)
                        """,
                            (session_id, name, current_date),
                        )
                    except sqlite3.OperationalError as e:
                        print(f"No se pudo añadir la columna created_at: {str(e)}")
                        cursor.execute(
                            f"""
                            INSERT OR REPLACE INTO {self.table_name}_sessions (session_id, session_name)
                            VALUES (?, ?)
                        """,
                            (session_id, name),
                        )
                else:
                    cursor.execute(
                        f"""
                        INSERT OR REPLACE INTO {self.table_name}_sessions (session_id, session_name, created_at)
                        VALUES (?, ?, ?)
                    """,
                        (session_id, name, current_date),
                    )
            else:
                self._create_sessions_table(cursor)
                cursor.execute(
                    f"""
                    INSERT INTO {self.table_name}_sessions (session_id, session_name, created_at)
                    VALUES (?, ?, ?)
                """,
                    (session_id, name, current_date),
                )

            conn.commit()
        except Exception as e:
            print(f"Error al guardar el nombre de la sesión: {str(e)}")
        finally:
            if "conn" in locals():
                conn.close()

    def _create_sessions_table(self, cursor):
        """Crea la tabla de sesiones con la estructura correcta."""
        cursor.execute(f"""
            CREATE TABLE {self.table_name}_sessions (
                session_id TEXT PRIMARY KEY,
                session_name TEXT,
                created_at TEXT
            )
        """)

    def set_session_name_from_message(self, session_id: str, message: str) -> str:
        """
        Establece el nombre de la sesión basado en el mensaje del usuario.

        Args:
            session_id: ID de la sesión.
            message: Mensaje del usuario.

        Returns:
            El nombre de sesión generado.
        """
        words = message.split()
        session_name_words = words[:10]

        if len(words) > 10:
            session_name = " ".join(session_name_words) + "..."
        else:
            session_name = " ".join(session_name_words)

        if len(session_name) > 100:
            session_name = session_name[:97] + "..."

        self.set_session_name(session_id, session_name)
        return session_name

    def create_new_session_record(self, session_id: str) -> None:
        """
        Crea un registro de nueva sesión en la base de datos.

        Args:
            session_id: ID de la nueva sesión.
        """
        try:
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name}_sessions (
                        session_id TEXT PRIMARY KEY,
                        session_name TEXT,
                        created_at TEXT
                    )
                """)

                cursor.execute(
                    f"""
                    INSERT INTO {self.table_name}_sessions (session_id, created_at)
                    VALUES (?, ?)
                """,
                    (session_id, current_date),
                )

                conn.commit()
            except Exception as e:
                print(f"Error al guardar fecha de creación: {str(e)}")
            finally:
                conn.close()
        except Exception:
            pass

    def get_session_name(self, session_id: str) -> Optional[str]:
        """
        Obtiene el nombre de una sesión.

        Args:
            session_id: ID de la sesión.

        Returns:
            Nombre de la sesión o None si no existe.
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

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
                    return result[0]
                return None
            except Exception as e:
                print(f"Error al cargar el nombre de la sesión: {str(e)}")
                return None
        except Exception:
            return None
        finally:
            if "conn" in locals():
                conn.close()

    def delete_session_record(self, session_id: str) -> None:
        """
        Elimina el registro de una sesión.

        Args:
            session_id: ID de la sesión a eliminar.
        """
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
                pass
        except Exception:
            pass
        finally:
            if "conn" in locals():
                conn.close()

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        Lista todas las sesiones disponibles.

        Returns:
            Lista de diccionarios con información de las sesiones.
        """
        try:
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                (f"{self.table_name}_sessions",),
            )
            table_exists = cursor.fetchone() is not None

            if table_exists:
                cursor.execute(f"PRAGMA table_info({self.table_name}_sessions)")
                columns = [info[1] for info in cursor.fetchall()]

                has_session_id = "session_id" in columns
                has_session_name = "session_name" in columns
                has_created_at = "created_at" in columns

                if has_session_id:
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
                    return self._get_sessions_from_main_table(cursor)
            else:
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
            cursor.execute(f"SELECT DISTINCT session_id FROM {self.table_name}")
            session_rows = cursor.fetchall()

            sessions = []
            for row in session_rows:
                session_id = row[0]

                try:
                    cursor.execute(
                        f"SELECT created_at FROM {self.table_name} WHERE session_id = ? LIMIT 1",
                        (session_id,),
                    )
                    created_data = cursor.fetchone()

                    if created_data and created_data[0]:
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

    def get_messages_from_db(
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

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                (self.table_name,),
            )
            if cursor.fetchone() is None:
                print(f"No existe la tabla {self.table_name} en la base de datos.")
                return []

            cursor.execute(f"PRAGMA table_info({self.table_name})")
            columns = [info[1] for info in cursor.fetchall()]

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

            if "memory" in columns:
                cursor.execute(
                    f"SELECT memory FROM {self.table_name} WHERE session_id = ?",
                    (session_id,),
                )
                memory_row = cursor.fetchone()

                if not memory_row or not memory_row[0]:
                    print(f"No hay datos de memory para la sesión {session_id}.")
                    return []

                memory_data = json.loads(memory_row[0])

                messages = []
                if isinstance(memory_data, dict):
                    if "messages" in memory_data and isinstance(
                        memory_data["messages"], list
                    ):
                        messages = memory_data["messages"]
                    elif (
                        "history" in memory_data
                        and isinstance(memory_data["history"], dict)
                        and "messages" in memory_data["history"]
                    ):
                        messages = memory_data["history"]["messages"]
                    elif "runs" in memory_data and isinstance(
                        memory_data["runs"], list
                    ):
                        for run in memory_data["runs"]:
                            if "messages" in run and isinstance(run["messages"], list):
                                messages.extend(run["messages"])

                if limit is not None and limit > 0 and messages:
                    messages = messages[-limit:]

                formatted_messages = []
                for msg in messages:
                    if isinstance(msg, dict):
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")

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
