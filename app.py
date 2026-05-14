import os
import asyncio
from fastapi import FastAPI, HTTPException, Security, Depends, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    WebScrapingStrategy,
)


API_KEY = os.environ.get("SCRAPER_SECRET_KEY", "my_fallback_secret_key")
api_key_header = APIKeyHeader(name="X-Scraper-Key", auto_error=True)


async def validate_api_key(api_key_header_value: str = Depends(api_key_header)):
    """
    Validates the incoming SCRAPER_SECRET_KEY header against the configured environment secret.
    """
    if not api_key_header_value or api_key_header_value != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing API Key"
        )
    return api_key_header_value


class CrawlRequest(BaseModel):
    url: HttpUrl


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 1. Define global state storage
state = {}

# 2. Modern Lifespan Event Handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the persistent lifecycle of the Crawl4AI browser pool.
    Replaces the deprecated @app.on_event hooks.
    """
    browser_config = BrowserConfig(
        headless=True,
        light_mode=True,
        extra_args=[
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--blink-settings=imagesEnabled=false",  # Stops the browser from requesting images
        ],
    )

    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.__aenter__()

    # Store the running instance in the state dictionary
    state["crawler"] = crawler
    state["run_config"] = CrawlerRunConfig(
        scraping_strategy=WebScrapingStrategy(),
        excluded_tags=["footer", "header", "style", "script"],
        css_selector=".tableList",
        wait_until="commit",
        exclude_external_links=True,
        cache_mode=1,
        prefetch=True,
    )

    yield  # The FastAPI server runs and handles traffic while frozen here

    # [SHUTDOWN]: Safely close browser processes when the container stops
    if "crawler" in state:
        await state["crawler"].__aexit__(None, None, None)


app = FastAPI(title="Modern Crawl4AI API", lifespan=lifespan)


@app.get("/healthz")
def health_check():
    """Lightweight endpoint for keep-alive pings"""
    return {"status": "healthy"}


@app.post("/crawlbook", dependencies=[Depends(validate_api_key)])
async def crawl_url(payload: CrawlRequest):
    try:
        crawler = state["crawler"]
        run_config = state["run_config"]
        result = await crawler.arun(url=payload.url, config=run_config)

        if not result.success:
            raise HTTPException(
                status_code=500, detail="Crawl operation timed out or failed"
            )

        return {"success": True, "html": result.html, "results": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
