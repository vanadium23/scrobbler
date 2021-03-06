"""A simple Flask extension that handles Last.fm API."""

import logging

import pylast

from .helpers import remove_html_tags


logger = logging.getLogger(__name__)


class LastFM(pylast.LastFMNetwork):
    _connected = False

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app

    def _connect(self):
        try:
            super(LastFM, self).__init__(
                api_key=self.app.config['LASTFM_API_KEY'],
                api_secret=self.app.config['LASTFM_API_SECRET'],
                username=self.app.config['LASTFM_USERNAME'],
                password_hash=pylast.md5(self.app.config['LASTFM_PASSWORD'])
            )

            self.enable_caching()

            self._connected = True
        except pylast.MalformedResponseError:
            logger.warning("[Flask_LastFM] Got a malformed response. Please check "
                           "that you are not overriding Last.FM servers in /etc/hosts")

    def artist(self, artist_name, tags=20):
        """Retrieves artist metadata with additional stuff (bio, image, tags etc.)"""

        if not self._connected:
            self._connect()

        data = {
            'name': None,
            'name_fixed': None,
            'tags': {},
            'bio': None,
            'image': None,
            'playcount': None,
            'mbid': None,
        }

        try:
            artist_info = self.get_artist(artist_name)
            data['name'] = artist_info.name
            data['name_fixed'] = artist_info.get_correction()

            data['tags'] = artist_info.get_top_tags()
            data['tags'] = {tag.item.name.lower(): int(tag.weight) for tag in data['tags'][:tags]}

            data['bio'] = artist_info.get_bio_summary()
            data['bio'] = data['bio'].replace('Read more on Last.fm', '')
            data['bio'] = remove_html_tags(data['bio']).strip()

            data['image'] = artist_info.get_cover_image()
            data['playcount'] = artist_info.get_playcount()
            data['mbid'] = artist_info.get_mbid()

        except Exception:
            self._connected = False
            logger.error(
                'Something went wrong! :( Connection was reset for the good.', exc_info=True)
            return False

        return data
