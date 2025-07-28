from sqlalchemy import Column, Integer, BigInteger, String, Text, ForeignKey, Float, DateTime, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, UTC

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, unique=True, nullable=False)
    current_group_id = Column(Integer, ForeignKey('groups.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    language = Column(String(8), default='en')  # User language for multilingual support
    
    memberships = relationship('GroupMember', back_populates='user')
    created_groups = relationship('Group', back_populates='creator', foreign_keys='Group.creator_user_id')
    # current_group = relationship('Group', foreign_keys=[current_group_id])  # if needed

    # Runtime-only field (not persisted in DB)
    def __init__(self, *args, telegram_user_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.telegram_user_id = telegram_user_id

class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=False)
    invite_code = Column(String(5), unique=True, nullable=False)
    creator_user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    
    creator = relationship('User', back_populates='created_groups', foreign_keys=[creator_user_id])
    members = relationship('GroupMember', back_populates='group')

class GroupMember(Base):
    __tablename__ = 'group_members'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id', ondelete='CASCADE'), index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True)
    nickname = Column(String(64), nullable=True)
    photo_url = Column(String(255), nullable=True)
    geolocation_lat = Column(Float)
    geolocation_lon = Column(Float)
    city = Column(String(128), nullable=True)
    country = Column(String(128), nullable=True)  # Country of the user (optional)
    role = Column(String(32), default='member')
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    balance = Column(Integer, default=0, nullable=False)
    gender = Column(String(16), nullable=True)  # 'male', 'female'
    looking_for = Column(String(16), nullable=True)  # 'male', 'female', 'all'
    bio = Column(Text, nullable=True)  # short introduction text
    
    group = relationship('Group', back_populates='members')
    user = relationship('User', back_populates='memberships')
    
    __table_args__ = (UniqueConstraint('group_id', 'user_id', name='_group_user_uc'),)

class GroupCreator(Base):
    __tablename__ = 'group_creators'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id', ondelete='CASCADE'), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    text = Column(Text, nullable=False)
    embedding = Column(String, nullable=True)  # for future AI
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    is_deleted = Column(Integer, default=0)  # soft delete

    group = relationship('Group')
    author = relationship('User')
    answers = relationship('Answer', back_populates='question')

class Answer(Base):
    __tablename__ = 'answers'
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    value = Column(Integer, nullable=True)  # -2, -1, 0, 1, 2
    status = Column(String(16), default='delivered', nullable=False, index=True)  # delivered, answered
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    __table_args__ = (UniqueConstraint('question_id', 'user_id'),)

    question = relationship('Question', back_populates='answers')
    user = relationship('User')

class MatchStatus(Base):
    __tablename__ = 'match_statuses'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey('groups.id', ondelete='CASCADE'), nullable=False, index=True)
    match_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    status = Column(String(16), nullable=False)  # 'hidden' | 'postponed'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    __table_args__ = (UniqueConstraint('user_id', 'group_id', 'match_user_id', name='_match_uc'),) 

class Match(Base):
    __tablename__ = 'matches'
    id = Column(Integer, primary_key=True)
    user1_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    user2_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    group_id = Column(Integer, ForeignKey('groups.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    status = Column(String(16), default='active')  # active/closed
    __table_args__ = (UniqueConstraint('user1_id', 'user2_id', 'group_id', name='_match_pair_uc'),) 