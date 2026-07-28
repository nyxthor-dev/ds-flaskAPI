# routes/tool_handler.py
import json
import logging
import re
import time
import uuid
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

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

def build_tool_calls_prompt(messages: List[Dict], tools: List[Dict]) -> str:
    """
    Construye un prompt para DeepSeek indicando qué herramientas están disponibles
    y pidiendo que devuelva JSON con la herramienta a usar (o null).
    """
    # Extraer el historial de la conversación
    conversation = ""
    for msg in messages:
        role = msg.get("role", "unknown")
        content = extract_text_content(msg.get("content", ""))
        if content:
            conversation += f"{role}: {content}\n"

    # Construir descripción de herramientas
    tools_desc = []
    for tool in tools:
        func = tool.get("function", {})
        name = func.get("name", "unknown")
        desc = func.get("description", "No description")
        params = func.get("parameters", {})
        tools_desc.append(f"- {name}: {desc} (parámetros: {json.dumps(params)})")

    tools_text = "\n".join(tools_desc)

    prompt = f"""Eres un asistente que debe decidir si usar una herramienta para responder al usuario.

Historial de la conversación:
{conversation}

Herramientas disponibles:
{tools_text}

INSTRUCCIONES:
1. Si necesitas usar una herramienta para responder, devuelve SOLO un JSON con:
   {{"tool": "nombre_de_la_herramienta", "arguments": {{"param1": "valor1", "param2": "valor2"}}}}

2. Si puedes responder sin herramientas, devuelve SOLO:
   {{"tool": null}}

3. Responde SOLO con el JSON, sin texto adicional.

Ejemplo:
{{"tool": "read_file", "arguments": {{"path": "archivo.txt"}}}}
"""
    return prompt

def parse_tool_decision(response_text: str) -> Optional[Dict]:
    """Parsea la respuesta de DeepSeek para extraer la decisión de herramienta."""
    try:
        # Buscar JSON en la respuesta
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            return None

        data = json.loads(json_match.group())
        if data.get("tool") is None:
            return None

        return {
            "id": f"call_{uuid.uuid4().hex[:12]}",
            "type": "function",
            "function": {
                "name": data["tool"],
                "arguments": json.dumps(data.get("arguments", {}))
            }
        }
    except Exception as e:
        logger.warning(f"⚠️ Error parseando decisión de herramienta: {e}")
        return None

def build_tool_response(tool_call: Dict, model: str) -> tuple:
    """Construye respuesta con tool_calls (formato OpenAI)."""
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