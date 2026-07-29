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
    """Construye prompt para decisión de herramientas con historial completo."""
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
INSTRUCCIONES:
1. Si necesitas usar una herramienta para responder al usuario, devuelve SOLO un JSON con:
   {"tool": "nombre_de_la_herramienta", "arguments": {"param1": "valor1", ...}}
2. Si puedes responder sin herramientas, devuelve SOLO:
   {"tool": null}
3. Responde SOLO con el JSON, sin texto adicional.

Ejemplo de JSON para usar herramienta:
{"tool": "read_file", "arguments": {"path": "archivo.txt"}}
Ejemplo de JSON para no usar herramienta:
{"tool": null}
"""

    full_prompt = f"""Historial de la conversación:
{history_prompt}

Herramientas disponibles:
{tools_text}

{instruction}
"""
    return full_prompt

def parse_tool_decision(response_text: str) -> Optional[Dict]:
    """Parsea la respuesta de DeepSeek para extraer la decisión de herramienta."""
    try:
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            return None

        data = json.loads(json_match.group())
        tool_name = data.get("tool")
        if tool_name is None:
            return None

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
        logger.warning(f"⚠️ Error parseando decisión de herramienta: {e}")
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
    return response, 200# routes/tool_handler.py - Manejo de herramientas con historial completo
import json
import logging
import re
import time
import uuid
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# ---------- Utilidades de formateo ----------

def extract_text_content(content) -> str:
    """Extrae texto de content (puede ser string o lista de partes)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
        return " ".join(parts)
    return ""

def has_tool_in_history(messages: List[Dict]) -> bool:
    """Retorna True si algún mensaje tiene role='tool'."""
    return any(msg.get("role") == "tool" for msg in messages)

def build_full_prompt(messages: List[Dict]) -> str:
    """
    Construye un único prompt de texto a partir de todo el historial de mensajes.
    Formato legible para DeepSeek:
      [Sistema]: ...
      [Usuario]: ...
      [Asistente]: ...
      [Resultado de herramienta (ID xxx)]: ...
    """
    lines = []
    for msg in messages:
        role = msg.get("role", "")
        content = extract_text_content(msg.get("content", ""))
        if role == "system":
            lines.append(f"[Sistema]: {content}")
        elif role == "user":
            lines.append(f"[Usuario]: {content}")
        elif role == "assistant":
            # Si el asistente tiene tool_calls, lo indicamos en lugar del contenido
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", {})
                    name = func.get("name", "desconocida")
                    args = func.get("arguments", "{}")
                    lines.append(f"[Asistente llamó a herramienta '{name}' con argumentos: {args}]")
            else:
                lines.append(f"[Asistente]: {content}")
        elif role == "tool":
            tool_call_id = msg.get("tool_call_id", "desconocido")
            lines.append(f"[Resultado de herramienta (ID {tool_call_id})]: {content}")
        # Otros roles (ej. function) se ignoran
    return "\n".join(lines)

# ---------- Decisión de herramientas ----------

def build_tool_decision_prompt(messages: List[Dict], tools: List[Dict]) -> str:
    """
    Construye un prompt que incluye todo el historial y las herramientas disponibles,
    pidiendo a DeepSeek que decida si usar alguna y devuelva JSON.
    """
    # Primero, el historial completo
    history_prompt = build_full_prompt(messages)

    # Descripción de herramientas disponibles
    tools_desc = []
    for tool in tools:
        func = tool.get("function", {})
        name = func.get("name", "unknown")
        desc = func.get("description", "No description")
        params = func.get("parameters", {})
        tools_desc.append(f"- {name}: {desc} (parámetros: {json.dumps(params, ensure_ascii=False)})")
    tools_text = "\n".join(tools_desc)

    # Instrucciones finales
    instruction = """
INSTRUCCIONES:
1. Si necesitas usar una herramienta para responder al usuario, devuelve SOLO un JSON con:
   {"tool": "nombre_de_la_herramienta", "arguments": {"param1": "valor1", ...}}
2. Si puedes responder sin herramientas, devuelve SOLO:
   {"tool": null}
3. Responde SOLO con el JSON, sin texto adicional.

Ejemplo de JSON para usar herramienta:
{"tool": "read_file", "arguments": {"path": "archivo.txt"}}
Ejemplo de JSON para no usar herramienta:
{"tool": null}
"""

    full_prompt = f"""Historial de la conversación:
{history_prompt}

Herramientas disponibles:
{tools_text}

{instruction}
"""
    return full_prompt

def parse_tool_decision(response_text: str) -> Optional[Dict]:
    """
    Parsea la respuesta de DeepSeek para extraer la decisión de herramienta.
    Retorna un tool_call en formato OpenAI si se decidió usar herramienta,
    o None si no.
    """
    try:
        # Buscar el primer JSON en la respuesta
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            return None

        data = json.loads(json_match.group())
        tool_name = data.get("tool")
        if tool_name is None:
            return None

        arguments = data.get("arguments", {})
        # Asegurar que arguments sea un dict
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
        logger.warning(f"⚠️ Error parseando decisión de herramienta: {e}")
        return None

def build_tool_response(tool_call: Dict, model: str) -> tuple:
    """
    Construye una respuesta completa con tool_calls (formato OpenAI).
    Retorna (response_dict, status_code).
    """
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
