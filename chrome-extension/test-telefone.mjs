/**
 * Testes de paridade JS — espelham extension/tests/test_telefone_identificacao.py
 * Executar: node chrome-extension/test-telefone.mjs
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = dirname(fileURLToPath(import.meta.url));

global.window = global;
eval(readFileSync(join(dir, 'telefone-utils.js'), 'utf8'));

const {
  variantesTelefone,
  canonicalizarTelefone,
  sufixos8Comparacao,
  telefonesEquivalentes,
} = global.KaramsTelefone;

function equivalentes(a, b) {
  return telefonesEquivalentes(a, b);
}

const casosVerdadeiros = [
  ['+55 44 99988-7766', '(44) 99988-7766'],
  ['44999887766', '5544999887766'],
  ['+55 71 9971-2271', '(71) 99971-2271'],
  ['557199712271', '71999712271'],
  ['(44) 3434-5678', '+55 44 3434-5678'],
  ['44 9 9988-7766', '(44) 99988-7766'],
  ['+554499000-0000', '4499000-0000'],
  ['+55 44 99000-0000', '(44) 99000-0000'],
  ['554499000000', '4499000000'],
];

const casosFalsos = [
  ['7199712271', '7199712272'],
  ['44999887766', '44999887755'],
  ['(44) 99988-7766', '(44) 3434-5678'],
];

let falhas = 0;

for (const [a, b] of casosVerdadeiros) {
  if (!equivalentes(a, b)) {
    console.error(`FALHA (deveria equivaler): ${a} ~ ${b}`);
    falhas += 1;
  }
}

for (const [a, b] of casosFalsos) {
  if (equivalentes(a, b)) {
    console.error(`FALHA (não deveria equivaler): ${a} ~ ${b}`);
    falhas += 1;
  }
}

const canon = canonicalizarTelefone('+55 71 9971-2271');
if (canon !== '5571999712271') {
  console.error(`FALHA canonicalizar: esperado 5571999712271, obteve ${canon}`);
  falhas += 1;
}

const s8a = new Set(sufixos8Comparacao('+554499000-0000'));
const s8b = new Set(sufixos8Comparacao('4499000-0000'));
const inter = [...s8a].filter((s) => s8b.has(s));
if (!inter.length) {
  console.error('FALHA sufixos8: +554499000-0000 e 4499000-0000 deveriam compartilhar sufixo');
  falhas += 1;
}

if (falhas) {
  console.error(`\n${falhas} falha(s).`);
  process.exit(1);
}

console.log(`OK — ${casosVerdadeiros.length + casosFalsos.length + 2} asserções de telefone.`);
