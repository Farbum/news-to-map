"""
News Article Location Extractor using Gemini API
Extracts real-world locations from news articles via URL or direct text input.
"""

import os
from typing import Dict
import argparse
import sys
from google import genai

import requests_cache
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

from dotenv import load_dotenv
load_dotenv()  #load environment variables from .env file

from article_text_extractor import extract_article_text as ext_url_text
from nlp_loc_extractor import extract_locations_with_gemini as ext_locations
from geocode_loc_finder import geocode_nominatim as ext_coordinates
from map_viz import create_styled_map, save_open_map_in_browser

class NoLocationsFound(Exception):
    pass
class NoArticleExtracted(Exception):
    pass


class ArticleLocationExtractor:
    def __init__(self, api_key: str, model_name:str = "gemini-2.5-pro", user_agent = "art_loc_extr_finder"):
        """Initialize with Gemini API key."""
        if api_key is None:
            print(f"LLM API key not directly provided, fetching it from environment")
            self.api_key = os.environ.get("GEMINI_API_KEY")
        else:
            self.api_key = api_key
        if not self.api_key:
            raise ValueError("Gemini API key not provided or set in GEMINI_API_KEY environment variable.")
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name

        """Initialize geocode with caching"""
        requests_cache.install_cache("geocode_cache", expire_after=7*24*3600)
        geolocator = Nominatim(user_agent=user_agent, timeout=10)
        self.geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.0, swallow_exceptions=True)


    def url_text_extractor(self, url):
        return ext_url_text(url)
    
    def location_extractor(self, text):
        return ext_locations(text, self.client, self.model_name, test_mode = False)

    def coord_finder(self, locations):
        return ext_coordinates(locations, self.geocode, test_mode = False)

    def create_intmap(self, coord_df, open_in_browser: bool = True):
        """
        Build the folium map. If open_in_browser=True, save and open it.
        Always return the folium.Map object so Streamlit can render it.
        """
        fmap = create_styled_map(coord_df)
        if open_in_browser:
            save_open_map_in_browser(fmap)
        return fmap
    

    def process_article(self, input_text: str, is_url: bool = False, for_streamlit: bool = False) -> Dict:
        """Main processing function."""
        
        # Extract/load text
        if is_url:
            print(f"Fetching article from URL: {input_text}")
            article_text = self.url_text_extractor(input_text)
            if not article_text:
                raise NoArticleExtracted("Article URL could not be fetched")
        else:
            article_text = input_text

        if "403 Forbidden" in article_text and len(article_text) < 100:
            raise NoArticleExtracted("Could not fetch article: newspaper is likely blocking AI/bots agents")
        else:
            print("     -article extracted")
        
        # Extract locations
        print("Extracting locations using Gemini API...")
        locations = self.location_extractor(article_text)
        if locations == {}:
            raise NoLocationsFound("Article does not seem to reference any real-world geographic location")
        else:
            print("     -locations extracted")

        # Fetch coordinates
        print("Extracting coordinate")
        coords_df_out = self.coord_finder(locations)
        print("     -Coordinates extracted")

        # Create/Launch interactive map
        print("Launching interactive map")
        fmap = self.create_intmap(coords_df_out, open_in_browser=not for_streamlit)       
        print("     -Map launched")


        if for_streamlit:
            # Return everything the UI might want
            return {
                "map": fmap,
                "coords_df": coords_df_out,
                "locations": locations,
                "article_text": article_text,
            }

        return {}
    

def main():
    parser = argparse.ArgumentParser(description="Extract locations from news articles using Gemini API")
    parser.add_argument("--api-key", help="Gemini API key")
    parser.add_argument("--url", help="URL of news article to process")
    parser.add_argument("--text", help="Direct text input instead of URL")
    
    args = parser.parse_args()
    
    if not any([args.url, args.text]):
        print("Please provide either --url or --text")
        sys.exit(1)
    
    extractor = ArticleLocationExtractor(args.api_key)
    
    try:
        if args.url:
            extractor.process_article(args.url, is_url=True)
        else:
            extractor.process_article(args.text, is_url=False)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"An error occurred: {e}")



if __name__ == "__main__":
    main()


