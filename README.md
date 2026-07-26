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

<details>
<summary><b>📦 Despliegue en Render.com</b></summary>

![Render Logo](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)

### Pasos de despliegue:

1. **Conecta tu repositorio**
   - Ve a [render.com](https://render.com)
   - Conecta tu cuenta de GitHub
   - Selecciona este repositorio

2. **Configuración del servicio**
   - **Service Type:** Web Service
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** Free (o Starter recomendado)

3. **Variables de entorno**
   ```
   DEEPSEEK_TOKEN=tu_token_aquí
   DEEPSEEK_COOKIES=tus_cookies_aquí
   PORT=5000
   ```

4. **Deploy**
   - Render desplegará automáticamente cada push a `main`
   - Tu API estará en: `https://tu-servicio.onrender.com`

### Tips:
- ⏱️ Los servicios Free se pausan tras 15 min de inactividad
- 🚀 Usa Starter Plan para producción ($7/mes)
- 📊 Monitorea en el dashboard de Render

</details>

<details>
<summary><b>🐳 Despliegue con Docker</b></summary>

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5000
EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
```

### Ejecutar localmente

```bash
docker build -t ds-flaskapi .
docker run -p 5000:5000 \
  -e DEEPSEEK_TOKEN=tu_token \
  -e DEEPSEEK_COOKIES=tus_cookies \
  ds-flaskapi
```

</details>

<details>
<summary><b>☁️ Despliegue en Railway/Heroku/Vercel</b></summary>

### Railway

```bash
railway link
railway up
```

Configura las variables de entorno en el dashboard de Railway.

### Variables necesarias en cualquier plataforma:
- `DEEPSEEK_TOKEN`
- `DEEPSEEK_COOKIES`
- `PORT` (si es requerido por la plataforma)

</details>

---

## 👥 Colaboradores

<div align="center">

| ![Víctor Manuel](https://github.com/vm1008079-web.png?size=100) |
|:---:|
| **[Víctor Manuel](https://github.com/vm1008079-web)** |
| 🏆 Creador & Mantenedor |

</div>

---

## 📄 Licencia

GNU GPL v3 © 2007 · [Ver licencia completa](LICENSE)

---

<div align="center">

[GitHub](https://github.com/vm1008079-web/ds-flaskAPI) • [OpenAI Docs](https://platform.openai.com/docs/api-reference) • [Render](https://render.com)

</div>
