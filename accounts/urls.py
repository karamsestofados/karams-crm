from django.urls import path

from core.views import BackupGerarView, BackupRestaurarView

from . import views

app_name = 'accounts'

urlpatterns = [
    path('configuracao-inicial/', views.configuracao_inicial, name='configuracao_inicial'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('perfil/', views.PerfilView.as_view(), name='perfil'),
    path('perfil/senha/', views.alterar_senha, name='alterar_senha'),
    path('perfil/backup/gerar/', BackupGerarView.as_view(), name='backup_gerar'),
    path('perfil/backup/restaurar/', BackupRestaurarView.as_view(), name='backup_restaurar'),
]
