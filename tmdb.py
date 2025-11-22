import aiohttp

class TMDB:
    def __init__(self, api_key: str, client: aiohttp.ClientSession):
        if not api_key:
            raise ValueError("API key is required")
        
        self.api_key = api_key
        self.client = client

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def exchange_for_id(self, imdb_id: str, lang: str = "it"):
        url = f"https://api.themoviedb.org/3/find/{imdb_id}?external_source=imdb_id&language={lang.lower()}"
        
        async with self.client.get(url, headers=self.headers) as response:
            response.raise_for_status()
            data = await response.json()
            return str(data["movie_results"][0]["id"])