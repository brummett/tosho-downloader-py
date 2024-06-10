# Represents the intent to download a single file, with one or more sources,
# each source having one or more pieces.  It will pick a source, then schedule
# tasks to download each of the pieces

import random
import os
import asyncio
import aiofiles
import hashlib

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
            if type(v) is list:
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
                filename = os.path.join(self.bundle, '%s.%03d' % ( self.filename, idx))
            else:
                filename = '%s.%03d' % ( self.filename, idx)

            # maybe don't need picker or peers?
            dl_tasks.append( chosen_source_class(url=link, filename=filename) )

        # Join the pieces when they're all done
        asyncio.create_task(self.finalize_file(dl_tasks))

        return dl_tasks

    def is_batch(self):
        return self.bundle != self.filename

    async def finalize_file(self, dl_tasks):
        dl_promises = [ t.done for t in dl_tasks ]
        try:
            print(f'{ self.filename } waiting on { len(dl_tasks) } DL tasks...')
            await asyncio.gather(*dl_promises)
        except Exception as e:
            self.print(f'There was an exception waiting for the pieces of { self.filename }: { e }\n')
            await self.flush_stdout()
            return

        if self.is_batch():
            filename = os.path.join(self.bundle, self.filename)
        else:
            filename = self.filename

        dirname = os.path.dirname(filename)
        try:
            if dirname:
                os.makedirs(dirname)
        except FileExistsError:
            pass

        if len(dl_tasks) > 1:
            self.print(f'All parts of { self.filename } are done\n')
            md5 = await self._join_file_parts(
                            filename,
                            [ os.path.join('working', dl_task.filename) for dl_task in dl_tasks ])

        else:
            self.print(f'{ self.filename } is just one part\n')
            md5 = await self._move_single_file(
                            filename,
                            os.path.join('working', dl_tasks[0].filename))

        if md5.hexdigest() != self.md5:
            self.print(f'*** { self.filename } md5 differs\n    Got      { md5.hexdigest() }\n    Expected { self.md5 }\n')
            dirname = os.path.dirname(self.filename)
            filename = os.path.basename(self.filename)
            os.rename(self.filename, os.path.join(dirname, f'badsum-{ filename }'))

    async def _join_file_parts(self, filename, parts):
        async with aiofiles.open(filename, 'wb') as fh:
            md5 = hashlib.md5()
            for part in parts:
                self.print(f'  { part }\n')
                await self.flush_stdout()
                async with aiofiles.open(part, 'rb') as part_fh:
                    chunk = await part_fh.read()
                    md5.update(chunk)
                    await fh.write(chunk)
        self.print(f'  ===> { filename }\n')
        await self.flush_stdout()

        for part in parts:
            os.remove(part)

        return md5

    async def _move_single_file(self, filename, dl_filename):
        md5 = hashlib.md5()
        async with aiofiles.open(dl_filename, 'rb') as part_fh:
            chunk = await part_fh.read()
            md5.update(chunk)
        os.rename(dl_filename, filename)

        return md5
