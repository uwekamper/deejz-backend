from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render_to_response
from party.models import PartyPlaylist, Song, SongVote, SongVeto, VetoedSong
from django.template import RequestContext
from django.core import serializers
import simplejson as json
from simplejson import JSONDecodeError
import random
import string
from datetime import datetime

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
	try:
		vetoedsongs = VetoedSong.objects.get(party=fete.id)
	except VetoedSong.DoesNotExist:
		vetoedsongs = []
	context = RequestContext(request, {'party': fete, 'songs': songs, 'vetoedsongs': vetoedsongs})
	return render_to_response('party.html', context)
	
def playlist_json(request, party_slug):
	songs = get_ordered_playlist(party_slug)
	data = serializers.serialize("json", songs)
	return HttpResponse(data, mimetype="application/json")
	
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
	return HttpResponse(data, mimetype="application/json")
	
# will move next song on playlist to current song
def get_next_song(request, party_slug):
	fete = PartyPlaylist.objects.get(slug=party_slug)
	try:
		current_song = Song.objects.get(party=fete.id, is_current_song=True)
		current_song.is_current_song = False
		current_song.save()
	except Song.DoesNotExist: 
		pass
	
	next_song = get_ordered_playlist(party_slug)[0]
	next_song.played = datetime.now()
	next_song.is_current_song = True
	next_song.save()
	
	data = serializers.serialize("json", [next_song])
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

	return HttpResponse('Song added.')
		
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
		s = Song.objects.get(id=song_id)
		s.votes = s.votes + 1
		s.save()
		v = SongVote(song=s, uuid=uuid)
		v.save()
		return HttpResponse('Vote add.')
		
# TODO veto handling and url
def veto_song(request, party_slug, song_id, uuid):
	try:
		maybe_veto = SongVote.objects.get(song=song_id, uuid=uuid)
		return HttpResponseForbidden('And not a veto was given that day.')
	except SongVote.DoesNotExist:
		s = Song.objects.get(id=song_id)
		v = SongVote(song=s, uuid=uuid)
		v.save()
		return HttpResponse('Veto given')	

def vote(request, party_slug):
	return HttpResponse("vote")
	
def veto(request, party_slug):
	return HttpResponse("VETO")