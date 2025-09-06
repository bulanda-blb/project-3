



from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.static import serve as static_serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('index.urls', namespace='index')),
    path('auth/', include('authentication.urls', namespace='auth')),
    path('employer/', include('employer_profile.urls', namespace='employer')),
    path('candidate/', include('candidate_profile.urls', namespace='candidate')),


]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

