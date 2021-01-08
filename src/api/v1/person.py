from http import HTTPStatus
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from services.person import PersonService, get_person_service
from services.film import FilmService, Roles, get_film_service
from api.v1.common import pagination
from api.v1.models import Person, PersonList, PersonShort
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
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='person not found')
    person_films = await film_service.get_by_person_id(person.id)
    return Person(id=person.id,
                  name=person.name,
                  actor=person_films[Roles.ACTOR.value],
                  writer=person_films[Roles.WRITER.value],
                  director=person_films[Roles.DIRECTOR.value],
                  )


@router.get('/', response_model=PersonList)
@cache_response(ttl=60 * 5, query_args=['sort'])
async def persons(request: Request,
                  person_service: PersonService = Depends(get_person_service),
                  pagination: dict = Depends(pagination)) -> List[Person]:
    page_number = pagination['pagenumber']
    page_size = pagination['pagesize']

    persons = await person_service.list(page_number, page_size)
    if not persons:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='persons not found')

    response = PersonList(__root__=[
        PersonShort(id=person.id,
                    name=person.name) for person in persons])
    return response
