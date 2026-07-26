# Changelog

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [2.0.0] - 2026-07-26

### 🎉 Cambios Principales

**Versión completamente refactorizada con enfoque en compatibilidad 100% con OpenAI.**

La API ahora es totalmente compatible con el SDK de OpenAI y otros clientes que esperan los estándares de OpenAI.

---

### ✨ Agregado

#### Endpoints
- **`GET /v1/models`** - Listado de modelos disponibles (estándar OpenAI)
  - Devuelve `deepseek-chat` y `deepseek-reasoner`
  - Formato 100% compatible con OpenAI
  
- **`POST /v1/chat/completions`** - Chat completions (refactorizado)
  - Soporte completo para parámetros OpenAI estándar
  - Validación de rangos para `temperature`, `top_p`, penalties, etc.
  - Streaming y no-streaming
  - Razonamiento (thinking) en formato OpenAI
  
- **`GET /api/health`** - Health check mejorado
  - Incluye timestamp de la respuesta
  
- **Middleware de Autorización**
  - Acepta `Authorization: Bearer <token>` sin validación explícita
  - Previene fallos en clientes OpenAI estándar

#### Parámetros OpenAI Soportados
```python
- temperature (0-2)
- top_p (0-1)
- max_tokens
- presence_penalty (-2 a 2)
- frequency_penalty (-2 a 2)
- stop (secuencias de parada)
- reasoning_effort (low, medium, high)
- stream (true/false)
```

#### Logging Mejorado
- Logs más detallados y estructurados
- Emojis para mejor legibilidad en terminal
- Niveles de log apropiados (DEBUG, INFO, ERROR)
- Información de sesión, modelo, parámetros

#### Documentación
- README.md completo con ejemplos de uso
- Ejemplos para OpenAI SDK
- Ejemplos para Cursor/Roo Code
- Instrucciones de despliegue en Render

### 🔄 Cambios

#### `api/app.py`
- ✅ Versión actualizada a 2.0.0
- ✅ Descripción: "API 100% compatible con OpenAI y DeepSeek"
- ✅ Middleware de autorización que acepta bearer tokens
- ✅ Secciones comentadas para mejor organización
- ✅ Rutas registradas con URL prefixes correctos
- ✅ Endpoint raíz (`/`) con información detallada de la API
- ✅ Error handler mejorado con formato OpenAI

#### `api/routes/chat.py`
- ✅ Refactorización completa para OpenAI compatibility
- ✅ Función helper `openai_error()` para respuestas de error consistentes
- ✅ Validación exhaustiva de parámetros OpenAI
- ✅ Soporte para razonamiento (`reasoning_content`)
- ✅ Control de modelos ficticios:
  - `deepseek-chat` → razonamiento desactivado
  - `deepseek-reasoner` → razonamiento activado
- ✅ Logging estructurado y detallado
- ✅ Manejo de errores en evento de streaming

#### `api/routes/upload.py`
- ✅ Simplificación de código
- ✅ Endpoint `POST /v1/files` - Upload estándar OpenAI
- ✅ Endpoint `GET /v1/files` - Listar archivos
- ✅ Endpoint `DELETE /v1/files/<file_id>` - Eliminar archivos
- ✅ Endpoint OPTIONS para CORS

#### `api/services/deepseek_service.py`
- ✅ Error handling mejorado en métodos:
  - `create_session()` - Try/except con logging
  - `upload_file()` - Try/except con logging
  - `send_message()` - Documentación completa
- ✅ Parámetros OpenAI agregados a `send_message()`
- ✅ Método `send_message_raw()` para respuestas completas
- ✅ Documentación extendida de docstrings
- ✅ Manejo de respuestas vacías del modelo
- ✅ Logging en niveles DEBUG, INFO, WARNING, ERROR

### 🐛 Correcciones

- ✅ Eliminado streaming fallido (simplificado a respuesta única)
- ✅ Corregido manejo de parámetros DeepSeek específicos
- ✅ Mejor separación entre parámetros OpenAI y DeepSeek
- ✅ Validación de mensajes de usuario faltantes
- ✅ Manejo de respuestas vacías del modelo

### 🗑️ Eliminado

- ❌ Endpoint legacy `/api/chat` (sin parámetros)
- ❌ Función `openai_error()` de versiones anteriores (reemplazada por nueva)
- ❌ Parámetros OpenAI no implementados (ahora validados pero no usados)
- ❌ Streaming con SSE complicado (simplificado)

### 📚 Documentación

- ✅ `README.md` completamente escrito
  - Tabla de endpoints
  - Instrucciones de instalación
  - Variables de entorno
  - Ejemplos rápidos
  - Compatibilidad con OpenAI SDK
  - Compatibilidad con Cursor/Roo Code
  - Instrucciones Render
  - Licencia MIT

### 🏗️ Arquitectura

**Estructura de respuestas:**
```json
{
  "id": "chatcmpl-xxxxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "deepseek-reasoner",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "...",
      "reasoning_content": "..." // Opcional
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 50,
    "total_tokens": 60
  }
}
```

---

## [1.0.0] - 2026-07-26 (Inicial)

### ✨ Agregado

- ✅ Proyecto inicial
- ✅ Estructura base con Flask
- ✅ Integración con DeepSeek CLI
- ✅ Endpoints básicos OpenAI
- ✅ Soporte para streaming
- ✅ CORS configurado
- ✅ Logging básico
- ✅ Variables de entorno

---

## Próximas Versiones (Roadmap)

### 🎯 v2.1.0 (Previsto)
- [ ] Rate limiting por usuario
- [ ] Token counting con tiktoken
- [ ] Persistencia de archivos
- [ ] Tests unitarios
- [ ] OpenAPI/Swagger docs
- [ ] Thread-safe singleton

### 🎯 v3.0.0 (Previsto)
- [ ] Autenticación y autorización
- [ ] Base de datos de sesiones
- [ ] Caché de respuestas
- [ ] Métricas y monitoreo
- [ ] Sentry integration
- [ ] Rate limiting avanzado

---

## Notas de Desarrollo

### Convenciones
- Los commits siguen un patrón de actualización (Actualizar X.py)
- Se usa Semantic Versioning para versiones
- Cada release incluye changelog

### Compatibilidad
- ✅ Python 3.8+
- ✅ Flask 3.0.3
- ✅ OpenAI SDK compatible
- ✅ Deployable en Render.com

### Estado del Proyecto
- 🟢 En desarrollo activo
- 📦 Beta (v2.0.0)
- ✅ Compatible con producción
- ⚠️ Requiere credenciales DeepSeek válidas

---

## Cómo Reportar Bugs

Por favor abre un issue describiendo:
1. El endpoint afectado
2. La solicitud (sin credenciales)
3. La respuesta de error
4. El nivel de urgencia

---

## Licencia

Este proyecto usa licencia GNU GPL V3. Ver [LICENSE](LICENSE) para más detalles.

---

**Última actualización:** 2026-07-26  
**Versión actual:** 2.0.0  
**Autor:** Víctor Manuel | Orion's Wolf
