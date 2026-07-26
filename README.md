<div align="center">

# 🌊 DS-FlaskAPI

**API 100% compatible con OpenAI** • Razonamiento + Búsqueda + Streaming

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-green)](https://flask.palletsprojects.com)

</div>

---

## 🚀 Inicio rápido

### Instalación

```bash
git clone https://github.com/vm1008079-web/ds-flaskAPI
cd ds-flaskAPI
pip install -r requirements.txt
cp .env.example .env
python app.py
```

### Variables de entorno

```env
DEEPSEEK_TOKEN=tu_token
DEEPSEEK_COOKIES=tu_cookies
PORT=5000
```

---

## 📋 API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/v1/chat/completions` | Chat compatible con OpenAI |
| `GET` | `/v1/models` | Lista de modelos disponibles |
| `POST` | `/v1/files` | Subir archivo |
| `GET` | `/api/health` | Health check |

---

## 💡 Ejemplos de uso

### cURL

```bash
curl -X POST https://tu-api.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-reasoner",
    "messages": [{"role": "user", "content": "Hola"}],
    "reasoning_enabled": true
  }'
```

### Python + OpenAI SDK

```python
import openai

openai.api_base = "https://tu-api.onrender.com/v1"
openai.api_key = "sk-dummy"

response = openai.ChatCompletion.create(
    model="deepseek-reasoner",
    messages=[{"role": "user", "content": "¿Cómo estás?"}]
)
```

---

## 🌐 Compatibilidad

- ✅ **OpenAI SDK** - Compatible 100%
- ✅ **Cursor** / **Roo Code** - Soportado
- ✅ **Streaming** - Habilitado

**Configuración para Cursor/Roo Code:**
- Base URL: `https://tu-api.onrender.com/v1`
- API Key: `sk-dummy`
- Modelo: `deepseek-reasoner`

---

## 🚢 Despliegue

### Render.com

1. Conecta tu repositorio en [render.com](https://render.com)
2. Configura:
   - **Build:** `pip install -r requirements.txt`
   - **Start:** `gunicorn app:app`
3. Agrega variables: `DEEPSEEK_TOKEN`, `DEEPSEEK_COOKIES`

---

## 📄 Licencia

GNU GPL v3 © 2007 · [Ver licencia completa](LICENSE)

---

<div align="center">

[GitHub](https://github.com/vm1008079-web/ds-flaskAPI) • [OpenAI Docs](https://platform.openai.com/docs/api-reference)

</div>
