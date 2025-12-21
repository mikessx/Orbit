import aiohttp
import re

VAVOO_DOMAIN = "vavoo.to"
VAVOO_PING_DOMAIN = "www.vavoo.tv"
GENRES_MAP = {
    "Sky": [
        "Sky Atlantic",
        "Sky Cinema Action",
        "Sky Cinema Action (Backup)",
        "Sky Cinema Collection",
        "Sky Cinema Comedy",
        "Sky Cinema Due",
        "Sky Cinema Due +24",
        "Sky Cinema Family",
        "Sky Cinema Romance",
        "Sky Cinema Suspense",
        "Sky Cinema Uno",
        "Sky Cinema Uno +24",
        "Sky Primafila 1",
        "Sky Primafila 10",
        "Sky Primafila 2",
        "Sky Primafila 3",
        "Sky Primafila 4",
        "Sky Primafila 5",
        "Sky Primafila 6",
        "Sky Primafila 7",
        "Sky Primafila 8",
        "Sky Primafila 9",
        "Sky Sport",
        "Sky Sport 24 [Live During Events Only]",
        "Sky Sport Calcio",
        "Sky Sport Football [Live During Events Only]",
        "Sky Sport Golf",
        "Sky Sport Motogp",
        "Sky Sport Nba",
        "Sky Sport Tennis",
        "Sky Sport Uno",
        "Sky Sports F1",
        "Sky Super Tennis",
        "Sky Tg 24",
        "Sky Uno"
    ],
    "Mediaset": [
        "Cine 34 Mediaset",
        "Canale 5",
        "Mediaset 1",
        "Mediaset 20",
        "Mediaset Iris",
        "Mediaset Italia 2",
        "Rete 4",
        "La 5",
        "Prima Tv"
    ],
    "Rai": [
        "Rai 1",
        "Rai 2",
        "Rai 3",
        "Rai 4",
        "Rai 5",
        "Rai Gulp",
        "Rai Italia",
        "Rai Movie",
        "Rai News 24",
        "Rai Premium",
        "Rai Scuola",
        "Rai Sport [Live During Events Only]",
        "Rai Sport+",
        "Rai Storia",
        "Rai Südtirol",
        "Rai Yoyo"
    ],
    "Regionali": [
        "Alto Adige Tv",
        "Antenna Sicilia",
        "Antenna Sud",
        "Carina Tv",
        "Cremona 1",
        "Elive Tv Brescia",
        "Entella Tv",
        "Espansione Tv",
        "Esperia Tv",
        "Esperia Tv 18",
        "Etv Marche",
        "Euro Tv",
        "Fano Tv",
        "Icaro Tv",
        "Italia 3",
        "Italia 3",
        "Italian Fishing Tv",
        "La 7",
        "Lazio Tv",
        "Lira Tv",
        "Onda Novara Tv",
        "Onda Tv",
        "Orler Tv",
        "Primo Canale",
        "Primocanale",
        "Quadrifoglio Tv",
        "Quarta Rete",
        "Reggio Tv",
        "Rete Oro",
        "Rete Sole",
        "Rete Tv Italia",
        "Rete Veneta",
        "Retebiella Tv",
        "Retesole Lazio",
        "Rtc Telecalabria",
        "Rttr",
        "Rttr Tv",
        "Rtv San Marino",
        "Rtv San Marino Sport",
        "Super Tv Aristanis",
        "Super Tv Brescia",
        "Supersix Lombardia",
        "Tele Abruzzo"
    ],
    "Cinema": [
        "Disney+ Film",
        "Rakuten Action Movies",
        "Rakuten Comedy Movies",
        "Rakuten Drama",
        "Rakuten Family",
        "Rakuten Top Free",
        "Rakuten Tv Shows",
        "Premium Crime",
        "Sky Cinema Action",
        "Sky Cinema Action (Backup)",
        "Sky Cinema Collection",
        "Sky Cinema Comedy",
        "Sky Cinema Due",
        "Sky Cinema Due +24",
        "Sky Cinema Family",
        "Sky Cinema Romance",
        "Sky Cinema Suspense",
        "Sky Cinema Uno",
        "Sky Cinema Uno +24",
        "Sky Primafila 1",
        "Sky Primafila 10",
        "Sky Primafila 2",
        "Sky Primafila 3",
        "Sky Primafila 4",
        "Sky Primafila 5",
        "Sky Primafila 6",
        "Sky Primafila 7",
        "Sky Primafila 8",
        "Sky Primafila 9",
        "Cine 34 Mediaset",
        "Mediaset Iris",
        "Rakuten Action Movies"
    ],
    "Sport": [
        "Dazn",
        "Eurosport 1",
        "Eurosport 2",
        "Sky Sport",
        "Sky Sport 24 [Live During Events Only]",
        "Sky Sport Calcio",
        "Sky Sport Football [Live During Events Only]",
        "Sky Sport Golf",
        "Sky Sport Motogp",
        "Sky Sport Nba",
        "Sky Sport Tennis",
        "Sky Sport Uno",
        "Sky Sports F1",
        "Sky Super Tennis",
        "Sport Italia",
        "Sport Italia Solo Calcio [Live During Events Only]",
        "Super Tennis",
        "Rai Sport [Live During Events Only]",
        "Rai Sport+",
        "Eurosport 1"
    ],
    "Kids": [
        "Baby Tv",
        "Boing",
        "Cartoon Network",
        "Cartoonito",
        "Cartoonito (Backup)",
        "Iunior Tv",
        "K2",
        "Rai Gulp",
        "Rai Yoyo",
        "Super!"
    ],
    "Musica": [
        "Euro Indie Music Chart Tv",
        "Kiss Kiss",
        "Kiss Kiss Italia",
        "Kiss Kiss Napoli",
        "Mtv",
        "Mtv Hits",
        "Ol3 Radio",
        "Radio 51",
        "Radio Capital",
        "Radio Freccia",
        "Rds Social",
        "Rds Social Tv",
        "Deejay Tv"
    ],
    "News": [
        "Bloomberg Tv",
        "France 24 (En)",
        "Rai News 24",
        "Sky Tg 24",
        "Camera Dei Deputati",
        "Senato Tv",
        "Senato Tv",
        "Byoblu",
        "Sky Tg 24",
        "Bloomberg Tv"
    ],
    "Documentari": [
        "Animal Planet",
        "Discovery Channel",
        "Discovery Focus",
        "Discovery K2",
        "Discovery Nove",
        "Nat Geo",
        "Nat Geo Wild",
        "Focus",
        "Giallo",
        "Dmax",
        "Motortrend",
        "Motortrend",
        "People Are Awesome"
    ],
    "Intrattenimento": [
        "111 Tv",
        "27 Twenty Seven",
        "Arte Network",
        "Aurora Arte",
        "Avengers Grimm Channel",
        "Bellla & Monella Tv",
        "Byoblu",
        "Catfish",
        "Cielo",
        "Comedy Central",
        "Company Tv",
        "Crime + Inv",
        "Deejay Tv",
        "Disney+ Film",
        "Euro Tv",
        "Fashion Tv",
        "Fm Italia",
        "Food Network",
        "Fox",
        "Globus Television",
        "Hgtv",
        "Icaro Tv",
        "Italia 3",
        "Italian Fishing Tv",
        "Kiss Kiss",
        "Kiss Kiss Italia",
        "La 5",
        "La 7",
        "Lazio Tv",
        "Lira Tv",
        "Mediaset 20",
        "Mediaset Italia 2",
        "Mtv",
        "Mtv Hits",
        "People Are Awesome",
        "Pesca E Caccia",
        "Prima Tv",
        "Primo Canale",
        "Primocanale",
        "Qvc",
        "Real Time",
        "Rei Tv",
        "Rete 4",
        "Rete Tv Italia",
        "Rsi La 1",
        "Rsi La 2",
        "Rtp (Rete Televisiva)",
        "Rttr",
        "Rttr Tv",
        "Rtv San Marino",
        "Sky Uno",
        "Super!",
        "Tele Abruzzo",
        "Other local/general channels"
    ],
    "Altro": []
}




