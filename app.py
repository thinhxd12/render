import os
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

app = FastAPI(title="Crawl4AI Optimized Low-RAM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CrawlRequest(BaseModel):
    url: str

# 1. Define the interception hook to abort resource-heavy requests
async def before_goto_hook(page, context=None):
    """
    Executes right before navigating to the target URL.
    Interceptors abort slow network traffic like images, fonts, and advertisements.
    """
    # Activate request interception on the Playwright page object
    await page.route("**/*", lambda route: handle_route_interception(route))

def handle_route_interception(route):
    """
    Evaluates request types and aborts non-essential crawling payload.
    """
    request = route.request
    resource_type = request.resource_type
    url = request.url.lower()

    # Block common resource-heavy file types
    ignored_types = ["image", "font", "media", "stylesheet", "websocket"]
    if resource_type in ignored_types:
        return route.abort()

    # Block tracking scripts, advertisements, and analytics
    ignored_domains = [
        "google-analytics.com",
        "googletagmanager.com",
        "facebook.net",
        "analytics",
        "telemetry",
        "doubleclick"
    ]
    if any(domain in url for domain in ignored_domains):
        return route.abort()

    # Continue downloading semantic HTML and foundational JavaScript blocks
    return route.continue_()


# 2. Global Browser Configuration
browser_config = BrowserConfig(
    headless=True,
    extra_args=[
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-setuid-sandbox",
        "--blink-settings=imagesEnabled=false" # Chromium level image disabling
    ]
)

# 3. Crawler Session Engine Configuration
run_config = CrawlerRunConfig(
    cache_mode=1, # Re-use page layout states if duplicate crawls occur
    wait_until="commit", # "commit" stops tracking as soon as HTML is delivered (faster than "networkidle")
)

# 4. Attach your custom hook to the crawler configuration instance
run_config.on_execution_started = before_goto_hook

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/crawl")
async def crawl_url(payload: CrawlRequest):
    try:
        # Pass the memory-optimized configs into the crawler context
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=payload.url, config=run_config)
            
            if not result.success:
                raise HTTPException(status_code=500, detail="Crawl failed")
                
            return {
                "success": True,
                "markdown": result.markdown,
                "html": result.html
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
