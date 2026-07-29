# routes/tool_handler.py - Compatibilidad con múltiples formatos de tool calling
import json
import logging
import re
import time
import uuid
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)

# ---------- Utilidades de formateo ----------

def extract_text_content(content) -> str:
    """Extrae texto de content (puede ser string o lista de partes)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                part_type = part.get("type", "")
                if part_type == "text":
                    parts.append(part.get("text", ""))
                elif part_type == "tool_result":
                    # Extraer texto del resultado de herramienta
                    result_content = part.get("content", [])
                    if isinstance(result_content, list):
                        for item in result_content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                parts.append(item.get("text", ""))
                    elif isinstance(result_content, str):
                        parts.append(result_content)
            elif isinstance(part, str):
                parts.append(part)
        return " ".join(parts)
    return ""

def normalize_tool_calls(message: Dict) -> Dict:
    """
    Normaliza los tool_calls de diferentes formatos a OpenAI estándar.
    Convierte el formato de RooCode/Anthropic a OpenAI.
    """
    content = message.get("content", [])
    if not isinstance(content, list):
        return message

    # Detectar si hay tool_use en el formato de Anthropic/RooCode
    tool_uses = []
    new_content = []
    
    for part in content:
        if isinstance(part, dict):
            if part.get("type") == "tool_use":
                # Convertir a formato OpenAI
                tool_uses.append({
                    "id": part.get("id", f"call_{uuid.uuid4().hex[:12]}"),
                    "type": "function",
                    "function": {
                        "name": part.get("name", ""),
                        "arguments": json.dumps(part.get("input", {}), ensure_ascii=False)
                    }
                })
            else:
                new_content.append(part)
        else:
            new_content.append(part)
    
    if tool_uses:
        # Crear una copia del mensaje con el formato OpenAI
        normalized = message.copy()
        normalized["content"] = None  # OpenAI espera content = None cuando hay tool_calls
        normalized["tool_calls"] = tool_uses
        
        # Si hay texto adicional, incluirlo en content
        if new_content:
            text_parts = [p.get("text", "") for p in new_content if isinstance(p, dict) and p.get("type") == "text"]
            if text_parts:
                normalized["content"] = " ".join(text_parts)
        
        return normalized
    
    return message

def normalize_tool_result(message: Dict) -> Dict:
    """
    Normaliza los tool_results de RooCode a formato OpenAI.
    Convierte tool_result a role: "tool"
    """
    content = message.get("content", [])
    if not isinstance(content, list):
        return message

    # Buscar tool_result en el contenido
    for part in content:
        if isinstance(part, dict) and part.get("type") == "tool_result":
            tool_use_id = part.get("tool_use_id", "")
            result_content = part.get("content", [])
            
            # Extraer texto del resultado
            text_result = ""
            if isinstance(result_content, list):
                for item in result_content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_result += item.get("text", "")
            elif isinstance(result_content, str):
                text_result = result_content
            
            # Crear mensaje en formato OpenAI
            return {
                "role": "tool",
                "tool_call_id": tool_use_id,
                "content": text_result
            }
    
    return message

def normalize_messages(messages: List[Dict]) -> List[Dict]:
    """Normaliza todos los mensajes al formato OpenAI estándar."""
    normalized = []
    for msg in messages:
        role = msg.get("role", "")
        
        if role == "assistant":
            # Verificar si tiene formato tool_use
            normalized_msg = normalize_tool_calls(msg)
        elif role == "user":
            # Verificar si tiene tool_result en el contenido
            normalized_msg = normalize_tool_result(msg)
            # Si no se convirtió a tool, mantener como user
            if normalized_msg.get("role") == "user":
                normalized_msg = msg
        else:
            normalized_msg = msg
        
        normalized.append(normalized_msg)
    
    return normalized

def has_tool_in_history(messages: List[Dict]) -> bool:
    """Retorna True si algún mensaje tiene role='tool' o contiene tool_result."""
    for msg in messages:
        if msg.get("role") == "tool":
            return True
        
        # También verificar tool_result en contenido
        content = msg.get("content", [])
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    return True
    
    return False

def build_full_prompt(messages: List[Dict]) -> str:
    """
    Construye un único prompt de texto a partir de todo el historial de mensajes.
    Soporta tanto formato OpenAI como Anthropic/RooCode.
    """
    # Primero normalizar todos los mensajes
    normalized_messages = normalize_messages(messages)
    
    lines = []
    for msg in normalized_messages:
        role = msg.get("role", "")
        content = extract_text_content(msg.get("content", ""))
        
        if role == "system":
            lines.append(f"[Sistema]: {content}")
        elif role == "user":
            lines.append(f"[Usuario]: {content}")
        elif role == "assistant":
            # Verificar si tiene tool_calls
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", {})
                    name = func.get("name", "desconocida")
                    args = func.get("arguments", "{}")
                    lines.append(f"[Asistente llamó a herramienta '{name}' con argumentos: {args}]")
            elif content:
                lines.append(f"[Asistente]: {content}")
        elif role == "tool":
            tool_call_id = msg.get("tool_call_id", "desconocido")
            lines.append(f"[Resultado de herramienta (ID {tool_call_id})]: {content}")
    
    return "\n".join(lines)

# ---------- Decisión de herramientas ----------

def build_tool_decision_prompt(messages: List[Dict], tools: List[Dict]) -> str:
    """Construye un prompt más directo para decisión de herramientas, pidiendo solo JSON."""
    history_prompt = build_full_prompt(messages)

    tools_desc = []
    for tool in tools:
        func = tool.get("function", {})
        name = func.get("name", "unknown")
        desc = func.get("description", "No description")
        params = func.get("parameters", {})
        tools_desc.append(f"- {name}: {desc} (parámetros: {json.dumps(params, ensure_ascii=False)})")
    tools_text = "\n".join(tools_desc)

    instruction = """
