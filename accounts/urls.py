from django.urls import path

from core.views import BackupGerarView, BackupRestaurarView
from extension.views import ExtensionTokenGerarView, ExtensionTokenRevogarView

from . import views

app_name = 'accounts'

urlpatterns = [
    path('configuracao-inicial/', views.configuracao_inicial, name='configuracao_inicial'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('perfil/', views.PerfilView.as_view(), name='perfil'),
    path('perfil/senha/', views.alterar_senha, name='alterar_senha'),
    path('perfil/extension-token/gerar/', ExtensionTokenGerarView.as_view(), name='extension_token_gerar'),
    path('perfil/extension-token/revogar/', ExtensionTokenRevogarView.as_view(), name='extension_token_revogar'),
    path('perfil/backup/gerar/', BackupGerarView.as_view(), name='backup_gerar'),
    path('perfil/backup/restaurar/', BackupRestaurarView.as_view(), name='backup_restaurar'),
    path('usuarios/', views.UsuarioListView.as_view(), name='usuarios_lista'),
    path('usuarios/novo/', views.UsuarioCreateView.as_view(), name='usuarios_novo'),
    path('usuarios/<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuarios_editar'),
    path('usuarios/<int:pk>/desativar/', views.UsuarioDesativarView.as_view(), name='usuarios_desativar'),
    path('usuarios/<int:pk>/resetar-senha/', views.UsuarioResetSenhaView.as_view(), name='usuarios_reset_senha'),
]
