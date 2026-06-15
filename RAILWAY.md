# Deploy Railway — CRM Karams

## 1. Repositório GitHub

Código: https://github.com/karamsestofados/karams-crm

## 2. Criar projeto no Railway

1. Acesse [railway.app/new](https://railway.app/new)
2. **Deploy from GitHub repo** → selecione `karamsestofados/karams-crm`
3. Nomeie o projeto: **CRM Karams**

## 3. Adicionar PostgreSQL

1. No projeto Railway → **+ New** → **Database** → **PostgreSQL**
2. O plugin injeta `DATABASE_URL` automaticamente no serviço web

## 4. Variáveis de ambiente (serviço web)

| Variável | Valor |
|----------|-------|
| `DJANGO_SETTINGS_MODULE` | `karams_crm.settings.production` |
| `SECRET_KEY` | gere uma chave aleatória (50+ chars) |
| `DEBUG` | `False` |

`DATABASE_URL`, `RAILWAY_PUBLIC_DOMAIN` e `PORT` são definidos pelo Railway.

Gerar SECRET_KEY localmente:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 5. Deploy

O Railway usa o `Procfile`:

```
release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn karams_crm.wsgi --log-file -
```

Após o deploy bem-sucedido, abra a URL pública (`*.railway.app`).

## 6. Pós-deploy (Railway Shell)

```bash
python manage.py seed_usuarios
python manage.py import_legacy_html
```

Credenciais demo: `admin` / `admin123`

## 7. Domínio customizado (opcional)

Settings → Networking → Generate Domain ou Custom Domain.
O `RAILWAY_PUBLIC_DOMAIN` é detectado automaticamente em `production.py`.
