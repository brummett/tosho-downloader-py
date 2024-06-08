# Given a tosho ID, return FileDownload tasks for each file.  If the ID
# is for a batch, there will be one task per file in the batch

#import httpx

from toshodl.Task import Task
from toshodl.Printable import Printable

class ToshoResolver(Printable, Task):
    base_url = 'https://feed.animetosho.org/json'

    def __init__(self, id, *args, **kwargs):
        self.id = id
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'ToshoResolver { self.id }'

    async def query_tosho(self):
        for retries in range(5):
            try:
                response = await self.client.get(self.base_url,
                                                 params={ 'show': 'torrent', 'id': self.id })
                self.print(f'Got response { response.status_code } for id { self.id }\n')
                data = response.json()
            except httpx.ConnectTimeout:
                logger.warn(f'Timeout getting id { self.id } from tosho')
                continue

            return data
        return None

    async def task_impl(self):
        self.print(f'Trying to get { self.id } from feed API\n')

        data = await self.query_tosho()
        if data is None:
            logger.error('No response from tosho about id { self.id }')
            return

        # status can be "complete", "skipped", "processing"
        # "complete_partial" means some but not all files in a group were fetched,
        # probably as part of a manually-triggered download
        if ('status' not in data) \
        or (data['status'] not in ['complete', 'complete_partial']):
            self.print("{ data['title'] } is not yet complete: { data['status'] }\n")
            return

        if data['num_files'] == 1:
            dl_tasks = ToshoFileMetadata(data['title'], data['files'][0])
        else:
            dl_tasks = [ ToshoFileMetadata(data['title'], f) for f in data['files'] ]

        return dl_tasks


# Represents what tosho knows about one given file.
# How many parts it's been split into.  The name, crc, etc.
# We expect file_info to be a hash shaped like this:
# 'links' may be missing if it hasn't completed uploading any pieces yet
# { id: int
#   filename: str
#   md5: str
#   links: {
#       'downloader1': 'https://example.com/blahblah
#       'downloader2:' [
#           'https://example.org/12345',
#           'https://example.org/9876',
#       ]
# }
class ToshoFileMetadata(object):
    def __init__(self, title, file_info):
        self.title = title
        self.filename = file_info['filename']
        self.md5 = file_info['md5']

        self.links = { }
        # Canonicalize all the link values to a list, even if only one item
        if 'links' in file_info:
            for k,v in file_info['links'].items():
                if type(v) == 'list':
                    self.links[k] = v
                else:
                    self.links[k] = [ v ]

    def __str__(self):
        return f"ToshoFileMetadata\n\ttitle %s\n\tfilename %s\n\tmd5 %s" \
                % ( self.title, self.filename, self.md5 )

    async def run(self):
        print(self)
