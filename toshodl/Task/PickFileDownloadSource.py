# Represents the intent to download a single file, with one or more sources,
# each source having one or more pieces.  It will pick a source, then schedule
# tasks to download each of the pieces

import random
import os

from toshodl.Task import Task
from toshodl.Printable import Printable

# A list of classes we've imported that we can download from.
from toshodl.Task.KrakenFilesDownloader import KrakenFilesDownloader
download_classes = {
    'KrakenFiles': KrakenFilesDownloader,
}

class PickFileDownloadSource(Printable, Task):
    def __init__(self, bundle, filename, md5, links={}, *args, **kwargs):
        # For a single file, this will be the same as the filename
        self.bundle = bundle
        self.filename = filename
        self.md5 = md5

        # Canonicalize all the link values to a list, even if only one item
        # 'links' will be missing if it hasn't uploaded any pieces there yet
        self.links = { }
        for k,v in links.items():
            if type(v) == 'list':
                self.links[k] = v
            else:
                self.links[k] = [ v ]

        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"PickFileDownloadSource\n\tbundle %s\n\tfilename %s\n\tmd5 %s" \
                % ( self.bundle, self.filename, self.md5 )

    async def task_impl(self):
        supported_sources = set(download_classes.keys())
        available_sources = set(self.links.keys())

        downloadable_sources = supported_sources.intersection(available_sources)
        if len(downloadable_sources) == 0:
            self.print(f'{ self.filename } has no supported sources\n')
            return

        chosen_source = random.choice(tuple(downloadable_sources))
        chosen_source_links = self.links[chosen_source]
        self.print(f'downloading { len(chosen_source_links) } pieces from { chosen_source } for { self.filename }\n')

        dl_tasks = []
        chosen_source_class = download_classes[chosen_source]
        for idx, link in enumerate(chosen_source_links, start=1):
            self.print(f'    { chosen_source }: { link }\n')
            if self.is_batch():
                #filename = self.bundle + '/' + self.filename + '.' + str(idx)
                filename = os.path.join(self.bundle, '%s.%03d' % ( self.filename, idx))
            else:
                #filename = self.filename + '.' + str(idx)
                filename = '%s.%03d' % ( self.filename, idx)

            dl_tasks.append( chosen_source_class(url=link, filename=filename, picker=self, peers=dl_tasks) )

        return dl_tasks

    def is_batch(self):
        return self.bundle != self.filename
