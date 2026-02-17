import urllib.robotparser
import requests
import random
from urllib.parse import urlparse
import time

class RobotExclusionManager:
    """
    Manages robots.txt compliance for various domains.
    Caches results to avoid frequent requests to robots.txt.
    """
    def __init__(self, user_agent="AntigravityBot/1.0"):
        self.user_agent = user_agent
        self.parsers = {}

    def can_fetch(self, url):
        """
        Checks if the given URL can be fetched according to robots.txt.
        """
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        robots_url = f"{base_url}/robots.txt"

        if base_url not in self.parsers:
            rp = urllib.robotparser.RobotFileParser()
            try:
                # Use a small timeout for robots.txt
                response = requests.get(robots_url, timeout=5, headers={"User-Agent": self.user_agent})
                if response.status_code == 200:
                    rp.parse(response.text.splitlines())
                else:
                    # If no robots.txt, assume allowed
                    rp.allow_all = True
            except Exception:
                # On error (timeout, etc.), default to allowed or restricted? 
                # Scrapers usually default to allowed if robots.txt is missing/inaccessible.
                rp.allow_all = True
            
            self.parsers[base_url] = rp

        return self.parsers[base_url].can_fetch(self.user_agent, url)

class UserAgentRotator:
    """
    Provides a variety of common browser User-Agents.
    """
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
    ]

    @classmethod
    def get_random_user_agent(cls):
        return random.choice(cls.USER_AGENTS)

# Shared instance for convenience
robots_manager = RobotExclusionManager()
