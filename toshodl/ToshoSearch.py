import httpx
import logging

from toshodl.Printable import Printable, flush_stdout

logger = logging.getLogger(__name__)

class ToshoSearch(Printable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = httpx.AsyncClient(base_url='https://feed.animetosho.org')
        self.cache = { }

    #@flush_stdout
    async def search(self, key):
        if key in self.cache:
            return self.cache[key]

        await self.load_one_page_of_results()
        if key in self.cache:
            return self.cache[key]

        matches = { title: id for title, id in self.cache.items() if title.find(key) >= 0 }
        if len(matches) == 1:
            return list(matches.values())[0]
        elif len(matches) > 1:
            self.print("*** There were multiple matches:\n\t%s\n" % ( "\n\t".join(matches.keys())))
            return None

        self.print("*** There were no matches to %s\n" % (key))
        return None

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

