import os
import shutil
import tempfile
import zipfile
import tarfile
import logging
from pathlib import Path
from typing import List, Set, Optional

logger = logging.getLogger(__name__)

# Extensiones consideradas de texto/código (se pueden ampliar)
TEXT_EXTENSIONS: Set[str] = {
    ".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".csv",
    ".xml", ".yaml", ".yml", ".sh", ".bat", ".ps1", ".rb", ".java",
    ".c", ".cpp", ".h", ".hpp", ".go", ".rs", ".swift", ".kt",
    ".log", ".conf", ".ini", ".properties", ".toml", ".sql",
    ".r", ".pl", ".pm", ".tcl", ".lua", ".vim", ".rst", ".tex",
    ".scss", ".less", ".sass", ".styl", ".vue", ".jsx", ".tsx",
    ".ts", ".coffee", ".dart", ".lisp", ".clj", ".cljs", ".edn",
    ".erl", ".hrl", ".ex", ".exs", ".fs", ".fsx", ".ml", ".mli",
    ".nim", ".cr", ".zig", ".v", ".vhd", ".vhdl", ".sv", ".svh",
    ".f", ".for", ".f90", ".f95", ".f03", ".f08", ".m", ".mm",
    ".p", ".p6", ".pm6", ".pl6", ".t", ".pod", ".make", ".cmake",
    ".gradle", ".sbt", ".pom", ".xml", ".xsd", ".wsdl", ".wadl",
    ".raml", ".oas", ".swagger", ".proto", ".thrift", ".avsc",
    ".avro", ".env", ".example", ".sample", ".template",
}

# Extensiones de archivos comprimidos soportados
ARCHIVE_EXTENSIONS: Set[str] = {".zip", ".tar", ".tgz", ".tar.gz", ".gz", ".rar"}

MAX_EXTRACTED_SIZE = 2 * 1024 * 1024  # 2 MB


def is_archive(filename: str) -> bool:
    """Determina si un archivo es un comprimido según su extensión."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ARCHIVE_EXTENSIONS


def is_text_file(filename: str) -> bool:
    """Determina si un archivo es de texto/código según su extensión."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in TEXT_EXTENSIONS


def safe_extract_zip(zip_path: str, dest_dir: str) -> List[str]:
    """
    Extrae un archivo ZIP de forma segura (protección contra zip slip).
    Devuelve lista de rutas extraídas (relativas a dest_dir).
    """
    extracted = []
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.namelist():
            # Protección zip slip
            member_path = os.path.join(dest_dir, member)
            if not os.path.realpath(member_path).startswith(os.path.realpath(dest_dir)):
                logger.warning("Zip slip detectado: %s", member)
                continue
            zf.extract(member, dest_dir)
            extracted.append(member)
    return extracted


def safe_extract_tar(tar_path: str, dest_dir: str) -> List[str]:
    """
    Extrae un archivo TAR (incluye .tar.gz, .tgz) de forma segura.
    """
    extracted = []
    with tarfile.open(tar_path, 'r:*') as tf:
        for member in tf.getmembers():
            if member.isdir():
                continue
            member_path = os.path.join(dest_dir, member.name)
            if not os.path.realpath(member_path).startswith(os.path.realpath(dest_dir)):
                logger.warning("Tar slip detectado: %s", member.name)
                continue
            tf.extract(member, dest_dir)
            extracted.append(member.name)
    return extracted


def safe_extract_rar(rar_path: str, dest_dir: str) -> List[str]:
    """
    Extrae un archivo RAR (requiere rarfile y unrar instalado).
    """
    try:
        import rarfile
    except ImportError:
        raise RuntimeError("El módulo 'rarfile' no está instalado. Instálalo con: pip install rarfile")
    extracted = []
    with rarfile.RarFile(rar_path) as rf:
        for member in rf.infolist():
            if member.isdir():
                continue
            member_path = os.path.join(dest_dir, member.filename)
            if not os.path.realpath(member_path).startswith(os.path.realpath(dest_dir)):
                logger.warning("Rar slip detectado: %s", member.filename)
                continue
            rf.extract(member, dest_dir)
            extracted.append(member.filename)
    return extracted


def extract_archive(archive_path: str, dest_dir: str) -> List[str]:
    """
    Extrae un archivo comprimido según su extensión.
    Devuelve lista de rutas extraídas (relativas a dest_dir).
    """
    ext = os.path.splitext(archive_path)[1].lower()
    if ext == ".zip":
        return safe_extract_zip(archive_path, dest_dir)
    elif ext in (".tar", ".tgz", ".tar.gz", ".gz"):
        return safe_extract_tar(archive_path, dest_dir)
    elif ext == ".rar":
        return safe_extract_rar(archive_path, dest_dir)
    else:
        raise ValueError(f"Formato de archivo no soportado: {ext}")


def filter_text_files(extracted_paths: List[str], base_dir: str) -> List[str]:
    """
    Filtra los archivos extraídos, devolviendo solo aquellos que son de texto/código.
    """
    text_files = []
    total_size = 0
    for rel_path in extracted_paths:
        full_path = os.path.join(base_dir, rel_path)
        if not os.path.isfile(full_path):
            continue
        if not is_text_file(rel_path):
            logger.info("Excluyendo archivo binario/no texto: %s", rel_path)
            continue
        size = os.path.getsize(full_path)
        if total_size + size > MAX_EXTRACTED_SIZE:
            logger.warning("Límite de tamaño total (%d bytes) excedido, omitiendo archivo: %s", MAX_EXTRACTED_SIZE, rel_path)
            break
        total_size += size
        text_files.append(rel_path)
    return text_files


def concatenate_files(file_paths: List[str], base_dir: str, output_path: str) -> int:
    """
    Concatena el contenido de todos los archivos en uno solo, con separadores.
    Devuelve el tamaño total del archivo generado.
    """
    total_bytes = 0
    with open(output_path, 'w', encoding='utf-8', errors='replace') as out_f:
        for rel_path in file_paths:
            full_path = os.path.join(base_dir, rel_path)
            try:
                with open(full_path, 'r', encoding='utf-8', errors='replace') as in_f:
                    content = in_f.read()
            except Exception as e:
                logger.warning("No se pudo leer el archivo %s: %s", rel_path, e)
                continue
            # Escribir encabezado con nombre del archivo
            out_f.write(f"--- Archivo: {rel_path} ---\n")
            out_f.write(content)
            out_f.write("\n\n")
            total_bytes += len(content.encode('utf-8'))
    return total_bytes


def process_archive(archive_path: str, output_txt_path: str) -> Optional[str]:
    """
    Procesa un archivo comprimido: extrae, filtra, concatena y genera un archivo .txt.
    Devuelve la ruta del archivo .txt generado, o None si no hay archivos de texto.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            extracted = extract_archive(archive_path, tmpdir)
        except Exception as e:
            logger.exception("Error al extraer archivo: %s", e)
            raise
        if not extracted:
            return None
        text_files = filter_text_files(extracted, tmpdir)
        if not text_files:
            logger.warning("No se encontraron archivos de texto en el comprimido.")
            return None
        total_size = concatenate_files(text_files, tmpdir, output_txt_path)
        logger.info("Archivo concatenado generado con %d bytes", total_size)
        return output_txt_path