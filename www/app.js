const LS_PROFILES = 'devilos.profiles';      // { [username]: {baseUrl, token} }
const LS_ACTIVE_PROFILE = 'devilos.active';   // username string
const LS_CHATS = 'devilos.chats';             // { [chatId]: {id,title,model,messages:[]} }
const LS_ACTIVE_CHAT = 'devilos.activeChat';

// ---------- estado ----------
let state = {
  profiles: {},
  activeProfile: null,
  chats: {},
  activeChatId: null,
  models: [],
  selectedModel: 'deepseek-chat',
  streaming: false,
  abortController: null,
  pendingAttachments: [], // [{id, localId, name, size, type, status, previewUrl}]
};

// ---------- helpers de storage ----------
function loadState(){
  try{ state.profiles = JSON.parse(localStorage.getItem(LS_PROFILES) || '{}'); }catch{ state.profiles = {}; }
  state.activeProfile = localStorage.getItem(LS_ACTIVE_PROFILE) || null;
  try{ state.chats = JSON.parse(localStorage.getItem(LS_CHATS) || '{}'); }catch{ state.chats = {}; }
  state.activeChatId = localStorage.getItem(LS_ACTIVE_CHAT) || null;
}
function saveProfiles(){ localStorage.setItem(LS_PROFILES, JSON.stringify(state.profiles)); }
function saveChats(){ localStorage.setItem(LS_CHATS, JSON.stringify(state.chats)); }
function setActiveProfile(username){
  state.activeProfile = username;
  if(username) localStorage.setItem(LS_ACTIVE_PROFILE, username);
  else localStorage.removeItem(LS_ACTIVE_PROFILE);
}
function setActiveChat(id){
  state.activeChatId = id;
  if(id) localStorage.setItem(LS_ACTIVE_CHAT, id);
  else localStorage.removeItem(LS_ACTIVE_CHAT);
}

function currentProfile(){
  return state.activeProfile ? state.profiles[state.activeProfile] : null;
}

// ---------- DOM refs ----------
const $ = (sel) => document.querySelector(sel);
const sidebar = $('#sidebar');
const chatList = $('#chatList');
const profileBtn = $('#profileBtn');
const profileDot = $('#profileDot');
const profileName = $('#profileName');
const profileSub = $('#profileSub');
const modelSelectBtn = $('#modelSelectBtn');
const modelSelectLabel = $('#modelSelectLabel');
const modelDropdown = $('#modelDropdown');
const messagesEl = $('#messages');
const emptyState = $('#emptyState');
const chatScroll = $('#chatScroll');
const composerForm = $('#composerForm');
const composerInput = $('#composerInput');
const sendBtn = $('#sendBtn');
const newChatBtn = $('#newChatBtn');
const clearChatBtn = $('#clearChatBtn');

const attachBtn = $('#attachBtn');
const attachMenu = $('#attachMenu');
const attachChips = $('#attachChips');
const fileInputCamera = $('#fileInputCamera');
const fileInputImage = $('#fileInputImage');
const fileInputFile = $('#fileInputFile');

const authScrim = $('#authScrim');
const authUsername = $('#authUsername');
const authBaseUrl = $('#authBaseUrl');
const authToken = $('#authToken');
const authStatus = $('#authStatus');
const authTestBtn = $('#authTestBtn');
const authSaveBtn = $('#authSaveBtn');
const authDeleteBtn = $('#authDeleteBtn');
const authCloseBtn = $('#authCloseBtn');
const profileListEl = $('#profileList');

// ============================================================
// MARKDOWN + CODE RENDERING
// ============================================================
marked.setOptions({
  breaks: true,
  gfm: true,
});

let codeBlockSeq = 0;

