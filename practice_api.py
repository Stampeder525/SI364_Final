import requests
import json
from client import clientid, secret


## Based on song data entered, the spotify api will be queried with a song and artist title, potentially with the album title as well.
## This will be used both to get data about the song specified and also to get recommendations based on the song, such as those that 
## are by the same artist, in the same album, or of a similar genre. Songs will be saved in the songs table, Artists in the artists table,
## and Albums in the albums table. Songs will also be added to the current user's list of song recommendations.
def query_api(song="", artist=""):
    query = song + " " + artist
    oauth_token = "BQA7F_tOxISs0yKO-B3ipx8BXq1EpieB-eEKTWy2lkTep8xKs0yuGaecak0mcT2-OSUX7e37K4EBgzhNb7Llvu5k4Mih-9eOGz4x8P2mGe_jryOoPutpycqnji9ZvEBWob9v6SPe-iUf8Tjdyw"
    headers ={"Content-Type": "application/json", "Authorization": "Bearer " + oauth_token}
    params = { 'q': query, 'type': 'track'}
    r = requests.get('https://api.spotify.com/v1/search?', headers=headers, params = params).json()
    return r


songresults = query_api(song="Jumper")
#print(json.dumps(songresults["tracks"]))
song = songresults["tracks"]["items"][0]
title = song["name"]
artists = []
for artist in song["artists"]:
    artists.append(artist["name"])

print(title)
print(artists)
print("\n")

songresults = query_api(song="The General", artist="Dispatch")
song = songresults["tracks"]["items"][0]
title = song["name"]
artists = []
for artist in song["artists"]:
    artists.append(artist["name"])

print(title)
print(artists)
