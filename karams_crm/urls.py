from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import include, path


def permission_denied_view(request, exception):
    return render(request, '403.html', status=403)


def server_error_view(request):
    return render(request, '500.html', status=500)


handler403 = permission_denied_view
handler500 = server_error_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('clientes/', include('clientes.urls')),
    path('produtos/', include('clientes.urls_produtos')),
    path('atividade-diaria/', include('relacionamento.urls_atividade')),
    path('relacionamento/', include('relacionamento.urls')),
    path('comissoes/', include('comissoes.urls')),
    path('relatorios/', include('relatorios.urls')),
    path('powerup/', include('powerup.urls')),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'Karams CRM'
admin.site.site_title = 'Karams CRM'
admin.site.index_title = 'Administração'
