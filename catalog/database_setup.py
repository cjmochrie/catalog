from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), nullable=False)
    picture = Column(String(1000), nullable=True)


class CatalogItem(Base):
    __tablename__ = 'catalog_item'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(1000), nullable=False)
    category = Column(String(100), nullable=False)
    image = Column(String, nullable=True)

    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship(User)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'image': self.image,
            'id': self.id,
            'user': self.user_id
        }


# AT END OF FILE
engine = create_engine('postgresql://catalog:123@udacity/catalog')

Base.metadata.create_all(engine)
