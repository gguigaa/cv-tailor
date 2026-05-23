// ── STATE ──
let accessToken = localStorage.getItem('access_token') || '';
let refreshToken = localStorage.getItem('refresh_token') || '';
let currentUser = null;
let lang = 'pt';
let lastOutput = '';
let lastGeneratedId = null;
let conversationHistory = [];
let isLoading = false;
const DEFAULT_PROMPT = `Você é um especialista em recrutamento técnico e redação de currículos para a área de tecnologia.\n\nAbaixo está o currículo mestre do candidato, que contém TODA a sua experiência:\n\n<curriculo_mestre>\n{CV}\n</curriculo_mestre>\n\nAbaixo está a descrição da vaga para a qual ele está se candidatando:\n\n<vaga>\n{VAGA}\n</vaga>\n\nSua tarefa é gerar um currículo otimizado para essa vaga específica, seguindo estas diretrizes:\n\n1. **Seleção de conteúdo**: Inclua apenas as experiências, projetos e habilidades mais relevantes para essa vaga.\n2. **Palavras-chave ATS**: Use as mesmas palavras-chave e terminologia presentes na descrição da vaga.\n3. **Linguagem**: Escreva em {IDIOMA}. Mantenha o idioma consistente em todo o documento.\n4. **Métricas e impacto**: Preserve e destaque todas as métricas quantitativas do currículo original.\n5. **Tom**: Adapte o tom ao perfil da empresa.\n6. **Formato**: Retorne em Markdown bem estruturado. Não inclua explicações — apenas o currículo pronto.\n\nGere o currículo agora:`;

