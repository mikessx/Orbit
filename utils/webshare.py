import aiohttp
import json

class Webshare:
    def __init__(self, api_key: str, client: aiohttp.ClientSession = None):
        self.api_key = api_key
        self.client = client

    async def get_proxy_list(self):
        url = "https://proxy.webshare.io/api/v2/proxy/list"
        headers = {
            "Authorization": f"Token {self.api_key}"
        }
        params = {
            "mode": "direct",
            "ordering": "valid",
            "valid": "true"
        }
        async with self.client.get(url, headers=headers, params=params) as response:
            response.raise_for_status()
            proxy_list = await response.json()

        proxy_return = {"count": proxy_list["count"], "results": []}
        for proxy in proxy_list["results"]:
            username = proxy["username"]
            password = proxy["password"]
            address = proxy["proxy_address"]
            port = proxy["port"]
            proxy_return["results"].append(f"http://{username}:{password}@{address}:{port}")
        return proxy_return
    
    async def get_notifications(self):
        url = "https://proxy.webshare.io/api/v2/notification/"
        headers = {
            "Authorization": f"Token {self.api_key}"
        }

        async with self.client.get(url, headers=headers) as response:
            response.raise_for_status()
            notifications = await response.json()
            notifications = notifications.get("results", [])
        
        return notifications
    
    async def get_message_associated(self, notifications: list[dict]) -> list[str]:
        messages = []

        for notification in notifications:
            ntf_type = notification.get("type", "")
            match ntf_type:
                case "100_percent_bandwidth_used":
                    messages.append({"msg": r"You used 100% of your available bandwith!", "stop": True})
                case "projected_proxy_usage_over_80":
                    messages.append({"msg": r"Your projected proxy usage is over 80%!", "stop": False})
        return messages
