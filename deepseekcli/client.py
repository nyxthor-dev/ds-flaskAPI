from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional, Tuple, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .errors import NetworkError, APIError, InvalidResponseError
from .auth import AuthStorage
from .chat_storage import ChatStorage
from .exporter import export_chat_to_html, export_chat_to_markdown
from .pow import DeepSeekPow

BASE_URL = "https://chat.deepseek.com"
logger = logging.getLogger(__name__)


class DeepSeekClient:
    def __init__(
        self,
        token: Optional[str] = None,
        cookies: Optional[str] = None,
        login_dir: Optional[Path] = None,
        timeout: int = 10,
    ):
        self.login_dir = Path(login_dir or Path(".login"))
        self.storage = AuthStorage(self.login_dir)
        self.chat_storage = ChatStorage(self.login_dir)
        self.token = token.strip() if token else None
        self.cookies = cookies.strip() if cookies else None
        self.pow_solver = DeepSeekPow()
        self._timeout = timeout

        # Sesión HTTP con retries
        self._session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=frozenset(
                ["GET", "POST", "PUT", "DELETE", "HEAD"]),
        )
        adapter = HTTPAdapter(max_retries=retries)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

        self.storage.ensure_dirs()
        credentials_exist = self.storage.credentials_path.exists()
        # Guardar credenciales solo si no existen y no son placeholders
        placeholder_values = {"test", "", None}
        if self.token and self.cookies and not credentials_exist and self.token not in placeholder_values and self.cookies not in placeholder_values:
            try:
                self.storage.save_credentials(self.token, self.cookies)
            except Exception as e:
                logger.warning("No se pudieron guardar credenciales: %s", e)
        else:
            try:
                self._load_credentials()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._session.close()

    def _load_credentials(self) -> None:
        creds = self.storage.load_credentials()
        self.token = creds["token"]
        self.cookies = creds["cookies"]

    def _ensure_credentials(self) -> None:
        if not self.token or not self.cookies:
            raise RuntimeError(
                "Faltan credenciales. Usa DeepSeekClient(token, cookies) o guarda en .login/credentials.json"
            )

    def _base_headers(self) -> dict[str, str]:
        self._ensure_credentials()
        return {
            "authorization": f"Bearer {self.token}",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0",
            "origin": "https://chat.deepseek.com",
            "referer": "https://chat.deepseek.com/",
            "cookie": self.cookies,
            "x-app-version": "2.2.0",
            "x-client-version": "2.2.0",
            "x-client-platform": "web",
            "x-client-locale": "en_US",
            "x-client-bundle-id": "com.deepseek.chat",
            "x-client-timezone-offset": "-14400",
            "accept": "*/*",
            "accept-language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "priority": "u=0",
            "te": "trailers",
        }

    def _send_request(self, method: str, url: str, stream: bool = False, **kwargs) -> requests.Response:
        try:
            kwargs.setdefault("timeout", self._timeout)
            resp = self._session.request(method, url, stream=stream, **kwargs)
        except requests.exceptions.RequestException as e:
            logger.debug("Error de red al solicitar %s: %s", url, e)
            raise NetworkError(str(e)) from e

        if not stream:
            try:
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                body = None
                try:
                    body = resp.text[:1000]
                except Exception:
                    body = None
                raise APIError(
                    "Error HTTP", status_code=resp.status_code, body=body) from e

        return resp

    # ==================== SESIÓN ====================

    def create_chat_session(self) -> str:
        url = f"{BASE_URL}/api/v0/chat_session/create"
        resp = self._send_request(
            "POST", url, headers=self._base_headers(), json={})
        try:
            data = resp.json()
        except ValueError as e:
            raise InvalidResponseError(
                "JSON inválido en create_chat_session") from e
        if data.get("code") != 0:
            raise APIError("Error al crear sesión", body=data)
        session_id = data["data"]["biz_data"]["chat_session"]["id"]
        logger.info("Sesión creada: %s", session_id)
        return session_id

    # ==================== POW ====================

    def request_pow_header(self, target_path: str) -> str:
        url = f"{BASE_URL}/api/v0/chat/create_pow_challenge"
        payload = {"target_path": target_path}
        resp = self._send_request(
            "POST", url, headers=self._base_headers(), json=payload)
        try:
            data = resp.json()
        except ValueError as e:
            raise InvalidResponseError(
                "JSON inválido en request_pow_header") from e
        if data.get("code") != 0:
            raise APIError("Error al obtener challenge PoW", body=data)
        challenge = data["data"]["biz_data"]["challenge"]
        return self.pow_solver.make_header(challenge)

    # ==================== ARCHIVOS ====================

    def upload_file(
        self,
        file_path: str,
        model_type: str = "default",
        thinking_enabled: bool = True,
    ) -> str:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        pow_header = self.request_pow_header("/api/v0/file/upload_file")
        url = f"{BASE_URL}/api/v0/file/upload_file"
        headers = self._base_headers()
        headers.pop("content-type", None)
        headers["x-ds-pow-response"] = pow_header
        headers["x-thinking-enabled"] = "1" if thinking_enabled else "0"
        headers["x-model-type"] = model_type
        headers["x-file-size"] = str(file_path_obj.stat().st_size)

        with open(file_path_obj, "rb") as f:
            files = {"file": (file_path_obj.name, f,
                              "application/octet-stream")}
            resp = self._send_request(
                "POST", url, headers=headers, files=files)
        try:
            data = resp.json()
        except ValueError as e:
            raise InvalidResponseError("JSON inválido en upload_file") from e
        if data.get("code") != 0:
            raise APIError("Error al subir archivo", body=data)

        file_id = data["data"]["biz_data"]["id"]
        logger.info("Archivo subido: %s", file_id)
        return file_id

    def fetch_file_status(self, file_id: str) -> dict[str, Any]:
        url = f"{BASE_URL}/api/v0/file/fetch_files?file_ids={file_id}"
        resp = self._send_request("GET", url, headers=self._base_headers())
        try:
            data = resp.json()
        except ValueError as e:
            raise InvalidResponseError(
                "JSON inválido en fetch_file_status") from e
        if data.get("code") != 0:
            raise APIError("Error al obtener estado del archivo", body=data)
        files = data["data"]["biz_data"].get("files", [])
        if not files:
            raise RuntimeError(
                f"No se encontró información para el archivo {file_id}")
        return files[0]

    def wait_for_file_ready(
        self,
        file_id: str,
        timeout: int = 120,
        poll_interval: int = 2,
    ) -> dict[str, Any]:
        start = time.time()
        while True:
            status_info = self.fetch_file_status(file_id)
            status = status_info.get("status", "").upper()
            if status == "SUCCESS":
                return status_info
            if status in {"FAILED", "ERROR"}:
                raise RuntimeError(
                    f"El procesamiento del archivo {file_id} falló: {status_info}")
            elapsed = time.time() - start
            if elapsed >= timeout:
                raise TimeoutError(
                    f"Tiempo de espera agotado para el archivo {file_id} después de {timeout}s"
                )
            time.sleep(poll_interval)

    # ==================== STREAM PROCESSOR (shared) ====================

    def _process_stream(
        self,
        resp: requests.Response,
        print_output: bool,
        on_think_chunk: Optional[Callable[[str], None]],
        on_response_chunk: Optional[Callable[[str], None]],
        on_message_id: Optional[Callable[[int], None]] = None,
    ) -> Tuple[str, str, Optional[int], bool]:
        """
        Procesa un stream SSE de chat/regenerate/continue.
        Devuelve: (think_text, response_text, response_message_id, is_incomplete)
        """
        fragments: dict[str, dict[str, Any]] = {}
        current_fragment_id: Optional[str] = None
        think_full: list[str] = []
        response_full: list[str] = []
        think_header_printed = False
        response_header_printed = False
        response_message_id: Optional[int] = None
        is_incomplete = False

        def print_think(text: str) -> None:
            nonlocal think_header_printed
            if on_think_chunk and text:
                on_think_chunk(text)
            if not print_output:
                return
            if not think_header_printed:
                sys.stdout.write("\n\n🧠 PENSAMIENTO:\n")
                think_header_printed = True
            sys.stdout.write(text)
            sys.stdout.flush()

        def print_response(text: str) -> None:
            nonlocal response_header_printed
            if on_response_chunk and text:
                on_response_chunk(text)
            if not response_header_printed:
                sys.stdout.write("\n\n💬 RESPUESTA:\n")
                response_header_printed = True
            sys.stdout.write(text)
            sys.stdout.flush()

        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue

            # Evento ready con IDs
            if line.startswith("event: ready"):
                continue

            if not line.startswith("data: "):
                # Detectar event: close para auto_resume
                if line.startswith("event: close"):
                    continue
                continue

            data_str = line[6:].strip()
            if not data_str or data_str == "{}" or data_str.startswith('"'):
                continue

            try:
                obj = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            # ---- Capturar response_message_id del evento ready (data) ----
            if "request_message_id" in obj and "response_message_id" in obj:
                msg_id = obj["response_message_id"]
                try:
                    response_message_id = int(msg_id)
                except (ValueError, TypeError):
                    logger.warning(
                        "response_message_id no es un entero: %s", msg_id)
                    response_message_id = msg_id
                if on_message_id and response_message_id is not None:
                    on_message_id(response_message_id)

            # ---- Detectar INCOMPLETE status ----
            if obj.get("p") == "response/status" and obj.get("o") == "SET" and obj.get("v") == "INCOMPLETE":
                is_incomplete = True
                continue

            # ---- Procesar fragmentos de respuesta ----
            # Caso 1: fragmentos dentro de "v.response.fragments"
            if "v" in obj and isinstance(obj["v"], dict) and "response" in obj["v"]:
                frags = obj["v"]["response"].get("fragments", [])
                for frag in frags:
                    if "id" in frag and "type" in frag:
                        fid = frag["id"]
                        ftype = frag["type"]
                        content = frag.get("content") or ""
                        prev = fragments.get(fid, {}).get("content") or ""
                        # DeepSeek a veces reenvía el snapshot completo del
                        # fragmento (no solo el delta). Solo emitimos la
                        # parte nueva respecto a lo ya recibido, si no se
                        # duplica el texto entero.
                        delta = content[len(prev):] if content.startswith(prev) else content
                        fragments[fid] = {
                            "type": ftype, "content": content}
                        if delta:
                            if ftype == "THINK":
                                print_think(delta)
                                think_full.append(delta)
                            elif ftype == "RESPONSE":
                                print_response(delta)
                                response_full.append(delta)
                        if ftype in {"THINK", "RESPONSE"}:
                            current_fragment_id = fid

            # Caso 2: actualización APPEND con estructura "p": "response/fragments"
            elif obj.get("p") == "response/fragments" and obj.get("o") == "APPEND":
                for frag in obj.get("v", []):
                    if "id" in frag and "type" in frag:
                        fid = frag["id"]
                        ftype = frag["type"]
                        content = frag.get("content") or ""
                        prev = fragments.get(fid, {}).get("content") or ""
                        delta = content[len(prev):] if content.startswith(prev) else content
                        fragments[fid] = {
                            "type": ftype, "content": content}
                        if delta:
                            if ftype == "THINK":
                                print_think(delta)
                                think_full.append(delta)
                            elif ftype == "RESPONSE":
                                print_response(delta)
                                response_full.append(delta)
                        if ftype in {"THINK", "RESPONSE"}:
                            current_fragment_id = fid

            # Caso 3: actualización directa de un fragmento existente
            elif obj.get("p", "").startswith("response/fragments/") and obj.get("o") == "APPEND" and isinstance(obj.get("v"), str):
                target_id = current_fragment_id
                if not target_id or target_id not in fragments or fragments[target_id]["type"] not in {"THINK", "RESPONSE"}:
                    response_ids = [
                        fid for fid, frag in fragments.items() if frag["type"] == "RESPONSE"]
                    if response_ids:
                        target_id = max(response_ids)
                if target_id and target_id in fragments:
                    fragments[target_id]["content"] = (
                        fragments[target_id]["content"] or "") + obj["v"]
                    if fragments[target_id]["type"] == "THINK":
                        print_think(obj["v"])
                        think_full.append(obj["v"])
                    elif fragments[target_id]["type"] == "RESPONSE":
                        print_response(obj["v"])
                        response_full.append(obj["v"])

            # Caso 4: mensaje simple con "p" y "v" (sin fragmentos explícitos)
            elif "p" in obj and "v" in obj and isinstance(obj["v"], str):
                target_id = current_fragment_id
                if target_id and target_id in fragments:
                    if fragments[target_id]["type"] == "THINK":
                        print_think(obj["v"])
                        think_full.append(obj["v"])
                    elif fragments[target_id]["type"] == "RESPONSE":
                        print_response(obj["v"])
                        response_full.append(obj["v"])
                    fragments[target_id]["content"] = (
                        fragments[target_id]["content"] or "") + obj["v"]
                elif fragments:
                    last_id = max(fragments.keys())
                    if fragments[last_id]["type"] == "THINK":
                        print_think(obj["v"])
                        think_full.append(obj["v"])
                    elif fragments[last_id]["type"] == "RESPONSE":
                        print_response(obj["v"])
                        response_full.append(obj["v"])
                    fragments[last_id]["content"] = (
                        fragments[last_id]["content"] or "") + obj["v"]
                else:
                    fragments["_default"] = {
                        "type": "RESPONSE", "content": obj["v"]}
                    print_response(obj["v"])
                    response_full.append(obj["v"])
                    current_fragment_id = "_default"

            # Caso 5: solo "v" (texto suelto)
            elif "v" in obj and isinstance(obj["v"], str) and "p" not in obj:
                target_id = current_fragment_id
                if target_id and target_id in fragments:
                    if fragments[target_id]["type"] == "THINK":
                        print_think(obj["v"])
                        think_full.append(obj["v"])
                    elif fragments[target_id]["type"] == "RESPONSE":
                        print_response(obj["v"])
                        response_full.append(obj["v"])
                    fragments[target_id]["content"] = (
                        fragments[target_id]["content"] or "") + obj["v"]
                elif fragments:
                    last_id = max(fragments.keys())
                    if fragments[last_id]["type"] == "THINK":
                        print_think(obj["v"])
                        think_full.append(obj["v"])
                    elif fragments[last_id]["type"] == "RESPONSE":
                        print_response(obj["v"])
                        response_full.append(obj["v"])
                    fragments[last_id]["content"] = (
                        fragments[last_id]["content"] or "") + obj["v"]
                else:
                    fragments["_default"] = {
                        "type": "RESPONSE", "content": obj["v"]}
                    print_response(obj["v"])
                    response_full.append(obj["v"])
                    current_fragment_id = "_default"

            # Detectar fin del stream
            if obj.get("finish_reason") == "stop":
                break

        sys.stdout.write("\n\n")
        sys.stdout.flush()

        think_text = "".join(think_full).strip()
        response_text = "".join(response_full).strip()
        think_text = think_text.replace("FINISHED", "").strip()
        response_text = response_text.replace("FINISHED", "").strip()

        return think_text, response_text, response_message_id, is_incomplete

    # ==================== CHAT ====================

    def chat(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        ref_file_ids: Optional[list[str]] = None,
        parent_message_id: Optional[Union[int, str]] = None,
        stream: bool = True,
        thinking_enabled: bool = True,
        search_enabled: bool = True,
        model_type: Optional[str] = None,
        print_output: bool = True,
        on_think_chunk: Optional[Callable[[str], None]] = None,
        on_response_chunk: Optional[Callable[[str], None]] = None,
        on_message_id: Optional[Callable[[int], None]] = None,
        save_history: bool = True,
    ) -> Tuple[str, str, Optional[int], bool]:
        """
        Envía un mensaje y devuelve (think, response, response_message_id, is_incomplete).
        """
        if parent_message_id is not None:
            try:
                parent_message_id = int(parent_message_id)
            except (ValueError, TypeError):
                raise ValueError(
                    f"parent_message_id debe ser un entero o None, recibido: {parent_message_id}")

        if session_id is None:
            session_id = self.create_chat_session()
            if print_output:
                print(f"📌 Nueva sesión: {session_id}")

        pow_header = self.request_pow_header("/api/v0/chat/completion")
        url = f"{BASE_URL}/api/v0/chat/completion"
        headers = self._base_headers()
        headers["x-ds-pow-response"] = pow_header

        payload = {
            "chat_session_id": session_id,
            "parent_message_id": parent_message_id,
            "model_type": model_type,
            "prompt": prompt,
            "ref_file_ids": ref_file_ids or [],
            "thinking_enabled": thinking_enabled,
            "search_enabled": search_enabled,
            "action": None,
            "preempt": False,
        }

        with self._send_request("POST", url, headers=headers, json=payload, stream=stream) as resp:
            think_text, response_text, response_message_id, is_incomplete = self._process_stream(
                resp, print_output, on_think_chunk, on_response_chunk, on_message_id
            )

        if save_history and response_message_id is not None:
            try:
                save_parent = int(
                    parent_message_id) if parent_message_id is not None else None
            except (ValueError, TypeError):
                save_parent = parent_message_id
            self.chat_storage.save_or_update_chat(
                session_id=session_id,
                prompt=prompt,
                think=think_text,
                response=response_text,
                ref_file_ids=ref_file_ids or [],
                parent_message_id=save_parent,
            )

        return think_text, response_text, response_message_id, is_incomplete

    # ==================== REGENERATE ====================

    def regenerate(
        self,
        session_id: str,
        child_message_id: Union[int, str],
        stream: bool = True,
        thinking_enabled: bool = True,
        search_enabled: bool = True,
        user_options: Optional[dict[str, Any]] = None,
        print_output: bool = True,
        on_think_chunk: Optional[Callable[[str], None]] = None,
        on_response_chunk: Optional[Callable[[str], None]] = None,
        on_message_id: Optional[Callable[[int], None]] = None,
        save_history: bool = True,
    ) -> Tuple[str, str, Optional[int], bool]:
        """
        Regenera una respuesta existente (reemplaza child_message_id).
        Devuelve (think, response, new_response_message_id, is_incomplete).
        """
        try:
            child_message_id = int(child_message_id)
        except (ValueError, TypeError):
            raise ValueError(f"child_message_id debe ser un entero, recibido: {child_message_id}")

        pow_header = self.request_pow_header("/api/v0/chat/completion")
        url = f"{BASE_URL}/api/v0/chat/regenerate"
        headers = self._base_headers()
        headers["x-ds-pow-response"] = pow_header

        payload = {
            "chat_session_id": session_id,
            "child_message_id": child_message_id,
            "search_enabled": search_enabled,
            "thinking_enabled": thinking_enabled,
            "user_options": user_options,
        }

        with self._send_request("POST", url, headers=headers, json=payload, stream=stream) as resp:
            think_text, response_text, response_message_id, is_incomplete = self._process_stream(
                resp, print_output, on_think_chunk, on_response_chunk, on_message_id
            )

        if save_history and response_message_id is not None:
            self.chat_storage.save_or_update_chat(
                session_id=session_id,
                prompt=f"[REGENERADO msg={child_message_id}]",
                think=think_text,
                response=response_text,
                ref_file_ids=[],
                parent_message_id=child_message_id,
            )

        return think_text, response_text, response_message_id, is_incomplete

    # ==================== STOP STREAM ====================

    def stop_stream(self, session_id: str, message_id: Union[int, str]) -> dict[str, Any]:
        """
        Detiene la generación en curso de un mensaje específico.
        Útil para cancelar desde otro hilo mientras chat()/regenerate() están activos.
        """
        try:
            message_id = int(message_id)
        except (ValueError, TypeError):
            raise ValueError(f"message_id debe ser un entero, recibido: {message_id}")

        url = f"{BASE_URL}/api/v0/chat/stop_stream"
        resp = self._send_request(
            "POST", url, headers=self._base_headers(), json={
                "chat_session_id": session_id,
                "message_id": message_id,
            }
        )
        try:
            data = resp.json()
        except ValueError as e:
            raise InvalidResponseError("JSON inválido en stop_stream") from e
        if data.get("code") != 0:
            raise APIError("Error al detener stream", body=data)
        logger.info("Stream detenido para message_id=%s", message_id)
        return data

    # ==================== CONTINUE ====================

    def continue_generation(
        self,
        session_id: str,
        message_id: Union[int, str],
        fallback_to_resume: bool = True,
        stream: bool = True,
        print_output: bool = True,
        on_think_chunk: Optional[Callable[[str], None]] = None,
        on_response_chunk: Optional[Callable[[str], None]] = None,
        on_message_id: Optional[Callable[[int], None]] = None,
        save_history: bool = False,
    ) -> Tuple[str, str, Optional[int], bool]:
        """
        Continúa una respuesta que quedó INCOMPLETE.
        Devuelve (think, response, response_message_id, is_incomplete).
        """
        try:
            message_id = int(message_id)
        except (ValueError, TypeError):
            raise ValueError(f"message_id debe ser un entero, recibido: {message_id}")

        url = f"{BASE_URL}/api/v0/chat/continue"
        headers = self._base_headers()
        # El capture no muestra x-ds-pow-response en continue; se omite por defecto.
        # Si el servidor lo exige, agregar: headers["x-ds-pow-response"] = self.request_pow_header("/api/v0/chat/completion")

        payload = {
            "chat_session_id": session_id,
            "message_id": message_id,
            "fallback_to_resume": fallback_to_resume,
        }

        with self._send_request("POST", url, headers=headers, json=payload, stream=stream) as resp:
            think_text, response_text, response_message_id, is_incomplete = self._process_stream(
                resp, print_output, on_think_chunk, on_response_chunk, on_message_id
            )

        if save_history and response_message_id is not None:
            self.chat_storage.save_or_update_chat(
                session_id=session_id,
                prompt=f"[CONTINUADO msg={message_id}]",
                think=think_text,
                response=response_text,
                ref_file_ids=[],
                parent_message_id=message_id,
            )

        return think_text, response_text, response_message_id, is_incomplete

    # ==================== GESTIÓN DE CHATS ====================

    def list_saved_chats(self) -> list[dict[str, Any]]:
        return self.chat_storage.list_chats()

    def load_saved_chat(self, file_name: str) -> dict[str, Any]:
        return self.chat_storage.load_chat(file_name)

    def export_chat(self, file_name: str, output_path: Optional[Path] = None, format: str = "md") -> Path:
        chat = self.chat_storage.load_chat(file_name)
        if output_path is None:
            output_path = self.login_dir / "exports"
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        if format == "md":
            destination = output_path / f"{Path(file_name).stem}.md"
            return export_chat_to_markdown(chat, destination)
        if format == "html":
            destination = output_path / f"{Path(file_name).stem}.html"
            return export_chat_to_html(chat, destination)
        raise ValueError("Formato no soportado: use 'md' o 'html'.")
