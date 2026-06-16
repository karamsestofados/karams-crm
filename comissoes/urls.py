from django.urls import path

from . import views

app_name = 'comissoes'

urlpatterns = [
    path('metas/', views.MetaListView.as_view(), name='metas_lista'),
    path('metas/nova/', views.MetaCreateView.as_view(), name='metas_nova'),
    path('metas/<int:pk>/editar/', views.MetaUpdateView.as_view(), name='metas_editar'),
    path('metas/<int:pk>/desativar/', views.MetaDesativarView.as_view(), name='metas_desativar'),
]
