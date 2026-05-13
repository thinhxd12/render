import os
import asyncio
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

@app.post("/api/scrape")
async def scrape_data(request: ScrapeRequest, api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    target_url = str(request.url)
    
    # Initialize Playwright browser context asynchronously
    async with async_playwright() as p:
        # Launch Chromium with anti-sandbox configurations for Linux Docker layers
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]
        )
        
        # Emulate a standard high-resolution desktop device browser fingerprint
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = await context.new_page()
        
        try:
            # Navigate and wait up to 30 seconds for network requests to finish settling
            await page.goto(target_url, wait_until="networkidle", timeout=30000)
            
            # (Optional fallback) Wait an explicit 2 seconds to let late client scripts render
            await asyncio.sleep(2)
            
            # Extract the live DOM state (including JavaScript injected elements)
            raw_html = await page.content()
            
            return {
                "success": True,
                "target": target_url,
                "html": raw_html
            }
            
        except Exception as e:
            return {"success": False, "error": f"Playwright engine crash: {str(e)}"}
        finally:
            # Safely close context allocations to prevent ghost processes and memory leaks
            await context.close()
            await browser.close()
