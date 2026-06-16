from django.urls import path

from . import views

app_name = 'atividade'

urlpatterns = [
    path('', views.AtividadeDiariaView.as_view(), name='atividade_diaria'),
    path('interacao/nova/', views.InteracaoGlobalCreateView.as_view(), name='interacao_nova'),
    path('calendario/<str:data_str>/', views.CalendarioDiaPartialView.as_view(), name='calendario_dia'),
    path('<int:pk>/concluir/', views.ConcluirFollowupView.as_view(), name='concluir_followup'),
]
