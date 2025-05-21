# CLI de Chat con Agente de Código

Esta aplicación implementa una interfaz CLI para chatear con un asistente de programación inteligente utilizando la biblioteca Agno y Claude de Anthropic.

## Requisitos

- Python 3.12 o superior
- [uv](https://github.com/astral-sh/uv) - Gestor de paquetes y entornos virtuales para Python
- Las dependencias están definidas en el archivo `pyproject.toml`:
  - agno>=1.5.2
  - anthropic>=0.51.0
  - openai>=1.79.0
  - pydantic-settings>=2.9.1
  - rich>=14.0.0
  - sqlalchemy>=2.0.41
  - typer>=0.15.4

## Configuración

1. Clona este repositorio
2. Configura el entorno e instala las dependencias con uv:
   ```bash
   # uv se encargará de crear el entorno virtual e instalar todas las dependencias
   uv sync
   
   # Activar el entorno virtual
   # En Windows
   .venv\Scripts\activate
   # En Linux/MacOS
   source .venv/bin/activate
   ```

3. Crea un archivo `.env` en la raíz del proyecto con tus claves API:
   ```
   ANTHROPIC_API_KEY=tu_clave_api_de_anthropic
   OPENAI_API_KEY=tu_clave_api_de_openai  # Opcional, no usado actualmente
   ```

## Arquitectura

Este proyecto sigue los principios de Arquitectura Hexagonal (Ports and Adapters) para mantener una estructura modular y fácil de mantener:

```
src/cli_coding_agent/
  ├── adapters/           # Implementaciones concretas que conectan con bibliotecas externas
  │   ├── storage/        # Adaptadores para almacenamiento (SQLite, etc.)
  │   └── claude_adapter.py  # Adaptador para el modelo Claude
  ├── agent/              # Módulo del agente de código
  │   ├── agent.py        # Implementación principal del agente
  │   ├── agent_config.py # Configuración del agente
  │   └── tools.py        # Herramientas que puede usar el agente
  ├── application/        # Lógica de la aplicación
  │   ├── chat_service.py # Servicio principal que orquesta la funcionalidad
  │   └── cli.py          # Interfaz de línea de comandos
  ├── domain/             # Entidades y lógica de negocio
  │   └── schemas.py      # Definiciones de Message, Session, etc.
  ├── ports/              # Interfaces/puertos para desacoplar componentes
  │   ├── ai_model_port.py   # Interfaz para modelos de IA
  │   └── storage_port.py    # Interfaz para almacenamiento
  ├── utils/              # Utilidades compartidas
  │   └── env_checker.py  # Verificador de archivo .env
  ├── config.py           # Configuración de la aplicación
  └── __main__.py         # Punto de entrada para la ejecución directa
```

## Uso

### Iniciar un chat

```bash
# Usando el comando instalado
clicode chat

# O alternativamente con python
python -m src.cli_coding_agent chat

# Para habilitar las herramientas del agente
clicode chat --tools
```

Este comando inicia un chat con el asistente de código. El historial se guarda automáticamente en una base de datos SQLite. La primera vez que inicies una conversación, el nombre de la sesión se generará automáticamente a partir de las primeras 10 palabras de tu mensaje.

#### Opciones disponibles

- `--session`, `-s`: Especifica un ID de sesión para continuar una conversación existente
- `--nuevo`, `-n`: Inicia una nueva sesión (ignorará la sesión activa)
- `--db`: Ruta al archivo de base de datos (predeterminado: `database/code_agent.db`)
- `--table`: Nombre de la tabla en la base de datos (predeterminado: `code_agent`)
- `--tools`: Habilita las herramientas para el agente (análisis de sistema, conteo de líneas de código, etc.)

### Comandos disponibles durante el chat

Durante una sesión de chat, puedes usar los siguientes comandos:

- `/ayuda`: Muestra la lista de comandos disponibles
- `/salir`: Sale del chat
- `/id`: Muestra el ID de la sesión actual

También puedes salir del chat escribiendo "salir", "exit" o "quit".

### Gestión de sesiones

La gestión de sesiones se realiza a través del comando `session` con diversas opciones:

#### Listar sesiones
```bash
clicode session --list
# O usando la forma abreviada
clicode session -l
```

Muestra todas las sesiones guardadas, con sus IDs, nombres y fechas de creación en una tabla formateada.

#### Eliminar una sesión
```bash
clicode session --delete <id_de_sesion>
# O usando la forma abreviada
clicode session -d <id_de_sesion>
```

Elimina permanentemente una sesión específica de la base de datos. Pedirá confirmación a menos que se use la opción `--yes` o `-y`.

#### Eliminar todas las sesiones
```bash
clicode session --delete-all
# O usando la forma abreviada
clicode session -a
```

Elimina permanentemente todas las sesiones de la base de datos. Pedirá confirmación a menos que se use la opción `--yes` o `-y`.

#### Ver mensajes de una sesión
```bash
clicode session --messages <id_de_sesion> --limit <numero>
# O usando la forma abreviada
clicode session -m <id_de_sesion>
```

Muestra los mensajes intercambiados en una sesión específica. Por defecto muestra los últimos 10 mensajes.

#### Opciones globales para el comando session

- `--yes`, `-y`: Confirma operaciones destructivas sin preguntar
- `--db`: Ruta al archivo de base de datos
- `--table`: Nombre de la tabla en la base de datos
- `--limit`: Número de mensajes a mostrar (con `--messages`)

#### Ejemplos de uso

```bash
# Listar todas las sesiones
clicode session -l

# Eliminar una sesión específica con confirmación
clicode session -d 8d8c0f45-3516-4d00-8313-73857b3c7419

# Eliminar una sesión sin confirmación
clicode session -d 8d8c0f45-3516-4d00-8313-73857b3c7419 -y

# Eliminar todas las sesiones sin confirmación
clicode session -a -y

# Ver los últimos 20 mensajes de una sesión
clicode session -m 8d8c0f45-3516-4d00-8313-73857b3c7419 --limit 20
```

## Ayuda

Para ver todos los comandos disponibles:

```bash
clicode --help
```

Para obtener ayuda sobre un comando específico:

```bash
clicode <comando> --help
```

Por ejemplo:

```bash
clicode session --help
```

## Herramientas del Agente

El agente de código puede utilizar varias herramientas cuando se habilita con la opción `--tools`. Las herramientas disponibles incluyen:

- **get_system_info**: Obtiene información sobre el sistema operativo, versión de Python, etc.
- **count_lines_of_code**: Analiza un directorio y cuenta las líneas de código por tipo de archivo.
- **check_internet_connection**: Verifica la conexión a internet intentando conectarse a un servidor específico.

Puedes solicitar al agente que utilice estas herramientas durante el chat, por ejemplo:
```
¿Puedes analizar cuántas líneas de código tiene este proyecto?
¿Podrías verificar si tengo conexión a internet?
¿Qué sistema operativo estoy usando?
```

## Personalización

Puedes personalizar el comportamiento del agente modificando la configuración en:

- `src/cli_coding_agent/config.py`: Configuración general de la aplicación
- `src/cli_coding_agent/agent/agent_config.py`: Configuración específica del agente

Algunas opciones interesantes:
- Cambiar las instrucciones o personalidad del asistente
- Ajustar el modelo de Claude a usar (claude-3-opus, claude-3-sonnet, etc.)
- Modificar el número de mensajes de historial que se conservan
- Cambiar la ubicación de la base de datos SQLite
- Ajustar la temperatura del modelo para respuestas más creativas o deterministas

## Extender el Agente

Para añadir nuevas herramientas al agente, puedes editar el archivo `src/cli_coding_agent/agent/tools.py` y añadir tus propias funciones.

## Desarrollo

Para desarrollar o modificar este proyecto:

```bash
# Instalar en modo desarrollo
uv add --dev .

# Actualizar dependencias
uv sync
```

## Licencia

Este proyecto está licenciado bajo MIT.
