from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import status

from services.person import PersonService, get_person_service
from services.film import FilmService, Roles, get_film_service
from api.v1.common import pagination
from api.v1.models import PersonList, Person, PaginatedPersonShortList, PersonShort, FilmShortList, FilmShort
from cache.redis import cache_response


router = APIRouter()


@router.get('/{person_id}', response_model=Person)
@cache_response(ttl=60 * 5, query_args=['person_id'])
async def person_details(person_id: UUID,
                         person_service: PersonService = Depends(
                             get_person_service),
                         film_service: FilmService = Depends(get_film_service)) -> Person:
    person = await person_service.get_by_id(person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail='person not found')
    person_films = await film_service.get_by_person_id(person.id)
    return Person(id=person.id,
                  name=person.name,
                  actor=[
                      film.id for film in person_films[Roles.ACTOR.value]],
                  writer=[
                      film.id for film in person_films[Roles.WRITER.value]],
                  director=[
                      film.id for film in person_films[Roles.DIRECTOR.value]],
                  )


@router.get('/{person_id}/film', response_model=FilmShortList)
@cache_response(ttl=60 * 5, query_args=['person_id'])
async def person_films(person_id: UUID,
                       person_service: PersonService = Depends(
                           get_person_service),
                       film_service: FilmService = Depends(get_film_service)) -> FilmShortList:
    person = await person_service.get_by_id(person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail='person not found')
    person_films_by_role = await film_service.get_by_person_id(person.id)
    person_films = []
    for films in person_films_by_role.values():
        person_films.extend(films)

    response = FilmShortList(
        result=[
            FilmShort(id=film.id,
                      title=film.title,
                      imdb_rating=film.imdb_rating) for film in person_films])
    return response


@router.get('/search/', response_model=PersonList)
@cache_response(ttl=60 * 5, query_args=['query'])
async def persons_search(request: Request,
                         query: str,
                         person_service: PersonService = Depends(
                             get_person_service),
                         film_service: FilmService = Depends(get_film_service)) -> List[Person]:
    response_person_models = []
    persons = await person_service.search(query)
    if not persons:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail='persons not found')

    for person in persons:

        person_films = await film_service.get_by_person_id(person.id)
        response_person_models.append(
            Person(id=person.id,
                   name=person.name,
                   actor=[
                       film.id for film in person_films[Roles.ACTOR.value]],
                   writer=[
                       film.id for film in person_films[Roles.WRITER.value]],
                   director=[
                       film.id for film in person_films[Roles.DIRECTOR.value]],
                   ))
    response = PersonList(__root__=response_person_models)
    return response


@router.get('/', response_model=PaginatedPersonShortList)
@cache_response(ttl=60 * 5, query_args=['sort'])
async def persons(request: Request,
                  person_service: PersonService = Depends(get_person_service),
                  pagination: dict = Depends(pagination)) -> List[Person]:
    page_number = pagination['pagenumber']
    page_size = pagination['pagesize']

    persons_total, persons = await person_service.list(page_number, page_size)
    if not persons:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail='persons not found')

    response = PaginatedPersonShortList(
        page_number=page_number,
        count=len(persons),
        total_pages=(persons_total // page_size) + 1,
        result=[
            PersonShort(id=person.id,
                        name=person.name) for person in persons]
    )
    return response
