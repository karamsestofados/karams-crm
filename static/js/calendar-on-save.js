(function () {
  var PROXIMAS_ACOES_CALENDAR = new Set([
    'LIGAR',
    'ENVIAR_CATALOGO',
    'ENVIAR_PROPOSTA',
    'AGENDAR_VISITA',
    'ENVIAR_WHATSAPP',
    'ENVIAR_EMAIL',
  ]);

  var RESULTADOS_BLOQUEIAM_CALENDAR = new Set([
    'SEM_INTERESSE',
    'PEDIDO_FECHADO',
  ]);

  function formShouldOpenCalendar(form) {
    var proxima = form.querySelector('[name="proxima_acao"]');
    var data = form.querySelector('[name="data_proxima_acao"]');
    var resultado = form.querySelector('[name="resultado"]');
    if (!proxima || !data) return false;

    var acao = (proxima.value || '').trim();
    if (!acao || acao === 'SEM_ACAO') return false;
    if (!PROXIMAS_ACOES_CALENDAR.has(acao)) return false;
    if (!(data.value || '').trim()) return false;

    var res = resultado ? (resultado.value || '').trim() : '';
    if (res && RESULTADOS_BLOQUEIAM_CALENDAR.has(res)) return false;

    return true;
  }

  function isCalendarForm(elt) {
    return elt && elt.closest && elt.closest('form[data-google-calendar-on-save]');
  }

  function isCalendarRequest(elt) {
    return pendingCalendarTab !== null || isCalendarForm(elt);
  }

  var pendingCalendarTab = null;
  var toastEl = document.getElementById('calendar-toast');
  var toastTimer = null;

  function parseCalendarUrl(triggerHeader) {
    if (!triggerHeader) return null;
    try {
      var payload = JSON.parse(triggerHeader);
      return payload.openGoogleCalendar || null;
    } catch (e) {
      return null;
    }
  }

  function showCalendarToast(message) {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.hidden = false;
    toastEl.classList.add('calendar-toast--visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toastEl.classList.remove('calendar-toast--visible');
      toastEl.hidden = true;
    }, 4000);
  }

  function scrollToCalendarFallback() {
    var banner = document.querySelector('.calendar-cta-banner');
    if (banner) {
      banner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      return;
    }
    var resumo = document.getElementById('cockpit-resumo');
    if (resumo) {
      resumo.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function openCalendarUrl(url) {
    if (!url) return false;
    if (pendingCalendarTab && !pendingCalendarTab.closed) {
      pendingCalendarTab.location.href = url;
      showCalendarToast('Abrindo Google Agenda em nova guia…');
      return true;
    }
    var fallbackTab = window.open(url, '_blank');
    if (fallbackTab) {
      showCalendarToast('Abrindo Google Agenda em nova guia…');
      return true;
    }
    showCalendarToast('Use o botão "Salvar no Google Agenda" abaixo.');
    scrollToCalendarFallback();
    return false;
  }

  function closePendingTab() {
    if (pendingCalendarTab && !pendingCalendarTab.closed) {
      pendingCalendarTab.close();
    }
    pendingCalendarTab = null;
  }

  function openCalendarFromCockpit(target) {
    if (!target) return;
    var marker = target.querySelector('#karams-open-calendar-url');
    if (marker && marker.dataset.calendarUrl) {
      openCalendarUrl(marker.dataset.calendarUrl);
    }
  }

  document.body.addEventListener('submit', function (evt) {
    var form = evt.target.closest('form[data-google-calendar-on-save]');
    if (!form || !formShouldOpenCalendar(form)) return;
    pendingCalendarTab = window.open('about:blank', '_blank');
  }, true);

  document.body.addEventListener('htmx:afterRequest', function (evt) {
    if (!isCalendarRequest(evt.detail.elt)) return;

    var xhr = evt.detail.xhr;
    var url = parseCalendarUrl(xhr.getResponseHeader('HX-Trigger'));

    if (url && evt.detail.successful) {
      openCalendarUrl(url);
    } else {
      closePendingTab();
    }
    pendingCalendarTab = null;
  });

  document.body.addEventListener('openGoogleCalendar', function (evt) {
    if (evt.detail && evt.detail.value) {
      openCalendarUrl(evt.detail.value);
    }
  });

  document.body.addEventListener('htmx:oobAfterSwap', function (evt) {
    var target = evt.detail.target;
    if (target.id === 'cockpit-main') {
      openCalendarFromCockpit(target);
      return;
    }
    if (target.id !== 'calendar-toast') return;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      var el = document.getElementById('calendar-toast');
      if (!el) return;
      el.classList.remove('calendar-toast--visible');
      el.hidden = true;
    }, 4000);
  });

  window.KaramsCalendarOnSave = {
    formShouldOpenCalendar: formShouldOpenCalendar,
  };
})();
