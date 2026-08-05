<div align="center">

<!-- BANNER -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=200&section=header&text=DS-FlaskAPI&fontSize=60&fontColor=fff&animation=fadeIn&fontAlignY=35&desc=API%20OpenAI-compatible%20para%20DeepSeek%20%7C%20Razonamiento%20%2B%20B%C3%BAsqueda%20%2B%20Streaming&descAlignY=55&descSize=18" />

<br>

<!-- BADGES PRINCIPALES -->
<p>
  <a href="https://github.com/vm1008079-web/ds-flaskAPI/stargazers">
    <img src="https://img.shields.io/github/stars/vm1008079-web/ds-flaskAPI?style=for-the-badge&logo=github&color=FFD700&logoColor=white" alt="Stars" />
  </a>
  <a href="https://github.com/vm1008079-web/ds-flaskAPI/network/members">
    <img src="https://img.shields.io/github/forks/vm1008079-web/ds-flaskAPI?style=for-the-badge&logo=github&color=00BFFF&logoColor=white" alt="Forks" />
  </a>
  <a href="https://github.com/vm1008079-web/ds-flaskAPI/issues">
    <img src="https://img.shields.io/github/issues/vm1008079-web/ds-flaskAPI?style=for-the-badge&logo=github&color=FF6B6B&logoColor=white" alt="Issues" />
  </a>
  <a href="https://github.com/vm1008079-web/ds-flaskAPI/pulls">
    <img src="https://img.shields.io/github/issues-pr/vm1008079-web/ds-flaskAPI?style=for-the-badge&logo=github&color=4ECDC4&logoColor=white" alt="Pull Requests" />
  </a>
</p>

<!-- BADGES DE ESTADO Y CALIDAD -->
<p>
  <a href="#">
    <img src="https://img.shields.io/badge/build-passing-brightgreen?style=for-the-badge&logo=githubactions&logoColor=white" alt="Build" />
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/tests-passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white" alt="Tests" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-GPL%20v3-blue?style=for-the-badge&logo=gnu&logoColor=white" alt="License" />
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/code%20style-black-000000?style=for-the-badge&logo=python&logoColor=white" alt="Code Style" />
  </a>
</p>

<!-- BADGES DE PLATAFORMAS Y COMPATIBILIDAD -->
<p>
  <img src="https://img.shields.io/badge/OpenAI-Compatible-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI Compatible" />
  <img src="https://img.shields.io/badge/DeepSeek-R1-1E3A8A?style=for-the-badge&logo=deepseek&logoColor=white" alt="DeepSeek" />
  <img src="https://img.shields.io/badge/Streaming-SSE-FF6D00?style=for-the-badge&logo=apachekafka&logoColor=white" alt="Streaming" />
  <img src="https://img.shields.io/badge/Reasoning-Enabled-10B981?style=for-the-badge&logo=brain&logoColor=white" alt="Reasoning" />
</p>

<br>

<!-- DESCRIPCIÓN CORTA -->
<p align="center">
  <b>🔌 API REST 100% compatible con OpenAI</b> que expone los modelos de <b>DeepSeek</b> 
  <br>
  (incluyendo <code>deepseek-reasoner</code> con razonamiento paso a paso) 
  <br>
  mediante una interfaz web. Soporta <b>streaming</b>, <b>búsqueda web</b> y múltiples clientes.
</p>

<br>

<!-- DEMO / PREVIEW -->
<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%">

</div>

<br>

<!-- TABLA DE CONTENIDOS -->
## 📑 Tabla de Contenidos

