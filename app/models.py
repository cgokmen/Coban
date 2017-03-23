#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import enum
from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime, Enum, func, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()

class ChannelEnum(enum.Enum):
    KanalD = "KanalD"

class Series(Base):
    __tablename__ = 'series'

    id = Column(String(128), primary_key=True)
    name = Column(String(128), nullable=False)
    friendlyName = Column(String(128), nullable=False)
    channel = Column(Enum(ChannelEnum), nullable=False)
    index_url = Column(String(128), nullable=False)
    tvdb_id = Column(Integer)

    def __repr__(self):
        return '<Series %r %r>' % (self.name, self.id)

class Season(Base):
    __tablename__ = 'seasons'

    id = Column(Integer, primary_key=True)
    season_number = Column(Integer, nullable=False)
    series_id = Column(Integer, ForeignKey('series.id'), nullable=False)
    season_starting_episode_number = Column(Integer, nullable=False)
    season_ending_episode_number = Column(Integer, nullable=True)
    found_on_tvdb = Column(Boolean, nullable=False)
    isPrediction = Column(Boolean, nullable=False)

    series = relationship(Series, back_populates="seasons")

    def __repr__(self):
        return '<Season %r of %r>' % (self.season_number, self.series.name)

class Episode(Base):
    __tablename__ = 'episodes'

    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False)
    media_link = Column(Text, nullable=False)
    season_id = Column(Integer, ForeignKey('seasons.id'), nullable=False)
    series_id = Column(Integer, ForeignKey('series.id'), nullable=False)
    date_aired = Column(DateTime, default=func.now())
    date_found = Column(DateTime, default=func.now())

    season = relationship(Season, back_populates="episodes")

    def __repr__(self):
        return '<Episode %r of season %r of %r>' % (self.number, self.season.season_number, self.season.series.name)

Series.seasons = relationship(Season, back_populates="series", cascade="all, delete, delete-orphan")
Series.episodes = relationship(Episode, back_populates="series", cascade="all, delete, delete-orphan")
Season.episodes = relationship(Episode, back_populates="season", cascade="all, delete, delete-orphan")
