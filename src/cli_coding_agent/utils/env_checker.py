"""
Utilidad para verificar y configurar el archivo .env requerido.
"""

from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt

console = Console()


def check_env_file():
    """
    Verifica si existe un archivo .env y contiene las claves API necesarias.
    Si no existe o no está configurado, guía al usuario para crearlo.

    Returns:
        bool: True si el archivo existe y está correctamente configurado.
    """
    base_dir = Path(__file__).parent.parent.parent.parent
    env_path = base_dir / ".env"

    # Verificar si el archivo existe
    if not env_path.exists():
        console.print(
            "[bold red]Archivo .env no encontrado en la raíz del proyecto.[/bold red]"
        )
        create = Prompt.ask(
            "¿Deseas crear ahora el archivo .env?", choices=["s", "n"], default="s"
        )

        if create.lower() == "s":
            return _create_env_file(env_path)
        else:
            console.print(
                "\n[bold yellow]Por favor, crea manualmente un archivo .env en la raíz "
                "del proyecto con el siguiente contenido:[/bold yellow]"
            )
            _show_env_template()
            return False

    # Verificar contenido del archivo
    with open(env_path, "r") as f:
        env_content = f.read()

    # Comprobar si contiene la clave API de Anthropic
    if (
        "ANTHROPIC_API_KEY=" not in env_content
        or "ANTHROPIC_API_KEY=tu_clave_api" in env_content
    ):
        console.print(
            "[bold red]La clave API de Anthropic no está configurada en el archivo .env[/bold red]"
        )
        update = Prompt.ask(
            "¿Deseas actualizar ahora el archivo .env?", choices=["s", "n"], default="s"
        )

        if update.lower() == "s":
            return _update_env_file(env_path, env_content)
        else:
            console.print(
                "\n[bold yellow]Por favor, actualiza manualmente el archivo .env en la raíz "
                "del proyecto con tu clave API de Anthropic:[/bold yellow]"
            )
            console.print("ANTHROPIC_API_KEY=tu_clave_api_aquí")
            return False

    return True


def _create_env_file(env_path):
    """
    Ayuda al usuario a crear un archivo .env nuevo.

    Args:
        env_path: Ruta al archivo .env a crear

    Returns:
        bool: True si se creó correctamente
    """
    console.print("\n[bold]Configuración del archivo .env[/bold]")

    try:
        # Solicitar las claves API
        anthropic_key = Prompt.ask("Introduce tu clave API de Anthropic", password=True)

        openai_key = Prompt.ask(
            "Introduce tu clave API de OpenAI (opcional, presiona Enter para omitir)",
            password=True,
            default="",
        )

        # Crear el contenido del archivo
        content = f"ANTHROPIC_API_KEY={anthropic_key}\n"
        if openai_key:
            content += f"OPENAI_API_KEY={openai_key}\n"

        # Escribir el archivo
        with open(env_path, "w") as f:
            f.write(content)

        console.print("[bold green]Archivo .env creado correctamente.[/bold green]")
        return True

    except Exception as e:
        console.print(f"[bold red]Error al crear el archivo .env: {e}[/bold red]")
        _show_env_template()
        return False


def _update_env_file(env_path, current_content):
    """
    Actualiza un archivo .env existente.

    Args:
        env_path: Ruta al archivo .env
        current_content: Contenido actual del archivo

    Returns:
        bool: True si se actualizó correctamente
    """
    try:
        anthropic_key = Prompt.ask("Introduce tu clave API de Anthropic", password=True)

        # Reemplazar o añadir la clave API
        if "ANTHROPIC_API_KEY=" in current_content:
            # Reemplazar la línea existente
            lines = current_content.splitlines()
            updated_lines = []

            for line in lines:
                if line.startswith("ANTHROPIC_API_KEY="):
                    updated_lines.append(f"ANTHROPIC_API_KEY={anthropic_key}")
                else:
                    updated_lines.append(line)

            updated_content = "\n".join(updated_lines)
        else:
            # Añadir la línea al final
            updated_content = (
                current_content.rstrip() + f"\nANTHROPIC_API_KEY={anthropic_key}\n"
            )

        # Escribir el archivo actualizado
        with open(env_path, "w") as f:
            f.write(updated_content)

        console.print(
            "[bold green]Archivo .env actualizado correctamente.[/bold green]"
        )
        return True

    except Exception as e:
        console.print(f"[bold red]Error al actualizar el archivo .env: {e}[/bold red]")
        return False


def _show_env_template():
    """Muestra la plantilla para el archivo .env"""
    console.print(
        "\n[bold cyan]Contenido recomendado para el archivo .env:[/bold cyan]"
    )
    console.print("```")
    console.print("ANTHROPIC_API_KEY=tu_clave_api_de_anthropic")
    console.print("OPENAI_API_KEY=tu_clave_api_de_openai  # Opcional")
    console.print("```")
    console.print(
        "Puedes obtener tu clave API de Anthropic en: https://console.anthropic.com/"
    )
