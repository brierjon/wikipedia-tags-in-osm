#! /usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright 2013 Fondazione Bruno Kessler
#  Author: <consonni@fbk.eu>
#  This work has been funded by Fondazione Bruno Kessler (Trento, Italy)
#  within the activities of the Digital Commons Lab
#
#  This file is part of wikipedia-tags-in-osm.
#  wikipedia-tags-in-osm is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  wikipedia-tags-in-osm is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with wikipedia-tags-in-osm.
#  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import urllib
import ConfigParser as configparser
from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import session
from flask import abort
from flask_mwoauth import MWOAuth
from jinja2 import Environment
from urlparse import urlparse
import binascii

from diff import get_difftable_difflib
from templates import find_coords_templates, get_new_text

app = Flask(__name__)

app.config.update(
    DEBUG=True,
    PROPAGATE_EXCEPTIONS=True
)

BASEDIR = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILENAME = 'settings.cfg'
CONFIG_FILE = os.path.realpath(
    os.path.join('..', 'wtosm', CONFIG_FILENAME))

# development settings
# CONFIG_FILENAME = 'settings.dev.cfg'
# CONFIG_FILE = os.path.realpath(
#    os.path.join('..', 'wtosm', 'dev', CONFIG_FILENAME))

config = configparser.ConfigParser()
config.read(CONFIG_FILE)

# print CONFIG_FILE

consumer_key = config.get('keys', 'consumer_key')
consumer_secret = config.get('keys', 'consumer_secret')

mwoauth = MWOAuth(base_url='https://it.wikipedia.org/w',
                  clean_url='https://it.wikipedia.org/wiki',
                  consumer_key=consumer_key,
                  consumer_secret=consumer_secret
                  )

app.register_blueprint(mwoauth.bp)

app.jinja_env.filters['unquote'] = urllib.unquote

templates_file = config.get('app', 'templates_file')

template_coords = []

try:
    from extract_templates import read
    template_coords = read(templates_file)
except:
    pass