- [🌟 Características](#-características)
- [🚀 Inicio Rápido](#-inicio-rápido)
  - [Prerrequisitos](#prerrequisitos)
  - [Instalación](#instalación)
  - [Variables de Entorno](#variables-de-entorno)
- [📡 API Endpoints](#-api-endpoints)
- [💡 Ejemplos de Uso](#-ejemplos-de-uso)
  - [cURL](#curl)
  - [Python (OpenAI SDK)](#python-openai-sdk)
  - [JavaScript](#javascript)
  - [Streaming](#streaming)
- [🔧 Compatibilidad](#-compatibilidad)
- [🛠️ Stack Tecnológico](#️-stack-tecnológico)
- [🚢 Despliegue](#-despliegue)
  - [Render](#render)
  - [Docker](#docker)
  - [Railway](#railway)
  - [Heroku](#heroku)
  - [Vercel](#vercel)
- [🧪 Tests](#-tests)
- [🤝 Contribuir](#-contribuir)
- [📊 Estadísticas del Repositorio](#-estadísticas-del-repositorio)
- [👥 Colaboradores](#-colaboradores)
- [📄 Licencia](#-licencia)

<br>

<!-- CARACTERÍSTICAS -->
## 🌟 Características

<div align="center">

| Feature | Descripción | Estado |
|:-------:|:------------|:------:|
| 🤖 **Chat Completions** | Endpoint `/v1/chat/completions` 100% compatible OpenAI | ✅ |
| 🧠 **Razonamiento** | Soporte para `deepseek-reasoner` con chain-of-thought | ✅ |
| 🔍 **Búsqueda Web** | DeepSeek puede buscar en internet en tiempo real | ✅ |
| ⚡ **Streaming SSE** | Respuestas en tiempo real vía Server-Sent Events | ✅ |
| 📁 **Subida de Archivos** | Endpoint `/v1/files` para gestión de archivos | ✅ |
| 🔐 **API Key Propia** | Protege tu API con keys personalizables | ✅ |
| 🌐 **CORS** | Configurable para múltiples orígenes | ✅ |
| ⏱️ **Rate Limiting** | Protección contra abuso incluida | ✅ |
| 📝 **Logging** | Logs detallados y configurables | ✅ |
| 🔄 **Múltiples Modelos** | Lista dinámica de modelos disponibles | ✅ |

</div>

> ⚠️ **Aviso Importante:** Esta API no utiliza la API oficial de DeepSeek. En su lugar, reproduce la interfaz de chat web mediante credenciales de sesión (token + cookies). Esto puede infringir los Términos de Servicio de DeepSeek y las credenciales pueden expirar o bloquearse. Úsalo bajo tu propio criterio y responsabilidad.

<br>

<!-- INICIO RÁPIDO -->
## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.8+
- pip
- Credenciales de sesión de DeepSeek (token + cookies)

### Instalación

```bash
# 1. Clona el repositorio
git clone https://github.com/vm1008079-web/ds-flaskAPI.git
cd ds-flaskAPI

# 2. Instala las dependencias
pip install -r requirements.txt

# 3. Copia y configura las variables de entorno
cp .env.example .env
# Edita .env con tus credenciales

# 4. Inicia el servidor
python app.py
```

El servidor estará corriendo en `http://localhost:5000` 🚀

### Variables de Entorno

Copia `.env.example` a `.env` y complétalo:

```env
# 🔑 Credenciales de DeepSeek (obligatorias)
DEEPSEEK_TOKEN=tu_token_aquí
DEEPSEEK_COOKIES=tus_cookies_aquí

# 🔒 Seguridad (recomendado en producción)
API_KEYS=sk-tu-key-larga-y-aleatoria
REQUIRE_API_KEY=true

# ⚙️ Configuración del servidor
PORT=5000

# 🌐 CORS (opcional)
CORS_ORIGINS=*

# 📊 Rate Limiting (opcional)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# 📝 Logging (opcional)
LOG_LEVEL=INFO
LOG_FILE=app.log
```

> 💡 Ver `.env.example` para la lista completa de opciones de configuración.

<br>

<!-- API ENDPOINTS -->
## 📡 API Endpoints

<div align="center">

| Método | Endpoint | Descripción | Auth |
|:------:|:---------|:------------|:----:|
| `POST` | `/v1/chat/completions` | Chat compatible con OpenAI | 🔑 |
| `GET` | `/v1/models` | Lista modelos disponibles | 🔑 |
| `POST` | `/v1/files` | Subir archivo | 🔑 |
| `GET` | `/api/health` | Health check | 🟢 |

</div>

### Request de ejemplo

```json
{
  "model": "deepseek-reasoner",
  "messages": [
    {"role": "system", "content": "Eres un asistente útil."},
    {"role": "user", "content": "¿Qué es la inteligencia artificial?"}
  ],
  "reasoning_enabled": true,
  "stream": false
}
```

<br>

<!-- EJEMPLOS DE USO -->
## 💡 Ejemplos de Uso

### cURL

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer tu_api_key" \
  -d '{
    "model": "deepseek-reasoner",
    "messages": [{"role": "user", "content": "Hola, ¿cómo estás?"}],
    "reasoning_enabled": true
  }'
```

### Python (OpenAI SDK)

```python
import openai

# Configura la base URL de tu instancia
openai.api_base = "http://localhost:5000/v1"
openai.api_key = "tu_api_key"

response = openai.ChatCompletion.create(
    model="deepseek-reasoner",
    messages=[
        {"role": "user", "content": "Explícame la teoría de la relatividad"}
    ],
    reasoning_enabled=True
)

print(response.choices[0].message.content)
```

### JavaScript

```javascript
const response = await fetch('http://localhost:5000/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer tu_api_key'
  },
  body: JSON.stringify({
    model: 'deepseek-chat',
    messages: [{ role: 'user', content: 'Hola mundo' }]
  })
});

const data = await response.json();
console.log(data.choices[0].message.content);
```

### Streaming

```bash
curl -N -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer tu_api_key" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Cuéntame un chiste"}],
    "stream": true
  }'
```

```python
# Python streaming
response = openai.ChatCompletion.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "Cuéntame una historia"}],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.get("content"):
        print(chunk.choices[0].delta.content, end="")
```

<br>

<!-- COMPATIBILIDAD -->
## 🔧 Compatibilidad

<div align="center">

| Cliente / Herramienta | Soporte | Configuración |
|:---------------------:|:-------:|:-------------|
| ✅ **OpenAI SDK** (Python/JS/Node) | Completo | `api_base = "http://tu-api.com/v1"` |
| ✅ **Cursor** | Completo | Base URL + `sk-dummy` como API Key |
| ✅ **Roo Code** | Completo | Base URL + `sk-dummy` como API Key |
| ✅ **Continue.dev** | Completo | OpenAI-compatible provider |
| ✅ **LangChain** | Completo | `OpenAI` con `openai_api_base` custom |
| ✅ **LiteLLM** | Completo | Proxy OpenAI-compatible |

</div>

**Configuración para Cursor / Roo Code:**

```
Base URL:   https://tu-api.onrender.com/v1
API Key:    sk-dummy
Modelo:     deepseek-reasoner
```

<br>

<!-- STACK TECNOLÓGICO -->
## 🛠️ Stack Tecnológico

<div align="center">

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/Gunicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white" alt="Gunicorn" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
</p>
<p>
  <img src="https://img.shields.io/badge/JSON-000000?style=for-the-badge&logo=json&logoColor=white" alt="JSON" />
  <img src="https://img.shields.io/badge/SSE-FF6D00?style=for-the-badge&logo=serverless&logoColor=white" alt="SSE" />
  <img src="https://img.shields.io/badge/REST-FF4438?style=for-the-badge&logo=fastapi&logoColor=white" alt="REST" />
  <img src="https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI" />
</p>

</div>

<br>

<!-- DESPLIEGUE -->
## 🚢 Despliegue

<details>
<summary><b>📦 Render.com (Recomendado)</b></summary>
<br>

1. **Conecta tu repositorio**
   - Ve a [render.com](https://render.com)
   - Conecta tu cuenta de GitHub
   - Selecciona este repositorio

2. **Configuración del servicio**
   | Campo | Valor |
   |-------|-------|
   | Service Type | Web Service |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn app:app` |
   | Instance Type | Free (o Starter para producción) |

3. **Variables de entorno**
   ```
   DEEPSEEK_TOKEN=tu_token_aquí
   DEEPSEEK_COOKIES=tus_cookies_aquí
   PORT=5000
   API_KEYS=sk-tu-key-segura
   REQUIRE_API_KEY=true
   ```

4. **Deploy**
   - Render desplegará automáticamente en cada push a `main`
   - Tu API estará en: `https://tu-servicio.onrender.com`

> 💡 **Tips:**
> - Los servicios Free se pausan tras 15 min de inactividad
> - Usa Starter Plan ($7/mes) para producción

</details>

<details>
<summary><b>🐳 Docker</b></summary>
<br>

**Dockerfile** (ya incluido en el repo):

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

**Ejecutar localmente:**

```bash
docker build -t ds-flaskapi .
docker run -p 5000:5000 \
  -e DEEPSEEK_TOKEN=tu_token \
  -e DEEPSEEK_COOKIES=tus_cookies \
  -e API_KEYS=sk-tu-key \
  ds-flaskapi
```

**Docker Compose:**

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DEEPSEEK_TOKEN=${DEEPSEEK_TOKEN}
      - DEEPSEEK_COOKIES=${DEEPSEEK_COOKIES}
      - API_KEYS=${API_KEYS}
      - REQUIRE_API_KEY=true
```

</details>

<details>
<summary><b>☁️ Railway</b></summary>
<br>

1. **Conecta tu repositorio**
   - Ve a [railway.app](https://railway.app)
   - Autoriza con GitHub
   - Importa este proyecto

2. **Configura variables**
   ```
   DEEPSEEK_TOKEN=tu_token
   DEEPSEEK_COOKIES=tus_cookies
   PORT=5000
   API_KEYS=sk-tu-key
   ```

3. **Deploy**
   ```bash
   railway link
   railway up
   ```

> ⚡ Despliegue instantáneo desde Git | $5 USD crédito inicial | Auto-deploy en push

</details>

<details>
<summary><b>🚀 Heroku</b></summary>
<br>

**Instalación de Heroku CLI:**

```bash
brew install heroku
heroku login
```

**Despliegue:**

```bash
heroku create tu-api-name
git push heroku main
heroku config:set DEEPSEEK_TOKEN=tu_token
heroku config:set DEEPSEEK_COOKIES=tus_cookies
heroku config:set API_KEYS=sk-tu-key
heroku logs --tail
```

**Archivo necesario (Procfile):**

```
web: gunicorn app:app
```

> ⚠️ Heroku descontinuó su plan gratuito en 2022. Considera Render o Railway como alternativa.

</details>

<details>
<summary><b>▲ Vercel</b></summary>
<br>

1. **Crea `vercel.json`**

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
   API_KEYS
   ```

> ⚠️ Vercel está optimizado para Next.js/Node. Para Python puro, considera Render o Railway.

</details>

<br>

<!-- TESTS -->
## 🧪 Tests

```bash
# Instala dependencias de desarrollo
pip install -r requirements-dev.txt

# Ejecuta los tests
pytest tests/ -v
```

> Los tests mockean el cliente de DeepSeek, así que corren sin credenciales reales ni acceso a red.

<br>

<!-- CONTRIBUIR -->
## 🤝 Contribuir

¡Las contribuciones son bienvenidas! 🎉

1. 🍴 Fork el repositorio
2. 🌿 Crea una rama (`git checkout -b feature/AmazingFeature`)
3. 💾 Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. 📤 Push a la rama (`git push origin feature/AmazingFeature`)
5. 🔃 Abre un Pull Request

Por favor, asegúrate de que tus cambios pasen los tests y siguen el estilo de código del proyecto.

<br>

<!-- ESTADÍSTICAS -->
## 📊 Estadísticas del Repositorio

<div align="center">

<p>
  <img src="https://github-readme-stats.vercel.app/api/pin/?username=vm1008079-web&repo=ds-flaskAPI&theme=tokyonight&hide_border=true" alt="Repo Card" />
</p>

<p>
  <img src="https://img.shields.io/github/languages/top/vm1008079-web/ds-flaskAPI?style=for-the-badge&color=3776AB" alt="Top Language" />
  <img src="https://img.shields.io/github/repo-size/vm1008079-web/ds-flaskAPI?style=for-the-badge&color=00BFFF" alt="Repo Size" />
  <img src="https://img.shields.io/github/last-commit/vm1008079-web/ds-flaskAPI?style=for-the-badge&color=4ECDC4" alt="Last Commit" />
  <img src="https://img.shields.io/github/contributors/vm1008079-web/ds-flaskAPI?style=for-the-badge&color=FFD700" alt="Contributors" />
</p>

<p>
  <img src="https://img.shields.io/github/languages/count/vm1008079-web/ds-flaskAPI?style=for-the-badge&color=FF6B6B" alt="Languages" />
  <img src="https://img.shields.io/github/license/vm1008079-web/ds-flaskAPI?style=for-the-badge&color=blue" alt="License" />
</p>

</div>

<br>

<!-- COLABORADORES -->
## 👥 Colaboradores

<div align="center">

<a href="https://github.com/nyxthor-dev">
  <img src="https://github.com/vm1008079-web.png?size=100" width="100" style="border-radius: 50%;" alt="Víctor Manuel" />
</a>

<br>

**[Víctor Manuel](https://github.com/nyxthor-dev)**

🏆 Creador & Mantenedor

</div>

<br>

<!-- LICENCIA -->
## 📄 Licencia

Distribuido bajo la licencia **GNU GPL v3**. Ver [`LICENSE`](LICENSE) para más información.

```
GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (C) 2024 Víctor Manuel

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
```

<br>

<!-- FOOTER -->
<div align="center">

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%">

<br>

<p>
  <a href="https://github.com/vm1008079-web/ds-flaskAPI">⭐ Star en GitHub</a> •
  <a href="https://github.com/vm1008079-web/ds-flaskAPI/issues">🐛 Reportar Bug</a> •
  <a href="https://github.com/vm1008079-web/ds-flaskAPI/pulls">🔃 Pull Request</a>
</p>

<p>
  <sub>Hecho con ❤️ por <a href="https://github.com/vm1008079-web">@vm1008079-web</a></sub>
</p>

<p>
  <a href="https://github.com/vm1008079-web/ds-flaskAPI">
    <img src="https://img.shields.io/badge/Volver%20arriba-⬆️-blue?style=flat-square" alt="Back to top" />
  </a>
</p>

</div>
