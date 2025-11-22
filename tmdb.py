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
    
    async def grab_details(self, imdb_id: str, lang: str = "it", media_type: str = "movie"):
        url = f"https://api.themoviedb.org/3/find/{imdb_id}?external_source=imdb_id&language={lang.lower()}"
        
        if media_type != "movie" and media_type != "tv":
            raise ValueError("Type must be either 'movie' or 'tv'")

        async with self.client.get(url, headers=self.headers) as response:
            response.raise_for_status()
            data = await response.json()
            
            if len(data["movie_results"]) >= 1 and media_type == "movie":
                data = data["movie_results"][0]
                return {
                    "tmdb_id": str(data["id"]),
                    "title": data["title"],
                    "vote_avg": round(data["vote_average"], 1),
                }
            elif len(data["tv_results"]) >= 1 and media_type == "tv":
                data = data["tv_results"][0]
                return {
                    "tmdb_id": str(data["id"]),
                    "title": data["name"],
                    "vote_avg": round(data["vote_average"], 1),
                }