from django.urls import path

from . import views

app_name = 'extension'

urlpatterns = [
    path('me/', views.ExtensionMeView.as_view(), name='me'),
    path('contexto/', views.ExtensionContextoView.as_view(), name='contexto'),
]
