import os
import json
import requests
import re
from flask import Flask, url_for, redirect, render_template, session, request, flash
from flask_sqlalchemy import SQLAlchemy
from wtforms import StringField, SubmitField, TextAreaField, IntegerField, FileField, HiddenField
from wtforms.validators import Required
from flask_login import LoginManager, login_required, login_user, logout_user, current_user, UserMixin
from requests_oauthlib import OAuth2Session
from requests.exceptions import HTTPError
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell
from flask_wtf import FlaskForm
from client import clientid, secret


### Setup ###
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
basedir = os.path.abspath(os.path.dirname(__file__))

class Auth:
    """Google Project Credentials"""
    CLIENT_ID = (clientid)
    CLIENT_SECRET = secret
    REDIRECT_URI = 'http://localhost:5000/callback'
    #REDIRECT_URI = 'https://si364-final-lorenha.herokuapp.com/callback'
    AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
    TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'
    USER_INFO = 'https://www.googleapis.com/userinfo/v2/me'
    SCOPE = ['profile', 'email']


app = Flask(__name__)
app.debug = True
app.use_reloader = True
app.static_folder = 'static'
app.config['SECRET_KEY'] = """According to all known laws of aviation, there is no way that a bee should be able to fly. 
                              Its wings are too small to get its fat little body off the ground. The bee, of course, flies anyways. 
                              Because bees don't care what humans think is impossible."""

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL') or "postgresql://lorenha:psqlpw@localhost/SI364finallorenha"
app.config['HEROKU_ON'] = os.environ.get('HEROKU')
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

manager = Manager(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app)


### Models ###

recommendations = db.Table('recommendations', db.Column('song_id',db.Integer, db.ForeignKey('songs.id')),db.Column('user_id',db.Integer,db.ForeignKey('users.id')))

collections = db.Table('collections',db.Column('album_id',db.Integer, db.ForeignKey('albums.id')),db.Column('artist_id',db.Integer, db.ForeignKey('artists.id')))

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    avatar = db.Column(db.String(200))
    active = db.Column(db.Boolean, default=False)
    tokens = db.Column(db.Text)
    songs = db.relationship('Song', secondary=recommendations,backref=db.backref('songs',lazy='dynamic'),lazy='dynamic')

class Song(db.Model):
    __tablename__ = "songs"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), unique=True, nullable=False)
    artistid = db.Column(db.Integer, db.ForeignKey("artists.id"))
    rating = db.Column(db.Integer)
    albumid = db.Column(db.Integer, db.ForeignKey("albums.id"))
    genre = db.Column(db.String(64))

class Artist(db.Model):
    __tablename__ = "artists"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    songs = db.relationship('Song',backref='Artist')

class Album(db.Model):
    __tablename__ = "albums"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    cover = db.Column(db.String(200))
    songs = db.relationship('Song', backref="Album")
    artists = db.relationship('Artist',secondary=collections,backref=db.backref('albums',lazy='dynamic'),lazy='dynamic')

### Forms ###

class SongForm(FlaskForm):
    title = StringField("Title", validators=[Required()])
    artist = StringField("Artist", validators=[Required()])
    genre = StringField("Genre", validators=[Required()])
    token = StringField("What is your spotify token?", validators=[Required()])
    def validate_token(self, field):
        token = field.data
        if " " in token:
            raise ValidationError("Your token cannot contain any whitespace.")
    submit = SubmitField()

class UpdateButtonForm(FlaskForm):
    submit = SubmitField("Update Rating")

class UpdateRatingForm(FlaskForm):
    rating = StringField("New Rating", validators=[Required()])
    songid = HiddenField("songid", validators=[Required()])
    def validate_rating(self, field):
        rating = field.data
        if not rating.isdigit() and rating < 11 and rating > 0:
            raise ValidationError("Rating must be a number between 1 and 10.")
    submit = SubmitField("Update")

class DeleteButtonForm(FlaskForm):
    submit = SubmitField("Delete")

### Helper Functions ###
def get_or_create_song(title, artist, album, genre, albumcover=""):
    s = db.session.query(Song).filter_by(title=title).first()
    if not s:
        # Query API here?
        artist = get_or_create_artist(artist)
        album = get_or_create_album(album, artists_list=[artist.name], cover=albumcover)
        s = Song(title=title, artistid=artist.id, genre=genre, rating=0, albumid=album.id)
        current_user.songs.append(s)
        db.session.add(s)
        db.session.commit()
    return s

def get_or_create_artist(name):
    a = db.session.query(Artist).filter_by(name=name).first()
    if not a:
        a = Artist(name=name)
        db.session.add(a)
        db.session.commit()
    return a

def get_or_create_album(name, artists_list=[], cover=""):
    a = db.session.query(Album).filter_by(name=name).first()
    if not a:
        a = Album(name=name, cover=cover)
        for artist in artists_list:
            artist = get_or_create_artist(artist)
            a.artists.append(artist)
        db.session.add(a)
        db.session.commit()
    return a

def query_spotify(song, artist, genre, token):
    query = song + " " + artist
    headers ={"Content-Type": "application/json", "Authorization": "Bearer " + token}
    params = { 'q': query, 'type': 'track', 'limit':'1'}
    r = requests.get('https://api.spotify.com/v1/search?', headers=headers, params = params).json()
    hit = r["tracks"]["items"][0]
    year = hit["album"]["release_date"][:4]
    lower = int(year) - 5
    upper = int(year) + 5
    years_range = "{}-{}".format(lower,upper)
    query = "year:{} AND genre:'{}'".format(years_range, genre)
    headers ={"Content-Type": "application/json", "Authorization": "Bearer " + token}
    params = { 'q': query, 'type': 'track', 'limit':'10'}
    r = requests.get('https://api.spotify.com/v1/search?', headers=headers, params = params).json()
    return r
    

