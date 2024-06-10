import httpx
import logging
import re

from toshodl.Printable import Printable, flush_stdout

logger = logging.getLogger(__name__)

class ToshoSearch(Printable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = httpx.AsyncClient(base_url='https://feed.animetosho.org')
        self.cache = { }

    async def search(self, key):
        if key in self.cache:
            return self.cache[key]

        await self.load_one_page_of_results()
        found = await self.find_cache_match(key)
        if found:
            return found

        await self.search_tosho(key)
        found = await self.find_cache_match(key)
        if found:
            return found

        self.print("*** There were no unique matches to %s\n" % (key))
        return None

    @flush_stdout
    async def find_cache_match(self, key):
        # A numeric tosho id
        if re.match(r'^\d+$', key):
            return key

        # Exact match
        if key in self.cache:
            return self.cache[key]

        # substr match
        matches = { title: id for title, id in self.cache.items() if title.find(key) >= 0 }
        if len(matches) == 1:
            return list(matches.values())[0]
        elif len(matches) > 1:
            self.print('*** There were multiple matches:\n');
            for title, id in matches.items():
                self.print(f'\t{id} {title}\n')

        return None

    @flush_stdout
    async def show_cache(self):
        for title, id in self.cache.items():
            self.print(f'{ id } { title }\n')

    async def load_one_page_of_results(self, page = 0):
        self.print(f'Updating feed page {page}\n')

        for retries in range(3):
            try:
                if page == 0:
                    response = await self.client.get('json')
                    break
                else:
                    response = await self.client.get('json',params={ 'page': page })
                    break
            except httpx.ConnectTimeout:
                logger.warn("Timout getting feed page from animetosho")
                continue

        for item in response.json():
            self.cache[ item['title'] ] = item['id']
            logger.debug('Got >>%s<< id %s', item['title'], item['id'])

    async def search_tosho(self, key):
        self.print(f'Searching for {key}\n')

        for retries in range(3):
            try:
                response = await self.client.get('json', params={'q': key})
                break
            except httpx.ConnectTimeout:
                logger.warn("Timout getting search results from animetosho")
                continue
        for item in response.json():
            #logger.debug('Got >>%s<< id %s', item['title'], item['id'])
            self.cache[ item['title'] ] = item['id']
