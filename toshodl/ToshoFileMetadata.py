# A class to formalize the info retrieved from each file at a given tosho
# ID's page at
# https://api.animetosho.org/json?show=torrent&id=XXXXX
# It's used to mediate data transfer between ToshoResolver and Task.FileDownload
# The bundle above will generate one or more of these ToshoFileMetadata instances,
# one for each file in the bundle, regardless of how many pieces the file may be
# split into

class ToshoFileMetadata(object):
    def __init__(self, title, file_info):
        self.title = title
        self.filename = file_info['filename']
        self.md5 = file_info['md5']

        self.links = { }
        # Canonicalize all the link values to a list, even if only one item
        # 'links' will be missing if it hasn't uploaded any pieces there yet
        if 'links' in file_info:
            for k,v in file_info['links'].items():
                if type(v) == 'list':
                    self.links[k] = v
                else:
                    self.links[k] = [ v ]

    def __str__(self):
        return f"ToshoFileMetadata\n\ttitle %s\n\tfilename %s\n\tmd5 %s" \
                % ( self.title, self.filename, self.md5 )

    # We're not really a task, but we'll pretend to be one for debugging
    # purposes
    async def run(self):
        print(self)