// ── API HELPERS ──
async function api(method, path, body) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${accessToken}` }
    };
    if (body) opts.body = JSON.stringify(body);
    let res = await fetch(path, opts);
    if (res.status === 401 && refreshToken) {
        // Try refresh
        const rr = await fetch('/api/auth/refresh', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
        if (rr.ok) {
            const t = await rr.json();
            accessToken = t.access_token; refreshToken = t.refresh_token;
            localStorage.setItem('access_token', accessToken);
            localStorage.setItem('refresh_token', refreshToken);
            opts.headers['Authorization'] = `Bearer ${accessToken}`;
            res = await fetch(path, opts);
        } else {
            doLogout(); return null;
        }
    }
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Erro desconhecido');
    }
    if (res.status === 204) return null;
    return res.json();
}

// ── AUTH ──
async function doLogin() {
    const btn = document.getElementById('login-btn');
    const err = document.getElementById('login-error');
    const user = document.getElementById('l-user').value.trim();
    const pass = document.getElementById('l-pass').value;
    err.style.display = 'none';
    btn.disabled = true; btn.textContent = 'Entrando...';
    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass })
        });
        if (!res.ok) { err.style.display = 'block'; return; }
        const t = await res.json();
        accessToken = t.access_token; refreshToken = t.refresh_token;
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
        await initApp();
    } catch { err.style.display = 'block'; }
    finally { btn.disabled = false; btn.textContent = 'Entrar'; }
}

document.getElementById('l-pass').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });

function doLogout() {
    localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token');
    accessToken = ''; refreshToken = '';
    document.getElementById('app-screen').style.display = 'none';
    document.getElementById('login-screen').style.display = 'flex';
}

// ── INIT ──
async function initApp() {
    try {
        currentUser = await api('GET', '/api/auth/me');
        document.getElementById('user-initial').textContent = (currentUser.display_name || currentUser.username)[0].toUpperCase();
        document.getElementById('user-name-label').textContent = currentUser.display_name || currentUser.username;
        if (currentUser.is_admin) document.getElementById('admin-btn').style.display = '';

        const profile = await api('GET', '/api/profile/');
        document.getElementById('cv-text').value = lang === 'pt' ? (profile.cv_pt || '') : (profile.cv_en || '');
        document.getElementById('prompt-text').value = profile.base_prompt || DEFAULT_PROMPT;
        updateCounts();

        document.getElementById('login-screen').style.display = 'none';
        document.getElementById('app-screen').style.display = 'flex';
        checkReady();
        loadHistory();
    } catch { doLogout(); }
}

// Auto-login if tokens exist
if (accessToken) initApp();

// ── LANG ──
async function setLang(l) {
    // Save current CV first
    await saveCV(true);
    lang = l;
    document.getElementById('btn-pt').classList.toggle('active', l === 'pt');
    document.getElementById('btn-en').classList.toggle('active', l === 'en');
    document.getElementById('cv-lang-label').textContent = l === 'pt' ? 'Português' : 'Inglês';
    const profile = await api('GET', '/api/profile/');
    document.getElementById('cv-text').value = l === 'pt' ? (profile.cv_pt || '') : (profile.cv_en || '');
    updateCounts();
}

// ── TABS ──
function switchTab(id) {
    document.querySelectorAll('.tab').forEach((t, i) => {
        t.classList.toggle('active', ['cv', 'job', 'prompt', 'history'][i] === id);
    });
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('tab-' + id).classList.add('active');
    if (id === 'history') loadHistory();
}

// ── SAVE ──
async function saveCV(silent = false) {
    const val = document.getElementById('cv-text').value;
    const body = lang === 'pt' ? { cv_pt: val } : { cv_en: val };
    await api('PUT', '/api/profile/', body);
    if (!silent) { const s = document.getElementById('cv-saved'); s.style.display = ''; setTimeout(() => s.style.display = 'none', 2000); }
}

async function savePrompt() {
    await api('PUT', '/api/profile/', { base_prompt: document.getElementById('prompt-text').value });
    const s = document.getElementById('prompt-saved'); s.style.display = ''; setTimeout(() => s.style.display = 'none', 2000);
}

function updateCounts() {
    const cv = document.getElementById('cv-text').value;
    const job = document.getElementById('job-text').value;
    const p = document.getElementById('prompt-text').value;
    document.getElementById('cv-count').textContent = cv.length.toLocaleString('pt-BR') + ' caracteres';
    document.getElementById('job-count').textContent = job.length.toLocaleString('pt-BR') + ' caracteres';
    document.getElementById('prompt-count').textContent = p.length.toLocaleString('pt-BR') + ' caracteres';
    checkReady();
}

document.getElementById('cv-text').addEventListener('input', updateCounts);
document.getElementById('job-text').addEventListener('input', updateCounts);
document.getElementById('prompt-text').addEventListener('input', updateCounts);

function checkReady() {
    const cv = document.getElementById('cv-text').value.trim();
    const job = document.getElementById('job-text').value.trim();
    const btn = document.getElementById('gen-btn');
    const status = document.getElementById('gen-status');
    if (!cv && !job) status.textContent = 'Preencha o CV e a vaga para começar';
    else if (!cv) status.textContent = 'Adicione o currículo mestre';
    else if (!job) status.textContent = 'Adicione a descrição da vaga';
    else status.textContent = 'Tudo pronto!';
    btn.disabled = !cv || !job || isLoading;
}

function insertVar(v) {
    const ta = document.getElementById('prompt-text');
    const s = ta.selectionStart, e = ta.selectionEnd;
    ta.value = ta.value.slice(0, s) + v + ta.value.slice(e);
    ta.selectionStart = ta.selectionEnd = s + v.length;
    ta.focus();
}

// ── GENERATE ──
function setLoading(on) {
    isLoading = on;
    document.getElementById('gen-btn').disabled = on;
    document.getElementById('adjust-btn').disabled = on;
    document.getElementById('gen-status').innerHTML = on ? '<span class="dots">Gerando</span>' : '';
    if (!on) checkReady();
}

async function generate() {
    if (isLoading) return;
    setLoading(true);
    await api('PUT', '/api/profile/', { base_prompt: document.getElementById('prompt-text').value });
    clearOutputSilent();
    showLoadingCard();
    conversationHistory = [];
    try {
        const result = await api('POST', '/api/cv/generate', {
            job_description: document.getElementById('job-text').value,
            lang,
            prompt_override: document.getElementById('prompt-text').value || null,
        });
        lastOutput = result.result;
        lastGeneratedId = result.id;
        const prompt = document.getElementById('prompt-text').value ||
            document.getElementById('prompt-text').placeholder;
        conversationHistory = [
            { role: 'user', content: prompt },
            { role: 'assistant', content: result.result }
        ];
        renderOutput(result.result);
    } catch (e) { renderError(e.message); }
    finally { setLoading(false); }
}

async function adjust() {
    const input = document.getElementById('adjust-input');
    const instruction = input.value.trim();
    if (!instruction || isLoading || !lastGeneratedId) return;
    input.value = '';
    setLoading(true);
    showLoadingCard(true);
    try {
        const result = await api('POST', '/api/cv/adjust', {
            generated_cv_id: lastGeneratedId,
            instruction,
            conversation_history: conversationHistory,
        });
        conversationHistory.push({ role: 'user', content: instruction });
        conversationHistory.push({ role: 'assistant', content: result.result });
        lastOutput = result.result;
        lastGeneratedId = result.id;
        renderOutput(result.result);
    } catch (e) { renderError(e.message); }
    finally { setLoading(false); }
}

function showLoadingCard(append = false) {
    const body = document.getElementById('output-body');
    if (!append) body.innerHTML = '';
    const card = document.createElement('div');
    card.className = 'output-card'; card.id = 'loading-card';
    card.innerHTML = `<div class="output-card-header"><span class="output-card-label">Gerando</span><span class="dots" style="font-size:11px;color:var(--ink-3)">processando</span></div><div class="output-text" style="color:var(--ink-3);font-style:italic;font-size:12px">Aguardando resposta...</div>`;
    body.appendChild(card);
    body.scrollTop = body.scrollHeight;
}

function renderOutput(text) {
    const body = document.getElementById('output-body');
    document.getElementById('loading-card')?.remove();
    const card = document.createElement('div');
    card.className = 'output-card';
    card.innerHTML = `<div class="output-card-header"><span class="output-card-label">Currículo gerado</span><span class="match-badge">✓ Otimizado para a vaga</span></div><div class="output-text">${esc(text)}</div>`;
    body.appendChild(card);
    body.scrollTop = body.scrollHeight;
    document.getElementById('copy-btn').style.display = '';
    document.getElementById('pdf-btn').style.display = '';
    document.getElementById('clear-btn').style.display = '';
    document.getElementById('adjust-bar').style.display = '';
}

function renderError(msg) {
    document.getElementById('loading-card')?.remove();
    const body = document.getElementById('output-body');
    const card = document.createElement('div');
    card.className = 'output-card';
    card.innerHTML = `<div class="output-card-header"><span class="output-card-label" style="color:var(--accent)">Erro</span></div><div class="output-text" style="color:var(--accent)">${esc(msg)}</div>`;
    body.appendChild(card);
}

function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

async function copyOutput() {
    await navigator.clipboard.writeText(lastOutput);
    const b = document.getElementById('copy-btn');
    b.textContent = '✓ Copiado'; b.style.color = 'var(--green)';
    setTimeout(() => { b.textContent = 'Copiar'; b.style.color = ''; }, 2000);
}

function clearOutputSilent() {
    document.getElementById('output-body').innerHTML = `<div class="empty-state" id="empty-state"><div class="empty-icon">CV</div><h3>Pronto para gerar</h3><p>Adicione o Master CV, cole a vaga e clique em <em>Gerar</em>.</p></div>`;
    document.getElementById('copy-btn').style.display = 'none';
    document.getElementById('pdf-btn').style.display = 'none';
    document.getElementById('clear-btn').style.display = 'none';
    document.getElementById('adjust-bar').style.display = 'none';
}

function clearOutput() {
    clearOutputSilent(); conversationHistory = []; lastOutput = ''; lastGeneratedId = null; checkReady();
}

// ── HISTORY ──
async function loadHistory() {
    const list = document.getElementById('history-list');
    try {
        const items = await api('GET', '/api/cv/history');
        if (!items.length) { list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--ink-3);font-size:13px;">Nenhum currículo gerado ainda.</div>'; return; }
        list.innerHTML = items.map(i => `
        <div class="history-item" onclick="loadHistoryItem(${i.id})">
          <span class="history-snippet">${esc(i.job_snippet)}</span>
          <span class="history-meta">${i.lang.toUpperCase()} · ${new Date(i.created_at).toLocaleDateString('pt-BR')}</span>
        </div>`).join('');
    } catch { list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--accent);font-size:13px;">Erro ao carregar histórico.</div>'; }
}

async function loadHistoryItem(id) {
  const item = await api('GET', `/api/cv/history/${id}`);
  openDetailModal(item);
}

// ── ADMIN ──
async function openAdmin() {
  document.getElementById('admin-panel').classList.add('open');
  switchAdminTab('users');
  loadUsers();
}

function closeAdmin() { document.getElementById('admin-panel').classList.remove('open'); }

async function loadUsers() {
    const ul = document.getElementById('users-list');
    const users = await api('GET', '/api/users/');
    ul.innerHTML = users.map(u => `
      <div class="user-row">
        <div class="user-row-info">
          <div class="user-row-name">${esc(u.display_name || u.username)} ${u.is_admin ? '<span class="badge-admin">admin</span>' : ''} ${!u.is_active ? '<span class="badge-inactive">inativo</span>' : ''}</div>
          <div class="user-row-meta">@${esc(u.username)} · desde ${new Date(u.created_at).toLocaleDateString('pt-BR')}</div>
        </div>
        ${u.id !== currentUser.id ? `
          <button class="btn-sm" onclick="toggleActive(${u.id}, ${u.is_active})">${u.is_active ? 'Desativar' : 'Ativar'}</button>
          <button class="btn-sm" onclick="deleteUser(${u.id})" style="color:var(--accent)">Remover</button>
        ` : '<span style="font-size:12px;color:var(--ink-3)">você</span>'}
      </div>`).join('');
}

async function createUser() {
    const err = document.getElementById('create-error');
    err.style.display = 'none';
    try {
        await api('POST', '/api/users/', {
            username: document.getElementById('new-username').value.trim(),
            display_name: document.getElementById('new-displayname').value.trim() || null,
            password: document.getElementById('new-password').value,
            is_admin: document.getElementById('new-is-admin').checked,
        });
        document.getElementById('new-username').value = '';
        document.getElementById('new-displayname').value = '';
        document.getElementById('new-password').value = '';
        document.getElementById('new-is-admin').checked = false;
        loadUsers();
    } catch (e) { err.textContent = e.message; err.style.display = ''; }
}

async function toggleActive(id, current) {
    await api('PATCH', `/api/users/${id}`, { is_active: !current });
    loadUsers();
}

async function deleteUser(id) {
    if (!confirm('Remover este usuário e todos os dados dele?')) return;
    await api('DELETE', `/api/users/${id}`);
    loadUsers();
}

async function exportPDF() {
  if (!lastOutput) return;
  const btn = document.getElementById('pdf-btn');
  btn.textContent = 'Gerando...';
  btn.disabled = true;

  const container = document.createElement('div');
  container.style.cssText = `
    width: 794px;
    padding: 60px 72px;
    box-sizing: border-box;
    font-family: Georgia, serif;
    font-size: 11px;
    line-height: 1.6;
    color: #1a1814;
    background: white;
  `;
  container.innerHTML = marked.parse(lastOutput);

  container.querySelectorAll('h1').forEach(el => {
    el.style.cssText = 'font-size:18px;margin-bottom:4px;border-bottom:2px solid #c84b2f;padding-bottom:6px;';
  });
  container.querySelectorAll('h2').forEach(el => {
    el.style.cssText = 'font-size:13px;color:#c84b2f;margin-top:14px;margin-bottom:3px;border-bottom:1px solid #e4e0d9;padding-bottom:3px;';
  });
  container.querySelectorAll('h3').forEach(el => {
    el.style.cssText = 'font-size:11px;font-weight:600;margin-top:8px;margin-bottom:2px;';
  });
  container.querySelectorAll('p, li').forEach(el => {
    el.style.cssText = 'text-align:justify;margin:3px 0;';
  });
  container.querySelectorAll('ul').forEach(el => {
    el.style.cssText = 'padding-left:16px;margin:3px 0;';
  });

  const opt = {
    margin: 0,
    filename: 'curriculo.pdf',
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: {
      scale: 2,
      useCORS: true,
      width: 794,
      windowWidth: 794,
      logging: false
    },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
  };

  try {
    await html2pdf().set(opt).from(container).save();
  } finally {
    btn.textContent = 'Exportar PDF';
    btn.disabled = false;
  }
}

function openProfile() {
    document.getElementById('profile-username').value = currentUser.username;
    document.getElementById('profile-displayname').value = currentUser.display_name || '';
    document.getElementById('profile-current-pass').value = '';
    document.getElementById('profile-new-pass').value = '';
    document.getElementById('profile-confirm-pass').value = '';
    document.getElementById('profile-name-msg').style.display = 'none';
    document.getElementById('profile-pass-msg').style.display = 'none';
    document.getElementById('profile-panel').classList.add('open');
}

function closeProfile() {
    document.getElementById('profile-panel').classList.remove('open');
}

async function saveProfileName() {
    const display_name = document.getElementById('profile-displayname').value.trim();
    const msg = document.getElementById('profile-name-msg');
    try {
        const updated = await api('PATCH', '/api/auth/me', { display_name });
        currentUser = updated;
        document.getElementById('user-name-label').textContent = updated.display_name || updated.username;
        document.getElementById('user-initial').textContent = (updated.display_name || updated.username)[0].toUpperCase();
        msg.textContent = '✓ Nome atualizado'; msg.style.color = 'var(--green)'; msg.style.display = '';
        setTimeout(() => msg.style.display = 'none', 2500);
    } catch (e) {
        msg.textContent = e.message; msg.style.color = 'var(--accent)'; msg.style.display = '';
    }
}

async function saveProfilePassword() {
    const current_password = document.getElementById('profile-current-pass').value;
    const new_password = document.getElementById('profile-new-pass').value;
    const confirm = document.getElementById('profile-confirm-pass').value;
    const msg = document.getElementById('profile-pass-msg');

    if (new_password !== confirm) {
        msg.textContent = 'As senhas não coincidem'; msg.style.color = 'var(--accent)'; msg.style.display = '';
        return;
    }
    if (new_password.length < 6) {
        msg.textContent = 'A senha deve ter ao menos 6 caracteres'; msg.style.color = 'var(--accent)'; msg.style.display = '';
        return;
    }

    try {
        await api('PATCH', '/api/auth/me', { current_password, new_password });
        msg.textContent = '✓ Senha alterada com sucesso'; msg.style.color = 'var(--green)'; msg.style.display = '';
        document.getElementById('profile-current-pass').value = '';
        document.getElementById('profile-new-pass').value = '';
        document.getElementById('profile-confirm-pass').value = '';
        setTimeout(() => msg.style.display = 'none', 2500);
    } catch (e) {
        msg.textContent = e.message; msg.style.color = 'var(--accent)'; msg.style.display = '';
    }
}

function switchAdminTab(tab) {
    document.getElementById('admin-tab-users').classList.toggle('active', tab === 'users');
    document.getElementById('admin-tab-usage').classList.toggle('active', tab === 'usage');
    document.getElementById('admin-body-users').style.display = tab === 'users' ? '' : 'none';
    document.getElementById('admin-body-usage').style.display = tab === 'usage' ? '' : 'none';
    if (tab === 'usage') loadUsage();
}

async function loadUsage() {
    const content = document.getElementById('usage-content');
    content.innerHTML = '<div style="padding:20px;text-align:center;color:var(--ink-3);font-size:13px;">Carregando...</div>';
    const users = await api('GET', '/api/admin/users-usage');
    content.innerHTML = users.map(u => `
    <div class="user-row" style="cursor:pointer" onclick="loadUserHistory(${u.id}, '${esc(u.display_name || u.username)}')">
      <div class="user-row-info">
        <div class="user-row-name">${esc(u.display_name || u.username)}</div>
        <div class="user-row-meta">@${esc(u.username)} · ${u.last_generation ? new Date(u.last_generation).toLocaleDateString('pt-BR') : 'nunca'}</div>
      </div>
      <div style="font-size:13px;font-weight:600;color:var(--accent)">${u.total_generations} gerações</div>
    </div>`).join('');
}

async function loadUserHistory(userId, userName) {
    const content = document.getElementById('usage-content');
    content.innerHTML = `
    <div style="padding:12px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px">
      <button class="btn-sm" onclick="loadUsage()">← Voltar</button>
      <span style="font-size:13px;font-weight:500">${esc(userName)}</span>
    </div>
    <div id="user-history-list"><div style="padding:20px;text-align:center;color:var(--ink-3);font-size:13px;">Carregando...</div></div>`;

    const items = await api('GET', `/api/admin/users-usage/${userId}`);
    const list = document.getElementById('user-history-list');

    if (!items.length) {
        list.innerHTML = '<div style="padding:20px;text-align:center;color:var(--ink-3);font-size:13px;">Nenhuma geração encontrada.</div>';
        return;
    }

    list.innerHTML = items.map(i => `
    <div class="history-item" onclick="openGenerationDetail(${i.id})">
      <span class="history-snippet">${esc(i.job_description.slice(0, 80))}</span>
      <span class="history-meta">${i.lang.toUpperCase()} · ${new Date(i.created_at).toLocaleDateString('pt-BR')}</span>
    </div>`).join('');
}

async function openGenerationDetail(cvId) {
    const item = await api('GET', `/api/admin/generated/${cvId}`);
    openDetailModal(item);
}

let currentDetail = null;

function openDetailModal(item) {
    currentDetail = item;
    switchDetailTab('result');
    document.getElementById('detail-panel').classList.add('open');
}

function closeDetail() {
    document.getElementById('detail-panel').classList.remove('open');
    currentDetail = null;
}

function switchDetailTab(tab) {
    ['result', 'job', 'cv', 'prompt'].forEach(t => {
        document.getElementById(`detail-tab-${t}`).classList.toggle('active', t === tab);
    });
    const body = document.getElementById('detail-body');
    const content = {
        result: currentDetail?.result,
        job: currentDetail?.job_description,
        cv: currentDetail?.cv_snapshot || '(não disponível — gerado antes desta funcionalidade)',
        prompt: currentDetail?.prompt_used || '(não disponível — gerado antes desta funcionalidade)',
    };
    body.innerHTML = `<pre style="font-family:var(--font-m);font-size:12px;line-height:1.7;white-space:pre-wrap;word-break:break-word">${esc(content[tab] || '')}</pre>`;
}

function restoreCV() {
    if (!currentDetail?.cv_snapshot) return;
    // Detecta idioma e restaura no campo correto
    const field = document.getElementById('cv-text');
    field.value = currentDetail.cv_snapshot;
    closeDetail();
    switchTab('cv');
    // Salva automaticamente
    saveCV();
    document.getElementById('cv-saved').style.display = '';
    setTimeout(() => document.getElementById('cv-saved').style.display = 'none', 2000);
}

function restorePrompt() {
    if (!currentDetail?.prompt_used) return;
    document.getElementById('prompt-text').value = currentDetail.prompt_used;
    closeDetail();
    switchTab('prompt');
    savePrompt();
}