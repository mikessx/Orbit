from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request
from vixsrc import VXSRCScraper
from dotenv import load_dotenv
from tmdb import TMDB

import os
import aiohttp
import logging


class Addon:
    def __init__(self):
        load_dotenv()
        self.client = aiohttp.ClientSession()
        self.tmdb = TMDB(os.getenv('TMDB_READ_API_KEY'), client=self.client)
        self.vixsrc = VXSRCScraper(self.client)

        self.addon_manifest = {           
            "id": "sex.film.orbit",
            "version": "0.0.1",
            "description": "Fast and easy-to-use stream provider. F&O",
            "name": "Orbit",
            "resources": [
                "stream"
            ],
            "types": [
                "movie",
                "series"
            ],
            "catalogs": [],
            "idPrefixes": ["tt"],
            "logo": f"https://i.postimg.cc/RF6QWqLd/logo.png",
            "background": f"https://i.postimg.cc/9MRtDzYg/background.png"
        }

        self.app = Starlette(debug=True, routes=[
            Route('/', self.health),
            Route('/manifest.json', self.manifest),
            Route('/stream/{type}/{id}.json', self.stream)
        ], on_startup=[self.on_startup])

        self.logger = logging.getLogger("uvicorn")

    def on_startup(self):
        print("Server started: http://127.0.0.1:5000/manifest.json")
    
    
    async def health(self, request: Request):
        return JSONResponse({
            "status": "OK",
            "version": self.addon_manifest['version'] 
        })


    async def manifest(self, request: Request):
        return JSONResponse(self.addon_manifest, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*',
            'Access-Control-Allow-Headers': '*'
        })


    async def stream(self, request: Request):
        # TODO: mediaflow
        stream_type = request.path_params['type']
        content_id = request.path_params['id']
        
        self.logger.info(f"Requested stream for {content_id} of type {stream_type}")
        
        if stream_type == "movie":
            tmdb_id = await self.tmdb.exchange_for_id(content_id)
            tokens = await self.vixsrc.extract_token(tmdb_id)
            m3u8 = await self.vixsrc.get_playlist(tokens)

        stream = {
            "url": m3u8,
            "name": "🚀 | Orbit",
            "description": f"VX | {tmdb_id}",
            "behaviorHints": {
                "notWebReady": True,
                "proxyHeaders": {
                    "request": { "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0" },
                    "response": { "Access-Control-Allow-Origin": "*" }
                }
            }
        }

        return JSONResponse({"streams": [stream]}, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*',
            'Access-Control-Allow-Headers': '*'
        })

addon = Addon()
app = addon.app