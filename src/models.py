from sqlalchemy import Column, Integer, BigInteger, String, Text, ForeignKey, Float, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    memberships = relationship('GroupMember', back_populates='user')
    created_groups = relationship('Group', back_populates='creator')

class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=False)
    invite_code = Column(String(5), unique=True, nullable=False)
    creator_user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    creator = relationship('User', back_populates='created_groups')
    members = relationship('GroupMember', back_populates='group')

class GroupMember(Base):
    __tablename__ = 'group_members'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id', ondelete='CASCADE'))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    nickname = Column(String(64), nullable=False)
    photo_url = Column(String(255))
    geolocation_lat = Column(Float)
    geolocation_lon = Column(Float)
    city = Column(String(128))
    role = Column(String(32), default='member')
    joined_at = Column(DateTime, default=datetime.utcnow)
    balance = Column(Integer, default=0, nullable=False)
    
    group = relationship('Group', back_populates='members')
    user = relationship('User', back_populates='memberships')
    
    __table_args__ = (UniqueConstraint('group_id', 'user_id', name='_group_user_uc'),)

class GroupCreator(Base):
    __tablename__ = 'group_creators'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow) 