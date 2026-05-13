import os
from fastapi import FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
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
        
        # Initialize a persistent Session to maintain automated state and cookies
        with requests.Session() as session:
            
            response = session.get(
                target_url, 
                impersonate="chrome", 
                allow_redirects=True, # Explicitly follow 301/302 redirect locations
                max_redirects=10,     # Stop infinite redirect loops gracefully
                timeout=20
            )
            response.raise_for_status()
            
            
            return {
                "success": True, 
                "target": target_url, 
                "final_url": response.url, # Returns the actual destination URL
                "html": response.text      # Captures destination source content
            }
        
    except Exception as e:
        return {"success": False, "error": f"Redirection capture failed: {str(e)}"}
