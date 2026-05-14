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

browser_config = BrowserConfig(
    headless=True,
    avoid_ads=True,
    avoid_css=True, 
    # memory_saving_mode=True,          # Aggressive cache/V8 heap flags
    # max_pages_before_recycle=100,     # Auto-restart browser after N pages
    # extra_args=[
    #     "--disable-gpu",
    #     "--no-sandbox",
    #     "--disable-dev-shm-usage",
    #     "--disable-setuid-sandbox",
    #     "--blink-settings=imagesEnabled=false" # Chromium level image disabling
    # ]
)

run_config = CrawlerRunConfig(
    cache_mode=1, # Re-use page layout states if duplicate crawls occur
    # wait_until="commit", # "commit" stops tracking as soon as HTML is delivered (faster than "networkidle")
    # scraping_strategy=WebScrapingStrategy()
)

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
