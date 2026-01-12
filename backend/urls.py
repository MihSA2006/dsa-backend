from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import handler404

urlpatterns = [
    path('***dsa-staff***/', admin.site.urls),
    path('api/', include('api.urls')),  # Inclut toutes les URLs de l'app api
    path('api/accounts/', include('accounts.urls')),
    path('api/', include('contests.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    from django.http import HttpResponseNotFound
    from django.template.loader import render_to_string

    def debug_404(request, exception=None):
        html = render_to_string("404.html")
        return HttpResponseNotFound(html)

    # Force Django à utiliser votre handler en mode debug
    handler404 = debug_404
