from django.urls import path

from . import views

app_name = 'produtos'

urlpatterns = [
    path('', views.ProdutoListView.as_view(), name='lista'),
    path('busca/', views.ProdutoBuscaAutocompleteView.as_view(), name='busca'),
    path('novo/', views.ProdutoCreateView.as_view(), name='novo'),
    path('<int:pk>/editar/', views.ProdutoUpdateView.as_view(), name='editar'),
]
