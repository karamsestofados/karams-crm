# Karams CRM 2.0

CRM multiusuário para a Karams Estofados — reconstrução do sistema legado (HTML + localStorage) em Django 5 + PostgreSQL.

## Stack

- Django 5.x + Python 3.12+
- PostgreSQL (Railway)
- Tailwind-compatible CSS customizado (paleta Karams)
- HTMX + Alpine.js (interatividade nas fases seguintes)
- Gunicorn + Whitenoise

## Identidade visual

- **Fundo:** branco (`#FFFFFF`)
- **Cor principal:** laranja Karams `#FF9220` (header, nav, botões, KPIs)
- **Logo:** oficial em `static/img/` (preta no login, branca no header)
- **Fontes:** Playfair Display (títulos) + DM Sans (UI)

## GitHub

Repositório: **https://github.com/karamsestofados/karams-crm**

```bash
git clone https://github.com/karamsestofados/karams-crm.git
cd karams-crm
```

## Desenvolvimento local

```bash
# Criar ambiente virtual (opcional)
python -m venv venv
venv\Scripts\activate        # Windows

# Instalar dependências
pip install -r requirements.txt

# Copiar variáveis de ambiente
copy .env.example .env

# Migrar banco
python manage.py migrate

# Criar usuários demo (admin + vendedor)
python manage.py seed_usuarios

# Importar clientes do HTML legado
python manage.py import_legacy_html

# Rodar servidor
python manage.py runserver
```

**Credenciais demo:**
- Admin: `admin` / `admin123`
- Vendedor: `vendedor` / `vendedor123`

## Deploy no Railway — projeto "CRM Karams"

### 1. Repositório GitHub

O código está em [github.com/karamsestofados/karams-crm](https://github.com/karamsestofados/karams-crm).

Para clonar em outra máquina:

```bash
git clone https://github.com/karamsestofados/karams-crm.git
```

### 2. Conectar ao Railway

1. Acesse [railway.app](https://railway.app) e crie um novo projeto chamado **CRM Karams**
2. Conecte o repositório GitHub
3. Adicione o plugin **PostgreSQL** (Railway injeta `DATABASE_URL` automaticamente)

### 3. Variáveis de ambiente

| Variável | Valor |
|----------|-------|
| `DJANGO_SETTINGS_MODULE` | `karams_crm.settings.production` |
| `SECRET_KEY` | string aleatória com 50+ caracteres |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `*.railway.app` |
| `CSRF_TRUSTED_ORIGINS` | `https://*.railway.app` |

### 4. Deploy

O `Procfile` executa migrations e collectstatic automaticamente no release:

```
release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn karams_crm.wsgi --log-file -
```

### 5. Pós-deploy

No shell do Railway:

```bash
python manage.py seed_usuarios
python manage.py import_legacy_html
```

Ou crie superusuário manualmente:

```bash
python manage.py createsuperuser
```

## Estrutura de apps

| App | Responsabilidade |
|-----|------------------|
| `core` | Dashboard, backup log, configurações globais |
| `accounts` | Usuários, papéis (admin/vendedor), perfil |
| `clientes` | Cliente, Produto, Histórico de interações |
| `atividades` | Registros diários de contato |
| `calendario` | Notas de relacionamento, alertas de retorno |
| `comissoes` | Vendas, metas mensais |
| `relatorios` | Exportações (Fase 5) |

## Importação de dados

### HTML legado (Fase 1)

```bash
python scripts/extract_seed_data.py   # gera JSON do HTML
python manage.py import_legacy_html   # importa para o banco
```

### Excel completo (Fase 2)

Comando `import_excel` será adicionado quando o arquivo `CLIENTES_E_PRODUTOS.xlsx` estiver disponível.

## Roadmap

- [x] **Fase 1** — Base: modelos, auth, admin, deploy Railway
- [ ] **Fase 2** — CRM de clientes (lista, ficha 360°, filtros HTMX)
- [ ] **Fase 3** — Dashboard de atividade diária + gráficos
- [ ] **Fase 4** — Calendário de relacionamento
- [ ] **Fase 5** — Comissões e relatórios (Excel/PDF)
- [ ] **Fase 6** — Backup/restore e polish UI

## Referência legada

O arquivo [`karams crm (8).html`](karams%20crm%20(8).html) permanece no repositório como referência de UX e dados seed.
