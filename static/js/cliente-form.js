(function () {
  function digitsOnly(value) {
    return value.replace(/\D/g, '');
  }

  function maskCep(input) {
    input.addEventListener('input', function () {
      var d = digitsOnly(input.value).slice(0, 8);
      if (d.length <= 5) {
        input.value = d;
      } else {
        input.value = d.slice(0, 5) + '-' + d.slice(5);
      }
    });
  }

  function maskTelefone(input) {
    input.addEventListener('input', function () {
      var d = digitsOnly(input.value).slice(0, 11);
      if (d.length === 0) {
        input.value = '';
      } else if (d.length <= 2) {
        input.value = '(' + d;
      } else if (d.length <= 6) {
        input.value = '(' + d.slice(0, 2) + ') ' + d.slice(2);
      } else if (d.length <= 10) {
        input.value = '(' + d.slice(0, 2) + ') ' + d.slice(2, 6) + '-' + d.slice(6);
      } else {
        input.value = '(' + d.slice(0, 2) + ') ' + d.slice(2, 7) + '-' + d.slice(7);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-mask="cep"]').forEach(maskCep);
    document.querySelectorAll('[data-mask="telefone"]').forEach(maskTelefone);

    var statusFunil = document.querySelector('[name="status_funil"]');
    var grpMotivo = document.getElementById('motivo-perda-cliente-group');
    var grpDetalhe = document.getElementById('motivo-perda-detalhe-cliente-group');
    if (statusFunil && grpMotivo) {
      function toggleMotivo() {
        var show = statusFunil.value === 'CLIENTE_PERDIDO';
        grpMotivo.style.display = show ? '' : 'none';
        if (grpDetalhe) grpDetalhe.style.display = show ? '' : 'none';
      }
      statusFunil.addEventListener('change', toggleMotivo);
      toggleMotivo();
    }
  });
})();
