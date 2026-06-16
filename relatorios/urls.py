from django.urls import path

from . import views

app_name = 'relatorios'

urlpatterns = [
    path('produtividade/', views.ProdutividadeComercialView.as_view(), name='produtividade'),
]
