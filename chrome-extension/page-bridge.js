(function () {
  function readActiveUser() {
    try {
      if (window.Store && window.Store.Chat && typeof window.Store.Chat.getActive === 'function') {
        var chat = window.Store.Chat.getActive();
        if (chat && chat.id) {
          return chat.id.user || chat.id._serialized;
        }
      }
    } catch (e1) { /* ignore */ }

    try {
      if (typeof window.require === 'function') {
        var Chat = window.require('WAWebCollections').Chat;
        var models = Chat && (Chat._models || Chat.models);
        if (models) {
          for (var i = 0; i < models.length; i++) {
            if (models[i].active && models[i].id) {
              return models[i].id.user;
            }
          }
        }
      }
    } catch (e2) { /* ignore */ }

    return null;
  }

  function emit(user) {
    if (user && String(user).indexOf('@') > -1) {
      user = String(user).split('@')[0];
    }
    document.dispatchEvent(new CustomEvent('karams-wa-phone', { detail: user }));
  }

  function attempt(retry) {
    var user = readActiveUser();
    if (user) {
      emit(user);
      return;
    }
    if (retry < 4) {
      setTimeout(function () { attempt(retry + 1); }, 120 * (retry + 1));
      return;
    }
    emit(null);
  }

  try {
    attempt(0);
  } catch (err) {
    emit(null);
  }
})();
