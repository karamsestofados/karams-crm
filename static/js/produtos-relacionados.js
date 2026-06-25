document.addEventListener('alpine:init', function () {
  Alpine.data('produtosRelacionadosField', function () {
    return {
      buscaUrl: '',
      selecionados: [],
      resultados: [],
      busca: '',
      aberto: false,
      buscando: false,
      buscou: false,
      fieldName: 'produtos_relacionados',
      debounceTimer: null,

      init() {
        this.buscaUrl = this.$el.dataset.buscaUrl || '';
        this.fieldName = this.$el.dataset.fieldName || 'produtos_relacionados';
        var configId = this.$el.dataset.configId;
        if (configId) {
          var configEl = document.getElementById(configId);
          if (configEl) {
            try {
              this.selecionados = JSON.parse(configEl.textContent || '[]');
            } catch (e) {
              this.selecionados = [];
            }
          }
        }
        this.selecionados = (this.selecionados || []).map(function (item) {
          return {
            id: String(item.id),
            nome: item.nome,
            tipo_produto: item.tipo_produto || '',
          };
        });
      },

      idsSelecionados() {
        return this.selecionados.map(function (item) { return String(item.id); });
      },

      async buscar() {
        var termo = this.busca.trim();
        if (termo.length < 2) {
          this.resultados = [];
          this.aberto = false;
          this.buscou = false;
          return;
        }
        this.buscando = true;
        try {
          var res = await fetch(this.buscaUrl + '?q=' + encodeURIComponent(termo));
          var data = await res.json();
          var ids = this.idsSelecionados();
          this.resultados = data.filter(function (item) {
            return ids.indexOf(String(item.id)) === -1;
          });
          this.buscou = true;
          this.aberto = true;
        } finally {
          this.buscando = false;
        }
      },

      onInput() {
        var self = this;
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(function () {
          self.buscar();
        }, 300);
      },

      adicionar(item) {
        var self = this;
        var sid = String(item.id);
        if (this.idsSelecionados().indexOf(sid) !== -1) return;
        this.selecionados.push({
          id: sid,
          nome: item.nome,
          tipo_produto: item.tipo_produto || '',
        });
        this.busca = '';
        this.resultados = [];
        this.buscou = false;
        this.aberto = false;
        this.$nextTick(function () {
          if (self.$refs.busca) self.$refs.busca.focus();
        });
      },

      remover(id) {
        var sid = String(id);
        this.selecionados = this.selecionados.filter(function (item) {
          return String(item.id) !== sid;
        });
      },

      removerUltimoSeNecessario() {
        if (this.busca === '' && this.selecionados.length) {
          this.selecionados.pop();
        }
      },

      fechar() {
        this.aberto = false;
      },
    };
  });
});

document.body.addEventListener('htmx:afterSwap', function (evt) {
  var target = evt.detail.target;
  if (typeof Alpine === 'undefined' || !target) return;
  if (target.hasAttribute('x-data') || target.querySelector('[x-data]')) {
    Alpine.initTree(target);
  }
});
