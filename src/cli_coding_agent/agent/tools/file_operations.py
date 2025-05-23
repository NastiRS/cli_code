"""
Herramientas de operaciones de archivos para el CLI agent - Inspiradas en Cline
"""

import os
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
import mimetypes
import re

# Importaciones para lectura de PDFs y DOCX
try:
    import PyPDF2
    import fitz  # PyMuPDF

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document

    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# Importaciones para tree-sitter
try:
    import tree_sitter_python as tspython
    import tree_sitter_javascript as tsjs
    import tree_sitter_typescript as tsts
    import tree_sitter_java as tsjava
    import tree_sitter_cpp as tscpp
    import tree_sitter_c as tsc
    import tree_sitter_rust as tsrust
    import tree_sitter_go as tsgo
    from tree_sitter import Parser, Node

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

from .base import BaseTool, ToolResult, ToolParameter, ToolType


class ReadFileTool(BaseTool):
    """Herramienta para leer contenido de archivos incluyendo PDFs y DOCX"""

    def __init__(self):
        super().__init__()
        self.name = "read_file"
        self.description = "Lee el contenido de un archivo. Soporta archivos de texto, PDFs y documentos DOCX"
        self.tool_type = ToolType.FILE_OPERATION
        self.parameters = [
            ToolParameter(
                name="path",
                type=str,
                description="Ruta del archivo a leer (relativa al directorio de trabajo)",
            )
        ]
        self.requires_approval = False

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs["path"]

        if not self.is_path_safe(path):
            return ToolResult(
                success=False, content="", error=f"Acceso denegado a la ruta: {path}"
            )

        absolute_path = self.get_absolute_path(path)

        if not os.path.exists(absolute_path):
            return ToolResult(
                success=False, content="", error=f"El archivo no existe: {path}"
            )

        if not os.path.isfile(absolute_path):
            return ToolResult(
                success=False, content="", error=f"La ruta no es un archivo: {path}"
            )

        try:
            # Detectar el tipo de archivo
            mime_type, _ = mimetypes.guess_type(absolute_path)
            file_extension = Path(absolute_path).suffix.lower()

            content = ""

            # Leer PDFs
            if file_extension == ".pdf":
                content = await self._read_pdf(absolute_path)
            # Leer DOCX
            elif file_extension == ".docx":
                content = await self._read_docx(absolute_path)
            # Leer archivos de texto
            else:
                content = await self._read_text_file(absolute_path)

            return ToolResult(
                success=True,
                content=content,
                metadata={
                    "file_path": path,
                    "absolute_path": absolute_path,
                    "file_size": os.path.getsize(absolute_path),
                    "mime_type": mime_type,
                    "file_extension": file_extension,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error leyendo el archivo {path}: {str(e)}",
            )

    async def _read_text_file(self, file_path: str) -> str:
        """Lee un archivo de texto con detección automática de encoding"""
        encodings = ["utf-8", "utf-16", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                async with aiofiles.open(file_path, "r", encoding=encoding) as f:
                    return await f.read()
            except UnicodeDecodeError:
                continue

        # Si ningún encoding funciona, leer como binario y decodificar con errores
        async with aiofiles.open(file_path, "rb") as f:
            raw_content = await f.read()
            return raw_content.decode("utf-8", errors="replace")

    async def _read_pdf(self, file_path: str) -> str:
        """Lee contenido de un archivo PDF"""
        if not PDF_AVAILABLE:
            return "[PDF no soportado - instale PyPDF2 y PyMuPDF]"

        try:
            # Intentar con PyMuPDF primero (mejor para texto complejo)
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception:
            try:
                # Fallback a PyPDF2
                with open(file_path, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    return text
            except Exception as e:
                return f"[Error leyendo PDF: {str(e)}]"

    async def _read_docx(self, file_path: str) -> str:
        """Lee contenido de un archivo DOCX"""
        if not DOCX_AVAILABLE:
            return "[DOCX no soportado - instale python-docx]"

        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            return f"[Error leyendo DOCX: {str(e)}]"


class WriteToFileTool(BaseTool):
    """Herramienta para escribir/crear archivos con contenido completo"""

    def __init__(self):
        super().__init__()
        self.name = "write_to_file"
        self.description = "Escribe contenido completo a un archivo. Si existe, lo sobrescribe. Si no existe, lo crea junto con directorios necesarios"
        self.tool_type = ToolType.FILE_OPERATION
        self.parameters = [
            ToolParameter(
                name="path",
                type=str,
                description="Ruta del archivo a escribir (relativa al directorio de trabajo)",
            ),
            ToolParameter(
                name="content",
                type=str,
                description="Contenido completo a escribir en el archivo",
            ),
        ]
        self.requires_approval = True

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs["path"]
        content = kwargs["content"]

        if not self.is_path_safe(path):
            return ToolResult(
                success=False, content="", error=f"Acceso denegado a la ruta: {path}"
            )

        absolute_path = self.get_absolute_path(path)

        try:
            # Crear directorios padre si no existen
            os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

            # Escribir el archivo
            async with aiofiles.open(absolute_path, "w", encoding="utf-8") as f:
                await f.write(content)

            file_exists = os.path.exists(absolute_path)
            file_size = os.path.getsize(absolute_path) if file_exists else 0

            return ToolResult(
                success=True,
                content=f"Archivo escrito exitosamente: {path}",
                metadata={
                    "file_path": path,
                    "absolute_path": absolute_path,
                    "file_size": file_size,
                    "lines_written": len(content.splitlines()),
                    "created_new": not file_exists,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error escribiendo el archivo {path}: {str(e)}",
            )


class ReplaceInFileTool(BaseTool):
    """Herramienta para reemplazar contenido específico usando bloques SEARCH/REPLACE"""

    def __init__(self):
        super().__init__()
        self.name = "replace_in_file"
        self.description = "Reemplaza contenido específico en un archivo usando bloques SEARCH/REPLACE. Busca texto exacto y lo reemplaza"
        self.tool_type = ToolType.FILE_OPERATION
        self.parameters = [
            ToolParameter(
                name="path",
                type=str,
                description="Ruta del archivo a modificar (relativa al directorio de trabajo)",
            ),
            ToolParameter(
                name="old_str",
                type=str,
                description="Texto exacto a buscar (debe coincidir completamente incluyendo espacios e indentación)",
            ),
            ToolParameter(name="new_str", type=str, description="Texto de reemplazo"),
        ]
        self.requires_approval = True

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs["path"]
        old_str = kwargs["old_str"]
        new_str = kwargs["new_str"]

        if not self.is_path_safe(path):
            return ToolResult(
                success=False, content="", error=f"Acceso denegado a la ruta: {path}"
            )

        absolute_path = self.get_absolute_path(path)

        if not os.path.exists(absolute_path):
            return ToolResult(
                success=False, content="", error=f"El archivo no existe: {path}"
            )

        try:
            # Leer el contenido actual
            async with aiofiles.open(absolute_path, "r", encoding="utf-8") as f:
                content = await f.read()

            # Verificar que el texto a buscar existe
            if old_str not in content:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"El texto especificado no se encontró en el archivo {path}",
                )

            # Contar ocurrencias
            occurrences = content.count(old_str)
            if occurrences > 1:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Se encontraron {occurrences} ocurrencias del texto. Debe ser más específico para reemplazar solo una",
                )

            # Realizar el reemplazo
            new_content = content.replace(old_str, new_str, 1)

            # Escribir el archivo modificado
            async with aiofiles.open(absolute_path, "w", encoding="utf-8") as f:
                await f.write(new_content)

            return ToolResult(
                success=True,
                content=f"Reemplazo realizado exitosamente en {path}",
                metadata={
                    "file_path": path,
                    "absolute_path": absolute_path,
                    "old_length": len(old_str),
                    "new_length": len(new_str),
                    "file_size": os.path.getsize(absolute_path),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error modificando el archivo {path}: {str(e)}",
            )


class ListFilesTool(BaseTool):
    """Herramienta para listar archivos y directorios"""

    def __init__(self):
        super().__init__()
        self.name = "list_files"
        self.description = "Lista archivos y directorios en una ruta específica. Puede ser recursivo o solo nivel superior"
        self.tool_type = ToolType.FILE_OPERATION
        self.parameters = [
            ToolParameter(
                name="path",
                type=str,
                description="Ruta del directorio a listar (relativa al directorio de trabajo)",
            ),
            ToolParameter(
                name="recursive",
                type=bool,
                description="Si listar recursivamente todos los subdirectorios",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="limit",
                type=int,
                description="Límite máximo de archivos a listar",
                required=False,
                default=1000,
            ),
        ]
        self.requires_approval = False

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs["path"]
        recursive = kwargs.get("recursive", False)
        limit = kwargs.get("limit", 1000)

        if not self.is_path_safe(path):
            return ToolResult(
                success=False, content="", error=f"Acceso denegado a la ruta: {path}"
            )

        absolute_path = self.get_absolute_path(path)

        if not os.path.exists(absolute_path):
            return ToolResult(
                success=False, content="", error=f"La ruta no existe: {path}"
            )

        if not os.path.isdir(absolute_path):
            return ToolResult(
                success=False, content="", error=f"La ruta no es un directorio: {path}"
            )

        try:
            files = []
            directories = []
            count = 0

            if recursive:
                for root, dirs, filenames in os.walk(absolute_path):
                    if count >= limit:
                        break

                    # Agregar directorios
                    for dirname in dirs:
                        if count >= limit:
                            break
                        full_path = os.path.join(root, dirname)
                        rel_path = self.get_relative_path(full_path)
                        directories.append(
                            {"name": dirname, "path": rel_path, "type": "directory"}
                        )
                        count += 1

                    # Agregar archivos
                    for filename in filenames:
                        if count >= limit:
                            break
                        full_path = os.path.join(root, filename)
                        rel_path = self.get_relative_path(full_path)
                        file_size = os.path.getsize(full_path)
                        files.append(
                            {
                                "name": filename,
                                "path": rel_path,
                                "type": "file",
                                "size": file_size,
                            }
                        )
                        count += 1
            else:
                # Solo nivel superior
                for item in os.listdir(absolute_path):
                    if count >= limit:
                        break

                    item_path = os.path.join(absolute_path, item)
                    rel_path = self.get_relative_path(item_path)

                    if os.path.isdir(item_path):
                        directories.append(
                            {"name": item, "path": rel_path, "type": "directory"}
                        )
                    else:
                        file_size = os.path.getsize(item_path)
                        files.append(
                            {
                                "name": item,
                                "path": rel_path,
                                "type": "file",
                                "size": file_size,
                            }
                        )
                    count += 1

            # Ordenar resultados
            directories.sort(key=lambda x: x["name"])
            files.sort(key=lambda x: x["name"])

            result = {
                "directories": directories,
                "files": files,
                "total_items": len(directories) + len(files),
                "truncated": count >= limit,
            }

            return ToolResult(
                success=True,
                content=result,
                metadata={
                    "path": path,
                    "recursive": recursive,
                    "limit": limit,
                    "total_directories": len(directories),
                    "total_files": len(files),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error listando archivos en {path}: {str(e)}",
            )


class ListCodeDefinitionNamesTool(BaseTool):
    """Herramienta para listar definiciones de código usando tree-sitter"""

    def __init__(self):
        super().__init__()
        self.name = "list_code_definition_names"
        self.description = "Lista definiciones de código (clases, funciones, métodos) en archivos fuente"
        self.tool_type = ToolType.FILE_OPERATION
        self.parameters = [
            ToolParameter(
                name="path",
                type=str,
                description="Ruta del directorio a analizar (relativa al directorio de trabajo)",
            )
        ]
        self.requires_approval = False

        # Configurar parsers de tree-sitter si está disponible
        self.parsers = {}
        if TREE_SITTER_AVAILABLE:
            try:
                self.parsers["python"] = self._setup_parser(tspython.language())
                self.parsers["javascript"] = self._setup_parser(tsjs.language())
                self.parsers["typescript"] = self._setup_parser(tsts.language())
                self.parsers["java"] = self._setup_parser(tsjava.language())
                self.parsers["cpp"] = self._setup_parser(tscpp.language())
                self.parsers["c"] = self._setup_parser(tsc.language())
                self.parsers["rust"] = self._setup_parser(tsrust.language())
                self.parsers["go"] = self._setup_parser(tsgo.language())
            except Exception:
                pass

    def _setup_parser(self, language):
        """Configura un parser de tree-sitter"""
        parser = Parser()
        parser.set_language(language)
        return parser

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs["path"]

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
            definitions = {}

            if os.path.isfile(absolute_path):
                # Analizar un solo archivo
                file_defs = await self._analyze_file(absolute_path)
                if file_defs:
                    definitions[self.get_relative_path(absolute_path)] = file_defs
            else:
                # Analizar directorio
                for root, dirs, files in os.walk(absolute_path):
                    for filename in files:
                        if self._is_code_file(filename):
                            file_path = os.path.join(root, filename)
                            file_defs = await self._analyze_file(file_path)
                            if file_defs:
                                rel_path = self.get_relative_path(file_path)
                                definitions[rel_path] = file_defs

            return ToolResult(
                success=True,
                content=definitions,
                metadata={
                    "path": path,
                    "files_analyzed": len(definitions),
                    "tree_sitter_available": TREE_SITTER_AVAILABLE,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error analizando definiciones en {path}: {str(e)}",
            )

    def _is_code_file(self, filename: str) -> bool:
        """Verifica si un archivo es de código fuente"""
        code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".rs",
            ".go",
            ".php",
            ".rb",
            ".cs",
            ".swift",
            ".kt",
            ".scala",
        }
        return Path(filename).suffix.lower() in code_extensions

    async def _analyze_file(self, file_path: str) -> Optional[List[Dict[str, Any]]]:
        """Analiza un archivo para extraer definiciones"""
        try:
            # Leer el archivo
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()

            file_extension = Path(file_path).suffix.lower()

            # Usar tree-sitter si está disponible
            if TREE_SITTER_AVAILABLE:
                return await self._analyze_with_tree_sitter(content, file_extension)
            else:
                # Fallback a análisis básico
                return await self._analyze_with_regex(content, file_extension)

        except Exception:
            try:
                # Fallback a análisis básico
                return await self._analyze_with_regex(content, file_extension)
            except Exception:
                return None

    async def _analyze_with_tree_sitter(
        self, content: str, file_extension: str
    ) -> List[Dict[str, Any]]:
        """Analiza código usando tree-sitter"""
        definitions = []

        # Mapear extensiones a lenguajes
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".rs": "rust",
            ".go": "go",
        }

        language = lang_map.get(file_extension)
        if not language or language not in self.parsers:
            return definitions

        try:
            parser = self.parsers[language]
            tree = parser.parse(content.encode("utf-8"))

            def extract_definitions(node: Node, depth: int = 0):
                if depth > 10:  # Evitar recursión infinita
                    return

                # Definiciones para diferentes lenguajes
                if language == "python":
                    if node.type in [
                        "function_def",
                        "class_definition",
                        "async_function_def",
                    ]:
                        name_node = node.child_by_field_name("name")
                        if name_node:
                            definitions.append(
                                {
                                    "name": name_node.text.decode("utf-8"),
                                    "type": "class"
                                    if node.type == "class_definition"
                                    else "function",
                                    "line": node.start_point[0] + 1,
                                }
                            )
                elif language in ["javascript", "typescript"]:
                    if node.type in [
                        "function_declaration",
                        "class_declaration",
                        "method_definition",
                    ]:
                        name_node = node.child_by_field_name("name")
                        if name_node:
                            definitions.append(
                                {
                                    "name": name_node.text.decode("utf-8"),
                                    "type": "class"
                                    if node.type == "class_declaration"
                                    else "function",
                                    "line": node.start_point[0] + 1,
                                }
                            )
                elif language == "java":
                    if node.type in [
                        "class_declaration",
                        "method_declaration",
                        "interface_declaration",
                    ]:
                        name_node = node.child_by_field_name("name")
                        if name_node:
                            definitions.append(
                                {
                                    "name": name_node.text.decode("utf-8"),
                                    "type": "class"
                                    if node.type
                                    in ["class_declaration", "interface_declaration"]
                                    else "function",
                                    "line": node.start_point[0] + 1,
                                }
                            )

                # Recursivamente analizar nodos hijos
                for child in node.children:
                    extract_definitions(child, depth + 1)

            extract_definitions(tree.root_node)

        except Exception:
            pass

        return definitions

    async def _analyze_with_regex(
        self, content: str, file_extension: str
    ) -> List[Dict[str, Any]]:
        """Análisis básico usando regex como fallback"""
        definitions = []
        lines = content.splitlines()

        if file_extension == ".py":
            # Patrones para Python
            class_pattern = re.compile(r"^class\s+(\w+).*:")
            func_pattern = re.compile(r"^(?:async\s+)?def\s+(\w+)\s*\(")

            for i, line in enumerate(lines):
                line = line.strip()

                class_match = class_pattern.match(line)
                if class_match:
                    definitions.append(
                        {"name": class_match.group(1), "type": "class", "line": i + 1}
                    )

                func_match = func_pattern.match(line)
                if func_match:
                    definitions.append(
                        {"name": func_match.group(1), "type": "function", "line": i + 1}
                    )

        elif file_extension in [".js", ".ts"]:
            # Patrones para JavaScript/TypeScript
            class_pattern = re.compile(r"^(?:export\s+)?class\s+(\w+)")
            func_pattern = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)")

            for i, line in enumerate(lines):
                line = line.strip()

                class_match = class_pattern.match(line)
                if class_match:
                    definitions.append(
                        {"name": class_match.group(1), "type": "class", "line": i + 1}
                    )

                func_match = func_pattern.match(line)
                if func_match:
                    definitions.append(
                        {"name": func_match.group(1), "type": "function", "line": i + 1}
                    )

        return definitions


# Instancias de las herramientas
read_file_tool = ReadFileTool()
write_to_file_tool = WriteToFileTool()
replace_in_file_tool = ReplaceInFileTool()
list_files_tool = ListFilesTool()
list_code_definition_names_tool = ListCodeDefinitionNamesTool()
