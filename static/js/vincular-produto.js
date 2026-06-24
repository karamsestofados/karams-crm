function fecharModalVinculoProduto() {
  var modal = document.getElementById('modal-vinculo-produto');
  if (modal) modal.classList.remove('open');
}

function submeterVinculoProduto(form) {
  if (typeof htmx !== 'undefined') {
    htmx.trigger(form, 'submit');
  } else {
    form.requestSubmit();
  }
}

function initVincularProdutoForm(form) {
  if (!form || form.dataset.vinculoInit === '1') return;
  form.dataset.vinculoInit = '1';

  form.addEventListener('submit', function (event) {
    if (form.dataset.confirmed === '1') {
      form.dataset.confirmed = '0';
      return;
    }

    event.preventDefault();
    var produtoSelect = form.querySelector('[name="produto"]');
    if (!produtoSelect || !produtoSelect.value) return;

    var avisoUrl = form.dataset.avisoUrl;
    if (!avisoUrl) {
      submeterVinculoProduto(form);
      return;
    }

    fetch(avisoUrl + '?produto=' + encodeURIComponent(produtoSelect.value) + '&format=json')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var alerta = data.alerta;
        if (!alerta) {
          submeterVinculoProduto(form);
          return;
        }
        abrirModalVinculoProduto(alerta, form);
      })
      .catch(function () {
        submeterVinculoProduto(form);
      });
  });
}

function abrirModalVinculoProduto(alerta, form) {
  var modal = document.getElementById('modal-vinculo-produto');
  var panel = document.getElementById('modal-vinculo-produto-panel');
  var titulo = document.getElementById('modal-vinculo-titulo');
  var conteudo = document.getElementById('modal-vinculo-conteudo');
  var acoes = document.getElementById('modal-vinculo-acoes');
  if (!modal || !panel || !conteudo || !acoes) return;

  panel.classList.remove('modal-vinculo-exclusivo', 'modal-vinculo-unico');
  var clientes = (alerta.clientes || []).join(', ');
  var bloquear = !!alerta.bloquear;

  if (bloquear) {
    panel.classList.add('modal-vinculo-unico');
    titulo.textContent = 'Produto Único — vínculo bloqueado';
    conteudo.innerHTML =
      '<p class="modal-vinculo-texto"><strong>' + escapeHtml(alerta.produto_nome) + '</strong> já está vinculado a <strong>' +
      escapeHtml(clientes) + '</strong>. Apenas um cliente pode possuir este produto.</p>' +
      '<p class="modal-vinculo-hint">Remova o vínculo no cliente atual antes de vincular a outro.</p>';
    acoes.innerHTML = '<button type="button" class="btn btn-secondary" onclick="fecharModalVinculoProduto()">Entendi</button>';
  } else {
    panel.classList.add('modal-vinculo-exclusivo');
    titulo.textContent = 'Produto Exclusivo';
    conteudo.innerHTML =
      '<p class="modal-vinculo-texto"><strong>' + escapeHtml(alerta.produto_nome) + '</strong> (Exclusivo) já está vinculado a: <strong>' +
      escapeHtml(clientes) + '</strong>.</p>' +
      '<p class="modal-vinculo-hint">Deseja vincular mesmo assim a este cliente?</p>';
    acoes.innerHTML =
      '<button type="button" class="btn btn-secondary" onclick="fecharModalVinculoProduto()">Cancelar</button>' +
      '<button type="button" class="btn btn-primary" id="modal-vinculo-confirmar">Confirmar vínculo</button>';
    document.getElementById('modal-vinculo-confirmar').onclick = function () {
      fecharModalVinculoProduto();
      form.dataset.confirmed = '1';
      submeterVinculoProduto(form);
    };
  }

  modal.classList.add('open');
}

function escapeHtml(text) {
  var div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', function () {
  var form = document.getElementById('vincular-produto-form-el');
  initVincularProdutoForm(form);
});

document.body.addEventListener('htmx:afterSwap', function (event) {
  if (event.target && event.target.id === 'produtos-vinculados') {
    var form = document.getElementById('vincular-produto-form-el');
    if (form) {
      delete form.dataset.vinculoInit;
      initVincularProdutoForm(form);
    }
  }
});
