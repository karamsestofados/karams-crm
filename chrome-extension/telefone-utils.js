/**
 * Normalização de telefone BR — espelha extension/services/telefone.py
 */
(function (global) {
  'use strict';

  function onlyDigits(val) {
    return String(val || '').replace(/\D/g, '');
  }

  function removerDdi(digitos) {
    if (digitos.startsWith('55') && digitos.length >= 12) return digitos.slice(2);
    return digitos;
  }

  function inserirNonoDigito(local) {
    if (local.length !== 10) return null;
    const ddd = local.slice(0, 2);
    const resto = local.slice(2);
    if (resto.length === 8 && resto[0] === '9') return `${ddd}9${resto}`;
    return null;
  }

  function removerNonoDigito(local) {
    if (local.length !== 11) return null;
    const ddd = local.slice(0, 2);
    const resto = local.slice(2);
    if (resto.length === 9 && resto[0] === '9') return `${ddd}${resto.slice(1)}`;
    return null;
  }

  function variantesTelefone(valor) {
    const digitos = onlyDigits(valor);
    if (!digitos) return [];

    const out = new Set();
    const local = removerDdi(digitos);

    if (local.length >= 11) out.add(local.slice(-11));
    if (local.length >= 10) out.add(local.slice(-10));
    out.add(digitos);

    const comNono = inserirNonoDigito(local);
    if (comNono) {
      out.add(comNono);
      out.add('55' + comNono);
    }

    const semNono = removerNonoDigito(local);
    if (semNono) {
      out.add(semNono);
      out.add('55' + semNono);
    }

    return [...out].filter((v) => v.length >= 10);
  }

  /** Formato preferido para enviar à API (DDI + 11 dígitos locais quando possível). */
  function canonicalizarTelefone(valor) {
    const variantes = variantesTelefone(valor);
    if (!variantes.length) return onlyDigits(valor);

    const com11 = variantes.find((v) => removerDdi(v).length === 11);
    if (com11) {
      const local = removerDdi(com11);
      return local.length === 11 ? '55' + local : com11;
    }

    const com10 = variantes.find((v) => removerDdi(v).length === 10);
    if (com10) {
      const local = removerDdi(com10);
      const comNono = inserirNonoDigito(local);
      if (comNono) return '55' + comNono;
      return '55' + local;
    }

    return variantes.sort((a, b) => b.length - a.length)[0];
  }

  global.KaramsTelefone = {
    onlyDigits,
    variantesTelefone,
    canonicalizarTelefone,
  };
})(typeof window !== 'undefined' ? window : self);
