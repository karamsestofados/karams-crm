# Karams CRM — Extensão WhatsApp Web (piloto interno)

Painel lateral **somente leitura** que identifica clientes pelo telefone no WhatsApp Web e exibe contexto comercial do CRM Karams.

## Pré-requisitos

- Google Chrome (desktop)
- Backend CRM com app `extension` (local ou Railway)
- Token API gerado em **Perfil → Integração WhatsApp** no CRM

## Instalação (modo desenvolvedor)

1. Abra `chrome://extensions/`
2. Ative **Modo do desenvolvedor** (canto superior direito)
3. Clique em **Carregar sem compactação**
4. Selecione a pasta `chrome-extension/` deste repositório
5. Clique com o botão direito no ícone da extensão → **Opções**
6. Informe a URL do CRM e cole o token
7. Clique em **Testar conexão** e depois **Salvar**
8. Acesse [web.whatsapp.com](https://web.whatsapp.com) e abra uma conversa individual

## Testar sem deploy no Railway (CRM local)

Use este fluxo quando a produção ainda não tiver a API da extensão:

```powershell
cd "D:\CRM Comercial"
python manage.py migrate
python manage.py runserver
```

1. Acesse `http://127.0.0.1:8000` e faça login
2. **Perfil → Integração WhatsApp → Gerar token** (copie o valor)
3. Extensão → **Opções** → URL: `http://127.0.0.1:8000` + token → **Testar conexão** → **Salvar**
4. Em `chrome://extensions/`, clique **Atualizar** na extensão Karams
5. Recarregue `web.whatsapp.com` (F5)
6. Abra o chat do cliente; se o nome comercial impedir detecção automática, abra **Dados do contato** ou use o campo **Colar telefone** no painel K

## Uso

- **Detecção automática** ao selecionar conversa na lista (não precisa abrir Dados do contato)
- Botão **⤢ Fixar** no cabeçalho: WhatsApp e painel CRM **lado a lado** na mesma guia (layout dividido)
- Botão **› Recolher**: esconde o painel (modo flutuante)
- Botão **K** na borda: mostrar/ocultar quando não fixado
- **Ver no CRM** abre a ficha do cliente no navegador
- Conversas em **grupo** não são suportadas no MVP

## Mensagens de erro

| Mensagem | Causa | Solução |
|----------|-------|---------|
| Não detectamos o número… | Header mostra nome, não telefone | Abra Dados do contato ou cole o número no painel |
| Configure o token… | Token vazio nas Opções | Gere token no Perfil e salve nas Opções |
| API não encontrada (404) | Backend sem app extension | Use CRM local (`runserver`) ou faça deploy |
| Falha de conexão | CRM offline ou URL errada | Confira URL e se `runserver` está rodando |
| Cliente não cadastrado | Telefone diferente no CRM | Confira DDD e 9º dígito do celular |

## Segurança

- O token é pessoal e revogável no Perfil do CRM
- A extensão **não** lê conteúdo de mensagens
- Distribuição interna — não publicada na Chrome Web Store

## API utilizada

- `GET /api/v1/extension/me/` — validação do token
- `GET /api/v1/extension/contexto/?telefone={digitos}` — contexto do cliente

## Atualizar após mudanças no código

Sempre que alterar arquivos em `chrome-extension/`:

1. `chrome://extensions/` → botão **Atualizar** na extensão
2. Recarregue a aba do WhatsApp Web (F5)
