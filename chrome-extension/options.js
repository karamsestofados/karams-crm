const crmUrlEl = document.getElementById('crmUrl');
const apiTokenEl = document.getElementById('apiToken');
const statusEl = document.getElementById('status');

function setStatus(text, ok) {
  statusEl.textContent = text;
  statusEl.className = ok === true ? 'ok' : ok === false ? 'err' : '';
}

chrome.storage.sync.get(
  { crmUrl: 'https://crm-karams.up.railway.app', apiToken: '' },
  (items) => {
    crmUrlEl.value = items.crmUrl;
    apiTokenEl.value = items.apiToken;
  }
);

document.getElementById('save').addEventListener('click', () => {
  chrome.storage.sync.set(
    {
      crmUrl: crmUrlEl.value.trim() || 'https://crm-karams.up.railway.app',
      apiToken: apiTokenEl.value.trim(),
    },
    () => setStatus('Configuração salva.', true)
  );
});

document.getElementById('test').addEventListener('click', () => {
  chrome.storage.sync.set(
    {
      crmUrl: crmUrlEl.value.trim(),
      apiToken: apiTokenEl.value.trim(),
    },
    () => {
      setStatus('Testando…', null);
      chrome.runtime.sendMessage({ type: 'TEST_CONNECTION' }, (resp) => {
        if (chrome.runtime.lastError) {
          setStatus('Erro interno da extensão.', false);
          return;
        }
        setStatus(resp.mensagem, resp.ok);
      });
    }
  );
});
