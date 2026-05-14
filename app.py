import os
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
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
    url: str


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

browser_config = BrowserConfig(
    headless=True,
    light_mode=True,
    extra_args=[
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--blink-settings=imagesEnabled=false",
    ],
    avoid_ads=True,
    avoid_css=True,
)

run_config = CrawlerRunConfig(
    # scraping_strategy=WebScrapingStrategy(),
    excluded_tags=["footer", "header", "style", "script"],
    # css_selector=".tableList",
    remove_forms=True,
    # wait_until="domcontentloaded",
    exclude_external_links=True,
    cache_mode=1,
    prefetch=True,
)


@app.get("/healthz")
def health_check():
    """Lightweight endpoint for keep-alive pings"""
    return {"status": "healthy"}


@app.post("/crawl", dependencies=[Depends(validate_api_key)])
async def crawl_url(payload: CrawlRequest):
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=payload.url, config=run_config)

            if not result.success:
                raise HTTPException(status_code=500, detail="Crawl failure")

            return {
                "success": True,
                "html": result.html,
                "cleaned": result.cleaned_html
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