INSTRUCCIÓN IMPORTANTE: Debes responder ÚNICAMENTE con un JSON válido. No incluyas texto adicional, ni explicaciones, ni etiquetas.

Si necesitas usar una herramienta, responde con:
{"tool": "nombre_de_la_herramienta", "arguments": {"param1": "valor1", ...}}

Si no necesitas herramienta, responde con:
{"tool": null}

EJEMPLOS:
- Para leer un archivo: {"tool": "read_file", "arguments": {"path": "README.md"}}
- Para listar archivos: {"tool": "list_files", "arguments": {"path": "."}}
- Para no usar herramienta: {"tool": null}

Responde SOLO con el JSON, nada más.
"""

    full_prompt = f"""Historial de la conversación:
{history_prompt}

Herramientas disponibles:
{tools_text}

{instruction}
"""
    return full_prompt

# ---------- Fallback para formato RooCode ----------

def parse_roocode_tool_format(text: str) -> Optional[Dict]:
    """
    Detecta el formato de RooCode como <nombre_herramienta path="..."> y lo convierte a tool_call.
    Ejemplos:
      <read_file path="README.md">
      <write_file path="file.txt" content="hola">
      <list_files path=".">
    """
    # Buscar etiquetas como <read_file ...>
    pattern = r'<([a-z_]+)(?:\s+([^>]+))?>'
    match = re.search(pattern, text)
    if not match:
        return None
    
    tool_name = match.group(1)
    attrs_str = match.group(2)
    
    # Parsear atributos: path="..." content="..."
    args = {}
    if attrs_str:
        attr_pattern = r'(\w+)\s*=\s*"([^"]*)"'
        for attr_match in re.finditer(attr_pattern, attrs_str):
            args[attr_match.group(1)] = attr_match.group(2)
    
    # Si no hay argumentos, intentar extraer el contenido entre etiquetas
    content_match = re.search(r'<{}[^>]*>(.*?)</{}>'.format(tool_name, tool_name), text, re.DOTALL)
    if content_match and not args:
        # Si la herramienta espera un solo argumento 'content' o 'path', usamos el contenido
        args = {"content": content_match.group(1).strip()}
    
    if not args:
        # Si no hay argumentos, usar un valor por defecto
        args = {"path": "."} if tool_name == "list_files" else {}
    
    return {
        "id": f"call_{uuid.uuid4().hex[:12]}",
        "type": "function",
        "function": {
            "name": tool_name,
            "arguments": json.dumps(args, ensure_ascii=False)
        }
    }

def parse_tool_decision(response_text: str) -> Optional[Dict]:
    """
    Parsea la decisión de herramienta, primero busca JSON, luego fallback a formato RooCode.
    """
    # 1. Intentar JSON
    try:
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            tool_name = data.get("tool")
            if tool_name is not None:
                arguments = data.get("arguments", {})
                if not isinstance(arguments, dict):
                    arguments = {}
                return {
                    "id": f"call_{uuid.uuid4().hex[:12]}",
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(arguments, ensure_ascii=False)
                    }
                }
    except Exception as e:
        logger.warning(f"⚠️ Error parseando JSON: {e}")

    # 2. Fallback: formato RooCode
    roo_tool = parse_roocode_tool_format(response_text)
    if roo_tool:
        logger.info(f"🔧 Detectado formato RooCode: {roo_tool['function']['name']}")
        return roo_tool

    return None

def build_tool_response(tool_call: Dict, model: str) -> tuple:
    """Construye respuesta con tool_calls en formato OpenAI."""
    response = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call]
            },
            "finish_reason": "tool_calls"
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }
    return response, 200
