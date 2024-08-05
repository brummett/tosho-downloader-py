# Represents the intent to download a single file
# That file might be part of a batch of files.  For a batch, a subdirectory
# will be created to hold all the files in the batch
#
# The file might have been split into multiple parts.  If so, we'll create
# tasks to download each of those parts, and then join them together when
# they're all downloaded.
#
# The file will have one or more download sources.  We'll make a list of
# the sources we support, randomize them, then try them in order

import os
import asyncio
import aiofiles
import aiofiles.os
import hashlib
import random

from toshodl.Printable import Printable
from toshodl.DownloadSourceBase import XTryAnotherSource

# A list of classes we've imported that we can download from.
from toshodl.KrakenFilesDownloader import KrakenFilesDownloader
from toshodl.GoFileDownloader import GoFileDownloader
from toshodl.ClickNUploadDownloader import ClickNUploadDownloader
download_classes = {
    'KrakenFiles': KrakenFilesDownloader,
    'GoFile': GoFileDownloader,
    'ClickNUpload': ClickNUploadDownloader,
}

class FileDownloader(Printable):

    dl_sem = asyncio.Semaphore(5)  # limit concurrent downloads

    def __init__(self,  filename,
                        md5,
                        links,
                        bundle = None,
                        *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.filename = filename
        self.pathname = os.path.join(bundle, filename) if bundle else filename
        self.working_pathname = os.path.join('working', self.pathname)
        self.md5 = md5

        supported_sources = set(download_classes.keys())
        available_sources = set(links.keys())
        self.sources = { k: links[k] for k in supported_sources.intersection(available_sources) }

    async def download(self):
        if self.is_already_downloaded():
            self.print(f'Skipping { self.filename } because it already exists\n')
            return

        source_names = list(self.sources.keys())
        random.shuffle(source_names)
        for source in source_names:
            try:
                self.print(f'Downloading { len(self.sources[source]) } pieces from { source } for { self.filename }\n')
                dl_class = download_classes[source]

                piece_tasks = [ ]
                async with asyncio.TaskGroup() as tg:
                    for idx, link in enumerate(self.sources[source], start=1):
                        task = tg.create_task(self.download_piece(dl_class, link, idx))
                        piece_tasks.append(task)

                working_filenames = [ t.result() for t in piece_tasks ]
                await self.finalize_file(working_filenames)
                return # This one worked; don't try other sources

            except* XTryAnotherSource as e:
                self.print(f'*** Source { source } gave up on { self.filename }, trying the next one...\n')
                await self.remove_working_files(source)

        self.print(f'*** There are no more sources for { self.filename }\n')

    async def remove_working_files(self, source):
        for i in range(len(self.sources[source])):
            dl_filename = '%s.%03d' % ( self.working_pathname, i+1)
            self.print(f'*** deleting: { dl_filename }\n')
            try:
                await aiofiles.os.unlink(dl_filename)
            except FileNotFoundError:
                pass

    def is_already_downloaded(self):
        return os.path.exists(self.pathname)

    # Download one piece of a file with the given download class and URL/link
    # Return the working filename
    async def download_piece(self, source_class, link, idx):
        async with FileDownloader.dl_sem:
            self.print(f'{ self.filename } part { idx }: { link }\n')
            dl_filename = '%s.%03d' % ( self.working_pathname, idx)
            dl = source_class(url=link, filename=dl_filename)
            await dl.download()
        return dl_filename

    # Join the pieces into the final combined file
    async def finalize_file(self, working_filenames):
        self.make_batch_subdir()

        if len(working_filenames) > 1:
            self.print(f'All parts of { self.pathname } are done\n')
            md5 = await self.join_file_parts(working_filenames)

        else:
            self.print(f'{ self.pathname } is just one part\n')
            md5 = await self.move_single_file(working_filenames[0])

        if md5.hexdigest() != self.md5:
            self.print(f'*** { self.pathname } md5 differs!\n    Got      { md5.hexdigest() }\n    Expected { self.md5 }\n')
            dirname = os.path.dirname(self.pathname)
            orig_filename = os.path.basename(self.pathname)
            os.rename(self.pathname, os.path.join(dirname, f'badsum-{ orig_filename }'))
            return False

        return True

    def make_batch_subdir(self):
        dirname = os.path.dirname(self.pathname)
        try:
            if dirname:
                os.makedirs(dirname)
        except FileExistsError:
            pass

    async def join_file_parts(self, parts):
        async with aiofiles.open(self.pathname, 'wb') as fh:
            md5 = hashlib.md5()
            for part in parts:
                self.print(f'  { part }\n')
                await self.flush_stdout()
                async with aiofiles.open(part, 'rb') as part_fh:
                    chunk = await part_fh.read()
                    md5.update(chunk)
                    await fh.write(chunk)
        self.print(f'  ===> { self.pathname }\n')
        await self.flush_stdout()

        for part in parts:
            os.remove(part)

        return md5

    async def move_single_file(self, dl_filename):
        md5 = hashlib.md5()
        async with aiofiles.open(dl_filename, 'rb') as part_fh:
            chunk = await part_fh.read()
            md5.update(chunk)
        os.rename(dl_filename, self.pathname)

        return md5
