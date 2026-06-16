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
- **Fontes:** Sora (títulos) + Inter (UI)

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

# Primeiro acesso: abra http://127.0.0.1:8000/ e conclua a configuração inicial
# (usuário admin + senha definidos manualmente)

# Opcional — vendedor demo + import legado
python manage.py seed_usuarios
python manage.py import_legacy_html

# Rodar servidor
python manage.py runserver
```

**Desenvolvimento local (opcional):** para pular a configuração inicial e usar admin demo:

```bash
python manage.py seed_usuarios --com-admin
```

Credenciais demo com `--com-admin`: `admin` / `admin123` · vendedor: `vendedor` / `vendedor123`

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
release: python manage.py migrate && python manage.py preparar_senha_admin && python manage.py collectstatic --noinput
web: gunicorn karams_crm.wsgi --log-file -
```

### 5. Primeiro acesso

A cada deploy, o comando `preparar_senha_admin` invalida a senha do usuário `admin`.

Abra a URL do Railway — em vez do login, aparece a tela **Senha** + **Confirmar senha**. Após salvar, você entra direto no CRM.

Login normal depois: usuário `admin` + senha definida por você.

```bash
python manage.py seed_usuarios
python manage.py import_legacy_html
```

O comando `seed_usuarios` cria apenas o vendedor demo. **Não** cria admin em produção.

## Estrutura de apps

| App | Responsabilidade |
|-----|------------------|
| `core` | Dashboard, backup log, configurações globais |
| `accounts` | Usuários, papéis (admin/vendedor), perfil |
| `clientes` | Cliente, Produto, vínculos comerciais |
| `relacionamento` | AtividadeCliente — hub central de interações comerciais |
| `atividades` | Registros diários de contato (legado, admin only) |
| `calendario` | Notas de relacionamento, alertas de retorno (legado, admin only) |
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

## Módulo de Produtos

O CRM trata produtos como base para exclusividades comerciais, não apenas catálogo.

- **Tipos:** Padrão (qualquer cliente), Exclusivo (vários clientes com vínculo manual), Único (máximo 1 cliente)
- **Vínculos:** tabela `ClienteProduto` com data de início e observações
- **Exclusividade territorial:** model `ProdutoExclusividade` preparado para alertas de renovação

### Extensões futuras (arquitetura preparada)

- Rotina diária por produto (`Produto` + `ClienteProduto`)
- Follow-up e campanhas comerciais (`ProdutoExclusividade`, datas de vigência)
- Histórico de vendas por produto (`comissoes.Venda.produtos` já vinculado)
- Comissões por produto
- Dashboard: produtos exclusivos/únicos, clientes por produto, produtos sem cliente (`ProdutoQuerySet.sem_cliente()`)

## Relacionamento Comercial

O app `relacionamento` centraliza todas as interações comerciais via model `AtividadeCliente`.

### Funcionalidades

- **Aba Relacionamento** no painel do cliente: resumo comercial, timeline e registro de interações (HTMX)
- **Atividade Diária** (`/atividade-diaria/`): fila Hoje / Atrasadas / Próximas derivada de follow-ups pendentes
- **Concluir follow-up:** marca a pendência como concluída e registra nova interação
- **Dashboard:** KPIs reais (contatos hoje, interações na semana, clientes sem contato 30+ dias, negociações, fechamentos)
- **Relatório** (`/relacionamento/relatorio/`): filtros por período/vendedor/cliente/produto/tipo e ranking de vendedores

### Model AtividadeCliente

Campos principais: tipo de contato, resumo, resultado, humor do cliente, produto relacionado, próxima ação + data. Soft delete via `deleted_at`.

### Migração de dados legados

A migration `relacionamento.0001_initial` migra automaticamente:

- `HistoricoInteracao` → atividades concluídas (histórico)
- `AlertaRetorno` (não dispensados) → follow-ups pendentes

Models legados permanecem read-only no admin.

## Backup e restauração

Disponível em **Configurações** (somente administradores):

- **Gerar backup** — exporta todo o banco de dados (clientes, produtos, atividades, usuários, etc.) e arquivos de mídia em um arquivo `.karamsbackup.zip` para download
- **Restaurar backup** — substitui todos os dados atuais pelo conteúdo do arquivo (ação irreversível; exige confirmação)

Guarde os arquivos de backup em local seguro fora do servidor para recuperação em emergências.

## Cockpit Comercial

A página **Atividade Diária** (`/atividade-diaria/`) funciona como cockpit de gestão comercial:

- **Resumo do dia** — atividades hoje/atrasadas/futuras, interações e clientes atendidos
- **Ações rápidas** — registrar interação, ligação, WhatsApp, e-mail, visita ou follow-up (modal global)
- **Calendário mensal** — indicadores por status (atrasado/hoje/futuro) com horário opcional
- **Clientes sem contato** — lista de clientes ativos sem interação há 30+ dias
- **Últimas interações** — timeline global cross-client
- **Fila de follow-ups** — cards enriquecidos com ação "Registrar Resultado"

No painel do cliente, a aba **Histórico Comercial** exibe resumo expandido, filtros por tipo de contato e timeline cronológica.

Services reutilizáveis para BI futuro: `relacionamento/services/cockpit.py`, `resumo_cliente.py`, `relatorio.py`.

## Roadmap

- [x] **Fase 1** — Base: modelos, auth, admin, deploy Railway
- [x] **Fase 2** — CRM de clientes (lista, ficha 360°, filtros HTMX)
- [x] **Fase 3** — Atividade diária + dashboard KPIs de relacionamento
- [ ] **Fase 4** — Calendário de relacionamento
- [ ] **Fase 5** — Comissões e relatórios (Excel/PDF)
- [x] **Fase 6** — Backup/restore e polish UI (backup implementado)

## Referência legada

O arquivo [`karams crm (8).html`](karams%20crm%20(8).html) permanece no repositório como referência de UX e dados seed.
