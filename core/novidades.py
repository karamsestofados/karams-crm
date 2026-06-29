EXTENSION_DOWNLOAD_URL = (
    'https://drive.google.com/drive/folders/18NQNOaPDePBdQf4iB488sC-CNo8LKUY6?usp=sharing'
)
SUPPORT_WHATSAPP_URL = 'https://wa.me/5544988133500'

IMPLEMENTACOES = [
    'Integração WhatsApp Web com extensão Chrome do Karams',
    'Painel lateral com contexto comercial ao abrir conversa',
    'Geração de token de API em Perfil → Integração WhatsApp',
]

AJUSTES = [
    'Identificação de clientes por telefone com normalização BR (nono dígito)',
    'Redesign do painel da extensão (v1.1.0)',
    'Correções na busca de produtos no modal de vínculo',
]

SESSION_KEY = 'novidades_popup'


def get_novidades():
    return {
        'implementacoes': IMPLEMENTACOES,
        'ajustes': AJUSTES,
        'extension_url': EXTENSION_DOWNLOAD_URL,
        'suporte_url': SUPPORT_WHATSAPP_URL,
    }


def marcar_novidades_popup(session):
    session[SESSION_KEY] = True


def dispensar_novidades_popup(session):
    session.pop(SESSION_KEY, None)