// Renderer personalizado: los bloques de código llevan cabecera,
// tamaño fijo (porcentaje del panel) y scroll interno.
const renderer = new marked.Renderer();
renderer.code = function(code, infoString){
  const lang = (infoString || '').trim().split(/\s+/)[0] || 'texto';
  let highlighted;
  let validLang = lang;
  try{
    if(lang && hljs.getLanguage(lang)){
      highlighted = hljs.highlight(code, { language: lang }).value;
    }else{
      const auto = hljs.highlightAuto(code);
      highlighted = auto.value;
      validLang = auto.language || 'texto';
    }
  }catch(e){
    highlighted = escapeHtml(code);
  }
  const id = 'cb' + (++codeBlockSeq);
  const encoded = encodeURIComponent(code);
  return `<div class="code-block">
    <div class="code-head">
      <span>${escapeHtml(validLang)}</span>
      <button class="code-copy-btn" type="button" data-code="${encoded}" onclick="copyCodeBlock(this)">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
        <span>copiar</span>
      </button>
    </div>
    <div class="code-scroll"><pre><code class="hljs language-${escapeHtml(validLang)}" id="${id}">${highlighted}</code></pre></div>
  </div>`;
};
marked.setOptions({ renderer });

function escapeHtml(str){
  return str.replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

window.copyCodeBlock = function(btn){
  const code = decodeURIComponent(btn.getAttribute('data-code'));
  navigator.clipboard.writeText(code).then(() => {
    btn.classList.add('copied');
    const span = btn.querySelector('span');
    const prev = span.textContent;
    span.textContent = 'copiado';
    setTimeout(() => { btn.classList.remove('copied'); span.textContent = prev; }, 1500);
  }).catch(() => {});
};

function renderMarkdown(text){
  try{
    return marked.parse(text || '');
  }catch(e){
    return escapeHtml(text || '');
  }
}

// ============================================================
// CHATS — CRUD
// ============================================================
function genId(){ return 'c' + Date.now().toString(36) + Math.random().toString(36).slice(2,7); }

function createChat(){
  const id = genId();
  state.chats[id] = {
    id,
    title: 'Nuevo chat',
    model: state.selectedModel,
    messages: [],
    createdAt: Date.now(),
  };
  saveChats();
  setActiveChat(id);
  renderChatList();
  renderMessages();
  return id;
}

function ensureActiveChat(){
  if(!state.activeChatId || !state.chats[state.activeChatId]){
    const ids = Object.keys(state.chats);
    if(ids.length){
      setActiveChat(ids.sort((a,b) => state.chats[b].createdAt - state.chats[a].createdAt)[0]);
    }
  }
}

function deleteChat(id){
  delete state.chats[id];
  saveChats();
  if(state.activeChatId === id){
    setActiveChat(null);
    ensureActiveChat();
  }
  renderChatList();
  renderMessages();
}

function getChat(){
  return state.chats[state.activeChatId] || null;
}

function updateChatTitleFromFirstMessage(chat){
  if(chat.title !== 'Nuevo chat') return;
  const firstUser = chat.messages.find(m => m.role === 'user');
  if(firstUser){
    const raw = (firstUser.displayText || firstUser.content).trim() || (firstUser.attachments && firstUser.attachments.length ? firstUser.attachments[0].name : '');
    const t = raw.slice(0, 42);
    chat.title = t.length < raw.length ? t + '…' : (t || 'Nuevo chat');
  }
}

// ============================================================
// RENDER: sidebar chat list
// ============================================================
function renderChatList(){
  const ids = Object.keys(state.chats).sort((a,b) => state.chats[b].createdAt - state.chats[a].createdAt);
  if(!ids.length){
    chatList.innerHTML = `<div class="sidebar-empty-hint">Sin sesiones todavía.<br>Crea un chat nuevo para empezar.</div>`;
    return;
  }
  chatList.innerHTML = ids.map(id => {
    const c = state.chats[id];
    const active = id === state.activeChatId ? 'active' : '';
    return `<div class="chat-item ${active}" data-id="${id}">
      <span class="chat-item-title">${escapeHtml(c.title)}</span>
      <button class="chat-item-del" data-del="${id}" title="Eliminar" aria-label="Eliminar chat">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>
      </button>
    </div>`;
  }).join('');

  chatList.querySelectorAll('.chat-item').forEach(el => {
    el.addEventListener('click', (e) => {
      if(e.target.closest('[data-del]')) return;
      setActiveChat(el.dataset.id);
      renderChatList();
      renderMessages();
      closeSidebarMobile();
    });
  });
  chatList.querySelectorAll('[data-del]').forEach(el => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      deleteChat(el.dataset.del);
    });
  });
}

