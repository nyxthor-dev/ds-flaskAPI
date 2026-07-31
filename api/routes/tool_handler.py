# routes/tool_handler.py - Compatibilidad total con RooCode
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
    """Convierte tool_use de Anthropic/RooCode a tool_calls de OpenAI."""
    content = message.get("content", [])
    if not isinstance(content, list):
        return message

    tool_uses = []
    new_content = []
    
    for part in content:
        if isinstance(part, dict):
            if part.get("type") == "tool_use":
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
        normalized = message.copy()
        normalized["content"] = None
        normalized["tool_calls"] = tool_uses
        if new_content:
            text_parts = [p.get("text", "") for p in new_content if isinstance(p, dict) and p.get("type") == "text"]
            if text_parts:
                normalized["content"] = " ".join(text_parts)
        return normalized
    
    return message

def normalize_tool_result(message: Dict) -> Union[Dict, List[Dict]]:
    """Convierte tool_result de RooCode a role:tool de OpenAI.

    Un mensaje 'user' de Anthropic/RooCode puede mezclar varios
    tool_result y/o texto en la misma lista de content. Antes solo se
    procesaba el primer tool_result encontrado y se descartaba todo lo
    demás (incluido texto del usuario). Ahora se devuelven TODOS los
    mensajes resultantes: uno role:tool por cada tool_result, y un
    mensaje role:user si además hay texto suelto.
    """
    content = message.get("content", [])
    if not isinstance(content, list):
        return message

    tool_messages = []
    text_parts = []

    for part in content:
        if isinstance(part, dict) and part.get("type") == "tool_result":
            tool_use_id = part.get("tool_use_id", "")
            result_content = part.get("content", [])
            text_result = ""
            if isinstance(result_content, list):
                for item in result_content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_result += item.get("text", "")
            elif isinstance(result_content, str):
                text_result = result_content

            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_use_id,
                "content": text_result
            })
        elif isinstance(part, dict) and part.get("type") == "text":
            text_parts.append(part.get("text", ""))
        elif isinstance(part, str):
            text_parts.append(part)

    if not tool_messages:
        # No había tool_result: devolver el mensaje sin tocar.
        return message

    result: List[Dict] = list(tool_messages)
    if text_parts:
        result.append({"role": "user", "content": " ".join(text_parts)})
    return result

def normalize_messages(messages: List[Dict]) -> List[Dict]:
    """Normaliza todos los mensajes al formato OpenAI estándar."""
    normalized = []
    for msg in messages:
        role = msg.get("role", "")
        if role == "assistant":
            normalized_msg = normalize_tool_calls(msg)
        elif role == "user":
            normalized_msg = normalize_tool_result(msg)
        else:
            normalized_msg = msg

        if isinstance(normalized_msg, list):
            normalized.extend(normalized_msg)
        else:
            normalized.append(normalized_msg)
    return normalized

def has_tool_in_history(messages: List[Dict]) -> bool:
    """Retorna True si ya hay un mensaje tool o tool_result."""
    for msg in messages:
        if msg.get("role") == "tool":
            return True
        content = msg.get("content", [])
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    return True
    return False

def build_full_prompt(messages: List[Dict]) -> str:
    """Construye prompt de texto a partir del historial completo."""
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

# ---------- Prompt de decisión ----------

def build_tool_decision_prompt(messages: List[Dict], tools: List[Dict]) -> str:
    """Prompt que fuerza al modelo a responder solo con JSON."""
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
RESPONDE ÚNICAMENTE CON UN JSON VÁLIDO. NO INCLUYAS NINGÚN OTRO TEXTO.

- Si necesitas usar una herramienta, usa este formato exacto:
{"tool": "nombre_de_la_herramienta", "arguments": {"param1": "valor1", ...}}

- Si NO necesitas herramienta, usa:
{"tool": null}

EJEMPLOS CORRECTOS:
{"tool": "read_file", "arguments": {"path": "README.md"}}
{"tool": "list_files", "arguments": {"path": "."}}
{"tool": null}

EJEMPLOS INCORRECTOS (NO LOS USES):
[Asistente llamó a herramienta 'read_file']
<read_file path="README.md">
"Creo que debo usar la herramienta read_file"

RECUERDA: SOLO EL JSON, NADA MÁS.
"""

    full_prompt = f"""Historial de la conversación:
{history_prompt}

Herramientas disponibles:
{tools_text}

