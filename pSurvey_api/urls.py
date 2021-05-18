from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from django.conf.urls import handler404, handler500, handler403
from errorPages import views

urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^', include('authApp.urls')),
    url(r'^', include('survey.urls')),
    url(r'^', include('reports.urls')),
    url(r'^auth/', include('djoser.urls')),
    url(r'^auth/', include('djoser.urls.authtoken')),

]
handler403 = views.error403
handler404 = views.error_404

