from django.urls import path

from .views import PowerUPView

app_name = 'powerup'

urlpatterns = [
    path('', PowerUPView.as_view(), name='index'),
]
