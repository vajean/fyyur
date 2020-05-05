# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import json
import itertools
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from sqlalchemy import func
from sqlalchemy.orm import defer, undefer
from sqlalchemy.sql.functions import now

from forms import *
from flask_migrate import Migrate

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)


# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(200))
    website = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean(), nullable=True, default=False)
    seeking_description = db.Column(db.String(250))
    shows = db.relationship('Show', backref='venue', lazy=True)


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(200))
    image_link = db.Column(db.String(500))
    website = db.Column(db.String(120))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean(), nullable=True, default=False)
    seeking_description = db.Column(db.String(250))
    shows = db.relationship('Show', backref='artist', lazy=True)


class Show(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'))
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'))


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Utils.
# ----------------------------------------------------------------------------#

# implement a counter on the number of upcoming shows
def upcoming_shows_counter(id, param):
    counter = 0
    if param == 'artist':
        shows = Show.query.filter_by(artist_id=id)
        for show in shows:
            if show.date >= datetime.now():
                counter += 1
    if param == 'venue':
        shows = Show.query.filter_by(venue_id=id)
        for show in shows:
            if show.date >= datetime.now():
                counter += 1
    return counter


def past_shows_counter(id, param):
    counter = 0
    if param == 'artist':
        shows = Show.query.filter_by(artist_id=id)
        for show in shows:
            if show.date <= datetime.now():
                counter += 1
    if param == 'venue':
        shows = Show.query.filter_by(venue_id=id)
        for show in shows:
            if show.date <= datetime.now():
                counter += 1
    return counter


# implement a basic name search function takes a query and a search term as arguments
def basic_name_search(query, search_term, param):
    search_hits = []
    search_term = search_term.strip().lower()
    for row in query:
        name = row.name.lower()
        hit = name.find(search_term)
        if hit != -1:
            search_hits.append({
                'id': row.id,
                'name': row.name,
                'num_upcoming_shows': upcoming_shows_counter(row.id, param)
            })
    return search_hits


# search function that looks for city and state matches
# allows for city and state search (works with or without the coma)
# aswell only city search

def location_search(query, search_term, param):
    search_hits = []
    search_term = search_term.lower().split()
    search_city = search_term[0].strip(',')
    if len(search_term) != 1:
        search_state = search_term[1]
        for row in query:
            city = row.city.lower()
            state = row.state.lower()
            if search_city == city and search_state == state:
                search_hits.append({
                    'id': row.id,
                    'name': row.name,
                    'num_upcoming_shows': upcoming_shows_counter(row.id, param)
                })
    else:
        for row in query:
            city = row.city.lower()
            if search_city == city:
                search_hits.append({
                    'id': row.id,
                    'name': row.name,
                    'num_upcoming_shows': upcoming_shows_counter(row.id, param)
                })
    return search_hits


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    latest_artists = Artist.query.order_by(Artist.id.desc()).limit(10)
    latest_venues = Venue.query.order_by(Venue.id.desc()).limit(10)
    return render_template('pages/home.html', latest_artists=latest_artists, latest_venues=latest_venues)


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    # Retrieve data from DB and sort it by City, State
    data = Venue.query.all()
    areas = {}
    for venue in data:
        if venue.city + ', ' + venue.state not in areas:
            areas[venue.city + ', ' + venue.state] = []
            areas[venue.city + ', ' + venue.state].append(venue)
        else:
            areas[venue.city + ', ' + venue.state].append(venue)
    return render_template('pages/venues.html', areas=areas);


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form['search_term']
    # Query only venue IDs and names and perform a search on the Python objects rather than the database
    venues = Venue.query.options(defer('*'), undefer("id"), undefer("name"))

    search = basic_name_search(venues, search_term, 'venue')
    # if name search returns 0 results, try city search using the same term
    if len(search) == 0:
        search = location_search(venues, search_term, 'venue')
        response = {}
        response['count'] = len(search)
        response['data'] = search
    else:
        response = {}
        response['count'] = len(search)
        response['data'] = search

    return render_template('pages/search_venues.html', results=response,
                           search_term=search_term)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    join = Venue.query.outerjoin(Show).filter(Venue.id == venue_id).first()
    join.upcoming_shows = [show for show in join.shows if show.date >= datetime.now()]
    join.upcoming_shows_count = upcoming_shows_counter(join.id, 'venue')
    join.past_shows_count = past_shows_counter(join.id, 'venue')
    join.past_shows = [show for show in join.shows if show.date <= datetime.now()]
    return render_template('pages/show_venue.html', venue=join)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    try:
        form = request.form

        try:
            form['seeking_talent'] == 'y'
            seeking = True
        except:
            seeking = False
        venue = Venue(name=form['name'], city=form['city'], state=form['state'],
                      address=form['address'], phone=form['phone'], genres=form.getlist('genres'),
                      facebook_link=form['facebook_link'], image_link=form['image_link'],
                      website=form['website'], seeking_talent=seeking,
                      seeking_description=form['seeking_description'])
        db.session.add(venue)
        db.session.commit()
        # on successful db insert, flash success
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except (RuntimeError, TypeError, NameError):
        db.session.rollback()
        flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
        # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    finally:
        db.session.close()

    return render_template('pages/home.html')


@app.route('/venues/<venue_id>/delete', methods=['POST'])
# As HTTP does not allow DELETE method in forms, and I don't want to use any AJAX
# I changed the endpoint for handling deletes to use post method on venue_id/delete
def delete_venue(venue_id):
    # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
    try:
        Venue.query.filter_by(id=venue_id).delete()
        db.session.commit()
        flash('Venue was successfully deleted!')
    except:
        db.session.rollback()
        flash('Venue not deleted!')
    finally:
        db.session.close()
    # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage
    return redirect(url_for('venues'))


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = Artist.query.all()
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form['search_term']

    # Query only venue IDs and names and perform a search on the Python objects rather than the database
    artists = Artist.query.options(defer('*'), undefer("id"), undefer("name"))

    search = basic_name_search(artists, search_term, 'artist')
    #if name search returns 0 results, try city search using the same term
    if len(search) == 0:
        search = location_search(artists, search_term, 'artist')
        response = {}
        response['count'] = len(search)
        response['data'] = search
    else:
        response = {}
        response['count'] = len(search)
        response['data'] = search

    return render_template('pages/search_venues.html', results=response,
                           search_term=search_term)


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the venue page with the given venue_id
    join = Artist.query.outerjoin(Show).filter(Artist.id == artist_id).first()
    join.upcoming_shows = [show for show in join.shows if show.date >= datetime.now()]
    join.upcoming_shows_count = upcoming_shows_counter(join.id, 'artist')
    join.past_shows_count = past_shows_counter(join.id, 'artist')
    join.past_shows = [show for show in join.shows if show.date <= datetime.now()]
    return render_template('pages/show_artist.html', artist=join)


@app.route('/test')
def test():
    data1 = Artist.query.join(Show)
    return render_template('pages/test.html', data1=data1, time=datetime.now())


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    try:
        form = request.form
        old_artist = Artist.query.get(artist_id)
        # get all column keys using __table__ attribute and set each column
        # using __setattr__ instead of going through each attribute manually
        for column in Artist.__table__.columns.keys():
            if column != 'id':
                if column == 'genres':
                    old_artist.__setattr__(column, form.getlist('genres'))
                elif column == 'seeking_venue':
                    # the form[seeking_venue] does not exist if not ticked, using a try to verify instead of if
                    try:
                        form[column] == 'y'
                        seeking = True
                    except:
                        seeking = False
                    old_artist.__setattr__(column, seeking)
                else:
                    old_artist.__setattr__(column, form[column])

        db.session.commit()
        # on successful db insert, flash success
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except (RuntimeError, TypeError, NameError):
        db.session.rollback()
        flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
        # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    finally:
        db.session.close()
    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/artists/<artist_id>/delete', methods=['POST'])
# As HTTP does not allow DELETE method in forms, and I don't want to use any AJAX
# I changed the endpoint for handling deletes to use post method on artist_id/delete
def delete_artist(artist_id):
    # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
    try:
        Artist.query.filter_by(id=artist_id).delete()
        db.session.commit()
        flash('Venue was successfully deleted!')
    except:
        db.session.rollback()
        flash('Venue not deleted!')
    finally:
        db.session.close()
    # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage
    return redirect(url_for('artists'))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get(venue_id)
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    # venue record with ID <venue_id> using the new attributes
    try:
        form = request.form
        old_venue = Venue.query.get(venue_id)
        # get all column keys using __table__ attribute and set each column
        # using __setattr__ instead of going through each attribute manually
        for column in Venue.__table__.columns.keys():
            if column != 'id':
                if column == 'genres':
                    old_venue.__setattr__(column, form.getlist('genres'))
                elif column == 'seeking_talent':
                    # the form[seeking_talent] does not exist if not ticked, using a try to verify instead of if
                    try:
                        form[column] == 'y'
                        seeking = True
                    except:
                        seeking = False
                    old_venue.__setattr__(column, seeking)
                else:
                    old_venue.__setattr__(column, form[column])

        db.session.commit()
        # on successful db insert, flash success
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except (RuntimeError, TypeError, NameError):
        db.session.rollback()
        flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
        # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    finally:
        db.session.close()
    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    # called upon submitting the new artist listing form
    try:
        form = request.form
        try:
            form['seeking_venue'] == 'y'
            seeking = True
        except:
            seeking = False
        artist = Artist(name=form['name'], city=form['city'], state=form['state'],
                        phone=form['phone'], genres=form.getlist('genres'), website=form['website'],
                        facebook_link=form['facebook_link'], image_link=form['image_link'],
                        seeking_venue=seeking, seeking_description=form['seeking_description'])
        db.session.add(artist)
        db.session.commit()
        # on successful db insert, flash success
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except (RuntimeError, TypeError, NameError):
        db.session.rollback()
        flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
    finally:
        db.session.close()

    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    shows = []
    data = Show.query.all()
    for show in data:
        shows.append({
            "venue_id": show.venue_id,
            "venue_name": show.venue.name,
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": str(show.date)
        })
    return render_template('pages/shows.html', shows=shows)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = request.form
    artist_id = form['artist_id']
    venue_id = form['venue_id']

    ## Check if the artist and venue IDs exist, if not return flash messages
    artist_exists = Artist.query.get(artist_id)
    venue_exists = Venue.query.get(venue_id)

    if artist_exists and venue_exists:
        show = Show(date=form['start_time'], artist_id=artist_id, venue_id=venue_id)
        db.session.add(show)
        db.session.commit()
        # on successful db insert, flash success
        flash('Show was successfully listed!')
    else:
        if artist_exists is None:
            flash('Artist ID not found')
        if venue_exists is None:
            flash('Venue ID not found')
        render_form = ShowForm()
        return render_template('forms/new_show.html', form=render_form)
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run(port=5000)

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
