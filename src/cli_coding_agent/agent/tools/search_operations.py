"""
Herramientas de operaciones de búsqueda para el CLI agent - Inspiradas en Cline
"""

import os
import re
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import aiofiles
from .base import BaseTool, ToolResult, ToolParameter, ToolType

# Importaciones opcionales para búsqueda fuzzy
try:
    from fuzzywuzzy import fuzz, process

    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False

# Para búsqueda con ripgrep si está disponible
RIPGREP_AVAILABLE = False
try:
    result = subprocess.run(["rg", "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        RIPGREP_AVAILABLE = True
except Exception:
    pass


class SearchFilesTool(BaseTool):
    """Herramienta para búsqueda regex en múltiples archivos con contexto"""

    def __init__(self):
        super().__init__()
        self.name = "search_files"
        self.description = "Realiza búsqueda regex en múltiples archivos mostrando coincidencias con contexto"
        self.tool_type = ToolType.SEARCH_OPERATION
        self.parameters = [
            ToolParameter(
                name="path",
                type=str,
                description="Ruta del directorio donde buscar (relativa al directorio de trabajo)",
            ),
            ToolParameter(
                name="regex",
                type=str,
                description="Patrón de expresión regular a buscar",
            ),
            ToolParameter(
                name="file_pattern",
                type=str,
                description="Patrón de archivos a incluir (ej: '*.py', '*.js')",
                required=False,
                default="*",
            ),
            ToolParameter(
                name="context_lines",
                type=int,
                description="Líneas de contexto antes y después de cada coincidencia",
                required=False,
                default=2,
            ),
            ToolParameter(
                name="max_results",
                type=int,
                description="Máximo número de resultados a retornar",
                required=False,
                default=100,
            ),
        ]
        self.requires_approval = False

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs["path"]
        regex = kwargs["regex"]
        file_pattern = kwargs.get("file_pattern", "*")
        context_lines = kwargs.get("context_lines", 2)
        max_results = kwargs.get("max_results", 100)

        if not self.is_path_safe(path):
            return ToolResult(
                success=False, content="", error=f"Acceso denegado a la ruta: {path}"
            )

        absolute_path = self.get_absolute_path(path)

        if not os.path.exists(absolute_path):
            return ToolResult(
                success=False, content="", error=f"La ruta no existe: {path}"
            )

        try:
            # Intentar usar ripgrep si está disponible
            if RIPGREP_AVAILABLE:
                results = await self._search_with_ripgrep(
                    absolute_path, regex, file_pattern, context_lines, max_results
                )
            else:
                # Fallback a búsqueda manual
                results = await self._search_manual(
                    absolute_path, regex, file_pattern, context_lines, max_results
                )

            formatted_results = self._format_search_results(results)

            return ToolResult(
                success=True,
                content=formatted_results,
                metadata={
                    "path": path,
                    "regex": regex,
                    "file_pattern": file_pattern,
                    "total_matches": len(results),
                    "context_lines": context_lines,
                    "used_ripgrep": RIPGREP_AVAILABLE,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error realizando búsqueda en {path}: {str(e)}",
            )

    async def _search_with_ripgrep(
        self,
        directory: str,
        regex: str,
        file_pattern: str,
        context_lines: int,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Búsqueda usando ripgrep"""
        cmd = [
            "rg",
            "--json",
            "--context",
            str(context_lines),
            "--glob",
            file_pattern,
            "--max-count",
            str(max_results),
            regex,
            directory,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode != 0 and proc.returncode != 1:
                raise Exception(f"Error en ripgrep: {stderr.decode()}")

            results = []
            for line in stdout.decode().splitlines():
                if line.strip():
                    try:
                        import json

                        data = json.loads(line)
                        if data.get("type") == "match":
                            match_data = data["data"]
                            results.append(
                                {
                                    "file": self.get_relative_path(
                                        match_data["path"]["text"]
                                    ),
                                    "line_number": match_data["line_number"],
                                    "line_content": match_data["lines"][
                                        "text"
                                    ].rstrip(),
                                    "match_text": match_data["submatches"][0]["match"][
                                        "text"
                                    ],
                                    "before_context": [],
                                    "after_context": [],
                                }
                            )
                    except (json.JSONDecodeError, KeyError):
                        continue

            return results

        except Exception as e:
            raise Exception(f"Error ejecutando ripgrep: {str(e)}")

    async def _search_manual(
        self,
        directory: str,
        regex: str,
        file_pattern: str,
        context_lines: int,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Búsqueda manual sin ripgrep"""
        try:
            pattern = re.compile(regex, re.MULTILINE | re.IGNORECASE)
        except re.error as e:
            raise Exception(f"Patrón regex inválido: {str(e)}")

        results = []

        # Buscar archivos que coincidan con el patrón
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if len(results) >= max_results:
                    break

                if self._matches_pattern(filename, file_pattern):
                    file_path = os.path.join(root, filename)

                    try:
                        file_results = await self._search_in_file(
                            file_path, pattern, context_lines
                        )
                        results.extend(file_results)

                        if len(results) >= max_results:
                            results = results[:max_results]
                            break

                    except Exception:
                        continue

            if len(results) >= max_results:
                break

        return results

    async def _search_in_file(
        self, file_path: str, pattern: re.Pattern, context_lines: int
    ) -> List[Dict[str, Any]]:
        """Busca en un archivo específico"""
        try:
            async with aiofiles.open(
                file_path, "r", encoding="utf-8", errors="ignore"
            ) as f:
                content = await f.read()

            lines = content.splitlines()
            results = []

            for i, line in enumerate(lines):
                if pattern.search(line):
                    # Obtener contexto antes
                    before_start = max(0, i - context_lines)
                    before_context = lines[before_start:i]

                    # Obtener contexto después
                    after_end = min(len(lines), i + context_lines + 1)
                    after_context = lines[i + 1 : after_end]

                    # Encontrar el texto que coincide
                    match = pattern.search(line)
                    match_text = match.group(0) if match else ""

                    results.append(
                        {
                            "file": self.get_relative_path(file_path),
                            "line_number": i + 1,
                            "line_content": line,
                            "match_text": match_text,
                            "before_context": before_context,
                            "after_context": after_context,
                        }
                    )

            return results

        except Exception:
            return []

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Verifica si un nombre de archivo coincide con el patrón"""
        if pattern == "*":
            return True

        # Convertir patrón glob a regex simple
        pattern = pattern.replace("*", ".*").replace("?", ".")
        try:
            return bool(re.match(pattern, filename, re.IGNORECASE))
        except re.error:
            return False

    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """Formatea los resultados de búsqueda para mostrar"""
        if not results:
            return "No se encontraron coincidencias."

        output = []
        current_file = None

        for result in results:
            if result["file"] != current_file:
                if current_file is not None:
                    output.append("")
                output.append(f"📁 {result['file']}")
                output.append("│" + "─" * 50)
                current_file = result["file"]

            # Mostrar contexto antes
            for line in result["before_context"]:
                output.append(f"│ {line}")

            # Mostrar la línea con la coincidencia (resaltada)
            line_num = result["line_number"]
            line_content = result["line_content"]
            output.append(f"│ {line_num:4d}: {line_content}")

            # Mostrar contexto después
            for line in result["after_context"]:
                output.append(f"│ {line}")

            output.append("│" + "─" * 30)

        summary = f"\n🔍 Se encontraron {len(results)} coincidencias."
        return "\n".join(output) + summary


class FileSearchTool(BaseTool):
    """Herramienta para búsqueda fuzzy de archivos por nombre"""

    def __init__(self):
        super().__init__()
        self.name = "file_search"
        self.description = (
            "Búsqueda fuzzy de archivos por nombre usando coincidencia aproximada"
        )
        self.tool_type = ToolType.SEARCH_OPERATION
        self.parameters = [
            ToolParameter(
                name="query",
                type=str,
                description="Término de búsqueda para nombres de archivos",
            ),
            ToolParameter(
                name="path",
                type=str,
                description="Ruta del directorio donde buscar",
                required=False,
                default=".",
            ),
            ToolParameter(
                name="limit",
                type=int,
                description="Máximo número de resultados",
                required=False,
                default=20,
            ),
        ]
        self.requires_approval = False

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs["query"]
        path = kwargs.get("path", ".")
        limit = kwargs.get("limit", 20)

        if not self.is_path_safe(path):
            return ToolResult(
                success=False, content="", error=f"Acceso denegado a la ruta: {path}"
            )

        absolute_path = self.get_absolute_path(path)

        if not os.path.exists(absolute_path):
            return ToolResult(
                success=False, content="", error=f"La ruta no existe: {path}"
            )

        try:
            # Recopilar todos los archivos
            all_files = await self._collect_files(absolute_path)

            # Realizar búsqueda fuzzy
            if FUZZYWUZZY_AVAILABLE:
                matches = await self._fuzzy_search(all_files, query, limit)
            else:
                matches = await self._simple_search(all_files, query, limit)

            formatted_results = self._format_file_search_results(matches)

            return ToolResult(
                success=True,
                content=formatted_results,
                metadata={
                    "query": query,
                    "path": path,
                    "total_files_searched": len(all_files),
                    "matches_found": len(matches),
                    "used_fuzzy": FUZZYWUZZY_AVAILABLE,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error en búsqueda de archivos: {str(e)}",
            )

    async def _collect_files(self, directory: str) -> List[Dict[str, Any]]:
        """Recopila todos los archivos en el directorio"""
        files = []

        for root, dirs, filenames in os.walk(directory):
            # Filtrar directorios comunes que se deben ignorar
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in {"node_modules", "__pycache__", "venv", "env", "dist", "build"}
            ]

            for filename in filenames:
                if not filename.startswith("."):
                    full_path = os.path.join(root, filename)
                    rel_path = self.get_relative_path(full_path)

                    files.append(
                        {
                            "name": filename,
                            "path": rel_path,
                            "full_path": full_path,
                            "size": os.path.getsize(full_path),
                            "dir": os.path.dirname(rel_path),
                        }
                    )

        return files

    async def _fuzzy_search(
        self, files: List[Dict[str, Any]], query: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Búsqueda fuzzy usando fuzzywuzzy"""
        # Crear lista de nombres para búsqueda
        file_names = [(f["name"], i) for i, f in enumerate(files)]

        # Realizar búsqueda fuzzy
        matches = process.extractBests(
            query,
            [name for name, _ in file_names],
            scorer=fuzz.partial_ratio,
            limit=limit,
            score_cutoff=30,
        )

        # Mapear de vuelta a archivos originales
        result_files = []
        for match_name, score in matches:
            # Encontrar el archivo original
            for name, index in file_names:
                if name == match_name:
                    file_info = files[index].copy()
                    file_info["score"] = score
                    result_files.append(file_info)
                    break

        return result_files

    async def _simple_search(
        self, files: List[Dict[str, Any]], query: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Búsqueda simple sin fuzzy matching"""
        query_lower = query.lower()
        matches = []

        for file_info in files:
            filename = file_info["name"].lower()
            path = file_info["path"].lower()

            # Calcular puntuación simple
            score = 0
            if query_lower == filename:
                score = 100
            elif filename.startswith(query_lower):
                score = 90
            elif query_lower in filename:
                score = 70
            elif query_lower in path:
                score = 50

            if score > 0:
                file_info_copy = file_info.copy()
                file_info_copy["score"] = score
                matches.append(file_info_copy)

        # Ordenar por puntuación
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:limit]

    def _format_file_search_results(self, matches: List[Dict[str, Any]]) -> str:
        """Formatea los resultados de búsqueda de archivos"""
        if not matches:
            return "No se encontraron archivos que coincidan."

        output = [f"🔍 Encontrados {len(matches)} archivos:"]
        output.append("")

        for match in matches:
            score = match.get("score", 0)
            size_kb = match["size"] / 1024

            if size_kb < 1:
                size_str = f"{match['size']}B"
            elif size_kb < 1024:
                size_str = f"{size_kb:.1f}KB"
            else:
                size_str = f"{size_kb / 1024:.1f}MB"

            output.append(f"📄 {match['path']:<50} ({size_str}, score: {score})")

        return "\n".join(output)


class SearchWorkspaceFilesTool(BaseTool):
    """Herramienta para búsqueda semántica de archivos en workspace"""

    def __init__(self):
        super().__init__()
        self.name = "search_workspace_files"
        self.description = "Búsqueda semántica avanzada de archivos en el workspace"
        self.tool_type = ToolType.SEARCH_OPERATION
        self.parameters = [
            ToolParameter(
                name="query", type=str, description="Consulta de búsqueda semántica"
            ),
            ToolParameter(
                name="file_types",
                type=str,
                description="Tipos de archivos a incluir (ej: 'py,js,ts')",
                required=False,
                default="",
            ),
            ToolParameter(
                name="limit",
                type=int,
                description="Máximo número de resultados",
                required=False,
                default=15,
            ),
        ]
        self.requires_approval = False

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs["query"]
        file_types = kwargs.get("file_types", "")
        limit = kwargs.get("limit", 15)

        workspace_path = self.working_directory

        try:
            # Recopilar archivos del workspace
            all_files = await self._collect_workspace_files(workspace_path, file_types)

            # Realizar búsqueda semántica
            matches = await self._semantic_search(all_files, query, limit)

            formatted_results = self._format_workspace_search_results(matches, query)

            return ToolResult(
                success=True,
                content=formatted_results,
                metadata={
                    "query": query,
                    "file_types": file_types,
                    "total_files_searched": len(all_files),
                    "matches_found": len(matches),
                    "workspace_path": workspace_path,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error en búsqueda de workspace: {str(e)}",
            )

    async def _collect_workspace_files(
        self, workspace_path: str, file_types: str
    ) -> List[Dict[str, Any]]:
        """Recopila archivos del workspace"""
        files = []

        # Parsear tipos de archivos
        if file_types:
            allowed_extensions = set(f".{ext.strip()}" for ext in file_types.split(","))
        else:
            allowed_extensions = {
                ".py",
                ".js",
                ".ts",
                ".jsx",
                ".tsx",
                ".java",
                ".cpp",
                ".c",
                ".h",
                ".cs",
                ".php",
                ".rb",
                ".go",
                ".rs",
                ".swift",
                ".kt",
                ".scala",
                ".md",
                ".txt",
                ".json",
                ".yaml",
                ".yml",
                ".xml",
                ".html",
                ".css",
            }

        for root, dirs, filenames in os.walk(workspace_path):
            # Filtrar directorios
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in {
                    "node_modules",
                    "__pycache__",
                    "venv",
                    "env",
                    "dist",
                    "build",
                    "target",
                    "bin",
                    "obj",
                    ".git",
                    ".svn",
                }
            ]

            for filename in filenames:
                if filename.startswith("."):
                    continue

                file_ext = Path(filename).suffix.lower()
                if file_ext in allowed_extensions:
                    full_path = os.path.join(root, filename)
                    rel_path = self.get_relative_path(full_path)

                    files.append(
                        {
                            "name": filename,
                            "path": rel_path,
                            "full_path": full_path,
                            "extension": file_ext,
                            "size": os.path.getsize(full_path),
                            "directory": os.path.dirname(rel_path),
                        }
                    )

        return files

    async def _semantic_search(
        self, files: List[Dict[str, Any]], query: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Realiza búsqueda semántica en archivos"""
        matches = []
        query_terms = query.lower().split()

        for file_info in files:
            score = await self._calculate_semantic_score(file_info, query_terms)

            if score > 0:
                file_info_copy = file_info.copy()
                file_info_copy["score"] = score
                matches.append(file_info_copy)

        # Ordenar por puntuación
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:limit]

    async def _calculate_semantic_score(
        self, file_info: Dict[str, Any], query_terms: List[str]
    ) -> float:
        """Calcula puntuación semántica para un archivo"""
        score = 0.0

        # Puntuación basada en nombre de archivo
        filename_lower = file_info["name"].lower()
        path_lower = file_info["path"].lower()

        for term in query_terms:
            # Coincidencia exacta en nombre
            if term in filename_lower:
                score += 10.0

            # Coincidencia en ruta
            if term in path_lower:
                score += 5.0

            # Coincidencia parcial
            if any(term in part for part in filename_lower.split("_")):
                score += 3.0

            if any(term in part for part in filename_lower.split("-")):
                score += 3.0

        # Bonificación por tipo de archivo relevante
        relevance_bonus = {
            ".py": 1.2,
            ".js": 1.1,
            ".ts": 1.1,
            ".md": 1.0,
            ".json": 0.8,
            ".yaml": 0.8,
            ".yml": 0.8,
        }

        score *= relevance_bonus.get(file_info["extension"], 1.0)

        # Penalización por archivos muy grandes
        if file_info["size"] > 1024 * 1024:  # 1MB
            score *= 0.8

        return score

    def _format_workspace_search_results(
        self, matches: List[Dict[str, Any]], query: str
    ) -> str:
        """Formatea los resultados de búsqueda de workspace"""
        if not matches:
            return f"No se encontraron archivos relacionados con '{query}'."

        output = [f"🔍 Archivos encontrados para '{query}':"]
        output.append("")

        for i, match in enumerate(matches, 1):
            score = match.get("score", 0)
            size_kb = match["size"] / 1024

            if size_kb < 1:
                size_str = f"{match['size']}B"
            elif size_kb < 1024:
                size_str = f"{size_kb:.1f}KB"
            else:
                size_str = f"{size_kb / 1024:.1f}MB"

            # Emoji por tipo de archivo
            ext_emoji = {
                ".py": "🐍",
                ".js": "📜",
                ".ts": "📘",
                ".md": "📝",
                ".json": "📋",
                ".yaml": "⚙️",
                ".yml": "⚙️",
            }

            emoji = ext_emoji.get(match["extension"], "📄")

            output.append(
                f"{i:2d}. {emoji} {match['path']:<45} ({size_str}, score: {score:.1f})"
            )

        return "\n".join(output)


# Instancias de las herramientas
search_files_tool = SearchFilesTool()
file_search_tool = FileSearchTool()
search_workspace_files_tool = SearchWorkspaceFilesTool()
