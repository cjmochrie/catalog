import random

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, CatalogItem


# Connect to Database and create database session
engine = create_engine('postgresql://catalog:123@udacity/catalog')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Define some placeholder categories, items, images, and description
categories = ['Soccer', 'Basketball', 'Baseball', 'Frisbee', 'Snowboarding']
items = ['Cleats', 'Helmet', 'Pants', 'Boards']
images = ['baseball.jpg', 'frisbee.jpg', 'golf.jpg', 'hockey.jpg']
description = """Lorem ipsum blah blah blah Lorem ipsum blah blah blah
      Lorem ipsum blah blah blahLorem ipsum blah blah blahLorem ipsum blah blah blah"""

# Create a 'TestUser' that will be adding these items to the database
user = User(name='TestUser', email='testemail@example.com',
            picture='images/cartoon.png')
session.add(user)
session.commit()
user_id = session.query(User).filter_by(
    email='testemail@example.com').first().id

# Add 50 items to the database with random combinations of names,
# descriptions, categories and images
for i in range(0, 50):
    item = CatalogItem(name=random.choice(items), description=description,
                       category=random.choice(categories), image=random.choice(images), user_id=user_id)
    session.add(item)
    session.commit()

items = session.query(CatalogItem).all()

# Print out the database as a check
for item in items:
    print str(item.serialize)