// ============================================================
// RENDER: messages
// ============================================================
function renderMessages(){
  const chat = getChat();
  if(!chat || chat.messages.length === 0){
    messagesEl.innerHTML = '';
    emptyState.classList.remove('hidden');
    return;
  }
  emptyState.classList.add('hidden');
  messagesEl.innerHTML = chat.messages.map((m, idx) => renderMessageHTML(m, idx)).join('');
  hydrateReasoningToggles();
  scrollToBottom();
}

function renderMessageHTML(m, idx){
  if(m.role === 'user'){
    const shown = m.displayText !== undefined ? m.displayText : m.content;
    let attachHtml = '';
    if(m.attachments && m.attachments.length){
      attachHtml = `<div class="msg-attachments">${m.attachments.map(a => {
        const thumb = a.previewUrl
          ? `<img class="msg-attach-thumb" src="${a.previewUrl}">`
          : `<span class="msg-attach-icon"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg></span>`;
        return `<span class="msg-attach-chip">${thumb}<span>${escapeHtml(a.name)}</span></span>`;
      }).join('')}</div>`;
    }
    const bodyHtml = shown ? `<div class="msg-body">${escapeHtml(shown)}</div>` : '';
    return `<div class="msg user" data-idx="${idx}">
      <div class="msg-role"><span class="role-dot"></span>tú</div>
      ${attachHtml}
      ${bodyHtml}
    </div>`;
  }
  // assistant
  let reasoningHtml = '';
  if(m.reasoning){
    const isStreaming = !m.content && !m.error;
    reasoningHtml = `<div class="reasoning-block ${m.reasoningOpen ? 'open' : ''} ${isStreaming ? 'streaming' : ''}" data-idx="${idx}">
      <button type="button" class="reasoning-toggle">
        <span class="chevron"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg></span>
        <span class="r-label">Razonamiento</span>
        <span class="r-status"></span>
      </button>
      <div class="reasoning-content">${escapeHtml(m.reasoning)}</div>
    </div>`;
  }
  const bodyHtml = m.content
    ? `<div class="msg-body md">${renderMarkdown(m.content)}</div>`
    : (m.error ? '' : `<div class="msg-status"><span class="dot-flash"><span></span><span></span><span></span></span>pensando</div>`);

  const errorHtml = m.error ? `<div class="msg-error">${escapeHtml(m.error)}</div>` : '';

  return `<div class="msg assistant" data-idx="${idx}">
    <div class="msg-role"><span class="role-dot"></span>Nykchat</div>
    ${reasoningHtml}
    ${bodyHtml}
    ${errorHtml}
  </div>`;
}

function hydrateReasoningToggles(){
  messagesEl.querySelectorAll('.reasoning-block').forEach(block => {
    const btn = block.querySelector('.reasoning-toggle');
    btn.onclick = () => {
      block.classList.toggle('open');
      const idx = block.dataset.idx;
      const chat = getChat();
      if(chat && chat.messages[idx]){
        chat.messages[idx].reasoningOpen = block.classList.contains('open');
        saveChats();
      }
    };
  });
}

function scrollToBottom(){
  requestAnimationFrame(() => { chatScroll.scrollTop = chatScroll.scrollHeight; });
}

// ============================================================
// API — models + chat completions (streaming)
// ============================================================
async function apiFetch(path, opts = {}){
  const profile = currentProfile();
  if(!profile) throw new Error('No hay conexión configurada.');
  const base = profile.baseUrl.replace(/\/+$/, '');
  const headers = Object.assign({
    'Authorization': 'Bearer ' + profile.token,
  }, opts.headers || {});
  return fetch(base + path, Object.assign({}, opts, { headers }));
}

async function loadModels(){
  const dropdown = modelDropdown;
  if(!currentProfile()){
    dropdown.innerHTML = `<div class="model-dropdown-empty">Configura tu conexión para ver los modelos disponibles.</div>`;
    return;
  }
  try{
    const res = await apiFetch('/v1/models');
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    state.models = (data.data || []).map(m => m.id);
    if(!state.models.length) state.models = ['deepseek-chat', 'deepseek-reasoner'];
  }catch(e){
    state.models = ['deepseek-chat', 'deepseek-reasoner'];
  }
  if(!state.models.includes(state.selectedModel)){
    state.selectedModel = state.models[0];
  }
  modelSelectLabel.textContent = state.selectedModel;
  renderModelDropdown();
}

