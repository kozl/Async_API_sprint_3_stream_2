from http import HTTPStatus
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from services.genre import GenreService, get_genre_service
from api.v1.models import Genre, PaginatedGenreList
from api.v1.common import pagination
from cache.redis import cache_response

router = APIRouter()


@router.get('/{genre_id}', response_model=Genre)
@cache_response(ttl=60 * 5, query_args=['genre_id'])
async def film_details(genre_id: UUID, genre_service: GenreService = Depends(get_genre_service)) -> Genre:
    genre = await genre_service.get_by_id(genre_id)
    if not genre:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='genre not found')
    return Genre(id=genre.id,
                 name=genre.name
                 )


@router.get('/', response_model=PaginatedGenreList)
@cache_response(ttl=60 * 5, query_args=['sort'])
async def films(request: Request,
                genre_service: GenreService = Depends(get_genre_service),
                pagination: dict = Depends(pagination)) -> List[Genre]:
    page_number = pagination['pagenumber']
    page_size = pagination['pagesize']

    genres_total, genres = await genre_service.list(page_number, page_size)
    if not genres:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='genres not found')

    response = PaginatedGenreList(
        page_number=page_number,
        count=len(genres),
        total_pages=(genres_total // page_size) + 1,
        result=[
            Genre(id=genre.id,
                  name=genre.name) for genre in genres],
    )
    return response
