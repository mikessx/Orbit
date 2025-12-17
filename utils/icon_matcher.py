from unidecode import unidecode
from rapidfuzz import fuzz, process
import os
import re

class TVIconMatcher:
    ICONS_INDEX = os.path.join(os.path.dirname(__file__), "icons.txt")
    STOP_WORDS = {
        "tv",
        "channel",
        "hd",
        "italia",
        "italy",
        "official",
        "stream",
        "live",
        "network",
        "plus",
        "it",
        "ita"
    }

    def __init__(self, icon_file: str = ICONS_INDEX, icon_not_available: str = ""):
        self.index = self.build_index(icon_file)
        self.icon_not_available = icon_not_available

    def normalize_name(self, name: str) -> str:
        name = unidecode(name.lower())
        name = re.sub(r"\.png$", "", name)
        name = re.sub(r"[-_]", " ", name)
        name = re.sub(r"\d+", "", name)

        tokens = [t for t in name.split() if t not in self.STOP_WORDS]
        return " ".join(tokens).strip()
    
    def build_index(self, icon_file: str) -> dict:
        with open(icon_file, "r", encoding="utf-8") as f:
            icons = [line.strip() for line in f if line.strip()]

        index = {}
        for icon in icons:
            normalized_icon = self.normalize_name(icon)
            index[icon] = normalized_icon
        return index

    def match_icon(self, channel_name: str, threshold: int = 80, return_logo_url: bool = False) -> str | None:
        normalized_channel = self.normalize_name(channel_name)
        
        match = process.extractOne(
            normalized_channel,
            self.index.values(),
            scorer=fuzz.token_sort_ratio
        )

        if not match:
            return self.icon_not_available
        match_name, score, indx = match

        if score < threshold:
            return self.icon_not_available
        
        choosen = list(self.index.keys())[indx]

        return choosen if not return_logo_url else f"https://github.com/tv-logo/tv-logos/blob/main/countries/italy/{choosen}?raw=true"