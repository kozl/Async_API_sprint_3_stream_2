from http import HTTPStatus
from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from services.film import FilmService, get_film_service, SortBy, FilterBy
from api.v1.models import FilmShort, Film, PaginatedFilmShortList, FilmShortList, Genre, Actor, Writer, Director
from cache.redis import cache_response
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
                genres=[Genre(**genre.dict()) for genre in film.genres],
                actors=[Actor(**actor.dict()) for actor in film.actors],
                writers=[Writer(**writer.dict()) for writer in film.writers],
                directors=[Director(**director.dict()) for director in film.directors],
                )


@router.get('/', response_model=PaginatedFilmShortList)
@cache_response(ttl=60 * 5, query_args=['sort'])
async def films(request: Request,
                film_service: FilmService = Depends(get_film_service),
                sort: Optional[str] = Query(
                    None, description='Сортировка по аттрибуту фильма', regex='^[-+].+$'),
                pagination: dict = Depends(pagination)) -> List[FilmShort]:
    sort_by = SortBy.from_query(sort)
    filter_by = FilterBy.from_query_params(request.query_params)
    page_number = pagination['pagenumber']
    page_size = pagination['pagesize']

    films_total, films = await film_service.list(page_number, page_size, sort_by, filter_by)
    if not films:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='films not found')

    response = PaginatedFilmShortList(
        page_number=page_number,
        count=len(films),
        total_pages=(films_total // page_size) + 1,
        result=[
            FilmShort(id=film.id,
                      title=film.title,
                      imdb_rating=film.imdb_rating) for film in films],
    )
    return response


@router.get('/search/', response_model=FilmShortList)
@cache_response(ttl=60 * 5, query_args=['query'])
async def film_search(request: Request,
                      query: str,
                      film_service: FilmService = Depends(get_film_service)) -> List[FilmShort]:

    films = await film_service.search(query)
    if not films:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='films not found')

    response = FilmShortList(
        __root__=[
            FilmShort(id=film.id,
                      title=film.title,
                      imdb_rating=film.imdb_rating) for film in films]
    )
    return response
