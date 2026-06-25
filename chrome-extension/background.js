const CACHE_TTL_MS = 60 * 1000;
const cache = new Map();

async function getConfig() {
  return chrome.storage.sync.get({
    crmUrl: 'https://crm-karams.up.railway.app',
    apiToken: '',
  });
}

function cacheKey(crmUrl, telefone) {
  return `${crmUrl}|${telefone}`;
}

async function fetchContexto(telefone) {
  const { crmUrl, apiToken } = await getConfig();
  if (!apiToken) {
    return { erro: 'Configure o token em Opções da extensão.' };
  }
  if (!telefone) {
    return { erro: 'Número não detectado.' };
  }

  const key = cacheKey(crmUrl, telefone);
  const hit = cache.get(key);
  if (hit && Date.now() - hit.ts < CACHE_TTL_MS) {
    return hit.data;
  }

  const base = crmUrl.replace(/\/$/, '');
  const url = `${base}/api/v1/extension/contexto/?telefone=${encodeURIComponent(telefone)}`;

  try {
    const resp = await fetch(url, {
      headers: { Authorization: `Bearer ${apiToken}` },
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      return { erro: data.erro || 'Erro ao consultar CRM.', status: resp.status };
    }
    if (data.encontrado) {
      cache.set(key, { ts: Date.now(), data });
    }
    return data;
  } catch (err) {
    return { erro: 'Falha de conexão com o CRM.' };
  }
}

async function testConnection() {
  const { crmUrl, apiToken } = await getConfig();
  if (!apiToken) {
    return { ok: false, mensagem: 'Informe o token.' };
  }
  const base = crmUrl.replace(/\/$/, '');
  try {
    const resp = await fetch(`${base}/api/v1/extension/me/`, {
      headers: { Authorization: `Bearer ${apiToken}` },
    });
    const data = await resp.json();
    if (!resp.ok) {
      return { ok: false, mensagem: data.erro || 'Token inválido.' };
    }
    return { ok: true, mensagem: `Conectado como ${data.nome || data.username}.` };
  } catch {
    return { ok: false, mensagem: 'Não foi possível conectar ao CRM.' };
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === 'FETCH_CONTEXTO') {
    fetchContexto(msg.telefone).then(sendResponse);
    return true;
  }
  if (msg.type === 'TEST_CONNECTION') {
    testConnection().then(sendResponse);
    return true;
  }
  return false;
});
