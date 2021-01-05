from http import HTTPStatus
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from services.genre import GenreService, get_genre_service
from api.v1.models import Genre, GenreList
from api.cache import cache_response

router = APIRouter()


@router.get('/{genre_id}', response_model=Genre)
@cache_response(ttl=60 * 5, query_args=['genre_id'])
async def film_details(genre_id: UUID, genre_service: GenreService = Depends(get_genre_service)) -> Genre:
    genre = await genre_service.get_by_id(genre_id)
    if not genre:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='film not found')
    return Genre(id=genre.id,
                 name=genre.name
                 )


@router.get('/', response_model=GenreList)
@cache_response(ttl=60 * 5, query_args=['sort'])
async def films(request: Request,
                genre_service: GenreService = Depends(get_genre_service),
                ) -> List[Genre]:
    genres = await genre_service.list()
    if not genres:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='films not found')

    response = GenreList(__root__=[
        Genre(id=genre.id,
              name=genre.name) for genre in genres])
    return response
