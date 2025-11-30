from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

from profiler import PyInstrumentMiddleware
from vixsrc import VXSRCScraper
from tmdb import TMDB

from dotenv import load_dotenv
from urllib.parse import unquote

import os
import aiohttp
import logging


class Addon:
    def __init__(self):
        dev_env_path = os.path.join(os.path.dirname(__file__), "dev.env")
        if os.path.exists(dev_env_path):
            load_dotenv(dotenv_path=dev_env_path)
        else:
            load_dotenv()


        self.client = aiohttp.ClientSession()
        self.tmdb = TMDB(os.getenv('TMDB_READ_API_KEY'), client=self.client)
        self.vixsrc = VXSRCScraper(self.client)

        self.addon_manifest = {           
            "id": "it.film.orbit",
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
        
        middleware = [
            Middleware(
                CORSMiddleware,
                allow_origins = ["*"],
                allow_methods = ["*"],
                allow_headers = ["*"]
            )
        ]
        if os.getenv('DEBUG', 'false').lower() == 'true':
            middleware.append(
                Middleware(
                    PyInstrumentMiddleware,
                    enabled = True,
                    profile_dir = "profiles"
                )
            )

        self.app = Starlette(
            routes = [
               Route('/', self.health),
                Route('/manifest.json', self.manifest),
                Route('/stream/{type}/{id}.json', self.stream) 
            ],
            on_shutdown = [self.on_shutdown],
            on_startup = [self.on_startup],
            debug = os.getenv('DEBUG', 'false').lower() == 'true',
            middleware = middleware
        )    

        self.logger = logging.getLogger("uvicorn")
        self.host_ip = "127.0.0.1"


    async def on_startup(self):
        if os.environ.get("SHOW_BANNER", False):
            banner = os.path.join(os.path.dirname(__file__), "assets", "banner.txt")
            with open(banner, "r") as f:
                print(f.read())

        if os.environ.get("ENABLE_IP_GET", False):
            async with self.client.get("http://checkip.amazonaws.com/") as response:
                response.raise_for_status()
                self.host_ip = await response.text()
                self.host_ip = self.host_ip.strip()

        self.logger.info(f"Stremio Manifest: http://{self.host_ip}:5000/manifest.json")

        if os.environ.get("TMDB_READ_API_KEY", None) is None or len(os.environ.get("TMDB_READ_API_KEY", "")) < 32:
            self.logger.error("TMDB_READ_API_KEY is not set or is invalid!")
            exit(1)
    

    async def on_shutdown(self):
        self.logger.warning("Orbiting away... bye bye!")
        await self.client.close()


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
        
        m3u8 = None
        description = None

        if stream_type == "movie":
            details = await self.tmdb.grab_details(content_id, media_type="movie")

            tmdb_id = details["tmdb_id"]
            tokens = await self.vixsrc.extract_token(tmdb_id)
            m3u8 = await self.vixsrc.get_playlist(tokens)

            description = f"🎥 ❯ {details['title']}\n⭐️ ❯ {details['vote_avg']}\n🌐 ❱ VXSRC"

        elif stream_type == "series":
            params = unquote(content_id).split(":")
            content_id = params[0] # tt00000
            season = params[1]
            episode = params[2]
            
            details = await self.tmdb.grab_details(content_id, media_type="tv")
            tokens = await self.vixsrc.extract_token(details["tmdb_id"], season, episode)
            m3u8 = await self.vixsrc.get_playlist(tokens)

            description = f"📺 ❯ {details['title']}\n⭐️ ❯ {details['vote_avg']}\n⌚ ❯ Season: {season} - Episode: {episode}\n🌐 ❱ VXSRC"            

        else:
            return JSONResponse({"error": "Invalid stream type"}, status_code=400)
        
        if m3u8 is None or description is None:
            self.logger.error(f"Failed to get stream for {content_id} of type {stream_type}. stream: {m3u8}, description: {description}")
            return JSONResponse({"error": "Failed to get stream"}, status_code=500)

        stream = {
            "url": m3u8,
            "name": "🔭 | Orbit",
            "description": description,
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