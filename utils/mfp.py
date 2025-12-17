import aiohttp

async def check_health(client: aiohttp.ClientSession, mfp_host: str) -> bool:
    mfp_host = mfp_host.rstrip('/')

    try:
        async with client.get(f"{mfp_host}/health") as response:
            response.raise_for_status()
            data = await response.json()
            return data.get("status") == "healthy"
    except Exception:
        return False

async def generate_url(client: aiohttp.ClientSession, mfp_host: str, destination: str, endpoint: str = "/proxy/hls/manifest.m3u8", api_password: str = "", request_headers: dict = { "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0", 'Referer': 'https://vavoo.to/'}, response_headers: dict = { "Access-Control-Allow-Origin": "*" }, check_health_first: bool = True, referer: str = None):
    mfp_host = mfp_host.rstrip('/')
    destination = destination.lstrip('/')

    if referer:
        request_headers['Referer'] = referer

    if check_health_first:
        is_healthy = await check_health(client, mfp_host)
        if not is_healthy:
            raise ConnectionError(f"MediaFlow Proxy at {mfp_host} is not healthy or unreachable.")

    payload = {
        "mediaflow_proxy_url": mfp_host,
        "endpoint": endpoint,
        "destination_url": destination,
        "request_headers": request_headers,
        "response_headers": response_headers,
        "api_password": api_password,
        "base64_encode_destination": False  
    }

    async with client.post(f"{mfp_host}/generate_url", json=payload) as response:
        response.raise_for_status()
        data = await response.json()
        return data.get("url")
    