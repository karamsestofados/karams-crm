# Health Check — Karams CRM

**Data:** 16/06/2026  
**Ambiente auditado:** código local + checklist para produção Railway  
**Branch:** `main`

---

## 1. Funcionalidades OK

| Menu | Rota | Status |
|------|------|--------|
| Dashboard | `/` (`core:dashboard`) | OK — KPIs, Meu Desempenho, gráficos Chart.js, ranking admin |
| Clientes | `/clientes/` | OK — CRUD, filtros HTMX, carteira por vendedor |
| Produtos | `/produtos/` | OK — CRUD, tipos, vínculos |
| Atividade Diária | `/atividade-diaria/` | OK — Cockpit, meta do dia, follow-ups |
| Relacionamento | `/relacionamento/relatorio/` | OK — Filtros, ranking |
| Relatórios | `/relatorios/produtividade/` | OK — Filtros, conversão, sem contato 30d |
| Meu perfil | `/accounts/perfil/` | OK — Conquistas, senha, backup admin |
| Usuários | `/accounts/usuarios/` | OK (admin) — CRUD, reset senha |
| Metas Comerciais | `/comissoes/metas/` | OK (pós-correção) — listagem, filtros, CRUD, desativar/ativar |
| Admin Django | `/admin/` | OK (admin) — vendedor bloqueado via middleware |

---

## 2. Funcionalidades com problemas / pendências

| Item | Severidade | Descrição |
|------|------------|-----------|
| Comissões (menu sidebar) | Baixa | Não implementado — link `href="#"` com classe `soon` e tooltip "Em breve" |
| Dashboard busca global | Baixa | Input desabilitado — placeholder "Disponível na Fase 2" |
| Exclusão de meta | Baixa | Apenas desativar/ativar; sem delete permanente (decisão de produto) |
| Logo `logo-karams-white.png` | Média | Arquivo ausente no repositório anteriormente; placeholder adicionado na auditoria |

---

## 3. Correções aplicadas nesta auditoria

### Metas Comerciais (HTTP 500)

- **Causa raiz:** template acessava `meta.vendedor.get_full_name` quando `vendedor=None` (meta de equipe) → `AttributeError`.
- **Correção:** bloco condicional em `templates/comissoes/metas_lista.html`.
- **Extras:** filtros GET (mês, ano, vendedor, status); validação `unique_together` no form; exibição de erros no formulário.

### Identidade do navegador

- Título fixo **Karams CRM** em `templates/base.html` (sem sufixo por página).
- Favicon: `static/img/favicon.ico`, `favicon.svg`, `apple-touch-icon.png`.
- Admin: `templates/admin/base_site.html` com título e favicon.

### UX e erros

- Estados vazios padronizados: **"Nenhum registro encontrado."** (usuários, produtos, dashboard, metas).
- Página amigável `templates/500.html` + `handler500` em `karams_crm/urls.py`.

### Testes automatizados

- `accounts/tests/test_permissions.py` — smoke de permissões admin/vendedor.
- `comissoes/tests/test_metas.py` — listagem meta equipe, filtros, duplicata rejeitada.

---

## 4. Erros encontrados

| Erro | Causa | Severidade | Status |
|------|-------|------------|--------|
| HTTP 500 em `/comissoes/metas/` | `vendedor=None` no template | **Alta** | Corrigido |
| Migration `comissoes.0002` não aplicada (Railway) | Deploy anterior sem migrate | **Alta** | Verificar pós-deploy (`showmigrations`) |
| Manifest staticfiles em testes | `CompressedManifestStaticFilesStorage` sem `collectstatic` | Média | Rodar `collectstatic` antes de testes em CI |
| Logo ausente no repo | `static/img/logo-karams-white.png` nunca versionado | Média | Placeholder adicionado |

---

## 5. Verificações executadas

```bash
python manage.py check                    # OK — 0 issues
python manage.py showmigrations --plan    # Todas [X], incluindo comissoes.0002
python manage.py makemigrations --check  # No changes detected
python manage.py test accounts.tests.test_permissions comissoes.tests.test_metas  # 13 OK
python manage.py collectstatic --noinput  # OK
```

### Matriz de permissões (testada)

| URL | Admin | Vendedor |
|-----|-------|----------|
| `/accounts/usuarios/` | 200 | 403 |
| `/comissoes/metas/` | 200 | 403 |
| `/admin/` | 200 | 403 |
| `/clientes/?id={outro}` | 200 | 403 |
| `/relatorios/produtividade/` | 200 | 200 |

---

## 6. Sugestões técnicas

1. **CI/CD:** rodar `collectstatic`, `check`, `makemigrations --check` e suite de testes no GitHub Actions antes do deploy.
2. **Monitoring Railway:** alertas em logs para HTTP 5xx e falhas de migrate no release.
3. **Comissões (Fase 5):** implementar módulo ou ocultar item do menu até estar pronto.
4. **Delete de meta:** avaliar soft-delete vs. exclusão permanente com confirmação.
5. **Logo oficial:** substituir placeholder `logo-karams-white.png` pelo asset de marca definitivo.
6. **Test settings:** considerar `STATICFILES_STORAGE` simples em testes para não depender de manifest.

---

## 7. Deploy Railway

**Procfile release:** `migrate` → `preparar_senha_admin` → `collectstatic`

**Pós-deploy (checklist manual):**

- [ ] Acessar `/comissoes/metas/` como admin — listagem sem 500
- [ ] Confirmar meta "Equipe" visível
- [ ] Criar/editar/desativar meta
- [ ] Favicon e título "Karams CRM" na aba
- [ ] Vendedor recebe 403 em metas e usuários
- [ ] `python manage.py showmigrations comissoes` no shell Railway — `0002` aplicada
