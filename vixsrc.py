import bs4
import aiohttp
import json


class VXSRCScraper:
    def __init__(self, client: aiohttp.ClientSession):
        self.client = client
        self.host = "https://vixsrc.to"
        self.headers = {
            "Host": "vixsrc.to",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "it-IT,it;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Referer": self.host
        }

    async def extract_token(self, tmdb_id: str, season: int = None, episode: int = None) -> dict:
        tmdb_id = tmdb_id.lstrip("tt").strip()

        url = f"{self.host}/movie/{tmdb_id}/" 
        if (
            season is not None and
            int(season) > 0 and
            episode is not None and
            int(episode) > 0
        ): url = f"{self.host}/tv/{tmdb_id}/{season}/{episode}/"

        async with self.client.get(url, headers = self.headers) as response:
            response.raise_for_status()
            text = await response.text()

            soup = bs4.BeautifulSoup(text, "html.parser")

        scripts = soup.find_all("script")
        credentials_script = [script for script in scripts if "window.masterPlaylist" in script.text][0]

        # Identify the part of the script containing the token and expiration date 
        open_line_number = credentials_script.text.index("window.masterPlaylist")
        closing_line_number = credentials_script.text.index("window.canPlayFHD", open_line_number)
        credentials_script = credentials_script.text[open_line_number:closing_line_number]

        # The script is just js code as a string, so we can convert it to a json string after appaying this replacement.
        replacements = [
            ("window.masterPlaylist = ", ""), # Remove variable assignment
            (";", ""),                        # Remove semicolons
            ("params", '"params"'),           # Convert "params" to json-accepted fields
            ("url", '"url"'),                 # Convert "url" to json-accepted fields
            ("'", '"'),
            ("\n", ""),
            (" ", ""),                        # Remove spaces to make it a one liner
            (",}", "}")                       # Remove trailing commass, as they will make the conversion fail
        ]
        
        cleaned_script = credentials_script
        for old, new in replacements:
            cleaned_script = cleaned_script.replace(old, new)
        
        keys_dict = json.loads(cleaned_script)
        token = keys_dict.get("params", {}).get("token", None)
        expiration = keys_dict.get("params", {}).get("expires", None)
        url = keys_dict.get("url", None)

        if token is None or expiration is None or url is None:
            raise Exception("Necessary parameters not found. Maybe the frist script has changed?")

        return {
            "token": token,
            "expiration": expiration,
            "playlist_url": url,
            "movie_id": tmdb_id
        }
    
    async def get_playlist(self, tokens: dict[str] = None, token: str = None, expiration: str = None, playlist_url: str = None, hd: bool = True, lang: str = "it", raw: bool = False):
        if tokens is not None:
            token = tokens["token"]
            expiration = tokens["expiration"]
            playlist_url = tokens["playlist_url"]
        
        params = {
            "token": token,
            "expires": expiration,
            "h": int(hd),
            "lang": lang
        }

        if not raw:
            return f"{playlist_url}?token={token}&expires={expiration}&h={int(hd)}&lang={lang}"
        
        async with self.client.get(playlist_url, headers = self.headers, params = params) as response:
            response.raise_for_status()
            m3u8 = await response.text()

            if raw:
                return m3u8

    


if __name__ == "__main__":
    import asyncio
    async def main():
        async with aiohttp.ClientSession() as client:
            scraper = VXSRCScraper(client)
            tokens = await scraper.extract_token("786892")
            m3u8 = await scraper.get_playlist(tokens, raw=True)
            print(m3u8)

    asyncio.run(main())