from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

"""
Здесь находятся модели, которые сериализются в ответ API
"""


class Genre(BaseModel):
    id: UUID
    name: str


class Person(BaseModel):
    id: UUID
    full_name: str


class Writer(Person):
    pass


class Actor(Person):
    pass


class Director(Person):
    pass


class FilmShort(BaseModel):
    id: UUID
    title: str
    imdb_rating: float


class Film(FilmShort):
    description: Optional[str]
    # genre: List[Genre]
    # actors: List[Actor]
    # writers: List[Writer]
    # directors: List[Director]

class FilmShortList(BaseModel):
    __root__: List[FilmShort]