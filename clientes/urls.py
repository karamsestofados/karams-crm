from django.urls import path

from relacionamento.views import (
    ClienteAtividadeCreateView,
    ClienteAtividadeUpdateView,
    ClienteHistoricoPdfView,
    ClienteTimelinePartialView,
)

from . import views

app_name = 'clientes'

urlpatterns = [
    path('busca/', views.ClienteBuscaAutocompleteView.as_view(), name='busca'),
    path('', views.ClienteListView.as_view(), name='lista'),
    path('novo/', views.ClienteCreateView.as_view(), name='novo'),
    path('<int:pk>/editar/', views.ClienteUpdateView.as_view(), name='editar'),
    path('<int:pk>/inativar/', views.ClienteInativarView.as_view(), name='inativar'),
    path('<int:pk>/reativar/', views.ClienteReativarView.as_view(), name='reativar'),
    path('<int:pk>/produtos/aviso/', views.ClienteProdutoAvisoView.as_view(), name='produto_vinculo_aviso'),
    path('<int:pk>/produtos/vincular/', views.ClienteProdutoVincularView.as_view(), name='produto_vincular'),
    path('<int:pk>/produtos/<int:vinculo_pk>/remover/', views.ClienteProdutoRemoverView.as_view(), name='produto_remover'),
    path('<int:pk>/atividades/nova/', ClienteAtividadeCreateView.as_view(), name='atividade_nova'),
    path('<int:pk>/atividades/<int:atividade_pk>/editar/', ClienteAtividadeUpdateView.as_view(), name='atividade_editar'),
    path('<int:pk>/atividades/', ClienteTimelinePartialView.as_view(), name='atividades_timeline'),
    path('<int:pk>/historico.pdf', ClienteHistoricoPdfView.as_view(), name='historico_pdf'),
]
