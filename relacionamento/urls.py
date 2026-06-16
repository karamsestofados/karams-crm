from django.urls import path

from . import views

app_name = 'relacionamento'

urlpatterns = [
    path('relatorio/', views.RelatorioRelacionamentoView.as_view(), name='relatorio'),
]
