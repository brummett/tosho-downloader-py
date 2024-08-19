from urllib.parse import urlparse
import os.path
import re
import asyncio

from toshodl.DownloadSourceBase import DownloadSourceBase,XTryAnotherSource

# Originally based on https://github.com/ltsdw/gofile-downloader, but heavily
# modified since then

class GoFileDownloader(DownloadSourceBase):
    # websiteToken is used in the getContent API endpoint.  They change it from
    # time-to-time, so we extract it from a source file and cache it for the
    # duration of the program
    # Make access to this serialized
    _website_token_lock = asyncio.Lock()
    _website_token = None
    async def website_token(self):
        async with GoFileDownloader._website_token_lock:
            if GoFileDownloader._website_token is None:
                response = await self.exception_retry(lambda: self.client.get('https://gofile.io/dist/js/alljs.js'), name='GoFile alljs.js')
                js_code = response.text

                # The code contains a line that looks like:
                # var fetchData = { wt: "4fd6sg89d7s6" }; // Move wt to URL query
                match = re.search(r'fetchData = { wt: "([^"]+)"', js_code)
                if match:
                    GoFileDownloader._website_token = match[1]
                    self.print(f'GoFile website_token { GoFileDownloader._website_token }\n')
                else:
                    raise ValueError('Could not find website token')

        return GoFileDownloader._website_token

    # A user/session token.  I don't know how long these anonymous users last,
    # but it seems to be long enough that we can create one when we first
    # download something, and use it for the whole life of the program.
    # A previous version created a new account for every download, and it got
    # throttled on their end for getting hit too often,
    # Make access to this serialized
    _dl_token_lock = asyncio.Lock()
    _dl_token = None
    async def dl_token(self):
        async with GoFileDownloader._dl_token_lock:
            if GoFileDownloader._dl_token is None:
                response = await self.exception_retry(lambda: self.client.post('https://api.gofile.io/accounts'), name='GoFile accounts')
                json_data = response.json()
                # looks like: {data => {token => 0eoxBkYGFYmHZ43mxkJpY2vWLeCYW5SV}, status => ok}
                if 'data' in json_data and 'token' in json_data['data']:
                    GoFileDownloader._dl_token = json_data['data']['token']
                    self.print(f'GoFile dl_token { GoFileDownloader._dl_token }\n')
                else:
                    raise KeyError(f'Could not get dl_token, got { json_data }')

        return GoFileDownloader._dl_token

    async def download_from_url(self):
        # The url we're created with looks like https://gofile.io/d/fileId
        # which would generate a javascript-driven page if you pointed browser
        # at it.  Instead, we'll use that "fileId" and use GoFile's API

        # It seems dirty to use basename to get the fileID, but urllib doesn't
        # seem to have any machinery around splitting up parts of the path
        uri = urlparse(self.url)
        file_id = os.path.basename(uri.path)

        website_token = await self.website_token()
        url = f'https://api.gofile.io/contents/{file_id}?wt={website_token}'
        print(f'{self.url} => {url}')

        dl_token = await self.dl_token()
        response = await self.exception_retry(lambda: self.client.get(url, headers={ 'Authorization': f'Bearer { dl_token }'}))
        json = response.json()
        # { data => {
        #       childrenIds => [2c5d5a3c-8d58-4256-a774-13a72691959a],
        #       code => fQKBdZ,
        #       children => {
        #           2c5d5a3c-8d58-4256-a774-13a72691959a => {
        #               createTime => 1680113395,
        #               directLink => https://store11.gofile.io/download/direct/same-uuid/url-encoded-filename.ext,
        #               downloadCount => 82,
        #               id => 2c5d5a3c-8d58-4256-a774-13a72691959a,
        #               link => https://file40.gofile.io/download/same-uuid/url-encoded-filename.ext,
        #               md5 => fcb830ed5d5d1e68f7fa965899c5299c,
        #               mimetype => video/x-matroska,
        #               name => filename.ext,
        #               parentFolder => 485b8173-1a2e-45be-9013-991e17dcded2,
        #               serverChoosen => file40, size => 298394797, type => file
        #           }
        #       },
        #       createTime => 1680113395,
        #       id => 485b8173-1a2e-45be-9013-991e17dcded2,
        #       name => fQKBdZ,
        #       parentFolder => 9ddbbd18-e5c0-4809-8515-3877e205f55a,
        #       public => True,
        #       totalDownloadCount => 82,
        #       totalSize => 298394797,
        #       type => folder
        #   },
        #   status => ok}
        # The response indicates multiple files can be in each "folder", but Tosho only ever does one
        # If the file is missing: { 'status': 'error-notFound', 'data': {}}
        if json['status'] == 'error-notFound':
            self.print(f'*** { self.url } is not found here\n')
            raise XTryAnotherSource()
        if json['status'] != 'ok':
            self.print(f'*** Unexpected link data: { json }\n')
            raise XTryAnotherSource()
        if len(json['data']['children']) != 1:
            raise ValueError(f"Expected 1 'children' but got { json['data']['children'] }")
        for v in json['data']['children'].values():
            dl_link = v['link']
            break

        self.print(f'Downloading from {url} => {dl_link}\n')
        dl_token = await self.dl_token()

        dl_headers = {
            'Cookie':           f'accountToken={ dl_token }',
            'Accept-Encoding':  'gzip, deflate, br',
            'Accept':           '*/*',
            'Referer':          'https://gofile.io/',
            'Pragma':           'no-cache',
            'Cache-Control':    'no-cache'
        }

        async with self.client.stream('GET', dl_link, headers=dl_headers) as response:
            await self.save_stream_response(response)

        return
