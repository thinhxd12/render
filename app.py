import os
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, WebScrapingStrategy

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

# Global persistent instances
global_crawler = None

# MATCH FIRECRAWL SPEED: Configure the browser infrastructure
browser_config = BrowserConfig(
    headless=True,
    # OPTION A: If you have a proxy provider (Smartproxy, Oxylabs, Bright Data), add it here.
    # This prevents Render data-center IPs from being throttled by Cloudflare.
    # proxy="http://username:password@proxy_host:port", 
    extra_args=[
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--blink-settings=imagesEnabled=false" # Stops the browser from requesting images
    ]
)

# MATCH FIRECRAWL SPEED: Optimize the execution strategy
run_config = CrawlerRunConfig(
    # 1. Skip JavaScript rendering if you just need content from standard sites
    # Set to True only if target pages require JS/React/Vue initialization
    magic_mode=False, 
    
    # 2. Firecrawl speed target: Cut the connection as soon as HTML hits the DOM.
    # "commit" stops execution instantly without waiting for analytics/trackers.
    wait_until="commit", 
    
    # 3. Bypass third-party tracking scripts entirely
    exclude_external_links=True,
    
    # 4. Use memory cache for repeated layout patterns
    cache_mode=1
)

@app.on_event("startup")
async def startup_event():
    global global_crawler
    global_crawler = AsyncWebCrawler(config=browser_config)
    await global_crawler.__aenter__() # Keeps the browser pool warm and running 24/7

@app.on_event("shutdown")
async def shutdown_event():
    global global_crawler
    if global_crawler:
        await global_crawler.__aexit__(None, None, None)

@app.post("/crawl")
async def crawl_url(payload: CrawlRequest):
    try:
        # Pull data using the warm browser pool and commit-immediate strategy
        result = await global_crawler.arun(url=payload.url, config=run_config)
        
        if not result.success:
            raise HTTPException(status_code=500, detail="Crawl operation timed out or failed")
            
        return {
            "success": True,
            "markdown": result.markdown
            "html": result.html
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)