from django.urls import path

from . import views

app_name = 'relatorios'

urlpatterns = [
    path('produtividade/', views.ProdutividadeComercialView.as_view(), name='produtividade'),
    path('produtividade/exportar.xlsx', views.ProdutividadeExportXlsxView.as_view(), name='produtividade_export_xlsx'),
    path('produtividade/exportar.pdf', views.ProdutividadeExportPdfView.as_view(), name='produtividade_export_pdf'),
]
