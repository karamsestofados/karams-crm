from django.urls import path

from . import views

app_name = 'atividade'

urlpatterns = [
    path('', views.AtividadeDiariaView.as_view(), name='atividade_diaria'),
    path('<int:pk>/concluir/', views.ConcluirFollowupView.as_view(), name='concluir_followup'),
]
