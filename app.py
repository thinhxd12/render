import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# 1. Import configuration modules to control the browser behavior
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

# 2. Configure a lightweight browser profile to prevent memory spikes
browser_config = BrowserConfig(
    headless=True,
    extra_args=[
        "--disable-gpu", 
        "--no-sandbox", 
        "--disable-dev-shm-usage",
        "--disable-setuid-sandbox"
    ]
)

# 3. Prevent downloading unnecessary assets like large photos/fonts
run_config = CrawlerRunConfig(
    cache_mode=1,  # Enable caching to save memory on duplicate page tracks
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
                "markdown": result.markdown
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
