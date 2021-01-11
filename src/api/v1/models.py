from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

"""
Здесь находятся модели, которые сериализются в ответ API
"""


class PaginatedList(BaseModel):
    page_number: int = Field(
        ..., description="Номер текущей страницы")
    count: int = Field(
        ..., description="Количество объектов на текущей странице")
    total_pages: int = Field(
        ..., description="Количество страниц в выдаче")


class Genre(BaseModel):
    id: UUID
    name: str = Field(
        ..., description="Имя жанра")


class PaginatedGenreList(PaginatedList):
    result: List[Genre]


class PersonShort(BaseModel):
    id: UUID
    name: str = Field(
        ..., description="Имя персоны")


class Actor(PersonShort):
    pass


class Writer(PersonShort):
    pass


class Director(PersonShort):
    pass


class Person(PersonShort):
    actor: List[UUID] = Field(
        ..., description="Список id фильмов, в которых персона участвовала в качестве актёра")
    writer: List[UUID] = Field(
        ..., description="Список id фильмов, в которых персона участвовала в качестве сценариста")
    director: List[UUID] = Field(
        ..., description="Список id фильмов, в которых персона участвовала в качестве режиссёра")


class PaginatedPersonShortList(PaginatedList):
    result: List[PersonShort]


class PersonList(BaseModel):
    __root__: List[Person]


class FilmShort(BaseModel):
    id: UUID
    title: str = Field(
        ..., description="Название фильма")
    imdb_rating: float = Field(
        ..., description="Рейтинг фильма")


class Film(FilmShort):
    description: Optional[str] = Field(
        ..., description="Описание фильма")
    genres: List[Genre] = Field(
        ..., description="Список жанров фильма")
    actors: List[Actor] = Field(
        ..., description="Список актёров фильма")
    writers: List[Writer] = Field(
        ..., description="Список сценаристов фильма")
    directors: List[Director] = Field(
        ..., description="Список режиссёров фильма")


class FilmShortList(BaseModel):
    __root__: List[FilmShort]


class PaginatedFilmShortList(PaginatedList):
    result: List[FilmShort]
