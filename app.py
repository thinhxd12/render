import os
from fastapi import FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from playwright.async_api import async_playwright

app = FastAPI()

API_KEY = os.environ.get("SCRAPER_SECRET_KEY", "my_fallback_secret_key")
api_key_header = APIKeyHeader(name="X-Scraper-Key", auto_error=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScrapeRequest(BaseModel):
    url: HttpUrl

# block pages by resource type. e.g. image, stylesheet
BLOCK_RESOURCE_TYPES = [
  'beacon',
  'csp_report',
  'font',
  'image',
  'imageset',
  'media',
  'object',
  'texttrack',
#  we can even block stylsheets and scripts though it's not recommended:
# 'stylesheet',
# 'script',  
# 'xhr',
]

def intercept_route(route):
    """intercept all requests and abort blocked ones"""
    if route.request.resource_type in BLOCK_RESOURCE_TYPES:
        return route.abort()
    if any(key in route.request.url for key in BLOCK_RESOURCE_NAMES):
        return route.abort()
    return route.continue_()


# we can also block popular 3rd party resources like tracking and advertisements.
BLOCK_RESOURCE_NAMES = [
  'adzerk',
  'analytics',
  'cdn.api.twitter',
  'doubleclick',
  'exelator',
  'facebook',
  'fontawesome',
  'google',
  'google-analytics',
  'googletagmanager',
]


# --- GLOBAL PLAYWRIGHT STATE ---
playwright_manager = None
global_browser = None

@app.on_event("startup")
async def startup_event():
    """Launches Chromium ONCE when the Docker container starts up"""
    global playwright_manager, global_browser
    print("🚀 Starting global background browser system...")
    playwright_manager = await async_playwright().start()
    global_browser = await playwright_manager.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]
    )
    print("✅ Global browser is live and idling.")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleans up browser allocation nodes when container goes offline"""
    if global_browser:
        await global_browser.close()
    if playwright_manager:
        await playwright_manager.stop()

@app.get("/healthz")
def health_check():
    """Lightweight endpoint for keep-alive pings"""
    return {"status": "healthy", "browser_live": global_browser is not None}

@app.post("/crawl")
async def scrape_data(request: ScrapeRequest, api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    target_url = str(request.url)
    
    # Fast: Open a temporary context tab inside the ALREADY running browser
    context = await global_browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        viewport={"width": 1920, "height": 1080}
    )

    page = await context.new_page()
    await page.route("**/*", intercept_route)

    try:
      # 1. Set up the listener for the main document request returning a 200 status
        async with page.expect_response(
            lambda response: response.url == target_url and response.status == 200
        ) as response_info:
            
            # 2. Trigger the navigation (use "commit" so it doesn't block itself)
            await page.goto(target_url, wait_until="commit")
        
        # 3. Resolve the response target
        response = await response_info.value
        
        # 4. Extract the exact raw HTML sent by the server
        raw_html = await response.text()
        return {"success": True, "target": target_url, "html": raw_html}
        
    except Exception as e:
        return {"success": False, "error": f"Scrape loop aborted: {str(e)}"}
    finally:
        # Instantly close only the tab context, leaving the global browser running
        await context.close()



