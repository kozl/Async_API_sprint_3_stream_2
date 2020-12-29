from http import HTTPStatus
from uuid import UUID
from typing import List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from services.film import FilmService, get_film_service, SortOrder, SortBy, FilterBy, FilterByAttr
from api.v1.models import FilmShort, Film

router = APIRouter()


@router.get('/{film_id}', response_model=Film)
async def film_details(film_id: UUID, film_service: FilmService = Depends(get_film_service)) -> Film:
    film = await film_service.get_by_id(film_id)
    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='film not found')
    return Film(id=film.id,
                title=film.title,
                description=film.description,
                imdb_rating=film.imdb_rating,
                # genre=film.genre,
                # actors=film.actors,
                # writers=film.writers,
                # directors=film.directors,
                )


@router.get('/', response_model=List[FilmShort])
async def films(request: Request,
                film_service: FilmService = Depends(get_film_service),
                sort: Optional[str] = Query(
                    None, description='Сортировка по аттрибуту фильма', regex='^[-+].+$'),
                ) -> List[FilmShort]:
    sort_by = SortBy.from_param(sort)
    filter_by = FilterBy.from_query(request.query_params)

    films = await film_service.list(sort_by, filter_by)
    if not films:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='films not found')

    response = []
    for film in films:
        response.append(
            FilmShort(id=film.id,
                      title=film.title,
                      imdb_rating=film.imdb_rating)
        )
    return response
