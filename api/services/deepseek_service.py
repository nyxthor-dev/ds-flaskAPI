"""
Wrapper del cliente DeepSeek con gestión de sesiones y archivos.
Importa el motor desde la carpeta deepseekcli.
"""

import logging
import os
import sys
import threading
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

deepseekcli_path = project_root / "deepseekcli"
if not deepseekcli_path.exists():
    raise ImportError(f"No se encontró la carpeta 'deepseekcli' en: {deepseekcli_path}")

from deepseekcli import DeepSeekClient  # noqa: E402

from config import Config  # noqa: E402


class DeepSeekService:
    """Servicio singleton (thread-safe) para mantener el cliente DeepSeek."""

    _instance = None
    _init_lock = threading.Lock()
    _client = None
    _chat_semaphore: Optional[threading.Semaphore] = None

    def __new__(cls):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Doble check bajo lock: __init__ se llama en cada DeepSeekService(),
        # pero solo debe inicializar el cliente real una vez.
        if self._client is not None:
            return
        with self._init_lock:
            if self._client is not None:
                return
            try:
                token, cookies = Config.DEEPSEEK_TOKEN, Config.DEEPSEEK_COOKIES
                if not token or not cookies:
                    raise ValueError("Faltan DEEPSEEK_TOKEN y/o DEEPSEEK_COOKIES")
                login_dir = Path(Config.DEEPSEEK_LOGIN_DIR)
                self._client = DeepSeekClient(token=token, cookies=cookies, login_dir=login_dir)
                self._chat_semaphore = threading.Semaphore(Config.MAX_CONCURRENT_CHATS)
                logger.info("✅ Cliente DeepSeek inicializado correctamente")
            except Exception:
                logger.exception("❌ Error al inicializar el cliente DeepSeek")
                raise

    @property
    def client(self) -> DeepSeekClient:
        return self._client

    def create_session(self) -> str:
        try:
            session_id = self.client.create_chat_session()
            logger.info("✅ Sesión creada: %s", session_id)
            return session_id
        except Exception:
            logger.error("❌ Error al crear sesión", exc_info=True)
            raise

    def upload_file(self, file_path: str, thinking: bool = True) -> str:
        try:
            file_id = self.client.upload_file(file_path, thinking_enabled=thinking)
            logger.info("✅ Archivo subido: %s", file_id)
            return file_id
        except Exception:
            logger.error("❌ Error al subir archivo", exc_info=True)
            raise

    def send_message(
        self,
        session_id: str,
        prompt: str,
        parent_message_id: Optional[int] = None,
        ref_file_ids: Optional[List[str]] = None,
        thinking_enabled: bool = True,
        search_enabled: bool = True,
        model_type: Optional[str] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Envía un mensaje y devuelve un generador de eventos (streaming interno).

        NOTA: los modelos deepseek-chat/deepseek-reasoner son FICTICIOS a nivel de
        API pública; aquí solo controlan thinking_enabled y search_enabled. El
        cliente real de DeepSeek no recibe un "modelo" explícito.
        """
        if Config.LOG_PROMPT_CONTENT:
            logger.info("📤 session=%s thinking=%s search=%s prompt=%r", session_id, thinking_enabled, search_enabled, prompt[:100])
        else:
            logger.info("📤 session=%s thinking=%s search=%s len(prompt)=%d", session_id, thinking_enabled, search_enabled, len(prompt))

        queue: Queue = Queue()
        acquired = self._chat_semaphore.acquire(timeout=Config.CHAT_TIMEOUT_SECONDS)
        if not acquired:
            yield {"type": "error", "data": "Servidor saturado, intenta de nuevo en unos segundos."}
            return

        def on_think(chunk: str):
            queue.put(("think", chunk))

        def on_response(chunk: str):
            queue.put(("response", chunk))

        def chat_thread():
            try:
                think, response, msg_id = self.client.chat(
                    prompt=prompt,
                    session_id=session_id,
                    parent_message_id=parent_message_id,
                    ref_file_ids=ref_file_ids,
                    stream=True,
                    thinking_enabled=thinking_enabled,
                    search_enabled=search_enabled,
                    print_output=False,
                    on_think_chunk=on_think,
                    on_response_chunk=on_response,
                    save_history=True,
                )
                logger.info("✅ Chat completado. Message ID: %s (think=%d chars, response=%d chars)", msg_id, len(think), len(response))

                if not response and not think:
                    logger.warning("⚠️ Respuesta vacía del modelo")
                    queue.put(("response", "Lo siento, no pude generar una respuesta. Por favor, intenta de nuevo."))

                queue.put(("done", msg_id))
            except Exception as e:
                logger.exception("❌ Error en el hilo de chat")
                queue.put(("error", str(e)))
            finally:
                self._chat_semaphore.release()

        thread = threading.Thread(target=chat_thread, daemon=True)
        thread.start()

        deadline_hit = False
        while True:
            try:
                event_type, data = queue.get(timeout=Config.CHAT_TIMEOUT_SECONDS)
            except Empty:
                deadline_hit = True
                yield {"type": "error", "data": "Tiempo de espera agotado esperando respuesta del backend."}
                break

            if event_type == "done":
                yield {"type": "done", "data": data}
                break
            elif event_type == "error":
                yield {"type": "error", "data": data}
                break
            else:
                yield {"type": event_type, "data": data}

        if deadline_hit:
            thread.join(timeout=1)
