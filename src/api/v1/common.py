from typing import Optional

from fastapi import Query


async def pagination(pagesize: Optional[int] = Query(50,
                                                     alias='page[size]',
                                                     title='Количество объектов на одной странице'),
                     pagenumber: Optional[int] = Query(1,
                                                       alias='page[number]',
                                                       title='Номер страницы')):
    return {'pagesize': pagesize, 'pagenumber': pagenumber}
