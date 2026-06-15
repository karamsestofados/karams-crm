# Deploy Railway — CRM Karams

## 1. Repositório GitHub

Código: https://github.com/karamsestofados/karams-crm

## 2. Criar projeto no Railway

1. Acesse [railway.app/new](https://railway.app/new)
2. **Deploy from GitHub repo** → selecione `karamsestofados/karams-crm`
3. Nomeie o projeto: **CRM Karams**

## 3. Adicionar PostgreSQL

1. No projeto Railway → **+ New** → **Database** → **PostgreSQL**
2. Conecte `DATABASE_URL` do Postgres ao serviço **web** (Add Variable → Postgres)

## 4. Variáveis de ambiente (serviço web)

| Variável | Valor |
|----------|-------|
| `DJANGO_SETTINGS_MODULE` | `karams_crm.settings.production` |
| `SECRET_KEY` | string aleatória com 50+ caracteres |
| `DEBUG` | `False` |

`DATABASE_URL`, `RAILWAY_PUBLIC_DOMAIN` e `PORT` são definidos pelo Railway.

Gerar SECRET_KEY localmente:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 5. Deploy

O `Procfile` executa migrations e collectstatic no release:

```
release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn karams_crm.wsgi --log-file -
```

## 6. Primeiro acesso (configuração inicial)

Após o deploy, abra a URL pública (`*.railway.app`).

Na **primeira visita**, o sistema redireciona para **Configuração inicial**, onde você:

1. Define o **usuário administrador** e a **senha** manualmente
2. Informa nome, e-mail e **metas da equipe** do mês

Depois disso, faça login normalmente. Essa tela só aparece enquanto não existir administrador no banco.

## 7. Dados opcionais (Railway Shell)

```bash
# Vendedor demo para importação de clientes legados
python manage.py seed_usuarios

# Importar clientes do HTML legado (requer vendedor demo)
python manage.py import_legacy_html
```

> **Produção:** não use `seed_usuarios --com-admin`. O admin deve ser criado apenas pela configuração inicial no navegador.

## 8. Domínio customizado (opcional)

Settings → Networking → Generate Domain ou Custom Domain.
O `RAILWAY_PUBLIC_DOMAIN` é detectado automaticamente em `production.py`.
