__author__ = 'Cameron'
import random
import string
import os
import httplib2
import json
import requests
import os

from flask import Flask, render_template, request, redirect, jsonify, url_for, flash, make_response
from flask import session as login_session
from flask.ext.seasurf import SeaSurf

from sqlalchemy import create_engine, asc, func
from sqlalchemy.orm import sessionmaker

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

from dict2xml import dict2xml as xmlify

from database_setup import Base, User, CatalogItem

app = Flask(__name__, static_folder='static')

# Implement SeaSurf extension for preventing cross-site request forgery
csrf = SeaSurf(app)

dirname, filename = os.path.split(os.path.abspath(__file__))

CLIENT_ID = json.loads(app.open_resource('static/client_secrets.json').read())['web']['client_id']
APPLICATION_NAME = "Catalog App"

# TEMPLATES
LOGIN_TEMPLATE = "login_template.html"
MAINPAGE_TEMPLATE = "mainpage_template.html"
CATEGORY_TEMPLATE = "category_template.html"
ITEM_TEMPLATE = "item_template.html"
ADD_ITEM_TEMPLATE = "add_item_template.html"
EDIT_ITEM_TEMPLATE = "edit_item_template.html"
DELETE_ITEM_TEMPLATE = "delete_item_template.html"

# STATIC FOLDERS
STATIC_IMAGES = "static/images/"


def checkLogin():
    if 'user_id' in login_session:
        return True
    else:
        return False

# Return a list of distinct categories in the database
def getCategories():
    categories = []
    for category in session.query(CatalogItem.category).distinct():
        categories.append(category[0])
    return categories

#
# HANDLERS
#

# Mainpage handler
@app.route('/')
@app.route('/catalog/')
def mainPage():

    # Render the last 10 items created
    items = session.query(CatalogItem).order_by(
        CatalogItem.id.desc()).limit(10)
    categories = getCategories()
    # Count the number of items in the catalog
    count = session.query(CatalogItem).count()
    return render_template(MAINPAGE_TEMPLATE, categories=categories, items=items,
                           count=count, login_session=login_session, logged_in=checkLogin())

# Category Handler
@app.route('/catalog/<string:category>/')
@app.route('/catalog/<string:category>/items/')
def categoryPage(category):

    # Render every item in the category and count
    items = session.query(CatalogItem).filter_by(category=category).all()
    count = len(items)
    categories = getCategories()
    return render_template(CATEGORY_TEMPLATE, items=items,
                           categories=categories, count=count, login_session=login_session)

# Item handler
@app.route('/catalog/<string:category>/<int:item_id>/')
def itemPage(category, item_id):

    # Render the item along with the name of the user that created it
    item = session.query(CatalogItem).filter_by(id=item_id).one()
    creator = session.query(User).filter_by(id=item.user_id).one()

    # Pass a flag to determine whether to render edit/delete buttons
    can_edit = False
    if checkLogin():
        if login_session['user_id'] == item.user_id:
            can_edit = True

    categories = getCategories()
    return render_template(ITEM_TEMPLATE, item=item, categories=categories,
                           login_session=login_session, creator=creator.name, can_edit=can_edit)

# Add item handler
@app.route('/catalog/addItem', methods=['GET', 'POST'])
def addItem():

    if checkLogin() == False:
        flash('Only registered users my add items to the catalog. Please log in!')
        return redirect('/catalog/')

    if request.method == 'POST':

        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        image = request.form['image']

        if name != "" and description != "" and category != "":
            item = CatalogItem(name=name, description=description,
                               category=category, user_id=login_session['user_id'])

            # Use the image input field and name of item to write the file to disk
            # If the file can't be downloaded for any reason it will be ignored
            item.image = writeImage(name, image)
            session.add(item)
            session.commit()

            flash('Added ' + name + ' to the catalog!')
            return redirect(url_for('mainPage'))
        else:
            flash('Invalid input')
            return render_template(ADD_ITEM_TEMPLATE, login_session=login_session)

    else:
        return render_template(ADD_ITEM_TEMPLATE, login_session=login_session)

# Edit item handler
@app.route('/catalog/''/<int:item_id>/edit/', methods=['GET', 'POST'])
@app.route('/catalog/<string:category>/<int:item_id>/edit/', methods=['GET', 'POST'])
def editItem(category, item_id):

    item = session.query(CatalogItem).filter_by(id=item_id).one()

    # Check to see if user is authorized to edit this item.
    if login_session['user_id'] != item.user_id:
        flash('No access to editing this item')
        return redirect(url_for('itemPage', category=category, item_id=item_id))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        image = request.form['image']

        if name != "" and description != "" and category != "":
            item.name = name
            item.description = description
            item.category = category
            item.user_id = login_session['user_id']

            # Use the image input field and name of item to write the file to disk
            # If the file can't be downloaded for any reason it will be ignored
            item.image = writeImage(name, image)

            session.commit()
            flash('Edited ' + name + ' !')
            return redirect(url_for('itemPage', category=category, item_id=item_id))

        else:
            flash('Invalid edit made')
            return render_template(EDIT_ITEM_TEMPLATE, login_session=login_session, item=item)

    else:
        return render_template(EDIT_ITEM_TEMPLATE, login_session=login_session, item=item)

