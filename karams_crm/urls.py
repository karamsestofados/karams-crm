from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('clientes/', include('clientes.urls')),
    path('produtos/', include('clientes.urls_produtos')),
    path('atividade-diaria/', include('relacionamento.urls_atividade')),
    path('relacionamento/', include('relacionamento.urls')),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'Karams CRM'
admin.site.site_title = 'Karams CRM'
admin.site.index_title = 'Administração'
