# Imports #####################################################################
###############################################################################

from util.env import (
    FOTRINO_SECRET_KEY,
    FOTRINO_REDIS_HOST,
    FOTRINO_REDIS_PORT,
    FOTRINO_REDIS_DB,
    FOTRINO_OAUTH_PROVIDERS,
    FOTRINO_MINIO_BUCKET,
    FOTRINO_HYDRA_HOST
    )

from workers.doppelganger import process_photo
from util.cache import cache
from models.photo import Photo
from models.user import User
from models.album import Album

import os
import json
from datetime import timedelta

from flask import (
    Flask,
    redirect,
    request
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user
)
from authlib.integrations.flask_client import OAuth
from loginpass import create_flask_blueprint, create_hydra_backend
from loginpass import (
    Facebook,
    Google,
    GitHub,
    Reddit,
    Instagram,
    Gitlab,
    LinkedIn,
    StackOverflow
)
from redis import Redis
from rq import Queue

from psycopg2.errors import UniqueViolation


# Flask Setup #################################################################
###############################################################################

# Initialise app
app = Flask(__name__)
app.secret_key = FOTRINO_SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

# Set up RQ
q = Queue(
    connection=Redis(
        host=FOTRINO_REDIS_HOST,
        port=FOTRINO_REDIS_PORT,
        db=FOTRINO_REDIS_DB
    )
)

# Set up cache
cache_config = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': 'redis://' + FOTRINO_REDIS_HOST + ':' + FOTRINO_REDIS_PORT + '/' + FOTRINO_REDIS_DB}
cache.init_app(app, config=cache_config)


# Set up login manager
login_manager = LoginManager()
login_manager.init_app(app)
@login_manager.unauthorized_handler
def unauthorized():
    return "Forbidden", 403


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


# Setup OAuth login
app.config.from_pyfile('util/oauth_config.py')
oauth = OAuth(app)


def handle_authorize(remote, token, user_info):
    if user_info.get("email") or user_info.get("email_verified"):
        external_id = user_info["sub"]
        name = user_info.get("name") or "Anonymous"
        email = user_info.get("email") or (remote.name + "-" + user_info["sub"])
    else:
        return redirect("/403")

    if remote.name == "facebook":
        profile_pic = "https://graph.facebook.com/{}/picture?type=large".format(external_id)
    else:
        profile_pic = user_info.get("picture")

    if not User.get_user_from_email(email):
        User.create(remote.name, external_id, name, email, profile_pic, request.headers.get('CF-IPCountry') or 'XX')
    user = User.get_user_from_email(email)
    if user.identity_provider != remote.name:
        return redirect("/409")

    # TODO updte last_login date
    login_user(user)

    return redirect("/gallery")


Hydra = create_hydra_backend("hydra", FOTRINO_HYDRA_HOST)

bp = create_flask_blueprint(
    [
        Facebook,
        Google,
        GitHub,
        Reddit,
        Instagram,
        Gitlab,
        LinkedIn,
        StackOverflow,
        Hydra
    ],
    oauth, handle_authorize
)
app.register_blueprint(bp, url_prefix='/api/account')


# Account Routes ##############################################################
###############################################################################

@app.route("/api/account/providers", methods=['GET'])
def get_oauth_providers():
    return json.dumps(FOTRINO_OAUTH_PROVIDERS)


@app.route("/api/account/profile", methods=['GET'])
@login_required
def get_profile():
    return json.dumps(current_user.__dict__)


@app.route("/api/account/logout", methods=['GET'])
def get_logout():
    logout_user()
    return redirect("/welcome")


# Album Routes ################################################################
###############################################################################

@app.route("/api/albums", methods=['GET'])
@login_required
def get_api_albums():
    albums = Album.get_all(current_user)
    return json.dumps([f.__dict__ for f in albums])


@app.route("/api/albums", methods=['POST'])
@login_required
def post_api_albums():
    try:
        album = Album.create(current_user, request.json['name'])
    except UniqueViolation:
        return "Album already exists", 400
    return json.dumps(album.__dict__)


@app.route("/api/albums", methods=['PUT'])
@login_required
def put_api_albums():
    try:
        album = Album.get(current_user, request.json['id'])
        album = album.update(current_user, request.json['name'])
    except ValueError as error:
        return error.args[0], 400
    return json.dumps(album.__dict__)