function renderModelDropdown(){
  if(!state.models.length){
    modelDropdown.innerHTML = `<div class="model-dropdown-empty">Sin modelos disponibles.</div>`;
    return;
  }
  modelDropdown.innerHTML = state.models.map(id => {
    const active = id === state.selectedModel ? 'active' : '';
    const isReasoner = /reason/i.test(id);
    return `<div class="model-option ${active}" data-model="${escapeHtml(id)}">
      <span>${escapeHtml(id)}</span>
      <span class="model-option-desc">${isReasoner ? 'con razonamiento extendido' : 'respuesta directa'}</span>
    </div>`;
  }).join('');
  modelDropdown.querySelectorAll('.model-option').forEach(el => {
    el.addEventListener('click', () => {
      state.selectedModel = el.dataset.model;
      modelSelectLabel.textContent = state.selectedModel;
      modelDropdown.classList.remove('open');
      renderModelDropdown();
      const chat = getChat();
      if(chat) { chat.model = state.selectedModel; saveChats(); }
    });
  });
}

function buildApiMessages(chat){
  return chat.messages
    .filter(m => !m.error || m.content)
    .map(m => ({ role: m.role, content: m.content }));
}

async function sendMessage(text, attachments){
  attachments = attachments || [];
  let chat = getChat();
  if(!chat){
    createChat();
    chat = getChat();
  }
  chat.model = state.selectedModel;

  let apiText = text;
  if(attachments.length){
    const refs = attachments.map(a => `[archivo adjunto: ${a.name} · id ${a.fileId}]`).join('\n');
    apiText = apiText ? `${apiText}\n\n${refs}` : refs;
  }

  chat.messages.push({
    role: 'user',
    content: apiText,
    displayText: text,
    attachments: attachments.map(a => ({ name: a.name, previewUrl: a.previewUrl, type: a.type })),
  });
  updateChatTitleFromFirstMessage(chat);
  const assistantMsg = { role: 'assistant', content: '', reasoning: '', reasoningOpen: true };
  chat.messages.push(assistantMsg);
  saveChats();
  renderChatList();
  renderMessages();

  state.streaming = true;
  updateComposerState();

  const controller = new AbortController();
  state.abortController = controller;

  try{
    const res = await apiFetch('/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        model: chat.model,
        stream: true,
        search_enabled: true,
        messages: buildApiMessages({ messages: chat.messages.slice(0, -1) }),
      }),
    });

    if(!res.ok || !res.body){
      let errText = 'Error HTTP ' + res.status;
      try{ const j = await res.json(); errText = (j.error && j.error.message) || errText; }catch{}
      throw new Error(errText);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while(true){
      const { value, done } = await reader.read();
      if(done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for(const line of lines){
        const trimmed = line.trim();
        if(!trimmed.startsWith('data:')) continue;
        const payload = trimmed.slice(5).trim();
        if(payload === '[DONE]') continue;
        let json;
        try{ json = JSON.parse(payload); }catch{ continue; }
        const choice = (json.choices && json.choices[0]) || null;
        if(!choice) continue;
        const delta = choice.delta || {};
        if(delta.reasoning_content){
          assistantMsg.reasoning += delta.reasoning_content;
        }
        if(delta.content){
          assistantMsg.content += delta.content;
        }
        renderAssistantLive(assistantMsg);
      }
    }
    assistantMsg.reasoningOpen = false;
  }catch(err){
    if(err.name === 'AbortError'){
      assistantMsg.error = 'Generación detenida.';
    }else{
      assistantMsg.error = err.message || 'Error de conexión con la API.';
    }
  }finally{
    state.streaming = false;
    state.abortController = null;
    saveChats();
    renderChatList();
    renderMessages();
    updateComposerState();
  }
}