{instruction}
"""
    return full_prompt

# ---------- Parsers ----------

def parse_roocode_tool_format(text: str) -> Optional[Dict]:
    """Detecta formato XML de RooCode: <nombre path="..."> ... </nombre>"""
    pattern = r'<([a-z_]+)(?:\s+([^>]+))?>'
    match = re.search(pattern, text)
    if not match:
        return None
    
    tool_name = match.group(1)
    attrs_str = match.group(2)
    args = {}
    if attrs_str:
        attr_pattern = r'(\w+)\s*=\s*"([^"]*)"'
        for attr_match in re.finditer(attr_pattern, attrs_str):
            args[attr_match.group(1)] = attr_match.group(2)
    
    content_match = re.search(r'<{}[^>]*>(.*?)</{}>'.format(tool_name, tool_name), text, re.DOTALL)
    if content_match and not args:
        args = {"content": content_match.group(1).strip()}
    
    if not args:
        args = {"path": "."} if tool_name == "list_files" else {}
    
    return {
        "id": f"call_{uuid.uuid4().hex[:12]}",
        "type": "function",
        "function": {
            "name": tool_name,
            "arguments": json.dumps(args, ensure_ascii=False)
        }
    }

def parse_natural_language_tool(text: str) -> Optional[Dict]:
    """
    Detecta frases como "llamó a herramienta 'nombre'" o "usando la herramienta nombre"
    y extrae el nombre y argumentos si los hay.
    """
    # Patrón: llamó a herramienta 'nombre' con argumentos: {...}
    patterns = [
        r"llamó a herramienta ['\"]([a-z_]+)['\"]",
        r"usando la herramienta ['\"]([a-z_]+)['\"]",
        r"herramienta ['\"]([a-z_]+)['\"]",
        r"\[Asistente llamó a herramienta '([a-z_]+)'",
    ]
    tool_name = None
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            tool_name = m.group(1)
            break
    
    if not tool_name:
        return None
    
    # Intentar extraer argumentos en formato JSON o clave=valor
    args = {}
    # Buscar {...} después del nombre
    json_match = re.search(r'\{.*\}', text)
    if json_match:
        try:
            args = json.loads(json_match.group())
        except:
            pass
    else:
        # Buscar pares clave=valor
        kv_pattern = r'(\w+)\s*=\s*"([^"]*)"'
        for kv in re.finditer(kv_pattern, text):
            args[kv.group(1)] = kv.group(2)
    
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

def _extract_balanced_json_objects(text: str) -> List[str]:
    """Extrae todas las subcadenas que son objetos JSON '{...}' balanceados,
    respetando llaves dentro de strings. Evita el problema del regex
    greedy '\\{.*\\}' que capturaba de más (o de menos) cuando el modelo
    agregaba texto antes/después del JSON o había varios objetos.
    """
    objects = []
    depth = 0
    start = None
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    objects.append(text[start:i + 1])
                    start = None
    return objects

def parse_tool_decision(response_text: str) -> Optional[Dict]:
    """
    Intenta parsear la decisión de herramienta en tres formatos: JSON, XML de RooCode y lenguaje natural.
    """
    # 1. JSON (busca objetos balanceados; si hay varios, usa el primero
    # que tenga la clave "tool")
    for candidate in _extract_balanced_json_objects(response_text):
        try:
            data = json.loads(candidate)
        except Exception:
            continue
        if not isinstance(data, dict) or "tool" not in data:
            continue
        tool_name = data.get("tool")
        if tool_name is None:
            # {"tool": null} explícito: el modelo decidió no usar herramienta.
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

    # 2. XML de RooCode
    roo_tool = parse_roocode_tool_format(response_text)
    if roo_tool:
        logger.info(f"🔧 Detectado formato XML de RooCode: {roo_tool['function']['name']}")
        return roo_tool

    # 3. Lenguaje natural
    natural_tool = parse_natural_language_tool(response_text)
    if natural_tool:
        logger.info(f"🔧 Detectado formato de lenguaje natural: {natural_tool['function']['name']}")
        return natural_tool

    return None

def build_tool_response(tool_call: Dict, model: str, prompt_tokens: int = 0, completion_tokens: int = 0) -> tuple:
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
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    }
    return response, 200

def build_tool_response_stream_chunks(tool_call: Dict, model: str, completion_id: str, created: int) -> List[str]:
    """Construye los chunks SSE (formato OpenAI) para una respuesta de tool_calls
    cuando el cliente pidió stream=true. Sin esto, un cliente que pide streaming
    y recibe un JSON completo con Content-Type application/json puede fallar al
    parsear la respuesta como eventos SSE.
    """
    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    base = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
    }

    chunks = []
    # Primer chunk: rol + inicio de tool_call (id, type, name)
    chunks.append(sse({
        **base,
        "choices": [{
            "index": 0,
            "delta": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "index": 0,
                    "id": tool_call["id"],
                    "type": "function",
                    "function": {
                        "name": tool_call["function"]["name"],
                        "arguments": ""
                    }
                }]
            },
            "finish_reason": None
        }]
    }))
    # Segundo chunk: argumentos completos (delta incremental)
    chunks.append(sse({
        **base,
        "choices": [{
            "index": 0,
            "delta": {
                "tool_calls": [{
                    "index": 0,
                    "function": {
                        "arguments": tool_call["function"]["arguments"]
                    }
                }]
            },
            "finish_reason": None
        }]
    }))
    # Chunk final: finish_reason
    chunks.append(sse({
        **base,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]
    }))
    chunks.append("data: [DONE]\n\n")
    return chunks
