#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort, jsonify
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from datetime import datetime
import pytz
import sys
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

from models import *

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------
@app.route('/venues')
def venues():
  #       num_shows should be aggregated based on number of upcoming shows per venue.
  venues = Venue.query.order_by(Venue.city, Venue.state).all()

  data = []

  current_city = ''

  i = -1
  for venue in venues:
    num_shows = db.session.query(Show).join(Artist).filter(Show.venue_id==venue.id).filter(
      Show.start_time > datetime.now()
    ).count()

    if current_city == venue.city:
      venue_data = {
        'id': venue.id,
        'name': venue.name,
        'num_upcoming_shows': num_shows
      }
      data[i]['venues'].append(venue_data)
    else:
      i += 1
      current_city = venue.city
      city_data = {
        'city': venue.city,
        'state': venue.state,
        'venues': [
          {
            'id': venue.id,
            'name': venue.name,
            'num_upcoming_shows': num_shows
          }
        ]
      }
      data.append(city_data)


  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
  search_term=request.form.get('search_term', '')

  venues = Venue.query.filter(Venue.name.ilike(f'%{search_term}%'))

  venues_data = []

  for venue in venues:
    num_shows = db.session.query(Show).join(Artist).filter(Show.venue_id==venue.id).filter(
      Show.start_time > datetime.now()
    ).count()

    venues_data.append({
      'id': venue.id,
      'name': venue.name,
      'num_upcoming_shows': num_shows
    })

  response = {
    'count': venues.count(),
    'data': venues_data
  }

  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  venue = Venue.query.get(venue_id)

  if not venue:
    abort(404)

  upcoming_shows = []
  past_shows = []
  now = datetime.now().astimezone(pytz.UTC)

  shows = db.session.query(Show).join(Artist).filter(Show.venue_id==venue.id)
  
  for show in shows:
    show_data = {
      'artist_id': show.artist_id,
      'artist_name': show.artist.name,
      'artist_image_link': show.artist.image_link,
      'start_time': show.start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    }

    if show.start_time.astimezone(pytz.UTC) > now:
      upcoming_shows.append(show_data)
    else:
      past_shows.append(show_data)

  venue_data = {
    'id': venue.id,
    'name': venue.name,
    'genres': venue.genres,
    'address': venue.address,
    'city': venue.city,
    'state': venue.state,
    'phone': venue.phone,
    'website': venue.website,
    'facebook_link': venue.facebook_link,
    'seeking_talent': venue.seeking_talent,
    'seeking_description': venue.seeking_description,
    'image_link': venue.image_link,
    'past_shows': past_shows,
    'upcoming_shows': upcoming_shows,
    'past_shows_count': len(past_shows),
    'upcoming_shows_count': len(upcoming_shows)
  }

  return render_template('pages/show_venue.html', venue=venue_data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  error = False

  form = VenueForm(request.form)
  try:
    if form.validate_on_submit():
      venue = Venue(
        name=form.name.data,
        city=form.city.data,
        state=form.state.data,
        address=form.address.data,
        phone=form.phone.data,
        image_link=form.image_link.data,
        facebook_link=form.facebook_link.data,
        website=form.website_link.data,
        genres=form.genres.data,
      )

      db.session.add(venue)
      db.session.commit()
    else:
      error = True
  except:
    db.session.rollback()
    error = True
    print(sys.exc_info())
  finally:
    db.session.close()

  if error:
    flash('An error occurred. Venue ' + form.name.data + ' could not be listed.')
  else:
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
  error = False

  venue = Venue.query.get(venue_id)

  if not venue:
    abort(404)

  try:
    Show.query.filter_by(venue_id=venue_id).delete()
    Venue.query.filter_by(id=venue_id).delete()
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info)
  finally:
    db.session.close()
  
  if error:
    abort(500)
  else:
    return jsonify({'success': True})

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artists = Artist.query.all()

  data = []
  for artist in artists:
    data.append({
      'id': artist.id,
      'name': artist.name
    })
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".

  search_term=request.form.get('search_term', '')

  artists = Artist.query.filter(Artist.name.ilike(f'%{search_term}%'))
  artists_data = []

  for artist in artists:
    num_shows = db.session.query(Show).join(Venue).filter(Show.artist_id==artist.id).filter(
      Show.start_time > datetime.now()
    ).count()

    artists_data.append({
      'id': artist.id,
      'name': artist.name,
      'num_upcoming_shows': num_shows
    })

  response = {
    'count': artists.count(),
    'data': artists_data
  }
  
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the artist page with the given artist_id
  artist = Artist.query.get(artist_id)

  if not artist:
    abort(404)
  
  upcoming_shows = []
  past_shows = []

  shows = db.session.query(Show).join(Venue).filter(Show.artist_id==artist.id)

  for show in shows:
    show_data = {
      'venue_id': show.venue_id,
      'venue_name': show.venue.name,
      'venue_image_link': show.venue.image_link,
      'start_time': show.start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    }

    if show.start_time.astimezone(pytz.UTC) > datetime.now().astimezone(pytz.UTC):
      upcoming_shows.append(show_data)
    else:
      past_shows.append(show_data)

  artist_data = {
    'id': artist.id,
    'name': artist.name,
    'genres': artist.genres,
    'city': artist.city,
    'state': artist.state,
    'phone': artist.phone,
    'seeking_venue': artist.seeking_venue,
    'seeking_description': artist.seeking_description,
    'image_link': artist.image_link,
    'past_shows': past_shows,
    'upcoming_shows': upcoming_shows,
    'past_shows_count': len(past_shows),
    'upcoming_shows_count': len(upcoming_shows)
  }
  # data = list(filter(lambda d: d['id'] == artist_id, [data1, data2, data3]))[0]
  return render_template('pages/show_artist.html', artist=artist_data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist={
    "id": 4,
    "name": "Guns N Petals",
    "genres": ["Rock n Roll"],
    "city": "San Francisco",
    "state": "CA",
    "phone": "326-123-5000",
    "website": "https://www.gunsnpetalsband.com",
    "facebook_link": "https://www.facebook.com/GunsNPetals",
    "seeking_venue": True,
    "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
    "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80"
  }

  artist = Artist.query.get(artist_id)

  if not artist:
    abort(404)

  form = ArtistForm(obj=artist)

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # artist record with ID <artist_id> using the new attributes
  error = False
  artist = Artist.query.get(artist_id)

  if not artist:
    abort(404)

  try:
    form = ArtistForm(request.form)

    if form.validate_on_submit():
      form.populate_obj(artist)
      db.session.add(artist)
      db.session.commit()
    else:
      error = True
  except:
    error = True
    db.rollback()
    print(sys.exc_info())
  
  if error:
    abort(500)

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue={
    "id": 1,
    "name": "The Musical Hop",
    "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
    "address": "1015 Folsom Street",
    "city": "San Francisco",
    "state": "CA",
    "phone": "123-123-1234",
    "website": "https://www.themusicalhop.com",
    "facebook_link": "https://www.facebook.com/TheMusicalHop",
    "seeking_talent": True,
    "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
    "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60"
  }

  venue = Venue.query.get(venue_id)
  if not venue:
    abort(404)

  form = VenueForm(obj=venue)
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # venue record with ID <venue_id> using the new attributes
  error = False
  
  venue = Venue.query.get(venue_id)
  if not venue:
    abort(404)

  try:
    form = VenueForm(request.form)

    if form.validate_on_submit():
      form.populate_obj(venue)
      db.session.add(venue)
      db.session.commit()
    else:
      error = True
  except:
    error = True
    db.rollback()
    print(sys.exc_info())
  finally:
      db.session.close()
  if error:
      abort(500)
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

  error = False

  form = ArtistForm(request.form)

  try:
    if form.validate_on_submit():
      artist = Artist(
        name=form.name.data,
        city=form.city.data,
        state=form.state.data,
        phone=form.phone.data,
        genres=form.genres.data,
        image_link=form.image_link.data,
        facebook_link=form.facebook_link.data,
        website=form.website_link.data,
        seeking_venue=form.seeking_venue.data,
        seeking_description=form.seeking_description.data
      )
      db.session.add(artist)
      db.session.commit()
    else:
      error = True
  except:
    db.session.rollback()
    error = True
    print(sys.exc_info)
  finally:
    db.session.close()
  
  if error:
    flash('An error occurred. Artist ' + form.name.data + ' could not be listed.')
  else:
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  #       num_shows should be aggregated based on number of upcoming shows per venue.
  data = []
  shows = Show.query.all()

  for show in shows:
    data.append({
      'venue_id': show.venue_id,
      'venue_name': show.venue.name,
      'artist_id': show.artist_id,
      'artist_name': show.artist.name,
      'artist_image_link': show.artist.image_link,
      'start_time': show.start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    })

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  error = False

  form = ShowForm(request.form)

  try:
    if form.validate_on_submit():
      show = Show(
        venue_id=form.venue_id.data,
        artist_id=form.artist_id.data,
        start_time=form.start_time.data
      )
      db.session.add(show)
      db.session.commit()
    else:
      error = True
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  if error:
    flash('An error occurred. Show could not be listed.')
  else:
    flash('Show was successfully listed!')

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

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
