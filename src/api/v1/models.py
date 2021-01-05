from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

"""
Здесь находятся модели, которые сериализются в ответ API
"""


class Genre(BaseModel):
    id: UUID
    name: str


class GenreList(BaseModel):
    __root__: List[Genre]


class PersonShort(BaseModel):
    id: UUID
    name: str


class Person(PersonShort):
    actor: List[UUID]
    writer: List[UUID]
    director: List[UUID]


class PersonList(BaseModel):
    __root__: List[PersonShort]


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