# Delete item handler
@app.route('/catalog/<string:category>/<int:item_id>/delete/', methods=['GET', 'POST'])
def deleteItem(category, item_id):

    item = session.query(CatalogItem).filter_by(id=item_id).one()
    creator = session.query(User).filter_by(id=item.user_id).one().name

    # Check to see if user is authorized to delete this item.
    if login_session['user_id'] != item.user_id:
        flash('No access to editing this item')
        return redirect(url_for('itemPage', category=category, item_id=item_id))

    name = item.name

    if request.method == 'POST':
        if item.image:
            # delete the iamge from the static folder
            os.remove(STATIC_IMAGES + item.image)

        session.delete(item)
        session.commit()
        flash('Deleted ' + name + ' from the catalog!')

        return redirect(url_for('mainPage'))
    else:
        return render_template(DELETE_ITEM_TEMPLATE, item=item, creator=creator, login_session=login_session)


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state

    return render_template(LOGIN_TEMPLATE, STATE=state, login_session=login_session)

# Couldn't figure out how to include the cookie in the AJAX request so exempted it from
# the CSRF. Protect add/edit/delete however
@csrf.exempt
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets(dirname + '/static/client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.to_json()
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None



# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gDisconnect():

    # Only disconnect a connected user.
    # Try-except structure to account for deleted cookies
    try:
        credentials = json.loads(login_session.get('credentials'))
    except TypeError:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = credentials['access_token']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    # if result['status'] == '200':
    #     # Reset the user's sesson.
    del login_session['credentials']
    del login_session['gplus_id']
    del login_session['username']
    del login_session['email']
    del login_session['picture']
    del login_session['user_id']
    del login_session['state']
    del login_session['provider']

    flash('Successfully disconnected.')
    return redirect(url_for('mainPage'))
    #
    # else:
    #     # For whatever reason, the given token was invalid.
    #     response = make_response(
    #         json.dumps('Failed to revoke token for given user.', 400))
    #     response.headers['Content-Type'] = 'application/json'
    #
    #     return response


#
# JSON Handlers
#

# Mainpage handler
@app.route('/json')
@app.route('/catalog/json/')
def mainPageJSON():

    items = session.query(CatalogItem).order_by(CatalogItem.id.desc()).all()
    return jsonify(CatalogItems=[i.serialize for i in items])

# Category Handler
@app.route('/catalog/<string:category>/json')
@app.route('/catalog/<string:category>/items/json')
def categoryPageJSON(category):

    items = session.query(CatalogItem).filter_by(category=category).all()
    return jsonify(CatalogItems=[i.serialize for i in items])

# Item handler
@app.route('/catalog/<string:category>/<int:item_id>/json')
def itemPageJSON(category, item_id):

    item = session.query(CatalogItem).filter_by(id=item_id).one()
    return jsonify(CatalogItem=[item.serialize])

#
# XML Handlers
#

# Mainpage handler
@app.route('/xml')
@app.route('/catalog/xml/')
def mainPageXML():

    items = session.query(CatalogItem).order_by(CatalogItem.id.desc()).all()
    return xmlify({'Catalog Item': [i.serialize for i in items]}, wrap='Catalog Items', indent='   ')

   # Category Handler
@app.route('/catalog/<string:category>/xml')
@app.route('/catalog/<string:category>/items/xml')
def categoryPageXML(category):

    items = session.query(CatalogItem).filter_by(category=category).all()
    return xmlify({'Catalog Item': [i.serialize for i in items]}, wrap='Catalog Items', indent='   ')

# Item handler
@app.route('/catalog/<string:category>/<int:item_id>/xml')
def itemPageXML(category, item_id):

    item = session.query(CatalogItem).filter_by(id=item_id).one()
    return xmlify(item.serialize, wrap='Catalog Item', indent='   ')


def writeImage(name, image_url):
    # Cribbed from http://stackoverflow.com/questions/9351765/how-do-i-save-a-file-using-pythons-httplib2
    # Only accept jpg image urls.
    # If input is satisfactory write to a randomized filename with name parameter prefix
    # and return the filename otherwise return nothing

    if image_url.endswith('jpg'):
        h = httplib2.Http('.cache')

        try:
            response, content = h.request(image_url)
            # Ensure the file was downloaded
            if response.status == 200:
                # create a filename to store the downloaded image
                filename = name + \
                    ''.join(random.choice(string.ascii_uppercase + string.digits)
                            for x in range(8)) + '.jpg'

                # write the file to the static image folder
                with open(STATIC_IMAGES + filename, 'wb') as f:
                    f.write(content)
                return filename

        except httplib2.ServerNotFoundError:
            return None
    return None

# Connect to Database and create database session
engine = create_engine('postgresql://catalog:123@udacity/catalog')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Program launcher - in debug mode
if __name__ == '__main__':
    app.debug = True
    app.run()