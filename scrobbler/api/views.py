import datetime

from flask import Blueprint, redirect, request, url_for
from sqlalchemy.dialects.postgresql import insert

from scrobbler import db
from scrobbler.api.consts import PONG, RADIO_HANDSHAKE, UPDATE_CHECK
from scrobbler.api.helpers import (api_response, authenticate, md5,
                                   parse_auth_request, parse_np_request, parse_scrobble_request)
from scrobbler.models import Album, Artist, NowPlaying, Scrobble, Session, User

blueprint = Blueprint('api', __name__)


@blueprint.route('/', methods=['GET', 'POST'])
def handshake():
    handshake = request.args.get('hs')

    if handshake is None:
        return redirect(url_for('webui.index'))

    data = parse_auth_request(request.args)

    if not data:
        return api_response('BADREQUEST'), 400

    user = db.session.query(User).filter_by(username=data['username']).first()
    user, token_id = authenticate(user, data['timestamp'], data['auth'])

    if user is None:
        return api_response('BADAUTH')

    session = db.session.query(Session).filter(
        Session.user_id == user.id,
        Session.token_id == token_id
    ).first()

    current_time = datetime.datetime.now()

    if session:
        session.updated_at = current_time
    else:
        session_id = md5(user.username + user.api_password + current_time.strftime('%s'))
        session = Session(
            user_id=user.id,
            token_id=token_id,
            session_id=session_id,
            created_at=current_time,
            updated_at=current_time,
        )
        db.session.add(session)

    db.session.commit()

    return api_response(
        'OK',
        session.session_id,
        'http://post.audioscrobbler.com:80/np_1.2',
        'http://post.audioscrobbler.com:80/protocol_1.2',
    )


@blueprint.route('/ass/pwcheck.php')
def password_check():
    data = parse_auth_request(request.args)
    if not data:
        return api_response('BADREQUEST'), 400

    user = db.session.query(User).filter_by(username=data['username']).first()
    user, token_id = authenticate(user, data['timestamp'], data['auth'])

    if user is None:
        return api_response('BADPASSWORD')

    return api_response('OK')


@blueprint.route('/np_1.2', methods=['POST'])
def now_playing():
    data = parse_np_request(request.form)
    if not data:
        return api_response('BADREQUEST'), 400

    session = db.session.query(Session).filter(Session.session_id == data['session_id']).first()

    if session is None:
        return api_response('BADSESSION')

    data.pop('session_id', None)
    data['user_id'] = session.user_id
    data['token_id'] = session.token_id
    data['played_at'] = datetime.datetime.now()
    np = NowPlaying(**data)
    db.session.add(np)
    db.session.commit()

    return api_response('OK')


@blueprint.route('/protocol_1.2', methods=['POST'])
def scrobble():
    session_id, scrobbles = parse_scrobble_request(request.form)
    if not session_id:
        return api_response('BADREQUEST'), 400

    session = db.session.query(Session).filter(Session.session_id == session_id).first()

    for data in scrobbles:
        artist = db.session.query(Artist).filter(Artist.name == data['artist']).first()
        artist_id = None
        album_id = None

        if artist:
            artist_id = artist.id
            artist.local_playcount += 1

            album = db.session.query(Album).filter(
                Album.artist_id == artist_id,
                Album.name == data['album']
            ).first()

            if album:
                album_id = album.id
                album.local_playcount += 1

        # PG 9.5+: DO NOTHING if duplicate
        query = insert(Scrobble).values(
            user_id=session.user_id,
            token_id=session.token_id,
            played_at=data.pop('timestamp'),
            artist_id=artist_id,
            album_id=album_id,
            **data
        ).on_conflict_do_nothing(
            index_elements=['user_id', 'played_at', 'artist', 'track']
        )
        db.session.execute(query)
        # PG <9.5
        # scrobble = Scrobble(
        #     user_id=session.user_id,
        #     played_at=data.pop('timestamp'),
        #     artist_id=artist_id,
        #     **data
        # )
        # db.session.add(scrobble)

    db.session.commit()

    return api_response('OK')


@blueprint.route('/1.0/rw/xmlrpc.php', methods=['POST'])
def xmlrpc():
    return PONG


@blueprint.route('/ass/upgrade.xml.php', methods=['GET', 'POST'])
def update_check():
    return UPDATE_CHECK


@blueprint.route('/radio/handshake.php')
def radio_handshake():
    return RADIO_HANDSHAKE
