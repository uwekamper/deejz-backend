from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'deejz.views.home', name='home'),
    # url(r'^deejz/', include('deejz.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
	url(r'^party/create/$', 'party.views.create_party'),
	url(r'^party/index\.json$', 'party.views.index'),
	url(r'^party\/(?P<party_slug>\w+)/$', 'party.views.party'),
	url(r'^party\/(?P<party_slug>\w+)/playlist\.json$', 'party.views.playlist_json'),
	url(r'^party\/(?P<party_slug>\w+)/complete_playlist\.json$', 'party.views.complete_playlist_json'),
	url(r'^party\/(?P<party_slug>\w+)/details\.json$', 'party.views.details_json'),
	url(r'^party\/(?P<party_slug>\w+)/add_song/$', 'party.views.add_song'),
	url(r'^party\/(?P<party_slug>\w+)/next_song\.json$', 'party.views.get_next_song'),
	url(r'^party\/(?P<party_slug>\w+)/current_song\.json$', 'party.views.get_current_song'),
	url(r'^party\/(?P<party_slug>\w+)\/song\/(?P<song_id>\d+)\/vote\/(?P<uuid>[\d\w\-]+)\/$', 'party.views.vote_song'),
	url(r'^party\/(?P<party_slug>\w+)\/song\/(?P<song_id>\d+)\/veto\/(?P<uuid>[\d\w\-]+)\/$', 'party.views.veto_song'),
	url(r'^party\/near/(?P<latitude>[\d.]+)\/(?P<longitude>[\d.]+)\/$', 'party.views.nearby_parties'),
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += staticfiles_urlpatterns()
