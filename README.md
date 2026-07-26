<!-- README.md -->
<h1 align="center">🌊 DS-FLACKAPI</h1>

<p align="center">
  <strong>API 100% compatible con OpenAI</strong><br>
  Razonamiento + Búsqueda + Streaming
</p>

<hr>

<h2>🚀 Endpoints</h2>

<table>
  <tr>
    <th>Método</th>
    <th>Endpoint</th>
    <th>Descripción</th>
  </tr>
  <tr>
    <td><code>POST</code></td>
    <td><code>/v1/chat/completions</code></td>
    <td>Chat (OpenAI)</td>
  </tr>
  <tr>
    <td><code>GET</code></td>
    <td><code>/v1/models</code></td>
    <td>Lista modelos</td>
  </tr>
  <tr>
    <td><code>POST</code></td>
    <td><code>/v1/files</code></td>
    <td>Subir archivo</td>
  </tr>
  <tr>
    <td><code>GET</code></td>
    <td><code>/api/health</code></td>
    <td>Health check</td>
  </tr>
</table>

<hr>

<h2>📦 Instalación</h2>

<pre>
git clone https://github.com/tu-usuario/deepseek-api
cd deepseek-api
pip install -r requirements.txt
cp .env.example .env
# Edita .env con tus credenciales
python app.py
</pre>

<hr>

<h2>🔧 Variables de entorno</h2>

<pre>
DEEPSEEK_TOKEN=tu_token
DEEPSEEK_COOKIES=tu_cookies
PORT=5000
</pre>

<hr>

<h2>🎯 Ejemplo rápido</h2>

<pre>
curl -X POST https://tu-api.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-reasoner",
    "messages": [{"role": "user", "content": "Hola"}],
    "reasoning_enabled": true
  }'
</pre>

<hr>

<h2>🔌 Compatibilidad</h2>

<h3>OpenAI SDK</h3>
<pre>
import openai
openai.api_base = "https://tu-api.onrender.com/v1"
openai.api_key = "sk-dummy"

response = openai.ChatCompletion.create(
    model="deepseek-reasoner",
    messages=[{"role": "user", "content": "Hola"}]
)
</pre>

<h3>Roo Code / Cursor</h3>
<table>
  <tr><td><strong>Base URL</strong></td><td><code>https://tu-api.onrender.com/v1</code></td></tr>
  <tr><td><strong>API Key</strong></td><td><code>sk-dummy</code></td></tr>
  <tr><td><strong>Modelo</strong></td><td><code>deepseek-reasoner</code></td></tr>
</table>

<hr>

<h2>🚢 Despliegue en Render</h2>

<ol>
  <li>Conecta tu repositorio en <a href="https://render.com">Render.com</a></li>
  <li>Configura:
    <ul>
      <li><strong>Build Command:</strong> <code>pip install -r requirements.txt</code></li>
      <li><strong>Start Command:</strong> <code>gunicorn app:app</code></li>
    </ul>
  </li>
  <li>Agrega variables: <code>DEEPSEEK_TOKEN</code>, <code>DEEPSEEK_COOKIES</code></li>
</ol>

<hr>

<h2>📄 Licencia</h2>
<p>GNU GPL V3 © 2007</p>

<hr>

<p align="center">
  <a href="https://github.com/tu-usuario/deepseek-api">GitHub</a> •
  <a href="https://render.com">Render</a> •
  <a href="https://platform.openai.com/docs/api-reference">OpenAI Docs</a>
</p>