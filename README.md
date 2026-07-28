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

Copia `.env.example` a `.env` y complétalo. Las más importantes:

```env
DEEPSEEK_TOKEN=tu_token
DEEPSEEK_COOKIES=tu_cookies

# Protege tu API con tu propia key (recomendado en producción)
API_KEYS=genera-una-key-larga-y-aleatoria
REQUIRE_API_KEY=true

PORT=5000
```

Ver `.env.example` para la lista completa (CORS, rate limiting, logging, concurrencia).

> ⚠️ **Nota importante:** esta API no usa la API oficial de DeepSeek, sino que
> reproduce su interfaz de chat web mediante credenciales de sesión (token +
> cookies). Esto puede infringir los Términos de Servicio de DeepSeek y las
> credenciales pueden expirar o bloquearse. Úsalo bajo tu propio criterio y
> responsabilidad; para un uso en producción, evalúa la API oficial de DeepSeek.

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
  -H "Authorization: Bearer tu_api_key" \
  -d '{
    "model": "deepseek-reasoner",
    "messages": [{"role": "user", "content": "Hola"}],
    "reasoning_enabled": true
  }'
```

### Streaming

```bash
curl -N -X POST https://tu-api.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer tu_api_key" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Cuéntame algo"}],
    "stream": true
  }'
```

### Python + OpenAI SDK

```python
import openai

openai.api_base = "https://tu-api.onrender.com/v1"
openai.api_key = "tu_api_key"  # el valor que pusiste en API_KEYS

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
<summary><b>📦 Render.com</b></summary>

<div align="center">

![Render](https://dashboard.render.com/)

</div>

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
<summary><b>🐳 Docker</b></summary>

<div align="center">

![Docker](https://www.docker.com/wp-content/uploads/2022/03/Moby-logo.png)

</div>

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

### Desplegar en contenedor

```bash
docker push tu-docker-registry/ds-flaskapi:latest
```

</details>

<details>
<summary><b>☁️ Railway</b></summary>

<div align="center">

![Railway](https://railway.app/brand/logotype-light.png)

</div>

### Despliegue rápido

1. **Conecta tu repositorio**
   - Ve a [railway.app](https://railway.app)
   - Autoriza con GitHub
   - Importa este proyecto

2. **Configura variables**
   ```
   DEEPSEEK_TOKEN=tu_token
   DEEPSEEK_COOKIES=tus_cookies
   PORT=5000
   ```

3. **Deploy**
   ```bash
   railway link
   railway up
   ```

### Características:
- ⚡ Despliegue instant desde Git
- 💰 $5 USD crédito inicial
- 🔄 Auto-deploy en push
- 📈 Scaling automático

</details>

<details>
<summary><b>🐘 Heroku</b></summary>

<div align="center">

![Heroku](https://brand.heroku.com/static/media/heroku-logotype-vertical.f7cf0322.svg)

</div>

### Instalación de Heroku CLI

```bash
brew install heroku
heroku login
```

### Despliegue

```bash
heroku create tu-api-name
git push heroku main
heroku config:set DEEPSEEK_TOKEN=tu_token
heroku config:set DEEPSEEK_COOKIES=tus_cookies
heroku logs --tail
```

### Archivo necesario (Procfile)

```
web: gunicorn app:app
```

### Nota:
- Heroku descontinuó su plan gratuito en 2022
- Considera usar Railway o Render como alternativa

</details>

<details>
<summary><b>🚀 Vercel</b></summary>

<div align="center">

![Vercel](https://assets.vercel.com/image/upload/v1606654385/repositories/next-js/next-logo.png)

</div>

### Configuración para Vercel

1. **Crea vercel.json**
```json
{
  "version": 2,
  "builds": [
    {
      "src": "app.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app.py"
    }
  ]
}
```

2. **Deploy**
```bash
npm i -g vercel
vercel
```

3. **Variables de entorno en Vercel Dashboard**
```
DEEPSEEK_TOKEN
DEEPSEEK_COOKIES
```

### Nota:
- Vercel está optimizado para Next.js/Node
- Para Python puro, considera Render o Railway

</details>

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Los tests mockean el cliente de DeepSeek, así que corren sin credenciales reales ni acceso a red.

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
