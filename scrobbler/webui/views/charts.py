import datetime

from flask import render_template
from flask.ext.login import current_user, login_required
from sqlalchemy import func

from scrobbler import app, db
from scrobbler.models import Scrobble
from scrobbler.webui.consts import PERIODS
from scrobbler.webui.helpers import get_argument
from scrobbler.webui.views import blueprint


@blueprint.route("/top/artists/")
@blueprint.route("/top/artists/<period>/")
@login_required
def top_artists(period=None):
    period, days = PERIODS.get(period, PERIODS['1w'])
    count = get_argument('count', default=app.config['RESULTS_COUNT'])

    scrobbles = func.count(Scrobble.artist).label('count')
    time_from = datetime.datetime.now() - datetime.timedelta(days=days)
    chart = (db.session
             .query(Scrobble.artist, scrobbles)
             .group_by(func.lower(Scrobble.artist))
             .filter(Scrobble.user_id == current_user.id)
             .filter(Scrobble.time >= time_from)
             .order_by(scrobbles.desc())
             .limit(count)
             .all()
             )

    max_count = chart[0][1]
    chart = enumerate(chart, start=1)

    return render_template(
        'charts/top_artists.html',
        period=period,
        chart=chart,
        max_count=max_count
    )


@blueprint.route("/top/tracks/")
@blueprint.route("/top/tracks/<period>/")
@login_required
def top_tracks(period=None):
    period, days = PERIODS.get(period, PERIODS['1w'])
    count = get_argument('count', default=app.config['RESULTS_COUNT'])

    scrobbles = func.count(Scrobble.artist).label('count')
    time_from = datetime.datetime.now() - datetime.timedelta(days=days)
    chart = (db.session
             .query(Scrobble.artist, Scrobble.track, scrobbles)
             .group_by(func.lower(Scrobble.artist), func.lower(Scrobble.track))
             .filter(Scrobble.user_id == current_user.id)
             .filter(Scrobble.time >= time_from)
             .order_by(scrobbles.desc())
             .limit(count)
             .all()
             )

    max_count = chart[0][2]
    chart = enumerate(chart, start=1)

    return render_template(
        'charts/top_tracks.html',
        period=period,
        chart=chart,
        max_count=max_count
    )


@blueprint.route("/top/tracks/yearly/")
@login_required
def top_tracks_yearly():
    scrobbles = func.count(Scrobble.artist).label('count')
    charts = {}

    year_from = 2006
    year_to = 2016
    stat_count = 10000
    show_count = 100

    for year in range(year_from, year_to + 1):
        time_from = datetime.datetime(year, 1, 1)
        time_to = datetime.datetime(year, 12, 31, 23, 59, 59, 999999)
        charts[year] = (db.session
                        .query(Scrobble.artist, Scrobble.track, scrobbles)
                        .filter(Scrobble.user_id == current_user.id)
                        .filter(Scrobble.time >= time_from, Scrobble.time <= time_to)
                        .group_by(func.lower(Scrobble.artist), func.lower(Scrobble.track))
                        .order_by(scrobbles.desc())
                        .limit(stat_count)
                        .all()
                        )

    position_changes = {}

    for year in range(year_from + 1, year_to + 1):

        chart = {
            '{} – {}'.format(artist, track): position for position, (artist, track, scrobbles) in enumerate(charts[year], 1)
        }

        prev_chart = {
            '{} – {}'.format(artist, track): position for position, (artist, track, scrobbles) in enumerate(charts[year - 1], 1)
        }

        prev_charts = (chart for chart_year, chart in charts.items() if chart_year < year)
        prev_tracks = {'{} – {}'.format(artist, track) for chart in prev_charts for (artist, track, scrobbles) in chart}

        if year not in position_changes:
            position_changes[year] = {}

        for title in chart:
            if title in prev_chart:
                position_changes[year][title] = prev_chart[title] - chart[title]
            elif title not in prev_tracks:
                position_changes[year][title] = 'new'

    charts = sorted(charts.items())

    return render_template(
        'charts/top_tracks_yearly.html',
        charts=charts,
        position_changes=position_changes,
        show_count=show_count
    )


@blueprint.route("/top/artists/yearly/")
@login_required
def top_artists_yearly():
    scrobbles = func.count(Scrobble.artist).label('count')
    charts = {}

    year_from = 2006
    year_to = 2016
    stat_count = 1000
    show_count = 100

    for year in range(year_from, year_to + 1):
        time_from = datetime.datetime(year, 1, 1)
        time_to = datetime.datetime(year, 12, 31, 23, 59, 59, 999999)
        charts[year] = (db.session
                        .query(Scrobble.artist, scrobbles)
                        .filter(Scrobble.user_id == current_user.id)
                        .filter(Scrobble.time >= time_from, Scrobble.time <= time_to)
                        .group_by(func.lower(Scrobble.artist))
                        .order_by(scrobbles.desc())
                        .limit(stat_count)
                        .all()
                        )

    position_changes = {}

    for year in range(year_from + 1, year_to + 1):
        chart = {artist: position for position, (artist, scrobbles) in enumerate(charts[year], 1)}
        prev_chart = {
            artist: position for position, (artist, scrobbles) in enumerate(charts[year - 1], 1)
        }

        prev_charts = (chart for chart_year, chart in charts.items() if chart_year < year)
        prev_artists = {artist for chart in prev_charts for (artist, scrobbles) in chart}

        if year not in position_changes:
            position_changes[year] = {}

        for artist, data in chart.items():
            if artist in prev_chart:
                position_changes[year][artist] = prev_chart[artist] - chart[artist]
            elif artist not in prev_artists:
                position_changes[year][artist] = 'new'

    charts = sorted(charts.items())

    return render_template(
        'charts/top_artists_yearly.html',
        charts=charts,
        position_changes=position_changes,
        show_count=show_count
    )