@app.route("/api/albums/share/<id>", methods=['PUT'])
@login_required
def put_api_albums_share(id):
    try:
        album = Album.get(current_user, id)
        album.share(current_user, request.json['shared'])
    except ValueError as error:
        return error.args[0], 400
    return json.dumps(album.__dict__)


@app.route("/api/albums/<id>", methods=['DELETE'])
@login_required
def delete_api_albums(id):
    try:
        album = Album.get(current_user, id)
        album.delete(current_user)
    except ValueError as error:
        return error.args[0], 400
    return json.dumps(True)


# Photo Routes ##############################################################
###############################################################################

@app.route("/api/photos/<id>", methods=['GET'])
@login_required
def get_api_photos(id):
    photos = Photo.get_photos(current_user, id)
    return json.dumps([i.__dict__ for i in photos], indent=4, sort_keys=True, default=str)


@app.route("/api/photos/shared/<album_uuid>", methods=['GET'])
def get_api_photos_shared(album_uuid):
    try:
        photos = Photo.get_shared_photos(album_uuid)
    except ValueError as error:
        return error.args[0], 400
    return json.dumps([i.__dict__ for i in photos], indent=4, sort_keys=True, default=str)


@app.route("/api/photos/preupload", methods=['PUT'])
@login_required
def put_api_photos_preupload():
    presigned_put_url = None
    description = None
    allowed = Photo.allowed_file(request.json['filename'])
    if not allowed:
        description = "Unsupported file type."
    if allowed:
        exists = Photo.exists(current_user, request.json['hash'])
        if exists:
            description = "Previously uploaded"
    filtered = (not allowed or exists)
    if not filtered:
        presigned_put_url = Photo.get_presigned_put_url(current_user, request.json['hash'], request.json['filename'])
    return json.dumps(
        {
            "filename": request.json['filename'],
            "hash": request.json['hash'],
            "valid": not filtered,
            "description": description,
            "presigned_put_url": presigned_put_url
        }
    )


@app.route("/api/photos", methods=['POST'])
@login_required
def post_api_photos():
    photo = Photo.create(current_user, request.json['album'], request.json['hash'], request.json['filename'], request.json['exif_datetime'])
    file_name, file_extension = os.path.splitext(request.json['filename'])
    new_object = str(current_user.id) + "/original/" + request.json['hash'][:2] + "/" + request.json['hash'] + file_extension
    q.enqueue(process_photo, FOTRINO_MINIO_BUCKET, new_object, photo.id)
    return json.dumps(photo.__dict__)


@app.route("/api/photos", methods=['PUT'])
@login_required
def put_api_photos():
    for new_photo in request.json:
        photo = Photo.get(current_user, new_photo['id'])
        try:
            photo = photo.update(current_user, new_photo['album'], new_photo['flag'], new_photo['exif_datetime'])
        except ValueError as error:
            return error.args[0], 400
    return json.dumps(photo.__dict__)


@app.route("/api/photos/<id>", methods=['DELETE'])
@login_required
def delete_api_photos(id):
    try:
        Photo.delete(current_user, id)
    except ValueError as error:
        return error.args[0], 400
    return json.dumps(True)


@app.route("/api/photos/exif/<id>", methods=['GET'])
@login_required
def get_api_photos_exif(id):
    return json.dumps(Photo.get_exif(current_user, id))


# Doppelganger Route ##########################################################
###############################################################################

@app.route("/api/photos/similar/<album>", methods=['GET'])
@login_required
def get_api_doppelganger(album):
    clusters = Photo.get_similar_photos(current_user, album)
    similar = []
    for cluster in clusters:
        for p in cluster:
            photo = Photo.get(current_user, p['id'])
            similar.append(photo.__dict__)
    return json.dumps(similar)


# Misc. Routes ################################################################
###############################################################################

@app.route("/api/country", methods=['GET'])
def get_api_country():
    return json.dumps(request.headers.get('CF-IPCountry') or 'XX')


# Main ########################################################################
###############################################################################

if __name__ == "__main__":
    app.run(ssl_context="adhoc", port=65442)
