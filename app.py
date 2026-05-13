import os
import requests
from selectolax.parser import HTMLParser
from fastapi import FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

app = FastAPI()

API_KEY = os.environ.get("SCRAPER_SECRET_KEY", "my_fallback_secret_key")
api_key_header = APIKeyHeader(name="X-Scraper-Key", auto_error=True)

origins = [
    "http://localhost:5173",     
    "vocabs1.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "X-Scraper-Key"],
)

class ScrapeRequest(BaseModel):
    url: HttpUrl

@app.post("/api/scrape")
def scrape_data(request: ScrapeRequest, api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        target_url = str(request.url)
        response = requests.get(target_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        tree = HTMLParser(response.text)
        # data = []
        
        # for node in tree.css('tr[itemtype="http://schema.org/Book"]')[:15]:
        #     href = node.attributes.get("href", "")
        #     text = node.text(strip=True)
        #     if href and text:
        #         data.append({
        #             "title": text,
        #             "url": href
        #         })
            
        return {"success": True, "target": target_url, "data": tree}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
