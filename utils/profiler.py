from pyinstrument import Profiler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse
import os


class PyInstrumentMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, enabled: bool = True, profile_dir: str = "profiles"):
        super().__init__(app)
        self.enabled = enabled
        self.profile_dir = profile_dir
        if enabled and not os.path.exists(profile_dir):
            os.makedirs(profile_dir)

    async def dispatch(self, request, call_next):
        if not self.enabled or request.url.path == "/profile":
            return await call_next(request)

        profiler = Profiler()
        profiler.start()
        
        response = await call_next(request)
        
        profiler.stop()
        
        # Save profile
        profile_path = f"{self.profile_dir}/{request.url.path.replace('/', '_')}.html"
        with open(profile_path, "w") as f:
            f.write(profiler.output_html())
        
        # Add profile header
        response.headers["X-Profile-Path"] = profile_path
        
        return response