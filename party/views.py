from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render_to_response, get_object_or_404
from party.models import PartyPlaylist, Song, SongVote, SongVeto, VetoedSong
from django.template import RequestContext
from django.core import serializers
import simplejson as json
from simplejson import JSONDecodeError
import random
import string
from datetime import datetime
# for distance calculation
from math import radians, cos, sin, asin, sqrt

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
	source: http://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    km = 6367 * c
    return km

def nearby_parties(request, latitude, longitude):
	nearby = []
	everyparty = PartyPlaylist.objects.all()
	for i in everyparty:
		dist = haversine(i.longitude, i.latitude, float(longitude), float(latitude))
		# distance is less than 5 km
		if dist < 5.0:
			nearby.append(i)
	data = serializers.serialize("json", nearby)
	response = HttpResponse(data, mimetype="application/json")
	response['Access-Control-Allow-Origin'] = '*'
	return response

def get_ordered_playlist(party_slug):
	fete = PartyPlaylist.objects.get(slug=party_slug)
	return list(fete.song_set.filter(played__isnull=True).order_by('-votes', 'added_at'))
	
def get_full_playlist(party_slug):
	# pl = get_ordered_playlist(party_slug)
	# [song for song in pl if song.played == None]
	# return pl
	pass
	
def index(request):
	data = serializers.serialize("json", PartyPlaylist.objects.all())
	return HttpResponse(data, mimetype="application/json")
	
def party(request, party_slug):
	fete = PartyPlaylist.objects.get(slug=party_slug)
	songs = get_ordered_playlist(party_slug)
	vetoedsongs = list(VetoedSong.objects.filter(party=fete.id))
	past_songs = fete.song_set.filter(played__isnull=False).order_by('-played')
	last_three_songs = past_songs[-3:]
	
	context = RequestContext(request, {'party': fete, 'songs': songs, 
		'vetoedsongs': vetoedsongs, 
		'last_three_songs': last_three_songs,
		'past_songs': past_songs})
	return render_to_response('party.html', context)
	
def playlist_json(request, party_slug):
	songs = get_ordered_playlist(party_slug)
	data = serializers.serialize("json", songs)
	response = HttpResponse(data, mimetype="application/json")
	response['Access-Control-Allow-Origin'] = '*'
	return response
	
def complete_playlist_json(request, party_slug):
	fete = PartyPlaylist.objects.get(slug=party_slug)
	pl = []
	# past songs
	pl.extend(fete.song_set.filter(played__isnull=False).order_by('played'))
	# future songs
	pl.extend(get_ordered_playlist(party_slug))
	data = serializers.serialize("json", pl)
	return HttpResponse(data, mimetype="application/json")

def details_json(request, party_slug):
	data = serializers.serialize("json", [PartyPlaylist.objects.get(slug=party_slug)])
	return HttpResponse(data, mimetype="application/json")
	
# get the current (without changing the playlist)
def get_current_song(request, party_slug):
	fete = PartyPlaylist.objects.get(slug=party_slug)
	data = serializers.serialize("json", fete.song_set.filter(is_current_song=True)[0:])
	response = HttpResponse(data, mimetype="application/json")
	response['Access-Control-Allow-Origin'] = '*'
	return response
	
# will move next song on playlist to current song
def get_next_song(request, party_slug):
	fete = PartyPlaylist.objects.get(slug=party_slug)
	try:
		current_song = Song.objects.get(party=fete.id, is_current_song=True)
		current_song.is_current_song = False
		current_song.save()
	except Song.DoesNotExist: 
		pass
	pl = get_ordered_playlist(party_slug)
	nextlist = []
	if len(pl) > 0:
		next_song = pl[0]
		next_song.played = datetime.now()
		next_song.is_current_song = True
		nextlist.append(next_song)
		next_song.save()
	
	data = serializers.serialize("json", nextlist)
	return HttpResponse(data, mimetype="application/json")
	
def add_song(request, party_slug):
	try:
		data = json.loads(request.raw_post_data)
		fete = PartyPlaylist.objects.get(slug=party_slug)
		
		# check if the song was vetoed before
		try:
			VetoedSong.objects.get(party=fete.id, deezer_id=data['deezer_id'])
		except VetoedSong.DoesNotExist:
			pass
		finally:
			HttpResponseForbidden('Song way vetoed. Sorry.')
			
		# check if the song is already in the playlist
		song, created = Song.objects.get_or_create(party=fete, 
			added_by_uuid=data['uuid'], 
			deezer_id=data['deezer_id'],
			title=data['title'])
			
		# if it existed before, than adding the song means voting for it.
		if not created:
			vote_song(request, party_slug, song.id, data['uuid'])
		else:	
			song.save()
	except KeyError, e:
		print e
		return HttpResponseBadRequest("KeyError: %s" % e)
	except JSONDecodeError, e:
		print e
		return HttpResponseBadRequest("JSONDecodeError: %s" % e)

	return HttpResponse('[{"message": "Song added."}]', mimetype="application/json")
		
def create_party(request):
	# try to create the autoslug as long as you need to get one that isn't in
	# database yet.
	autoslug = ''
	while(True):
		autoslug = ''.join(random.sample(string.ascii_lowercase, 10))
		try: 
			partylist = PartyPlaylist.objects.get(slug=autoslug)
		except PartyPlaylist.DoesNotExist:
			break
	try:
		data = json.loads(request.raw_post_data)
		fete = PartyPlaylist(slug=autoslug,
			name=data['name'],
			address=data['address'],
			longitude=float(data['longitude']),
			latitude=float(data['latitude']))
		fete.save()
	except KeyError, e:
		print e
		return HttpResponseBadRequest("KeyError: %s" % e)
	except JSONDecodeError, e:
		print e
		return HttpResponseBadRequest("JSONDecodeError: %s" % e)
	return HttpResponse('{"partyslug": "%s"}' % autoslug, mimetype="application/json")

def vote_song(request, party_slug, song_id, uuid):
	try:
		maybe_vote = SongVote.objects.get(song=song_id, uuid=uuid)
		return HttpResponseForbidden('Already voted.')
	except SongVote.DoesNotExist:
		s = get_object_or_404(Song, pk=song_id)
		s.votes = s.votes + 1
		s.save()
		v = SongVote(song=s, uuid=uuid)
		v.save()
		return HttpResponse('Vote add.')
		
# TODO veto handling and url
def veto_song(request, party_slug, song_id, uuid):
	fete = get_object_or_404(PartyPlaylist, slug=party_slug)
	try:
		maybe_veto = SongVeto.objects.get(song=song_id, uuid=uuid)
		return HttpResponseForbidden('And not a veto was given that day.')
	except SongVeto.DoesNotExist:
		song = get_object_or_404(Song, pk=song_id)
		song.vetoes = song.vetoes + 1
		song.save()
		if song.vetoes > 1:
			song.vetoed = True
			vs = VetoedSong(party=fete, deezer_id=song.deezer_id, title=song.title)
			vs.save()
		song.save()
		v = SongVeto(song=song, uuid=uuid)
		v.save()
		
		return HttpResponse('Veto registered.')	