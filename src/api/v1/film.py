from http import HTTPStatus
from uuid import UUID
from typing import List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from services.film import FilmService, get_film_service, SortOrder, SortBy, FilterBy, FilterByAttr
from api.v1.models import FilmShort, Film, FilmShortList
from api.cache import cache_response
from api.v1.common import pagination

router = APIRouter()


@router.get('/{film_id}', response_model=Film)
@cache_response(ttl=60 * 5, query_args=['film_id'])
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


@router.get('/', response_model=FilmShortList)
@cache_response(ttl=60 * 5, query_args=['sort'])
async def films(request: Request,
                film_service: FilmService = Depends(get_film_service),
                sort: Optional[str] = Query(
                    None, description='Сортировка по аттрибуту фильма', regex='^[-+].+$'),
                pagination: dict = Depends(pagination)) -> List[FilmShort]:
    sort_by = SortBy.from_param(sort)
    filter_by = FilterBy.from_query(request.query_params)
    page_number = pagination['pagenumber']
    page_size = pagination['pagesize']

    films = await film_service.list(page_number, page_size, sort_by, filter_by)
    if not films:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='films not found')

    response = FilmShortList(__root__=[
        FilmShort(id=film.id,
                  title=film.title,
                  imdb_rating=film.imdb_rating) for film in films])
    return response
