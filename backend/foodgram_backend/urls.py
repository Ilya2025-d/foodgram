"""URL configuration for foodgram_backend project."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from api.v1.views import redirect_to_recipe


urlpatterns = [
    path('admin/', admin.site.urls),
    path('s/<str:short_code>/', redirect_to_recipe, name='redirect_to_recipe'),
    path('api/', include('api.urls'))
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
