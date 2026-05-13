import os
from fastapi import FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
# Import the browser-impersonating requests engine
from curl_cffi import requests

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
def scrape_data(request: ScrapeRequest, api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    
    try:
        target_url = str(request.url)
        
        # 'impersonate="chrome"' fakes the TLS JA3/JA4 fingerprint at the network layer
        response = requests.get(
            target_url, 
            impersonate="chrome", 
            timeout=15
        )
        response.raise_for_status()
        
        # Cleanly captures raw source HTML bypassing the 202 blocker page
        raw_html = response.text
        
        return {"success": True, "target": target_url, "html": raw_html}
        
    except Exception as e:
        return {"success": False, "error": f"Scrape execution failed: {str(e)}"}
