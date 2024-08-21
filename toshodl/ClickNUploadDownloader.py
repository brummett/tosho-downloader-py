# ClickNUpload has a 3-step process to get the download link.
# First, a "landing page" where there's a form button labeled "Slow Download"
# Submitting that form with a post() presents another form with a 4-digit
# captcha, sometimes also with a countdown timer.  Submitting that form
# with a post() presents the final page that includes the download link.
#
# All these requests are made to the same uri.  The first is a get(), the
# other two are post().  The difference in the two post() requests is the
# form params.
#
# Also annoying is that sometimes you'll get the 4-digit captcha that we
# can solve.  Sometimes you get an image-matching captcha that we can't solve
#
# Note that AnimeTosho hasn't used ClickNUpload since 4 Aug 2024

from io import BytesIO
from bs4 import BeautifulSoup
import asyncio
import re
import urllib.parse
import httpx

from toshodl.DownloadSourceBase import DownloadSourceBase,XTryAnotherSource

class ClickNUploadDownloader(DownloadSourceBase):
    # GETting the file stream will return a 503 (Service Temporarily Unavailable)
    # response if more than one download from CnD is happening simultaneously.  Yes,
    # this means we're wasting a worker slot with a job that's just waiting for
    # another ClickNUploadDownloader instance to finish.  There shouldn't be a
    # deadlock since presumedly one will have the lock and be downloading something
    _serial_lock = asyncio.Lock()

    async def download_from_url(self):
        response = await self.exception_retry(lambda: self.client.get(self.url, follow_redirects=True))
        redirected_url = str(response.url)

        page1_inputs = self._handle_page1_landing_page(response)
        page2_inputs = await self._handle_page2_captcha_page(redirected_url, page1_inputs)

        dl_link = await self._handle_page3_download_page(redirected_url, page2_inputs)

        async with ClickNUploadDownloader._serial_lock:
            async with httpx.AsyncClient(verify=False) as no_verify_client:
                async with no_verify_client.stream('GET', dl_link, timeout=15.0) as response:
                    await self.save_stream_response(response)

        return

    def _handle_page1_landing_page(self, response):
        dom = BeautifulSoup(BytesIO(response.content), features='html.parser')
        form = dom.select_one('div.download form')
        if not form:
            self.print(f'did not find download form at { self.url }\n')
            raise XTryAnotherSource()
        inputs = extract_inputs_from_form(form)
        return inputs

    async def _handle_page2_captcha_page(self, url, page1_inputs):
        self.print(f'POST to { url }\n')

        response = await self.client.post(url,
                                        headers={
                                            'content-type': 'application/x-www-form-urlencoded',
                                            'referer': url,
                                        },
                                        data=page1_inputs)
        dom = BeautifulSoup(BytesIO(response.content), features='html.parser')

        form = dom.select_one('form[name=F1]')
        captcha = self._solve_captcha(form)
        if not captcha:
            self.print(f'*** Could not solve captcha at {url}\n')
            raise XTryAnotherSource
        self.print(f'Solved captcha: { captcha }\n')

        await self._handle_countdown(dom)

        inputs = extract_inputs_from_form(form)
        inputs['code'] = captcha
        inputs['adblock_detected'] = '0'
        return inputs

    # The captcha page has a countdown timer, and the for submission will be
    # rejected if sent too soon
    async def _handle_countdown(self, dom):
        countdown = dom.select_one('span#countdown span.seconds')
        if countdown:
            seconds = int(countdown.get_text())
            self.print(f'  Pausing for { seconds } countdown...\n')
            await asyncio.sleep(seconds + 2)

    # The captcha is presented as 4 span elements that display numbers.
    # The HTML has them out of order, but uses "padding-left" styles to display
    # them in the proper order.  Find the elements, sort them in the right order,
    # and return the 4-digit string.
    def _solve_captcha(self, form):
        digit_elts = form.select('div.download span[style*=padding-left]')

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

    async def _handle_page3_download_page(self, url, page2_inputs):
        self.print(f'POST again to { url }\n')
        response = await self.client.post(url,
                                        headers={
                                            'content-type': 'application/x-www-form-urlencoded',
                                            'referer': url,
                                        },
                                        data=page2_inputs)
        dom = BeautifulSoup(BytesIO(response.content), features='html.parser')
        dl_link = dom.select_one('a.downloadbtn')
        if not dl_link:
            # I don't yet know why this happens.  Print out what we got
            self.print(f'*** Could not find download button at {url}\n{ response.content }\n\n\n')
            raise XTryAnotherSource

        # This link contains spaces which need to be url-encoded, but only
        # the "path" portion of the url
        original_url = urllib.parse.urlparse(dl_link.get('href'))
        original_path = original_url.path
        encoded_url = original_url._replace(path = urllib.parse.quote(original_path))

        encoded_href = urllib.parse.urlunparse(encoded_url)
        self.print(f'dl link is { encoded_href }\n')
        return urllib.parse.urlunparse(encoded_url)


def extract_inputs_from_form(form):
    input_elts = form.select('input')
    inputs = { }
    for elt in input_elts:
        inputs[elt.get('name')] = elt.get('value')
    return inputs
