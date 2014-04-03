from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from dajaxice.core import dajaxice_autodiscover, dajaxice_config
dajaxice_autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'coint.views.home', name='home'),
    url(dajaxice_config.dajaxice_url, include('dajaxice.urls')),
    url(r'^tz-detect/', include('tz_detect.urls'))
)

urlpatterns += staticfiles_urlpatterns()