// Actualiza en vivo el último mensaje del asistente sin re-renderizar todo el hilo
function renderAssistantLive(assistantMsg){
  const chat = getChat();
  const idx = chat.messages.length - 1;
  emptyState.classList.add('hidden');
  let el = messagesEl.querySelector(`.msg.assistant[data-idx="${idx}"]`);
  const html = renderMessageHTML(assistantMsg, idx);
  if(!el){
    messagesEl.insertAdjacentHTML('beforeend', html);
  }else{
    el.outerHTML = html;
  }
  el = messagesEl.querySelector(`.msg.assistant[data-idx="${idx}"]`);
  if(el){
    const body = el.querySelector('.msg-body.md');
    if(body){
      body.insertAdjacentHTML('beforeend', '<span class="cursor-blink"></span>');
    }else{
      const status = el.querySelector('.msg-status');
      if(status) status.insertAdjacentHTML('beforeend', '<span class="cursor-blink"></span>');
    }

    const block = el.querySelector('.reasoning-block');
    if(block){
      const toggle = block.querySelector('.reasoning-toggle');
      toggle.onclick = () => { block.classList.toggle('open'); };
      const status = block.querySelector('.r-status');
      if(status && !assistantMsg.content) status.textContent = 'generando';
    }
  }
  scrollToBottom();
}

// ============================================================
// ADJUNTOS — botón +, menú, subida a /v1/files
// ============================================================
attachBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  if(!currentProfile()){
    attachMenu.classList.remove('open');
    attachBtn.classList.remove('open');
    openAuthModal();
    return;
  }
  const isOpen = attachMenu.classList.toggle('open');
  attachBtn.classList.toggle('open', isOpen);
});
document.addEventListener('click', (e) => {
  if(!e.target.closest('.attach-wrap')){
    attachMenu.classList.remove('open');
    attachBtn.classList.remove('open');
  }
});
attachMenu.querySelectorAll('.attach-option').forEach(btn => {
  btn.addEventListener('click', () => {
    attachMenu.classList.remove('open');
    attachBtn.classList.remove('open');
    const action = btn.dataset.action;
    if(action === 'camera') fileInputCamera.click();
    else if(action === 'image') fileInputImage.click();
    else if(action === 'file') fileInputFile.click();
  });
});

[fileInputCamera, fileInputImage, fileInputFile].forEach(input => {
  input.addEventListener('change', () => {
    const files = Array.from(input.files || []);
    files.forEach(handleFileSelected);
    input.value = ''; // permite volver a elegir el mismo archivo
  });
});

const ALLOWED_EXT = ['.txt', '.pdf', '.md', '.csv', '.json', '.png', '.jpg', '.jpeg'];

function handleFileSelected(file){
  const ext = '.' + (file.name.split('.').pop() || '').toLowerCase();
  if(!ALLOWED_EXT.includes(ext)){
    const localId = 'att' + Date.now() + Math.random().toString(36).slice(2,6);
    state.pendingAttachments.push({
      localId, name: file.name, status: 'error',
      errorMsg: 'extensión no permitida',
    });
    renderAttachChips();
    return;
  }
  const localId = 'att' + Date.now() + Math.random().toString(36).slice(2,6);
  const isImage = /^image\//.test(file.type);
  const item = {
    localId, name: file.name, size: file.size, type: file.type,
    status: 'uploading', previewUrl: isImage ? URL.createObjectURL(file) : null,
  };
  state.pendingAttachments.push(item);
  renderAttachChips();
  uploadAttachment(item, file);
}

async function uploadAttachment(item, file){
  try{
    const profile = currentProfile();
    if(!profile) throw new Error('sin conexión');
    const form = new FormData();
    form.append('file', file, file.name);
    form.append('purpose', 'assistants');
    const res = await fetch(profile.baseUrl.replace(/\/+$/, '') + '/v1/files', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + profile.token },
      body: form,
    });
    if(!res.ok){
      let msg = 'HTTP ' + res.status;
      try{ const j = await res.json(); msg = (j.error && j.error.message) || msg; }catch{}
      throw new Error(msg);
    }
    const data = await res.json();
    item.status = 'ready';
    item.fileId = data.id;
  }catch(err){
    item.status = 'error';
    item.errorMsg = err.message || 'error al subir';
  }
  renderAttachChips();
}

function removeAttachment(localId){
  const item = state.pendingAttachments.find(a => a.localId === localId);
  if(item && item.previewUrl) URL.revokeObjectURL(item.previewUrl);
  state.pendingAttachments = state.pendingAttachments.filter(a => a.localId !== localId);
  renderAttachChips();
}

