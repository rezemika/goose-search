from django.conf.urls import include, url
from django.contrib import admin
from search import views
from goose import settings

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^results/$', views.results, name='results'),
    url(r'^getresults/$', views.get_results, name='getresults'),
    url(r'^getmap/$', views.get_map, name='getmap'),
    url(r'^about/$', views.about, name='about'),
    url(r'^light/$', views.light_home, name='light'),
    url(r'^light/about/$', views.about, name='light-about'),
    url(r'^admin/', admin.site.urls)
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

handler404 = "search.views.handler404"
handler500 = "search.views.handler500"
