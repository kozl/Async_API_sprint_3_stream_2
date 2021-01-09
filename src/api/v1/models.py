from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from models.person import Actor, Writer, Director

"""
Здесь находятся модели, которые сериализются в ответ API
"""


class PaginatedList(BaseModel):
    page_number: int
    count: int
    total_pages: int


class Genre(BaseModel):
    id: UUID
    name: str


class PaginatedGenreList(PaginatedList):
    result: List[Genre]


class PersonShort(BaseModel):
    id: UUID
    name: str


class Person(PersonShort):
    actor: List[UUID]
    writer: List[UUID]
    director: List[UUID]


class PaginatedPersonShortList(PaginatedList):
    result: List[PersonShort]


class PersonList(BaseModel):
    __root__: List[Person]


class FilmShort(BaseModel):
    id: UUID
    title: str
    imdb_rating: float


class Film(FilmShort):
    description: Optional[str]
    genres: List[Genre]
    actors: List[Actor]
    writers: List[Writer]
    directors: List[Director]


class FilmShortList(BaseModel):
    __root__: List[FilmShort]


class PaginatedFilmShortList(PaginatedList):
    result: List[FilmShort]