function renderAttachChips(){
  if(!state.pendingAttachments.length){
    attachChips.innerHTML = '';
    return;
  }
  attachChips.innerHTML = state.pendingAttachments.map(a => {
    const thumb = a.previewUrl ? `<img class="attach-chip-thumb" src="${a.previewUrl}">` : '';
    let statusIcon = '';
    if(a.status === 'uploading') statusIcon = '<span class="chip-status">…</span>';
    else if(a.status === 'ready') statusIcon = '<span class="chip-status">✓</span>';
    else if(a.status === 'error') statusIcon = `<span class="chip-status" title="${escapeHtml(a.errorMsg || '')}">!</span>`;
    return `<span class="attach-chip ${a.status}" title="${escapeHtml(a.errorMsg || a.name)}">
      ${thumb}
      <span class="chip-name">${escapeHtml(a.name)}</span>
      ${statusIcon}
      <button type="button" class="attach-chip-remove" data-remove="${a.localId}" aria-label="Quitar">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </span>`;
  }).join('');
  attachChips.querySelectorAll('[data-remove]').forEach(btn => {
    btn.addEventListener('click', () => removeAttachment(btn.dataset.remove));
  });
  updateComposerState();
}

function clearAttachmentsAfterSend(){
  state.pendingAttachments.forEach(a => { if(a.previewUrl) URL.revokeObjectURL(a.previewUrl); });
  state.pendingAttachments = [];
  renderAttachChips();
}

// ============================================================
// COMPOSER
// ============================================================
function updateComposerState(){
  const uploading = state.pendingAttachments.some(a => a.status === 'uploading');
  sendBtn.disabled = state.streaming || !currentProfile() || uploading;
  composerInput.disabled = state.streaming;
  if(!currentProfile()){
    composerInput.placeholder = 'Configura tu conexión para empezar…';
  } else {
    composerInput.placeholder = 'Envía un mensaje...';
  }
}

composerInput.addEventListener('input', () => {
  composerInput.style.height = 'auto';
  composerInput.style.height = Math.min(composerInput.scrollHeight, 200) + 'px';
});

composerInput.addEventListener('keydown', (e) => {
  if(e.key === 'Enter' && !e.shiftKey){
    e.preventDefault();
    composerForm.requestSubmit();
  }
});

composerForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = composerInput.value.trim();
  const attachments = state.pendingAttachments;
  if(!text && !attachments.length) return;
  if(state.streaming) return;
  if(!currentProfile()){
    openAuthModal();
    return;
  }
  if(attachments.some(a => a.status === 'uploading')) return; // esperar a que terminen
  const readyAttachments = attachments.filter(a => a.status === 'ready');

  composerInput.value = '';
  composerInput.style.height = 'auto';
  clearAttachmentsAfterSend();
  sendMessage(text, readyAttachments);
});

// ============================================================
// SIDEBAR toggle (desktop collapse + mobile drawer)
// ============================================================
$('#toggleSidebar').addEventListener('click', () => {
  document.body.classList.toggle('sidebar-collapsed');
});
$('#openSidebar').addEventListener('click', () => {
  document.body.classList.add('sidebar-open');
});
$('#sidebarScrim').addEventListener('click', closeSidebarMobile);
function closeSidebarMobile(){ document.body.classList.remove('sidebar-open'); }

newChatBtn.addEventListener('click', () => { createChat(); closeSidebarMobile(); });
clearChatBtn.addEventListener('click', () => {
  const chat = getChat();
  if(!chat) return;
  if(!chat.messages.length) return;
  chat.messages = [];
  chat.title = 'Nuevo chat';
  saveChats();
  renderChatList();
  renderMessages();
});

// ============================================================
// MODEL DROPDOWN toggle
// ============================================================
modelSelectBtn.addEventListener('click', () => {
  modelDropdown.classList.toggle('open');
});
document.addEventListener('click', (e) => {
  if(!e.target.closest('.model-select-wrap')) modelDropdown.classList.remove('open');
});

