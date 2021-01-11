from typing import Optional

from fastapi import Query

DEFAULT_PAGE_SIZE = 1000


async def pagination(pagesize: Optional[int] = Query(DEFAULT_PAGE_SIZE,
                                                     alias='page[size]',
                                                     title='Количество объектов на одной странице'),
                     pagenumber: Optional[int] = Query(1,
                                                       alias='page[number]',
                                                       title='Номер страницы')):
    """
    Добавляет пагинацию в метод API.
    """
    return {'pagesize': pagesize, 'pagenumber': pagenumber}
