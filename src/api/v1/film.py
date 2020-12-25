from http import HTTPStatus
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.film import FilmService, get_film_service

router = APIRouter()


class Genre(BaseModel):
    uuid: UUID
    name: str


class Person(BaseModel):
    uuid: UUID
    full_name: str


class Writer(Person):
    pass


class Actor(Person):
    pass


class Director(Person):
    pass


class FilmShort(BaseModel):
    uuid: UUID
    title: str
    imdb_rating: float


class Film(FilmShort):
    description: Optional[str]
    genre: List[Genre]
    actors: List[Actor]
    writers: List[Writer]
    directors: List[Director]


@router.get('/{film_id}', response_model=Film)
async def film_details(film_id: UUID, film_service: FilmService = Depends(get_film_service)) -> Film:
    film = await film_service.get_by_id(film_id)
    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='film not found')
    return Film(id=film.id,
                title=film.title,
                description: film.description,
                genre: film.genre,
                actors: film.actors,
                writers: film.writers,
                directors: film.directors)


@router.get('/', response_model=List[FilmShort])
async def films(film_service: FilmService = Depends(get_film_service)) -> List[FilmShort]:
    films = await film_service.list()
    if not films:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='films not found')

    response = []
    for film in films:
        response.append(
            FilmShort(uuid=film.id,
                      title=film.title,
                      imdb_rating=film.imdb_rating)
        )
    return response
