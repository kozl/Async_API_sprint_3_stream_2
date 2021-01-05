from http import HTTPStatus
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from services.person import PersonService, get_person_service
from api.v1.models import Person, PersonList, PersonShort
from api.cache import cache_response

router = APIRouter()


@router.get('/{person_id}', response_model=Person)
@cache_response(ttl=60 * 5, query_args=['person_id'])
async def person_details(person_id: UUID, person_service: PersonService = Depends(get_person_service)) -> Person:
    person = await person_service.get_person_by_id(person_id)
    if not person:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='person not found')
    return Person(id=person.id,
                  name=person.name,
                  actor=person.actor,
                  writer=person.writer,
                  director=person.director
                  )


@router.get('/', response_model=PersonList)
@cache_response(ttl=60 * 5, query_args=['sort'])
async def persons(request: Request,
                  person_service: PersonService = Depends(get_person_service),
                  ) -> List[Person]:
    persons = await person_service.list()
    if not persons:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail='persons not found')

    response = PersonList(__root__=[
        PersonShort(id=person.id,
                    name=person.name) for person in persons])
    return response
