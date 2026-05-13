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

@app.post("/api/scrape")
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
    
    try:
        # Perform dynamic scraping
        await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        raw_html = await page.content()
        return {"success": True, "target": target_url, "html": raw_html}
        
    except Exception as e:
        return {"success": False, "error": f"Scrape loop aborted: {str(e)}"}
    finally:
        # Instantly close only the tab context, leaving the global browser running
        await context.close()

@app.get("/healthz")
def health_check():
    """Lightweight endpoint for keep-alive pings"""
    return {"status": "healthy", "browser_live": global_browser is not None}

