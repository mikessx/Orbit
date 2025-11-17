import aiohttp
import json
from bs4 import BeautifulSoup

class IMDB:
    def __init__(self, language: str = "it", base_url: str = "https://imdb.com"):
        self.session = None
        self.base_url = base_url
        self.headers = {
           "Accept": "application/json, text/plain, */*",
           "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36",
           "Referer": "https://www.imdb.com/",
           "Accept-Language": f"{language}"
        }

    async def get_by_id(self, id: str):
        if self.session is None:
            self.session = aiohttp.ClientSession()

        async with self.session.get(f"{self.base_url}/title/{id}/", headers=self.headers) as response:
            response.raise_for_status()
            text = await response.text()
            soup = BeautifulSoup(text, "html.parser")
            result = soup.find("script", {"type": "application/ld+json"})
            if result is None:
                return None
            
            p = json.loads(result.text)
            return {
                "type": p.get("@type"),
                "name": p.get("name"),
                "alternateName": p.get("alternateName"),
                "url": p.get("url"),
                "poster": p.get("image"),
                "description": p.get("description"),
                "review": {
                    "author": p.get("review", {}).get("author", {}).get("name"),
                    "dateCreated": p.get("review", {}).get("dateCreated"),
                    "inLanguage": p.get("review", {}).get("inLanguage"),
                    "heading": p.get("review", {}).get("name"),
                    "reviewBody": p.get("review", {}).get("reviewBody"),
                    "reviewRating": {
                        "worstRating": p.get("review", {}).get("reviewRating", {}).get("worstRating"),
                        "bestRating": p.get("review", {}).get("reviewRating", {}).get("bestRating"),
                        "ratingValue": p.get("review", {}).get("reviewRating", {}).get("ratingValue"),
                    },
                },
                "rating": {
                    "ratingCount": p.get("aggregateRating", {}).get("ratingCount"),
                    "bestRating": p.get("aggregateRating", {}).get("bestRating"),
                    "worstRating": p.get("aggregateRating", {}).get("worstRating"),
                    "ratingValue": p.get("aggregateRating", {}).get("ratingValue"),
                },
                "contentRating": p.get("contentRating"),
                "genre": p.get("genre"),
                "datePublished": p.get("datePublished"),
                "keywords": p.get("keywords"),
                "duration": p.get("duration"),
                "actor": [
                    {"name": actor.get("name"), "url": actor.get("url")} for actor in p.get("actor", [])
                ],
                "director": [
                    {"name": director.get("name"), "url": director.get("url")} for director in p.get("director", [])
                ],
                "creator": [
                    {"name": creator.get("name"), "url": creator.get("url")} for creator in p.get("creator", [])
                    if creator.get("@type") == "Person"
                ],
            }
