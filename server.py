from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

from providers.vixsrc import VXSRCScraper
from providers.vavoo import VavooScraper
from providers.cb01 import CB01Scraper
from utils.profiler import PyInstrumentMiddleware
from utils.icon_matcher import TVIconMatcher
from utils.tmdb import TMDB
from utils.general import get_env_bool
from utils.mfp import generate_url, check_health, extract_video

from dotenv import load_dotenv
from urllib.parse import unquote, urlencode
from datetime import datetime

import os
import aiohttp
import logging
import json
import asyncio

from rich.pretty import pprint

class Addon:
    def __init__(self):
        dev_env_path = os.path.join(os.path.dirname(__file__), "dev.env")
        if os.path.exists(dev_env_path):
            load_dotenv(dotenv_path=dev_env_path)
        else:
            load_dotenv()

        self.client = None
        self.tmdb = None
        self.vixsrc = None
        self.vavoo = None
        self.cb01 = None
        self.icon_matcher = TVIconMatcher(icon_file=os.path.join(os.path.dirname(__file__), "assets", "icons.txt"), icon_not_available="https://i.postimg.cc/RF6QWqLd/logo.png")

        self.metadata_cache = {}
        self.channel_cache = {}

        self.addon_manifest = {           
            "id": "it.film.orbit",
            "version": "0.0.1",
            "description": "Fast and easy-to-use stream provider. F&O",
            "name": "Orbit",
            "resources": [
                "stream",
                "catalog",
                "meta"
            ],
            "types": [  
                "movie",
                "series",
                "tv"
            ],
            "catalogs": [
                {
                    "type": "tv",
                    "id": "orbit-tv",
                    "name": "Orbit LiveTV",
                    "extra": [
                        {
                            "name": "genre", 
                            "options": [
                                "Tutti",
                                "Sky",
                                "Mediaset",
                                "Rai",
                                "Regionali",
                                "Cinema",
                                "Sport",
                                "Kids",
                                "Musica",
                                "News",
                                "Documentari",
                                "Intrattenimento",
                            ]
                        },
                        { "name": "genre", "isRequired": False },
                        { "name": "search", "isRequired": False }
                    ]
                }
            ],
            "idPrefixes": ["tt", "tmdb", "orbit-tv"],
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
        if get_env_bool("DEBUG") and get_env_bool("ENABLE_PROFILER"):
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
                Route('/stream/{type}/{id}.json', self.stream_endpoint),
                Route('/catalog/{type}/{name}.json', self.catalog),
                Route('/catalog/{type}/{name}/{extra}.json', self.catalog),
                Route('/meta/{type}/{id}.json', self.meta)
            ],
            on_shutdown = [self.on_shutdown],
            on_startup = [self.on_startup],
            debug = get_env_bool("DEBUG"),
            middleware = middleware
        )    

        self.logger = logging.getLogger("uvicorn")
        self.host_ip = "127.0.0.1"


    async def on_startup(self):
        self.client = aiohttp.ClientSession()
        self.tmdb = TMDB(os.getenv('TMDB_READ_API_KEY'), client=self.client)
        self.vixsrc = VXSRCScraper(self.client)
        self.vavoo = VavooScraper(self.client, self.icon_matcher)
        self.cb01 = CB01Scraper(self.client)
        
        if get_env_bool("SHOW_BANNER"):
            banner = os.path.join(os.path.dirname(__file__), "assets", "banner.txt")
            with open(banner, "r") as f:
                self.logger.info( "\n" + f.read())

        if get_env_bool("ENABLE_IP_GET"):
            async with self.client.get("http://checkip.amazonaws.com/") as response:
                response.raise_for_status()
                self.host_ip = await response.text()
                self.host_ip = self.host_ip.strip()

        self.logger.info(f"Stremio Manifest: http://{self.host_ip}:5000/manifest.json")

        if os.environ.get("TMDB_READ_API_KEY", None) is None or len(os.environ.get("TMDB_READ_API_KEY", "")) < 32:
            self.logger.error("TMDB_READ_API_KEY is not set or is invalid!")
            exit(1)
        
        
        mfp_enabled = get_env_bool("MFP_ENABLED", False)
        mfp_host, mfp_port = os.getenv("MFP_HOST", "127.0.0.1").split(":")

        if mfp_enabled:
            self.logger.info(f"Checking for MFP at {mfp_host}:{mfp_port}")
            try:
                async with self.client.get(f"http://{mfp_host}:{mfp_port}/health") as response:
                    response.raise_for_status()
                    
                    status = await response.json()
                    status = status["status"]

                    if status != "healthy":
                        self.logger.error("MFP is not running! Please start it and try again.")
                        exit(1)
                    else:
                        self.logger.info("MFP is running smoothly!")
            except Exception as e:
                self.logger.error(f"Failed to connect to MFP: {e}")
                self.logger.error("Please start MFP and try again, or disable it in the config.")
                await self.client.close()
                exit(1)

        self.logger.info("Gathering TV Channels...")
        channels = await self.vavoo.getChannels()
        
        self.channel_cache = {
            "last_updated": datetime.now().isoformat(),
            "channels": {channel["name"]: channel for channel in channels}
        }

        self.logger.info(f"{len(channels)} TV Channels cached!")


    async def on_shutdown(self):
        self.logger.warning("Orbiting away... bye bye!")
        await self.client.close()


    async def health(self, request: Request):
        return JSONResponse({
            "status": "OK",
            "version": self.addon_manifest['version'] 
        })


    async def manifest(self, request: Request):
        return JSONResponse(self.addon_manifest)


    async def stream_endpoint(self, request: Request):
        stream_type = request.path_params['type']
        content_id: str = request.path_params['id']

        self.logger.info(f"Requested stream for {content_id} of type {stream_type}.")
        streams = []
        episode = None
        season = None

        match stream_type:
            case "tv":
                if content_id.startswith("orbit-tv:"):
                    channel_name = unquote(content_id.removeprefix("orbit-tv:")).replace("_", " ")
                    vavoo_streams = await self.get_streams_tv(channel_name)
                    streams.extend(vavoo_streams)
                return JSONResponse({"streams": streams})

            case "series":
                params = unquote(content_id).split(":")
                content_id = params[0] # tt00000
                season = params[1]
                episode = params[2]

        details = await self.tmdb.grab_details(content_id, media_type="tv" if stream_type == "series" else "movie")
        
        tasks = [
            asyncio.create_task(self.get_streams_vixsrc(details, media_type=stream_type, season=season, episode=episode)),
            asyncio.create_task(self.get_streams_cb01(details, media_type=stream_type, season=season, episode=episode))
        ]
        
        done, pending = await asyncio.wait(tasks, timeout=2.0)
        
        for task in pending:
            self.logger.warning(f"Task timed out: {task}")
            task.cancel()
        
        for task in done:
            try:
                result = task.result()
                if result:
                    streams.extend(result)
            except Exception as e:
                self.logger.error(f"Task failed: {e}")

        return JSONResponse({"streams": streams})


    async def get_streams_vixsrc(self, details, media_type: str = "movie", season: int = None, episode: int = None, use_mfp: bool = True) -> list[dict]:
        if media_type == "tv" and (season is None or episode is None):
            raise ValueError("Season and episode must be provided for TV shows")
        
        tokens = await self.vixsrc.extract_token(details["tmdb_id"], season, episode)
        m3u8 = await self.vixsrc.get_playlist(tokens)

        streams = [
            {
                "url": m3u8,
                "name": "🪐 | Orbit",
                "description": f"🎬 ❯ {details["title"]}\n⭐️ ❯ {details["vote_avg"]}\n🌐 ❱ VIXSRC",
                "behaviorHints": {
                    "notWebReady": True,
                    "proxyHeaders": {
                        "request": { 
                            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0", 
                            "Referer": self.vixsrc.host 
                        },
                        "response": { "Access-Control-Allow-Origin": "*" }
                    }
                }
            }
        ]

        if use_mfp:
            mfp = self.get_mfp()
            if not mfp: 
                return streams
            
            request_headers = None 
            response_headers = None
        
            if "behaviorHints" in streams[0]:
                request_headers = streams[0]["behaviorHints"]["proxyHeaders"]["request"]
                response_headers = streams[0]["behaviorHints"]["proxyHeaders"]["response"]
                refer = request_headers["Referer"]

            proxied_m3u8 = await generate_url(
                client = self.client,
                mfp_host= mfp,
                destination = m3u8,
                request_headers = request_headers,
                response_headers = response_headers,
                api_password = os.getenv("API_PASSWORD", ""),
                referer = refer
            )
            if proxied_m3u8:
                streams.append({
                    "url": proxied_m3u8,
                    "name": "🪐 | Orbit",
                    "description": f"🎬 ❯ {details["title"]}\n⭐️ ❯ {details["vote_avg"]}\n🌐 ❱ VIXSRC\n🔗 ❯ Proxied via MFP"
                })
        return streams


    async def get_streams_cb01(self, details, media_type: str = "movie", season: int = None, episode: int = None) -> dict:
        if media_type == "tv" and (season is None or episode is None):
            raise ValueError("Season and episode must be provided for TV shows")
        if media_type == "tv":
            self.logger.warning("CB01 Serie non implementato.")
            return

        release_date = details["release_date"][:4]
        mixdrop = await self.cb01.search_movies(details["title"], release_date)
        
        try:
            extracted = await extract_video(
                mfp_host = self.get_mfp(),
                stream_url = mixdrop,
                provider = "Mixdrop",
                api_password = os.getenv("API_PASSWORD", ""),
                client = self.client
            )
        except aiohttp.ClientResponseError:
            self.logger.error("Exeception raised remotly and failed to extract video from Mixdrop.")
            return

        if not extracted:
            self.logger.error("Failed to extract video from Mixdrop.")
            return

        m3u8 = extracted.get("destination_url")
        proxied_url = await generate_url(
            client = self.client,
            mfp_host= self.get_mfp(),
            destination = m3u8,
            request_headers = extracted.get("request_headers"),
            api_password = os.getenv("API_PASSWORD", ""),
            endpoint = extracted.get("mediaflow_proxy_url")
        )

        streams = [
            {
                "url": proxied_url,
                "name": "🪐 | Orbit",
                "description": f"🎬 ❯ {details["title"]}\n⭐️ ❯ {details["vote_avg"]}\n🌐 ❱ CB01 + MFP",
            }
        ]
        return streams


    async def get_streams_tv(self, channel_name: str, use_mfp: bool = True):
        channel = self.__get_channel(channel_name)
        if channel is None:
            return None
        
        streams = []
        m3u8 = await self.vavoo.get_stream(channel["url"])

        streams.append({
            "url": m3u8,
            "name": "🪐 | Orbit",
            "description": f"📺 ❯ {channel['name']}\n🌐 ❱ VAVOO",
            "behaviorHints": {
                "notWebReady": True,
                "proxyHeaders": {
                    "request": {
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0",
                        "Referer": "https://vavoo.to/"
                    },
                    "response": { "Access-Control-Allow-Origin": "*" }
                }
            }
        })

        if use_mfp:
            mfp = self.get_mfp()
            if not mfp:
                return streams

            proxied_m3u8 = await generate_url(
                client = self.client,
                mfp_host= mfp,
                destination = m3u8,
                api_password = os.getenv("API_PASSWORD", ""),
            )
            if proxied_m3u8:
                streams.append({
                    "url": proxied_m3u8,
                    "name": "🪐 | Orbit",
                    "description": f"📺 ❯ {channel['name']}\n🌐 ❱ VAVOO\n🔗 ❱ Proxied via MFP"
                })
        return streams
    

    async def catalog(self, request: Request):
        catalog_type = request.path_params['type']
        catalog_name = request.path_params['name']
        
        extra = request.path_params.get('extra', None)
        genre = None
        if extra and extra.startswith("genre="):
            genre = unquote(extra).split("=")[1]
        
        self.logger.info(f"Requested catalog for {catalog_name} of type {catalog_type} with genre {genre if extra else 'N/A'}")

        if catalog_type == "tv" and catalog_name == "orbit-tv":
            metaitems = []

            for channel_name, channel in self.channel_cache.get("channels", {}).items():
                if extra and genre != "Tutti":
                    if "genres" not in channel or genre not in channel["genres"]:
                        continue

                metaitems.append({
                    "id": "orbit-tv:" + channel["name"].replace(" ", "_"),
                    "type": "tv",
                    "name": channel["name"],
                    "poster": channel["icon"],
                    "background": channel["icon"],
                    "logo": channel["icon"],
                    "description": f"📺 ❯ {channel['name']}",
                    "genres": channel.get("genres", ["Tutti"])
                })

                self.metadata_cache["orbit-tv:" + channel["name"].replace(" ", "_")] = metaitems[-1]
            return JSONResponse({"metas": metaitems})


    def get_mfp(self):
        if not get_env_bool("MFP_ENABLED", False):
            return None
        
        try:
            mfp_host, mfp_port = os.getenv("MFP_HOST", "127.0.0.1:8888").split(":")
        except ValueError:
            mfp_host = os.getenv("MFP_HOST")
            if not check_health(self.client, mfp_host):
                self.logger.error("MFP_HOST is not set correctly!")
                return None
        else:
            mfp_host = f"http://{mfp_host}:{mfp_port}"
        return mfp_host


    async def meta(self, request: Request):
        meta_type = request.path_params['type']
        content_id = unquote(request.path_params['id'])

        if meta_type == "tv" and content_id.startswith("orbit-tv:"):

            if content_id in self.metadata_cache:
                self.logger.info(f"Returning cached metadata for {content_id}")
                return JSONResponse({"meta": self.metadata_cache[content_id]})

            self.logger.warning(f"Metadata for {content_id} not found in cache, regenerating...")
            channel_name = content_id.split("orbit-tv:")[1].replace("_", " ")

            channel = self.__get_channel(channel_name)

            if channel is not None:
                metaitem = {
                    "id": "orbit-tv:" + channel["name"].replace(" ", "_"),
                    "type": "tv",
                    "name": channel["name"],
                    "poster": channel["icon"],
                    "background": channel["icon"],
                    "logo": channel["icon"],
                    "description": f"📺 ❯ {channel['name']}",
                    "genres": channel.get("genres", ["Tutti"])
                }
                return JSONResponse({"meta": metaitem})
        
        if meta_type == "movie":
            return JSONResponse({"meta": None})
        if meta_type == "series":
            return JSONResponse({"meta": None})

    def __get_channel(self, channel_name: str) -> dict | None:
        return self.channel_cache.get("channels", {}).get(channel_name, None)


if __name__ == "__main__":
    import uvicorn
    import asyncio
    from uvicorn.protocols.http.h11_impl import H11Protocol
    
    class DebugProtocol(H11Protocol):
        def data_received(self, data: bytes):
            print(f"\n{'='*50}")
            print(f"RAW DATA ({len(data)} bytes):")
            print(data[:200].hex(' '))
            print(f"{'='*50}\n")
            return super().data_received(data)
    
    addon = Addon()
    app = addon.app
    
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="debug",
        access_log=True,
        ssl_certfile="cert.pem",
        ssl_keyfile="key.pem"
    )
    config.http = DebugProtocol
    server = uvicorn.Server(config)
    server.run()
else:
    addon = Addon()
    app = addon.app