class VavooScraper:
    def __init__(self, client: aiohttp.ClientSession, matcher):
        self.client = client
        self.icon_matcher = matcher
    
    async def getSignature(self, proxy = None) -> str:
        """Funzione che replica esattamente quella dell'addon utils.py"""
        headers = {
            "user-agent": "okhttp/4.11.0",
            "accept": "application/json",
            "content-type": "application/json; charset=utf-8",
            "accept-encoding": "gzip"
        }
        data = {
            "token": "tosFwQCJMS8qrW_AjLoHPQ41646J5dRNha6ZWHnijoYQQQoADQoXYSo7ki7O5-CsgN4CH0uRk6EEoJ0728ar9scCRQW3ZkbfrPfeCXW2VgopSW2FWDqPOoVYIuVPAOnXCZ5g",
            "reason": "app-blur",
            "locale": "de",
            "theme": "dark",
            "metadata": {
                "device": {
                    "type": "Handset",
                    "brand": "google",
                    "model": "Nexus",
                    "name": "21081111RG",
                    "uniqueId": "d10e5d99ab665233"
                },
                "os": {
                    "name": "android",
                    "version": "7.1.2",
                    "abis": ["arm64-v8a", "armeabi-v7a", "armeabi"],
                    "host": "android"
                },
                "app": {
                    "platform": "android",
                    "version": "3.1.20",
                    "buildId": "289515000",
                    "engine": "hbc85",
                    "signatures": ["6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e"],
                    "installer": "app.revanced.manager.flutter"
                },
                "version": {
                    "package": "tv.vavoo.app",
                    "binary": "3.1.20",
                    "js": "3.1.20"
                }
            },
            "appFocusTime": 0,
            "playerActive": False,
            "playDuration": 0,
            "devMode": False,
            "hasAddon": True,
            "castConnected": False,
            "package": "tv.vavoo.app",
            "version": "3.1.20",
            "process": "app",
            "firstAppStart": 1743962904623,
            "lastAppStart": 1743962904623,
            "ipLocation": "",
            "adblockEnabled": True,
            "proxy": {
                "supported": ["ss", "openvpn"],
                "engine": "ss",
                "ssVersion": 1,
                "enabled": True,
                "autoServer": True,
                "id": "pl-waw"
            },
            "iap": {
                "supported": False
            }
        }

        try:
            async with self.client.post("https://www.vavoo.tv/api/app/ping", json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=10), expect100=False, proxy=proxy) as resp:
                resp.raise_for_status()
                json_data = await resp.json()
                return json_data.get("addonSig")
        except Exception as e:
            print(f"Errore nel recupero della signature: {e}")
            return None
    

    async def getChannels(self, groups: list[str] = ["Italy"], proxy = None) -> list[dict]:
        signature = await self.getSignature(proxy=proxy)
        if signature is None or signature == "":
            print("Signature non valida")
            return None
        
        headers = {
            "user-agent": "okhttp/4.11.0",
            "accept": "application/json",
            "content-type": "application/json; charset=utf-8",
            "accept-encoding": "gzip",
            "mediahubmx-signature": signature
        }

        saved = list()

        for group in groups:
            cursor = 0
            while True:
                data = {
                    "language": "de",
                    "region": "AT",
                    "catalogId": "iptv",
                    "id": "iptv",
                    "adult": False,
                    "search": "",
                    "sort": "name",
                    "filter": {"group": group},
                    "cursor": cursor,
                    "clientVersion": "3.0.2"
                }
                async with self.client.post(f"https://{VAVOO_DOMAIN}/mediahubmx-catalog.json", json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=10), expect100=False, proxy=proxy) as response:
                    response.raise_for_status()
                    payload = await response.json()

                    items = payload.get("items", [])

                    for item in items:
                        name = item["name"]
                        name.strip()
                        name = re.sub(r'\s+\.[a-zA-Z]$', '', name)
                        name = name.title()
                        item["name"] = name
                    
                        item.pop("ids", None)
                        item.pop("group", None)
                        item.pop("logo", None)
                        item.pop("type", None)

                        possible_icon = self.icon_matcher.match_icon(name, return_logo_url=True)
                        item["icon"] = possible_icon

                        item["genres"] = self.generate_genres(name)

                    saved.extend(items)
                    
                    cursor = payload.get("nextCursor")
                    if not cursor:
                        break
        return saved

    async def get_stream(self, channel_link: str, return_details: bool = False, proxy = None) -> dict | str:
        signature = await self.getSignature(proxy=proxy)
        if signature is None or signature == "":
            print("Signature non valida")
            return None
        
        headers = {
            "user-agent": "MediaHubMX/2",
            "accept": "application/json",
            "content-type": "application/json; charset=utf-8",
            "accept-encoding": "gzip",
            "mediahubmx-signature": signature
        }
        data = {
            "language": "de",
            "region": "AT",
            "url": channel_link,
            "clientVersion": "3.0.2"
        }

        async with self.client.post(f"https://{VAVOO_DOMAIN}/mediahubmx-resolve.json", json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=10), expect100=False, proxy=proxy) as response:
            response.raise_for_status()
            payload = await response.json()
            
            if isinstance(payload, list):
                payload = payload[0]
            if return_details:
                return payload
            return payload["url"] # Headers : { 'User-Agent': DEFAULT_VAVOO_UA, 'Referer': 'https://vavoo.to/' }


    def generate_genres(self, channel_name: str) -> list[str]:
        global GENRES_MAP
        genres = ["Tutti"]

        for genre, channels in GENRES_MAP.items():
            if channel_name in channels:
                genres.append(genre)
        return genres