def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = binascii.b2a_hex(os.urandom(24))
    return session['_csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token


@app.route("/")
def index():
    username = repr(mwoauth.get_current_user(False))
    return "logged in as: " + username + "<br />" + \
           "pippo 5<br />" + \
           '<a href="login">login</a> / <a href="logout">logout</a>'


@app.route("/login/success")
def login_success():
    username = repr(mwoauth.get_current_user(False))
    return render_template('loginsuccess.html',
                           username=username
                           )


def validate_parameters(args):
    try:
        lat = float(args.get('lat', ''))
        lon = float(args.get('lon', ''))
    except ValueError:
        lat = None
        lon = None

    title = urllib.quote(args.get('title', ''))

    dim = int(args.get('dim', 0))
    referrer = args.get('ref', '')
    id_ = args.get('id', '')

    error = 0
    if not (lat and lon and title):
        error = 1
        parameters = {'lat': "La latitudine dell'oggetto",
                      'lon': "La longitudine dell'oggetto",
                      'title': "Il titolo della corrispondente voce"
                               "di Wikipedia"
                      }
        optional = {'dim': "La dimensione lineare dell'oggetto"
                           "ad esempio la sua diagonale nel caso di "
                           "un'edificio",
                    'ref': "La pagina referrer che ti ha inviato qui",
                    'id': "L'id del link che ti ha inviato qui"
                    }
    else:
        parameters = {'lat': lat,
                      'lon': lon,
                      'title': title
                      }
        optional = {'dim': dim,
                    'ref': referrer,
                    'id': id_
                    }

    return parameters, optional, error


@app.route("/map")
def show_map():
    parameters, optional, error = validate_parameters(request.args)

    if error:
        return render_template('missingparameters.html',
                               parameters=parameters,
                               optional=optional
                               )

    return render_template('wikimap.html',
                           lat=parameters['lat'],
                           lon=parameters['lon'],
                           title=urllib.quote_plus(parameters['title']),
                           dim=optional['dim'],
                           referrer=urllib.quote_plus(optional['referrer']),
                           id=optional['id']
                           )


def get_domain(url):
    parsed_uri = urlparse(mwoauth.base_url)
    domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
    return domain


@app.route("/preview")
def preview():
    parameters, optional, error = validate_parameters(request.args)

    if error:
        return render_template('missingparameters.html',
                               parameters=parameters,
                               optional=optional
                               )

    next_url = 'preview?'\
               'lat={lat}'\
               '&lon={lon}'\
               '&title={title}'\
               '&dim={dim}'

    next_url = next_url.format(lat=parameters['lat'],
                               lon=parameters['lon'],
                               title=parameters['title'],
                               dim=optional['dim']
                               )

    if optional['ref']:
        next_url = next_url + '&ref={ref}'.format(ref=optional['ref'])

    if optional['id']:
        next_url = next_url + '&id={id}'.format(id=optional['id'])

    next_url = urllib.quote_plus(next_url)

    if mwoauth.get_current_user(False) is None:
        return redirect('../app/login?next={next}'.format(next=next_url))
    else:
        title = parameters['title']
        clear_title = urllib.unquote_plus(title).replace('_', ' ')
        token_req = mwoauth.request({'action': 'query',
                                     'titles': clear_title,
                                     'prop': 'info|revisions',
                                     'rvprop': 'timestamp|user'
                                               '|comment|content',
                                     'rvlimit': 1,
                                     'intoken': 'edit'
                                     })

        try:
            pageid = token_req['query']['pages'].keys()[0]
        except KeyError:
            info = token_req['error']['info']
            return render_template('error.html', info=info)

        pages = token_req['query']['pages']

        if pageid == '-1':
            if pages[pageid].get('missing', None) is not None:
                domain = get_domain(mwoauth.base_url)
                return render_template('missing.html',
                                       title=clear_title,
                                       site=domain)

        token = token_req['query']['pages'][pageid]['edittoken']

        revs = token_req['query']['pages'][pageid]['revisions'][0]

        old_text = revs['*']

        template = find_coords_templates(old_text)

        new_text, old_text, section = get_new_text(lat=parameters['lat'],
                                                   lon=parameters['lon'],
                                                   dim=optional['dim'],
                                                   old_text=old_text,
                                                   template=template
                                                   )

        difftable = get_difftable_difflib(old_text, new_text, pageid, section)

        return render_template('preview.html',
                               difftable=difftable,
                               new_text=new_text,
                               rows=len(new_text.split('\n')),
                               title=title,
                               section=section,
                               edit_token=token
                               )


def mock_success():
    result = dict()
    result['edit'] = dict()
    result['edit']['result'] = 'Success'
    result['edit']['newrevid'] = 1

    return result


@app.route("/edit", methods=['POST'])
def edit():

    print "This is /edit"

    csrf_token = session.pop('_csrf_token', None)
    if not csrf_token or csrf_token != request.form.get('_csrf_token'):
        abort(403)

    if mwoauth.get_current_user(False) is None:
        return 'Something went wrong, you are not logged in'
    else:
        edit_token = request.form['edit_token']
        title = request.form['title']
        new_text = request.form['new_text']
        summary = '[wtosm] aggiunta coordinate'
        section = request.form['section']
        referrer = request.form['referrer']

        edit_query = {'action': 'edit',
                      'title': title,
                      'summary': summary,
                      'text': new_text.encode('utf-8'),
                      'token': edit_token
                      }

        if section != '-1':
            edit_query['section'] = int(section)

        # result = mwoauth.request(edit_query)

        result = mock_success()

        try:
            assert(result['edit']['result'] == 'Success')
            link = mwoauth.base_url + '/wiki/' + title
            if 'nochange' in result['edit']:
                return render_template('nochange.html',
                                       link=link,
                                       title=title,
                                       )
            elif 'newrevid' in result['edit']:
                return render_template('success.html',
                                       link=link,
                                       title=title,
                                       summary=summary,
                                       referrer=referrer
                                       )

        except Exception as e:
            print e

            try:
                info = result['error']['info']
            except:
                info = None

            if info:
                return render_template('error.html', info=info)
            else:
                return render_template('error.html',
                                       info="Nessuna informazione")


@app.route("/edit/test", methods=['POST'])
def edit_test():

    print "This is /edit/test"

    csrf_token = session.pop('_csrf_token', None)
    if not csrf_token or csrf_token != request.form.get('_csrf_token'):
        abort(403)

    if mwoauth.get_current_user(False) is None:
        return 'Something went wrong, you are not logged in'
    else:
        edit_token = request.form['edit_token']
        title = request.form['title']
        new_text = request.form['new_text']
        summary = '[wtosm] aggiunta coordinate'
        section = request.form['section']

        edit_query = {'action': 'edit',
                      'title': 'Utente:CristianCantoro'
                               '/Sandbox/wtosm',
                      'summary': summary,
                      'text': new_text.encode('utf-8'),
                      'token': edit_token
                      }

        if section != '-1':
            edit_query['section'] = int(section)

        # result = mwoauth.request(edit_query)
        result = mock_success()

        try:
            assert(result['edit']['result'] == 'Success')
            message = 'Well done!'
        except:
            message = 'Oh Noes!'

        return message

if __name__ == "__main__":
    from werkzeug.wsgi import DispatcherMiddleware
    from flask import redirect
    from flask import send_from_directory

    app.secret_key = "local secret is secret"

    @app.route('/css/<path:filename>')
    def serve_css(filename):
        return send_from_directory('css', filename)

    @app.route('/js/<path:filename>')
    def serve_js(filename):
        return send_from_directory('js', filename)

    @app.route('/lib/<path:filename>')
    def serve_lib(filename):
        return send_from_directory('lib', filename)

    @app.route('/img/<path:filename>')
    def serve_img(filename):
        return send_from_directory('img', filename)

    redirect_app = Flask(__name__)

    @redirect_app.route('/')
    @redirect_app.route('/app')
    def app_index():
        oauth_verifier = request.args.get('oauth_verifier')
        oauth_token = request.args.get('oauth_token')
        if oauth_verifier and oauth_token:
            return redirect('http://wtosmtest.it/app/oauth-callback'
                            '?oauth_verifier={oauth_verifier}'
                            '&oauth_token={oauth_token}'.format(
                                oauth_verifier=oauth_verifier,
                                oauth_token=oauth_token)
                            )
        else:
            return redirect('/app/')

    base_app = Flask(__name__)

    base_app.config.update(
        DEBUG=True,
        PROPAGATE_EXCEPTIONS=True
    )

    base_app.wsgi_app = DispatcherMiddleware(redirect_app, {
        '/app':     app
    })

    base_app.run(host='localhost',
                 port=5000,
                 debug=True,
                 )