### Login Manager ### 
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_google_auth(state=None, token=None):
    if token:
        return OAuth2Session(Auth.CLIENT_ID, token=token)
    if state:
        return OAuth2Session(
            Auth.CLIENT_ID,
            state=state,
            redirect_uri=Auth.REDIRECT_URI
        )
    oauth = OAuth2Session(
        Auth.CLIENT_ID,
        redirect_uri=Auth.REDIRECT_URI,
        scope=Auth.SCOPE
    )
    return oauth

### Views ###

@app.route('/', methods=["POST","GET"]) # Should render a form for entering song data, then query the spotify api and add the results to the database.
@login_required
def index():
    """Submit songs for recommendations here."""
    form = SongForm()
    #if request.method == "POST":
    if form.validate_on_submit():
        title = form.title.data
        title = title.lower()
        artist = form.artist.data
        artist = artist.lower()
        genre = form.genre.data
        genre = genre.lower()
        token = form.token.data
        #try:
        songresults = query_spotify(title, artist, genre, token)
        songs = songresults["tracks"]["items"]
        for song in songs:
            title = song["name"]
            artist = ""
            for a in song["artists"]:
                artist = artist + a["name"] +", "
            artist = artist.strip()[:-1]
            album = song["album"]["name"]
            albumcover = song["album"]["images"][1]["url"]
            s = get_or_create_song(title, artist, album, genre, albumcover)
        return redirect(url_for('index'))
        #except KeyError:
        #    flash("Your API Key has expired, you need a new one.")
    return render_template('index.html', form=form, user=current_user)

@app.route('/song/<song_id>', methods=["GET", "POST"]) # Render the title, author, album, and possible other details of a specific song.
def song_details(song_id):
    """See details of a specific song."""
    form = DeleteButtonForm()
    song = db.session.query(Song).filter_by(id=song_id).first()
    artist = db.session.query(Artist).filter_by(id=song.artistid).first()
    album = db.session.query(Album).filter_by(id=song.albumid).first()
    return render_template("song.html", song=song, artist=artist, album=album, form=form, user=current_user)

@app.route('/recommendations', methods=["GET","POST"]) # Render a list of song recommendations based on their recent searches. Each list item is a link to that specific song's page.
@login_required
def recommendations():
    """See recommendations based on searches."""
    form = UpdateButtonForm()
    context = {}
    if request.method == "GET" and 'rating' in request.args:
        rating = request.args.get('rating')
        songid = request.args.get('songid')
        print("SONGID", songid)
        song = db.session.query(Song).filter_by(id=songid).first()
        song.rating = rating
        db.session.commit()
        flash("Updated rating of " + song.title)
        #return redirect(url_for('recommendations'))
    all_songs = current_user.songs.all()
    context["songs"] = []
    for song in all_songs:
        artist = db.session.query(Artist).filter_by(id=song.artistid).first()
        album = db.session.query(Album).filter_by(id=song.albumid).first()
        context["songs"].append({
            "song":song,
            "artist":artist,
            "album":album
        })        
    return render_template("recommendations.html", **context, form=form, user=current_user)

@app.route('/callback') #This app will implement oauth security and thus require a callback for the spotify account in question.
def callback():
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('index'))
    if 'error' in request.args:
        if request.args.get('error') == 'access_denied':
            return 'You denied access.'
        return 'Error encountered.'
    if 'code' not in request.args and 'state' not in request.args:
        return redirect(url_for('login'))
    else:
        google = get_google_auth(state=session['oauth_state'])
        try:
            token = google.fetch_token(
                Auth.TOKEN_URI,
                client_secret=Auth.CLIENT_SECRET,
                authorization_response=request.url)
        except HTTPError:
            return 'HTTPError occurred.'
        google = get_google_auth(token=token)
        resp = google.get(Auth.USER_INFO)
        if resp.status_code == 200:
            user_data = resp.json()
            email = user_data['email']
            user = User.query.filter_by(email=email).first()
            if user is None:
                user = User()
                user.email = email
            user.name = user_data['name']
            user.tokens = json.dumps(token)
            user.avatar = user_data['picture']
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('index'))
        return 'Could not fetch your information.'

@app.route('/login') # Users can log in here.
def login():
    """Login section."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    google = get_google_auth()
    auth_url, state = google.authorization_url(
        Auth.AUTH_URI, access_type='online')
    session['oauth_state'] = state
    return render_template('login.html', auth_url=auth_url)

@app.route('/logout') # Users are redirected here to log out.
@login_required
def logout():
    """Logout section."""
    logout_user()
    return redirect(url_for('index'))

@app.route('/update/<song_id>', methods=["GET","POST"])
def update(song_id):
    form = UpdateRatingForm(songid=song_id)
    form.songid.data = song_id
    song = db.session.query(Song).filter_by(id=song_id).first()
    return render_template('update_rating.html', song=song, form=form, user=current_user)

@app.route('/delete/<song_id>', methods=["GET", "POST"])
def delete(song_id):
    song = db.session.query(Song).filter_by(id=song_id).first()
    title = song.title
    db.session.delete(song)
    db.session.commit()
    flash("Deleted song " + title)
    return redirect(url_for('recommendations'))

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500

if __name__ == "__main__":
    db.create_all()
    manager.run()