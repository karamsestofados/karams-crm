from django.urls import path

from . import views

app_name = 'clientes'

urlpatterns = [
    path('', views.ClienteListView.as_view(), name='lista'),
    path('novo/', views.ClienteCreateView.as_view(), name='novo'),
    path('<int:pk>/editar/', views.ClienteUpdateView.as_view(), name='editar'),
    path('<int:pk>/inativar/', views.ClienteInativarView.as_view(), name='inativar'),
    path('<int:pk>/reativar/', views.ClienteReativarView.as_view(), name='reativar'),
    path('<int:pk>/produtos/vincular/', views.ClienteProdutoVincularView.as_view(), name='produto_vincular'),
    path('<int:pk>/produtos/<int:vinculo_pk>/remover/', views.ClienteProdutoRemoverView.as_view(), name='produto_remover'),
]
