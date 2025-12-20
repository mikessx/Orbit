import aiohttp
import re
from urllib.parse import quote_plus

class CB01Scraper:
    def __init__(self, client: aiohttp.ClientSession):
        self.client = client
        self.base_url = "https://cb01net.shop"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "it-IT,it;q=0.9",
            "Referer": self.base_url,
        }

    def __pick_year_match(self, html: str, expected_year: str | None) -> str | None:
        pattern = r'<div[^>]+class="card-content"[\s\S]*?<h3[^>]*class="card-title"[\s\S]*?<a[^>]+href="([^"]+)"'
        year_pattern = r'(19|20)\d{2}'
        first = None

        for match in re.finditer(pattern, html):
            href = match.group(1)
            if first is None:
                first = href

            slug = href.rstrip('/').split('/')[-1]
            year_match = re.search(year_pattern, slug)
            if year_match and expected_year and year_match.group(0) == expected_year:
                return href

        return first

    async def _resolve_to_mixdrop(self, raw: str, page_html: str) -> str | None:
        link = raw.strip()

        # stayonline bypass
        if re.search(r'stayonline\.', link, re.IGNORECASE):
            try:
                parts = link.split('/')
                content_id = parts[-2] if len(parts) >= 2 else ''
                if not content_id:
                    return None

                # POST request to ajax endpoint
                data = {'id': content_id, 'ref': ''}
                headers = {
                    'User-Agent': self.headers['User-Agent'],
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'Origin': 'https://stayonline.pro',
                    'Referer': 'https://stayonline.pro/'
                }

                async with self.client.post('https://stayonline.pro/ajax/linkEmbedView.php', data=data, headers=headers) as res:
                    if res.ok:
                        js = await res.json()
                        v = js.get('data', {}).get('value')
                        if isinstance(v, str):
                            direct = v.strip()
                            if re.search(r'mixdrop', direct, re.IGNORECASE):
                                link = direct
                            else:
                                mm = re.search(r'https?://[^"\'<>]*mixdrop[^"\'<>]*', direct, re.IGNORECASE)
                                if mm:
                                    link = mm.group(0)

                # Fallback: GET embed page
                if not re.search(r'mixdrop', link, re.IGNORECASE):
                    try:
                        embed_url = link if re.search(r'/e/|/v/', link, re.IGNORECASE) else f'https://stayonline.pro/e/{content_id}/'
                        headers = {'User-Agent': self.headers['User-Agent'], 'Referer': 'https://stayonline.pro/'}
                        async with self.client.get(embed_url, headers=headers) as pg:
                            if pg.ok:
                                txt = await pg.text()
                                mm = re.search(r'https?://[^"\'<>]*mixdrop[^"\'<>]*', txt, re.IGNORECASE)
                                if mm:
                                    link = mm.group(0)
                    except:
                        pass
            except:
                return None

        if not re.search(r'mixdrop', link, re.IGNORECASE):
            return None

        return link

    async def stayonline_get_meta(self, url: str) -> tuple[str, str]:
        url = url if not url.endswith("/") else url[:-1]
        content_id = url.split("/")[-1] # altra soluzione è trovare lelemento "e" e fare idx +1 ma per ora va bene così.
        stayonline_url = f"https://stayonline.pro/l/${content_id}/"

        headers = self.headers.copy()
        headers.update({"Referer": "https://stayonline.pro/"})

        async with self.client.get(stayonline_url, headers=headers) as response:
            response.raise_for_status()
            html = await response.text()

        try:
            btn = re.search(r'<button[^>]*btnClickToContinueLink[^>]*>([\s\S]*?)</button>', html, re.IGNORECASE)
            if not btn:
                return None

            inner = btn.group(1)
            name_match = re.search(r'([^<]+\.mp4)\s*<span', inner, re.IGNORECASE)
            size_match = re.search(r'<span[^>]*>([0-9.,]+\s*(?:GB|MB|KB))</span>', inner, re.IGNORECASE)

            filename = name_match.group(1).strip() if name_match else None
            file_size = size_match.group(1).replace(',', '.') if size_match else None

            return (filename, file_size)
        except Exception:
            return None

    async def search_movies(self, query: str, film_year: str):
        url = f"{self.base_url}/?s={quote_plus(query)}"

        async with self.client.get(url, headers=self.headers) as response:
            response.raise_for_status()
            html = await response.text()

        best_match = self.__pick_year_match(html, film_year) # href or None
        if not best_match:
            return None

        async with self.client.get(best_match, headers=self.headers) as response:
            response.raise_for_status()
            movie_page = await response.text()

        iframe2 = re.search(r'<div[^>]+id="iframen2"[^>]*data-src="([^"]+)"', movie_page, re.IGNORECASE)
        iframe1 = re.search(r'<div[^>]+id="iframen1"[^>]*data-src="([^"]+)"', movie_page, re.IGNORECASE)
        candidate = iframe2.group(1) if iframe2 else (iframe1.group(1) if iframe1 else None)

        if not candidate:
            return None

        #try:
        #    print("Getting meta...")
        #    filename, file_size = await self.stayonline_get_meta(candidate)
        #    print(f"Filename: {filename} - Size: {file_size}")
        #except Exception as e:
        #    print(f"Error getting meta: {e}")
        #    filename, file_size = None, None
            
        print("Resolving to Mixdrop...")
        mixdrop = await self._resolve_to_mixdrop(candidate, movie_page)
        print(mixdrop)
        return mixdrop #(mixdrop, filename, file_size)


if __name__ == "__main__":
    import asyncio

    async def main():
        async with aiohttp.ClientSession() as client:
            scraper = CB01Scraper(client)
            r = await scraper.search_movies("Inception", "2010")
            print(r)

    asyncio.run(main())
