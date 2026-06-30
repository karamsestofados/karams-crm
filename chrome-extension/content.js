(function () {
  'use strict';

  const DEBOUNCE_MS = 300;
  const PANEL_WIDTH = 320;
  let debounceTimer = null;
  let lastPhone = null;
  let manualPhone = null;
  let manualInputDraft = '';
  let lastChatKey = '';
  let panelMode = 'idle';
  let isPinned = false;
  let isCollapsed = false;
  let shadowRoot = null;
  let panelEl = null;
  let pendingInject = false;
  let detectionRetryTimer = null;
  let detectionRetryCount = 0;
  const MAX_DETECTION_RETRIES = 4;
  let extensionDead = false;
  let chatObserver = null;
  let drawerObserver = null;

  const PHONE_TEXT_RE = /(?:\+55[\s-]?)?(?:\(\d{2}\)[\s-]?|\d{2}[\s-])\d{4,5}[\s-]?\d{4}|\+[\d\s()-]{12,18}|\b\d{2}[\s-]?\d{4,5}[\s-]?\d{4}\b/g;

  function runtimeAlive() {
    try {
      return Boolean(typeof chrome !== 'undefined' && chrome.runtime?.id);
    } catch {
      return false;
    }
  }

  function isContextInvalidatedError(err) {
    const msg = String(err?.message || err || '');
    return /invalidated|extension context/i.test(msg);
  }

  function shutdownContentScript() {
    if (extensionDead) return;
    extensionDead = true;
    clearTimeout(debounceTimer);
    debounceTimer = null;
    clearDetectionRetry();
    chatObserver?.disconnect();
    drawerObserver?.disconnect();
    chatObserver = null;
    drawerObserver = null;
  }

  function handleRuntimeDead() {
    shutdownContentScript();
    renderReloadExtension();
  }

  function renderReloadExtension() {
    try {
      createPanel();
      panelMode = 'stale';
      hideFooter();
      setBody(`
        <div class="karams-state">
          <div class="karams-state-card">
            <div class="karams-state-icon">🔄</div>
            <p class="karams-state-title">Extensão atualizada</p>
            <p class="karams-muted">Recarregue o WhatsApp (F5) para reconectar o Karams CRM.</p>
            <button type="button" id="karams-reload-wa" class="karams-btn-primary karams-btn-inline">Recarregar página</button>
          </div>
        </div>
      `);
      shadowRoot?.getElementById('karams-reload-wa')?.addEventListener('click', () => location.reload());
    } catch {
      /* painel indisponível após invalidação */
    }
  }

  function sendRuntimeMessage(payload) {
    return new Promise((resolve) => {
      if (extensionDead || !runtimeAlive()) {
        handleRuntimeDead();
        resolve(null);
        return;
      }
      try {
        chrome.runtime.sendMessage(payload, (resp) => {
          const err = chrome.runtime.lastError;
          if (err) {
            if (isContextInvalidatedError(err)) {
              handleRuntimeDead();
              resolve(null);
              return;
            }
            resolve({ erro: err.message || 'Erro na extensão.' });
            return;
          }
          resolve(resp);
        });
      } catch (err) {
        if (isContextInvalidatedError(err)) handleRuntimeDead();
        resolve(null);
      }
    });
  }

  function storageGet(keys, callback) {
    if (extensionDead || !runtimeAlive()) return;
    try {
      chrome.storage.local.get(keys, (items) => {
        if (chrome.runtime.lastError) {
          if (isContextInvalidatedError(chrome.runtime.lastError)) handleRuntimeDead();
          return;
        }
        callback(items);
      });
    } catch (err) {
      if (isContextInvalidatedError(err)) handleRuntimeDead();
    }
  }

  function storageSet(values) {
    if (extensionDead || !runtimeAlive()) return;
    try {
      chrome.storage.local.set(values, () => {
        if (chrome.runtime.lastError && isContextInvalidatedError(chrome.runtime.lastError)) {
          handleRuntimeDead();
        }
      });
    } catch (err) {
      if (isContextInvalidatedError(err)) handleRuntimeDead();
    }
  }

  function createPanel() {
    if (document.getElementById('karams-wa-host')) return;
    if (!runtimeAlive()) {
      handleRuntimeDead();
      return;
    }

    const host = document.createElement('div');
    host.id = 'karams-wa-host';
    document.body.appendChild(host);
    shadowRoot = host.attachShadow({ mode: 'open' });

    const link = document.createElement('link');
    link.rel = 'stylesheet';
    try {
      link.href = chrome.runtime.getURL('panel.css');
    } catch {
      handleRuntimeDead();
      return;
    }
    shadowRoot.appendChild(link);

    panelEl = document.createElement('div');
    panelEl.className = 'karams-panel';
    panelEl.innerHTML = `
      <button type="button" class="karams-toggle" title="Mostrar/ocultar Karams">K</button>
      <div class="karams-inner">
        <header class="karams-header">
          <div class="karams-header-row">
            <div>
              <span class="karams-logo">Karams</span>
              <span class="karams-sub">CRM WhatsApp</span>
            </div>
            <div class="karams-header-actions">
              <button type="button" class="karams-icon-btn" id="karams-pin-btn" title="Fixar painel (WhatsApp + CRM lado a lado)">⤢</button>
              <button type="button" class="karams-icon-btn" id="karams-collapse-btn" title="Recolher painel">›</button>
            </div>
          </div>
        </header>
        <div class="karams-body" id="karams-body">
          <p class="karams-muted">Abra uma conversa para ver o contexto.</p>
        </div>
        <footer class="karams-footer hidden" id="karams-footer"></footer>
      </div>
    `;
    shadowRoot.appendChild(panelEl);

    panelEl.querySelector('.karams-toggle').addEventListener('click', () => {
      if (isPinned) return;
      setCollapsed(!isCollapsed);
    });

    shadowRoot.getElementById('karams-pin-btn')?.addEventListener('click', () => {
      setPinned(!isPinned);
    });

    shadowRoot.getElementById('karams-collapse-btn')?.addEventListener('click', () => {
      if (isPinned) {
        setPinned(false);
        setCollapsed(true);
      } else {
        setCollapsed(true);
      }
    });

    storageGet({ karamsPinned: false }, (items) => {
      if (items.karamsPinned) setPinned(true);
      else updateLayout();
    });
  }

  function setPinned(pinned) {
    isPinned = pinned;
    if (pinned) isCollapsed = false;
    storageSet({ karamsPinned: pinned });
    updateLayout();
    updatePinButton();
  }

  function setCollapsed(collapsed) {
    isCollapsed = collapsed;
    updateLayout();
  }

  function updatePinButton() {
    const btn = shadowRoot?.getElementById('karams-pin-btn');
    if (!btn) return;
    btn.classList.toggle('active', isPinned);
    btn.title = isPinned
      ? 'Desafixar painel (modo flutuante)'
      : 'Fixar painel (WhatsApp + CRM lado a lado)';
    btn.textContent = isPinned ? '⤡' : '⤢';
  }

  function updateLayout() {
    if (!panelEl) return;
    const showPanel = isPinned || !isCollapsed;
    panelEl.classList.toggle('collapsed', !showPanel);
    panelEl.classList.toggle('pinned', isPinned);
    document.documentElement.classList.toggle('karams-pinned', isPinned);
    document.documentElement.classList.toggle('karams-panel-open', showPanel);
    document.documentElement.style.setProperty('--karams-panel-offset', showPanel ? `${PANEL_WIDTH}px` : '0px');
    applyWaOffset(showPanel);
  }

  function applyWaOffset(showPanel) {
    const app = document.querySelector('#app') || document.body;
    if (!app) return;
    if (!app.dataset.karamsPadded) {
      app.dataset.karamsPadded = '1';
      app.style.transition = 'width 0.2s ease, max-width 0.2s ease, margin-right 0.2s ease';
    }
    if (isPinned && showPanel) {
      app.style.width = `calc(100vw - ${PANEL_WIDTH}px)`;
      app.style.maxWidth = `calc(100vw - ${PANEL_WIDTH}px)`;
      app.style.marginRight = '0';
    } else if (showPanel) {
      app.style.width = '';
      app.style.maxWidth = '';
      app.style.marginRight = `${PANEL_WIDTH}px`;
    } else {
      app.style.width = '';
      app.style.maxWidth = '';
      app.style.marginRight = '0';
    }
  }

  function onlyDigits(val) {
    return String(val || '').replace(/\D/g, '');
  }

  function canonicalizar(val) {
    if (typeof KaramsTelefone !== 'undefined') {
      return KaramsTelefone.canonicalizarTelefone(val);
    }
    return onlyDigits(val);
  }

  function variantes(val) {
    if (typeof KaramsTelefone !== 'undefined') {
      return KaramsTelefone.variantesTelefone(val);
    }
    return [onlyDigits(val)].filter((v) => v.length >= 10);
  }

  function phonesEquivalent(a, b) {
    if (!a || !b) return false;
    if (typeof KaramsTelefone !== 'undefined' && KaramsTelefone.telefonesEquivalentes) {
      return KaramsTelefone.telefonesEquivalentes(a, b);
    }
    const va = new Set(variantes(a).map(onlyDigits));
    for (const v of variantes(b)) {
      if (va.has(onlyDigits(v))) return true;
    }
    return canonicalizar(a) === canonicalizar(b);
  }

  function clearDetectionRetry() {
    clearTimeout(detectionRetryTimer);
    detectionRetryTimer = null;
    detectionRetryCount = 0;
  }

  function scheduleDetectionRetry(reason) {
    if (extensionDead || !runtimeAlive()) return;
    if (detectionRetryCount >= MAX_DETECTION_RETRIES) return;
    if (panelMode !== 'notfound' && panelMode !== 'manual') return;

    clearTimeout(detectionRetryTimer);
    const delay = reason === 'notfound' ? 500 + detectionRetryCount * 400 : 400 + detectionRetryCount * 350;
    detectionRetryTimer = setTimeout(async () => {
      detectionRetryCount += 1;
      const phone = await extractPhone({ skipStore: false });
      if (!phone) {
        if (detectionRetryCount < MAX_DETECTION_RETRIES) scheduleDetectionRetry(reason);
        return;
      }
      if (panelMode === 'result' && phonesEquivalent(phone, lastPhone)) return;
      fetchContexto(phone, true);
    }, delay);
  }

  function isValidPhoneDigits(digits) {
    return digits.length >= 10 && digits.length <= 15;
  }

  function normalizePhoneCandidate(raw) {
    const digits = onlyDigits(raw);
    if (!isValidPhoneDigits(digits)) return null;
    return digits;
  }

  function looksLikeBrPhone(digits) {
    const d = onlyDigits(digits);
    if (d.length < 10 || d.length > 13) return false;
    let local = d;
    if (d.startsWith('55') && d.length >= 12) local = d.slice(2);
    if (local.length < 10 || local.length > 11) return false;
    const ddd = parseInt(local.slice(0, 2), 10);
    return ddd >= 11 && ddd <= 99;
  }

  function acceptPhoneCandidate(raw) {
    const digits = normalizePhoneCandidate(raw);
    if (!digits) return null;
    if (!looksLikeBrPhone(digits)) return null;
    return digits;
  }

  function getHeaderTitle() {
    const header = document.querySelector('#main header');
    if (!header) return '';
    const titled = header.querySelector('span[title], [data-testid="conversation-info-header-chat-title"]');
    return (titled?.getAttribute('title') || titled?.textContent || header.textContent || '').trim();
  }

  function getChatKey() {
    const title = getHeaderTitle();
    const fromStore = lastPhone;
    return title.slice(0, 100) || fromStore || window.location.pathname;
  }

  async function extractPhone(options = {}) {
    if (isGroupChat()) return null;

    const trySources = () => {
      const fromContact = extractPhoneFromContactPanel();
      if (fromContact) return canonicalizar(fromContact);

      const fromHeader = extractPhoneFromHeader();
      if (fromHeader) return canonicalizar(fromHeader);

      const fromSelected = extractPhoneFromSelectedChat();
      if (fromSelected) return canonicalizar(fromSelected);

      return null;
    };

    let phone = trySources();
    if (phone) return phone;

    if (!options.skipStore) {
      for (const delay of [0, 450]) {
        if (delay) await new Promise((r) => setTimeout(r, delay));
        const fromStore = await requestPhoneFromWhatsAppPage();
        if (fromStore && looksLikeBrPhone(fromStore)) return canonicalizar(fromStore);
      }
    }

    phone = trySources();
    if (phone) return phone;

    const fromUrl = acceptPhoneCandidate(window.location.href.match(/(\d{10,15})/)?.[1]);
    if (fromUrl) return canonicalizar(fromUrl);

    return null;
  }

  function resetForNewChat() {
    const key = getChatKey();
    if (!key || key === lastChatKey) return false;
    lastChatKey = key;
    lastPhone = null;
    manualPhone = null;
    manualInputDraft = '';
    panelMode = 'idle';
    clearDetectionRetry();
    return true;
  }

  function extractJidFromValue(val) {
    if (!val) return null;
    const m = String(val).match(/(\d{10,15})@c\.us/);
    return m ? m[1] : null;
  }

  function extractJidFromNode(node) {
    if (!node?.getAttribute) return null;
    for (const attr of ['data-id', 'data-jid', 'id', 'href', 'title', 'aria-label']) {
      const jid = extractJidFromValue(node.getAttribute(attr));
      if (jid) return jid;
    }
    return null;
  }

  function extractJidsFromRoot(root) {
    const found = new Set();
    if (!root) return [];
    root.querySelectorAll('[data-id*="@c.us"], [data-jid*="@c.us"]').forEach((node) => {
      const jid = extractJidFromNode(node);
      if (jid) found.add(jid);
    });
    let node = root;
    for (let i = 0; i < 15 && node; i++) {
      const jid = extractJidFromNode(node);
      if (jid) found.add(jid);
      node = node.parentElement;
    }
    return [...found];
  }

  function extractPhoneFromSelectedChat() {
    const paneSide = document.querySelector('#pane-side');
    if (!paneSide) return null;

    const title = getHeaderTitle();
    if (!title || title.length < 4) return null;

    const snippet = title.slice(0, Math.min(title.length, 32));

    const selected =
      paneSide.querySelector('[aria-selected="true"]') ||
      paneSide.querySelector('[data-testid="cell-frame-container"][aria-selected="true"]');

    if (selected && selected.textContent.includes(snippet)) {
      const jid = pickBestJid(extractJidsFromRoot(selected));
      if (jid) return jid;
    }

    for (const row of paneSide.querySelectorAll('[data-id*="@c.us"]')) {
      const container = row.closest('[aria-selected="true"]');
      if (container && container.textContent.includes(snippet)) {
        const jid = extractJidFromNode(row);
        if (jid) return jid;
      }
    }

    return null;
  }

  function pickBestJid(candidates) {
    if (!candidates.length) return null;
    return candidates.sort((a, b) => b.length - a.length)[0];
  }

  function findPhoneInText(text) {
    if (!text) return null;
    PHONE_TEXT_RE.lastIndex = 0;
    let match;
    while ((match = PHONE_TEXT_RE.exec(text)) !== null) {
      const digits = acceptPhoneCandidate(match[0]);
      if (digits) return digits;
    }
    return null;
  }

  function extractPhoneFromLeafSpans(root) {
    if (!root) return null;
    for (const el of root.querySelectorAll('span, div, a, button')) {
      const href = el.getAttribute?.('href') || '';
      if (href.startsWith('tel:')) {
        const fromTel = acceptPhoneCandidate(href.replace(/^tel:/i, ''));
        if (fromTel) return fromTel;
      }
      if (el.children.length > 3) continue;
      const text = (el.textContent || '').trim();
      if (text.length < 8 || text.length > 32) continue;
      if (!text.startsWith('+') && !/^\(\d{2}\)/.test(text) && !/^\d{2}[\s-]?\d/.test(text) && !/^\+?\d[\d\s()-]{9,}$/.test(text)) {
        continue;
      }
      const digits = acceptPhoneCandidate(text);
      if (digits) return digits;
    }
    return null;
  }

  function extractPhoneFromContactPanel() {
    const roots = new Set();

    for (const sel of [
      '[data-testid="contact-info-drawer"]',
      '[data-testid="drawer-right"]',
      '[data-testid="contact-info"]',
      '[data-testid="drawer-middle"]',
      '[data-testid="contact-info-screen"]',
    ]) {
      document.querySelectorAll(sel).forEach((el) => roots.add(el));
    }

    document.querySelectorAll('a[href^="tel:"]').forEach((el) => {
      const drawer = el.closest('[data-testid="drawer-right"], [data-testid="contact-info-drawer"]');
      if (drawer) roots.add(drawer);
    });

    document.querySelectorAll('span, h1, h2, div').forEach((el) => {
      const t = (el.textContent || '').trim();
      if (t === 'Dados do contato' || t === 'Contact info' || t === 'Info do contato') {
        const drawer = el.closest('[data-testid="drawer-right"]') || el.parentElement?.parentElement?.parentElement;
        if (drawer) roots.add(drawer);
      }
    });

    const main = document.querySelector('#main');
    if (main?.parentElement) {
      for (const sibling of main.parentElement.children) {
        if (sibling !== main && sibling.id !== 'pane-side') roots.add(sibling);
      }
    }

    for (const root of roots) {
      const fromLeaf = extractPhoneFromLeafSpans(root);
      if (fromLeaf) return fromLeaf;
      const fromText = findPhoneInText(root.textContent || '');
      if (fromText) return fromText;
    }
    return null;
  }

  function extractPhoneFromHeader() {
    const header = document.querySelector('#main header');
    if (!header) return null;
    for (const node of header.querySelectorAll('[data-id*="@c.us"], [title], span, div')) {
      const jid = extractJidFromNode(node);
      if (jid) return jid;
    }
    return extractPhoneFromLeafSpans(header);
  }

  let storePhonePromise = null;

  function requestPhoneFromWhatsAppPage() {
    if (storePhonePromise) return storePhonePromise;

    storePhonePromise = new Promise((resolve) => {
      pendingInject = true;

      const timeout = setTimeout(() => {
        pendingInject = false;
        storePhonePromise = null;
        resolve(null);
      }, 1800);

      const handler = (event) => {
        clearTimeout(timeout);
        pendingInject = false;
        storePhonePromise = null;
        document.removeEventListener('karams-wa-phone', handler);
        const user = event.detail;
        if (user && looksLikeBrPhone(String(user))) {
          resolve(String(user));
        } else {
          resolve(null);
        }
      };
      document.addEventListener('karams-wa-phone', handler);

      const script = document.createElement('script');
      try {
        script.src = chrome.runtime.getURL('page-bridge.js');
      } catch {
        clearTimeout(timeout);
        pendingInject = false;
        storePhonePromise = null;
        document.removeEventListener('karams-wa-phone', handler);
        resolve(null);
        return;
      }
      script.onload = () => script.remove();
      script.onerror = () => {
        clearTimeout(timeout);
        pendingInject = false;
        storePhonePromise = null;
        document.removeEventListener('karams-wa-phone', handler);
        resolve(null);
      };
      (document.documentElement || document.head).appendChild(script);
    });

    return storePhonePromise;
  }

  function isGroupChat() {
    const header = document.querySelector('#main header');
    if (!header) return false;
    const text = header.textContent || '';
    if (text.includes('participantes') || text.includes('participants')) return true;
    return Boolean(header.querySelector('[data-icon="default-group"]'));
  }

  function setBody(html) {
    if (!shadowRoot) return;
    const body = shadowRoot.getElementById('karams-body');
    if (body) body.innerHTML = html;
  }

  function setFooter(html) {
    if (!shadowRoot) return;
    const footer = shadowRoot.getElementById('karams-footer');
    if (!footer) return;
    footer.innerHTML = html;
    footer.classList.remove('hidden');
  }

  function hideFooter() {
    if (!shadowRoot) return;
    const footer = shadowRoot.getElementById('karams-footer');
    if (footer) {
      footer.innerHTML = '';
      footer.classList.add('hidden');
    }
  }

  function formatMoney(val) {
    if (val == null || val === '') return '—';
    const n = Number(val);
    if (Number.isNaN(n)) return val;
    return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  function formatMoneyCompact(val) {
    if (val == null || val === '') return '—';
    const n = Number(val);
    if (Number.isNaN(n)) return val;
    return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
  }

  function formatDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString('pt-BR');
  }

  function badgeClassForCategoria(categoria) {
    const map = {
      ativo: 'karams-badge-ativo',
      adormecido: 'karams-badge-adormecido',
      prospeccao: 'karams-badge-prospeccao',
      inativo: 'karams-badge-inativo',
    };
    return map[categoria] || 'karams-badge-default';
  }

  function alertIcon(nivel) {
    if (nivel === 'danger') return '⚠';
    if (nivel === 'warning') return '⚡';
    return 'ℹ';
  }

  function renderLoading() {
    panelMode = 'loading';
    hideFooter();
    setBody(`
      <div class="karams-state">
        <div class="karams-spinner"></div>
        <p class="karams-state-title">Buscando informações</p>
        <p class="karams-muted">Consultando o CRM Karams…</p>
      </div>
    `);
  }

  function renderError(msg, hint, retryPhone) {
    panelMode = 'error';
    hideFooter();
    setBody(`
      <div class="karams-state">
        <div class="karams-state-card">
          <div class="karams-state-icon">📡</div>
          <p class="karams-state-title">Erro de conexão</p>
          <div class="karams-alert danger">${escapeHtml(msg)}</div>
          ${hint ? `<p class="karams-muted">${escapeHtml(hint)}</p>` : ''}
          ${retryPhone ? '<button type="button" id="karams-retry-btn" class="karams-btn-secondary">Tentar novamente</button>' : ''}
        </div>
      </div>
    `);
    if (retryPhone) {
      shadowRoot.getElementById('karams-retry-btn')?.addEventListener('click', () => {
        lastPhone = null;
        fetchContexto(retryPhone, true);
      });
    }
  }

  function formatPhoneDebug(digits) {
    const d = onlyDigits(digits);
    if (d.length === 13 && d.startsWith('55')) {
      return `+${d.slice(0, 2)} ${d.slice(2, 4)} ${d.slice(4, 9)}-${d.slice(9)}`;
    }
    if (d.length === 12 && d.startsWith('55')) {
      return `+${d.slice(0, 2)} ${d.slice(2, 4)} ${d.slice(4, 8)}-${d.slice(8)}`;
    }
    return d;
  }

  function renderNotFound(msg, phone) {
    panelMode = 'notfound';
    hideFooter();
    const display = phone ? formatPhoneDebug(phone) : '';
    setBody(`
      <div class="karams-state">
        <div class="karams-state-card">
          <div class="karams-state-icon">👤</div>
          <p class="karams-state-title">Cliente não encontrado</p>
          <p class="karams-muted">${escapeHtml(msg || 'Não cadastrado com este telefone.')}</p>
          ${display ? `<p class="karams-muted">Número buscado: <strong>${escapeHtml(display)}</strong></p>` : ''}
          <p class="karams-muted">Cadastre ou atualize o telefone no CRM.</p>
          <button type="button" id="karams-manual-again" class="karams-btn-primary karams-btn-inline">Buscar outro número</button>
        </div>
      </div>
    `);
    shadowRoot.getElementById('karams-manual-again')?.addEventListener('click', () => {
      manualPhone = null;
      lastPhone = null;
      manualInputDraft = phone || '';
      panelMode = 'idle';
      clearDetectionRetry();
      renderManualFallback();
    });
    scheduleDetectionRetry('notfound');
  }

  function renderGroup() {
    panelMode = 'group';
    hideFooter();
    setBody(`
      <div class="karams-state">
        <div class="karams-state-card">
          <div class="karams-state-icon">👥</div>
          <p class="karams-state-title">Grupo WhatsApp</p>
          <p class="karams-muted">Conversas em grupo não são suportadas no MVP.</p>
        </div>
      </div>
    `);
  }

  function bindManualForm() {
    const input = shadowRoot.getElementById('karams-phone-input');
    const btn = shadowRoot.getElementById('karams-phone-btn');
    if (!input || !btn) return;
    if (manualInputDraft) input.value = manualInputDraft;

    input.addEventListener('input', () => { manualInputDraft = input.value; });

    const submit = () => {
      manualInputDraft = input.value;
      const digits = normalizePhoneCandidate(input.value);
      if (!digits) {
        renderError('Informe um telefone válido (mín. 10 dígitos).');
        return;
      }
      manualPhone = digits;
      lastPhone = null;
      fetchContexto(digits, true);
    };

    btn.addEventListener('click', submit);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') submit(); });
  }

  function renderManualFallback() {
    panelMode = 'manual';
    hideFooter();
    setBody(`
      <div class="karams-state">
        <div class="karams-state-card">
          <div class="karams-state-icon">📱</div>
          <p class="karams-state-title">Número não detectado</p>
          <p class="karams-muted">Cole o telefone abaixo e busque no CRM:</p>
          <div class="karams-manual">
            <input type="text" id="karams-phone-input" class="karams-input" placeholder="+55 71 99971-2271" value="${escapeHtml(manualInputDraft)}" />
            <button type="button" id="karams-phone-btn" class="karams-btn-primary">Buscar no CRM</button>
          </div>
        </div>
      </div>
    `);
    bindManualForm();
  }

  function mapApiError(resp) {
    const msg = resp?.erro || '';
    if (msg.includes('Token')) {
      return { text: msg, hint: 'Gere um novo token no Perfil e atualize nas Opções da extensão.' };
    }
    if (msg.includes('conexão') || msg.includes('conectar')) {
      return { text: msg, hint: 'Confirme se runserver está ativo em http://127.0.0.1:8000' };
    }
    if (resp?.status === 404) {
      return { text: 'API não encontrada (404).', hint: 'Use CRM local ou faça deploy.' };
    }
    return { text: msg || 'Erro ao consultar CRM.', hint: '' };
  }

  function fetchContexto(phone, force, altAttempt = false) {
    if (extensionDead || !runtimeAlive()) {
      handleRuntimeDead();
      return;
    }

    const toSend = canonicalizar(phone);

    if (!force && !altAttempt && toSend === lastPhone && (panelMode === 'result' || panelMode === 'loading')) {
      return;
    }
    if (!altAttempt) lastPhone = toSend;
    manualPhone = null;
    renderLoading();

    sendRuntimeMessage({ type: 'FETCH_CONTEXTO', telefone: toSend }).then((resp) => {
      if (extensionDead) return;
      if (!resp) {
        if (!extensionDead) renderError('Extensão desconectada. Recarregue o WhatsApp (F5).', null, toSend);
        return;
      }
      if (resp?.erro) {
        const mapped = mapApiError(resp);
        renderError(mapped.text, mapped.hint, toSend);
        return;
      }
      if (!resp?.encontrado) {
        if (!altAttempt) {
          const contactPhone = extractPhoneFromContactPanel();
          if (contactPhone && !phonesEquivalent(contactPhone, phone)) {
            fetchContexto(contactPhone, true, true);
            return;
          }
          const rawDigits = acceptPhoneCandidate(phone);
          if (rawDigits && !phonesEquivalent(rawDigits, toSend)) {
            fetchContexto(rawDigits, true, true);
            return;
          }
        }
        renderNotFound(resp?.mensagem, toSend);
        return;
      }
      panelMode = 'result';
      clearDetectionRetry();
      renderContext(resp);
    }).catch(() => {
      if (!extensionDead) handleRuntimeDead();
    });
  }

  function renderContext(data) {
    const c = data.cliente;
    const m = data.metricas || {};
    const i = data.interacoes || {};
    const alertas = data.alertas || [];

    const catBadge = badgeClassForCategoria(c.categoria);
    const local = [c.cidade, c.estado].filter(Boolean).join(' / ') || '—';

    const ultimoProduto = m.ultimo_produto_comprado || '—';
    const refCompra = m.ultima_compra_referencia
      ? ` <span class="karams-muted">(${escapeHtml(m.ultima_compra_referencia)})</span>`
      : '';

    const alertasHtml = alertas.length
      ? `<section class="karams-section">
          <h3 class="karams-section-title">Alertas</h3>
          ${alertas.map((a) => `
            <div class="karams-alert-card ${escapeHtml(a.nivel)}">
              <span class="karams-alert-icon">${alertIcon(a.nivel)}</span>
              <span>${escapeHtml(a.mensagem)}</span>
            </div>`).join('')}
        </section>`
      : '';

    setBody(`
      <section class="karams-id-block">
        <h2 class="karams-name">${escapeHtml(c.nome)}</h2>
        <p class="karams-meta">${escapeHtml(local)}</p>
        <p class="karams-meta">${escapeHtml(c.telefone || '')}</p>
        ${c.consultor_nome ? `
          <div class="karams-meta-row">
            <span class="karams-meta-label">Consultor</span>
            <span class="karams-meta-value">${escapeHtml(c.consultor_nome)}</span>
          </div>` : ''}
        ${c.responsavel ? `
          <div class="karams-meta-row">
            <span class="karams-meta-label">Responsável</span>
            <span class="karams-meta-value">${escapeHtml(c.responsavel)}</span>
          </div>` : ''}
        <div class="karams-badges">
          <span class="karams-badge ${catBadge}">${escapeHtml((c.categoria_label || '').toUpperCase())}</span>
          <span class="karams-badge karams-badge-funil">${escapeHtml((c.status_funil_label || '').toUpperCase())}</span>
        </div>
      </section>

      <section class="karams-section">
        <h3 class="karams-section-title">Visão rápida</h3>
        <div class="karams-quick-card">
          <div class="karams-quick-grid">
            <div class="karams-quick-cell">
              <span class="karams-quick-label">Última compra</span>
              <span class="karams-quick-value highlight">${formatMoneyCompact(m.ultima_compra_valor)}</span>
            </div>
            <div class="karams-quick-cell">
              <span class="karams-quick-label">Dias sem comprar</span>
              <span class="karams-quick-value">${m.dias_sem_comprar ?? '—'}</span>
            </div>
            <div class="karams-quick-cell">
              <span class="karams-quick-label">Ticket médio</span>
              <span class="karams-quick-value">${formatMoneyCompact(m.ticket_medio)}</span>
            </div>
            <div class="karams-quick-cell">
              <span class="karams-quick-label">Orçamentos</span>
              <span class="karams-quick-value">${i.orcamentos_abertos ?? 0}</span>
            </div>
          </div>
        </div>
      </section>

      ${alertasHtml}

      <section class="karams-section">
        <h3 class="karams-section-title">Resumo comercial</h3>
        <div class="karams-summary-card">
          <div class="karams-summary-row">
            <span class="karams-summary-label">Total comprado</span>
            <span class="karams-summary-value">${formatMoney(m.total_comprado)}</span>
          </div>
          <div class="karams-summary-row">
            <span class="karams-summary-label">Produto mais comprado</span>
            <span class="karams-summary-value">${escapeHtml(m.produto_mais_comprado || '—')}</span>
          </div>
          <div class="karams-summary-row">
            <span class="karams-summary-label">Último produto</span>
            <span class="karams-summary-value">${escapeHtml(ultimoProduto)}${refCompra}</span>
          </div>
          <div class="karams-summary-row">
            <span class="karams-summary-label">Última interação</span>
            <span class="karams-summary-value">${formatDate(i.ultimo_contato_em)}</span>
          </div>
          <div class="karams-summary-row">
            <span class="karams-summary-label">Total interações</span>
            <span class="karams-summary-value">${i.total_interacoes ?? 0}</span>
          </div>
        </div>
      </section>
    `);

    setFooter(`
      <a class="karams-btn-primary" href="${escapeHtml(c.url_crm)}" target="_blank" rel="noopener">
        Ver ficha completa no CRM ↗
      </a>
    `);
  }

  function escapeHtml(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  async function resolveAndFetch(chatChanged) {
    if (extensionDead || !runtimeAlive()) {
      handleRuntimeDead();
      return;
    }

    if (isGroupChat()) {
      renderGroup();
      return;
    }

    if (chatChanged) {
      await new Promise((r) => setTimeout(r, 280));
    }

    if (manualPhone && !chatChanged && panelMode !== 'idle') {
      fetchContexto(manualPhone, false);
      return;
    }

    const phone = await extractPhone();

    if (phone) {
      const shouldFetch =
        chatChanged ||
        !phonesEquivalent(phone, lastPhone) ||
        panelMode === 'notfound' ||
        panelMode === 'manual' ||
        panelMode === 'idle' ||
        panelMode === 'error';
      if (shouldFetch) {
        clearDetectionRetry();
        fetchContexto(phone, true);
      }
      return;
    }

    if (panelMode === 'result' && !chatChanged) return;

    renderManualFallback();
    scheduleDetectionRetry('nophone');
  }

  function onChatChange() {
    if (extensionDead || !runtimeAlive()) {
      handleRuntimeDead();
      return;
    }
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      createPanel();
      updateLayout();
      const chatChanged = resetForNewChat();
      await resolveAndFetch(chatChanged);
    }, DEBOUNCE_MS);
  }

  function observeChat() {
    createPanel();
    lastChatKey = getChatKey();

    const paneSide = document.querySelector('#pane-side');
    paneSide?.addEventListener('click', () => setTimeout(onChatChange, 350));

    document.addEventListener('click', (e) => {
      const t = e.target;
      if (t?.closest?.('#main header') || t?.closest?.('[data-testid="drawer-right"]')) {
        setTimeout(onChatChange, 200);
      }
    }, true);

    function onContactPanelUpdate() {
      if (extensionDead || !runtimeAlive()) return;
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(async () => {
        createPanel();
        updateLayout();
        await resolveAndFetch(false);
      }, 180);
    }

    drawerObserver = new MutationObserver((mutations) => {
      if (extensionDead) return;
      for (const m of mutations) {
        const nodes = [...m.addedNodes, ...(m.type === 'characterData' ? [m.target] : [])];
        if (nodes.some((n) => n.nodeType === 1 && (
          n.matches?.('[data-testid="drawer-right"]') ||
          n.closest?.('[data-testid="drawer-right"]') ||
          n.querySelector?.('[data-testid="drawer-right"]')
        ))) {
          onContactPanelUpdate();
          break;
        }
      }
    });
    drawerObserver.observe(document.body, { childList: true, subtree: true, characterData: true });

    const targets = [document.querySelector('#main'), document.querySelector('#pane-side'), document.body].filter(Boolean);
    chatObserver = new MutationObserver(onChatChange);
    targets.forEach((t) => chatObserver.observe(t, { childList: true, subtree: true, attributes: true }));

    window.addEventListener('popstate', onChatChange);
    onChatChange();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', observeChat);
  } else {
    observeChat();
  }
})();