// ============================================================
// AUTH MODAL
// ============================================================
function openAuthModal(){
  authScrim.classList.add('open');
  const profile = currentProfile();
  authUsername.value = state.activeProfile || '';
  authBaseUrl.value = profile ? profile.baseUrl : '';
  authToken.value = profile ? profile.token : '';
  authStatus.textContent = '';
  authStatus.className = 'auth-status';
  renderProfileList();
}
function closeAuthModal(){ authScrim.classList.remove('open'); }

profileBtn.addEventListener('click', openAuthModal);
authCloseBtn.addEventListener('click', closeAuthModal);
authScrim.addEventListener('click', (e) => { if(e.target === authScrim) closeAuthModal(); });

authTestBtn.addEventListener('click', async () => {
  const baseUrl = authBaseUrl.value.trim().replace(/\/+$/, '');
  const token = authToken.value.trim();
  if(!baseUrl || !token){
    authStatus.textContent = 'completa URL y token';
    authStatus.className = 'auth-status err';
    return;
  }
  authStatus.textContent = 'probando…';
  authStatus.className = 'auth-status';
  try{
    const res = await fetch(baseUrl + '/api/health', {
      headers: { 'Authorization': 'Bearer ' + token },
    });
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    authStatus.textContent = data.status === 'ok' ? 'conexión correcta' : 'respuesta inesperada';
    authStatus.className = 'auth-status ok';
  }catch(e){
    authStatus.textContent = 'no se pudo conectar';
    authStatus.className = 'auth-status err';
  }
});

authSaveBtn.addEventListener('click', () => {
  const username = authUsername.value.trim();
  const baseUrl = authBaseUrl.value.trim().replace(/\/+$/, '');
  const token = authToken.value.trim();
  if(!username || !baseUrl || !token){
    authStatus.textContent = 'completa todos los campos';
    authStatus.className = 'auth-status err';
    return;
  }
  state.profiles[username] = { baseUrl, token };
  saveProfiles();
  setActiveProfile(username);
  closeAuthModal();
  updateProfileBadge();
  loadModels();
  updateComposerState();
});

authDeleteBtn.addEventListener('click', () => {
  const username = authUsername.value.trim();
  if(!username || !state.profiles[username]) return;
  delete state.profiles[username];
  saveProfiles();
  if(state.activeProfile === username) setActiveProfile(null);
  renderProfileList();
  updateProfileBadge();
  authUsername.value = '';
  authBaseUrl.value = '';
  authToken.value = '';
});

function renderProfileList(){
  const names = Object.keys(state.profiles);
  if(!names.length){
    profileListEl.innerHTML = `<div class="profile-list-empty">Aún no hay perfiles guardados.</div>`;
    return;
  }
  profileListEl.innerHTML = names.map(name => {
    const active = name === state.activeProfile ? 'active' : '';
    return `<button type="button" class="profile-list-item ${active}" data-name="${escapeHtml(name)}">
      <span>${escapeHtml(name)}</span>
    </button>`;
  }).join('');
  profileListEl.querySelectorAll('.profile-list-item').forEach(el => {
    el.addEventListener('click', () => {
      const name = el.dataset.name;
      const p = state.profiles[name];
      setActiveProfile(name);
      authUsername.value = name;
      authBaseUrl.value = p.baseUrl;
      authToken.value = p.token;
      renderProfileList();
      updateProfileBadge();
      loadModels();
      updateComposerState();
    });
  });
}

function updateProfileBadge(){
  const profile = currentProfile();
  if(profile){
    profileDot.className = 'profile-dot online';
    profileName.textContent = state.activeProfile;
    profileSub.textContent = profile.baseUrl.replace(/^https?:\/\//, '');
  }else{
    profileDot.className = 'profile-dot';
    profileName.textContent = 'sin conexión';
    profileSub.textContent = 'configurar API';
  }
}

// ============================================================
// INIT
// ============================================================
function init(){
  loadState();
  ensureActiveChat();
  updateProfileBadge();
  renderChatList();
  renderMessages();
  updateComposerState();
  if(currentProfile()){
    loadModels();
  }else{
    modelSelectLabel.textContent = 'sin modelo';
    modelDropdown.innerHTML = `<div class="model-dropdown-empty">Configura tu conexión para ver los modelos disponibles.</div>`;
    setTimeout(openAuthModal, 300);
  }
}

init();
