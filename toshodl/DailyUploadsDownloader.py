# DailyUploads has a 2-step process to get the download link, and it's
# really similar to the ClickNUpload layout.
#
# There's a landing page retrieved with a GET() that includes a form with a
# text-based captcha, submitted with a POST() request to the same URL.  That
# generates another page with a download link styled as a form button

from io import BytesIO
from bs4 import BeautifulSoup
import re
import urllib.parse

from toshodl.DownloadSourceBase import DownloadSourceBase,XTryAnotherSource

class DailyUploadsDownloader(DownloadSourceBase):
    async def download_from_url(self):
        response = await self.exception_retry(lambda: self.client.get(self.url))

        page1_inputs = await self._handle_page1_captcha_page(response)
        dl_link = await self._handle_page2_download_page(page1_inputs)

        async with self.client.stream('GET', dl_link, timeout=15.0) as response:
            await self.save_stream_response(response)

        return

    async def _handle_page1_captcha_page(self, response):
        dom = BeautifulSoup(BytesIO(response.content), features='html.parser')
        form = dom.select_one('form[name=F29]')
        if not form:
            self.print(f'did not find download form at { self.url }\n')
            raise XTryAnotherSource()

        captcha = self._solve_captcha(form)
        if not captcha:
            self.print(f'*** Could not solve captcha at { self.url }\n')
            raise XTryAnotherSource
        self.print(f'Solved captcha: { captcha }\n')

        inputs = extract_inputs_from_form(form)
        inputs['code'] = captcha
        inputs['adblock_detected'] = '0'
        return inputs

    async def _handle_page2_download_page(self, form_inputs):
        self.print(f'POST to { self.url }\n')
        response = await self.client.post(self.url,
                                          headers={
                                            'content-type': 'application/x-www-form-urlencoded',
                                            'referer': self.url,
                                        },
                                        data=form_inputs)
        dom = BeautifulSoup(BytesIO(response.content), features='html.parser')
        dl_link = dom.select_one('a#fbtn1')
        if not dl_link:
            # I don't yet know why this happens.  Print out what we got
            self.print(f'*** Could not find download button at { self.url }\n{ response.content }\n\n\n')
            raise XTryAnotherSource

        # This link contains spaces which need to be url-encoded, but only
        # the "path" portion of the url
        original_url = urllib.parse.urlparse(dl_link.get('href'))
        original_path = original_url.path
        encoded_url = original_url._replace(path = urllib.parse.quote(original_path))

        encoded_href = urllib.parse.urlunparse(encoded_url)
        self.print(f'dl link is { encoded_href }\n')
        return urllib.parse.urlunparse(encoded_url)

    # The captcha is presented as 4 span elements that display numbers.
    # The HTML has them out of order, but uses "padding-left" styles to display
    # them in the proper order.  Find the elements, sort them in the right order,
    # and return the 4-digit string.
    def _solve_captcha(self, form):
        digit_elts = form.select('div#commonId table span[style*=padding-left]')

        def captcha_element_ordering(x):
            style = x.get('style')
            match = re.search(r'padding-left:\s*(\d+)', style)
            if match:
                return int(match[1])
            else:
                return 0

        sorted_elts = sorted(digit_elts, key=captcha_element_ordering)
        sorted_digits = [ e.text for e in sorted_elts ]
        return ''.join(sorted_digits)


def extract_inputs_from_form(form):
    input_elts = form.select('input')
    inputs = { }
    for elt in input_elts:
        inputs[elt.get('name')] = elt.get('value')
    return inputs
