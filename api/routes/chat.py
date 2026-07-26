from flask import Blueprint, request, Response, jsonify
import json
import time
import uuid
import logging
from services.deepseek_service import DeepSeekService

logger = logging.getLogger(__name__)
chat_bp = Blueprint('chat', __name__)
service = DeepSeekService()


# ============================================================
# ENDPOINT ORIGINAL (compatibilidad con clientes existentes)
# ============================================================
@chat_bp.route('', methods=['POST'])
def send_message():
    """Envía un mensaje y devuelve stream SSE con formato propio."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Datos JSON requeridos"}), 400
        
        session_id = data.get('session_id')
        prompt = data.get('prompt')
        if not session_id or not prompt:
            return jsonify({"error": "session_id y prompt son obligatorios"}), 400
        
        parent_message_id = data.get('parent_message_id')
        ref_file_ids = data.get('ref_file_ids', [])
        thinking_enabled = data.get('thinking_enabled', True)
        search_enabled = data.get('search_enabled', True)
        model_type = data.get('model_type')
        
        def generate():
            """Generador de eventos SSE (formato propio)."""
            yield "event: start\ndata: {}\n\n"
            try:
                for event in service.send_message(
                    session_id=session_id,
                    prompt=prompt,
                    parent_message_id=parent_message_id,
                    ref_file_ids=ref_file_ids,
                    thinking_enabled=thinking_enabled,
                    search_enabled=search_enabled,
                    model_type=model_type
                ):
                    yield f"event: {event['type']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.exception("Error en generador de chat")
                yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        
        return Response(generate(), mimetype="text/event-stream")
    except Exception as e:
        logger.exception("Error en send_message")
        return jsonify({"error": str(e)}), 500


# ============================================================
# ENDPOINT: FORMATO COMPATIBLE CON OPENAI (CORREGIDO)
# ============================================================
@chat_bp.route('/openai', methods=['POST'])
def send_message_openai():
    """
    Endpoint con formato compatible con OpenAI Chat Completion (streaming).
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Datos JSON requeridos"}), 400

        session_id = data.get('session_id')
        prompt = data.get('prompt')
        if not session_id or not prompt:
            return jsonify({"error": "session_id y prompt son obligatorios"}), 400

        parent_message_id = data.get('parent_message_id')
        ref_file_ids = data.get('ref_file_ids', [])
        thinking_enabled = data.get('thinking_enabled', True)
        search_enabled = data.get('search_enabled', True)
        model_type = data.get('model_type', 'deepseek-chat')

        def generate_openai():
            try:
                # Identificadores para el chunk
                chunk_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
                created = int(time.time())
                model = model_type or "deepseek-chat"

                # Variables para controlar el estado
                has_content = False
                thinking_phase = True

                # 1) Primer chunk: anuncia el rol 'assistant'
                first_chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None
                        }
                    ]
                }
                yield f"data: {json.dumps(first_chunk, ensure_ascii=False)}\n\n"

                # 2) Iterar sobre los eventos internos
                for event in service.send_message(
                    session_id=session_id,
                    prompt=prompt,
                    parent_message_id=parent_message_id,
                    ref_file_ids=ref_file_ids,
                    thinking_enabled=thinking_enabled,
                    search_enabled=search_enabled,
                    model_type=model_type
                ):
                    try:
                        if event['type'] in ('think', 'response'):
                            content = event['data']
                            if content:
                                # Si es pensamiento y estamos en esa fase, agregar prefijo
                                if event['type'] == 'think' and thinking_phase:
                                    content = f"💭 {content}"
                                elif event['type'] == 'response':
                                    thinking_phase = False
                                
                                chunk = {
                                    "id": chunk_id,
                                    "object": "chat.completion.chunk",
                                    "created": created,
                                    "model": model,
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {"content": content},
                                            "finish_reason": None
                                        }
                                    ]
                                }
                                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                                has_content = True

                        elif event['type'] == 'done':
                            # Mensaje final con finish_reason
                            final_chunk = {
                                "id": chunk_id,
                                "object": "chat.completion.chunk",
                                "created": created,
                                "model": model,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {},
                                        "finish_reason": "stop"
                                    }
                                ]
                            }
                            yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
                            yield "data: [DONE]\n\n"
                            break

                        elif event['type'] == 'error':
                            # En caso de error, lo mostramos como contenido y finalizamos
                            error_msg = event['data']
                            error_chunk = {
                                "id": chunk_id,
                                "object": "chat.completion.chunk",
                                "created": created,
                                "model": model,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {"content": f"[Error: {error_msg}]"},
                                        "finish_reason": "stop"
                                    }
                                ]
                            }
                            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                            yield "data: [DONE]\n\n"
                            break
                    except Exception as e:
                        logger.exception("Error procesando evento")
                        # Enviar error como chunk
                        error_chunk = {
                            "id": chunk_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": f"[Error interno: {str(e)}]"},
                                    "finish_reason": "stop"
                                }
                            ]
                        }
                        yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                        yield "data: [DONE]\n\n"
                        break

                # Si nunca llegó contenido ni done (caso raro), forzamos final
                if not has_content:
                    final_chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop"
                            }
                        ]
                    }
                    yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
            except Exception as e:
                logger.exception("Error en generate_openai")
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"

        return Response(generate_openai(), mimetype="text/event-stream")
    except Exception as e:
        logger.exception("Error en send_message_openai")
        return jsonify({"error": str(e)}), 500