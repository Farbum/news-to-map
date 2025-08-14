import json
import os
import re
from typing import Dict
import time
from google import genai

from dotenv import load_dotenv
load_dotenv()  #load environment variables from .env file



def parse_fallback_response(text: str) -> Dict:
    """Fallback parser if JSON extraction fails."""
    locations = {
        "cities": [],
        "states_provinces": [],
        "countries": [],
        "landmarks": [],
        "regions": []
    }
    
    # Simple pattern matching as fallback
    lines = text.split('\n')
    current_category = None
    
    for line in lines:
        line = line.strip()
        if 'cities' in line.lower():
            current_category = 'cities'
        elif 'states' in line.lower() or 'provinces' in line.lower():
            current_category = 'states_provinces'
        elif 'countries' in line.lower():
            current_category = 'countries'
        elif 'landmarks' in line.lower():
            current_category = 'landmarks'
        elif 'regions' in line.lower():
            current_category = 'regions'
        elif current_category and line:
            # Extract location names from line
            items = re.findall(r'[A-Z][a-zA-Z\s]+', line)
            locations[current_category].extend(items)
    
    return locations
    
                
def extract_locations_with_gemini(text: str, client, model_name:str, test_mode = False) -> Dict:
    """Use Gemini API to extract locations from text."""
    if test_mode:
        print(f"\n{'#'*20}text input to gemini: {text}\n{'#'*20}")
    # Craft a detailed prompt for location extraction
    prompt = f"""
    Please analyze the following news article and extract ALL real-world locations mentioned, as well as a very concise summary of why this location is mentioned in the article.
    
    For each location found, categorize it as:
    - Cities
    - provinces/counties 
    - States
    - Countries
    - Landmarks
    - Summary of why location is mentioned
    
    Return the results in valid JSON format like this:
    {{
        "cities": ["City1", "City2"],
        "provinces_counties": ["Province1","Province2"],
        "states": ["State1","State2"],
        "countries": ["Country1", "Country2"],
        "landmarks": ["Landmark1","Landmark2"],
        "summary": ["Summary1","Summary2"]
    }}
    
    Only include actual geographical locations, not fictional places or organization names.
    Avoid duplicates and be comprehensive.

    Make sure that each json entry (cities, provinces_counties, etc.) is a list with the same number of items across categories. 
    i.e. if there are 3 cities, there should be 3 provinces_counties, 3 countries, 3 summaries etc. 
    If a category does not apply or is not found, use your knowledge to determine the most appropriate response, and return "None" if there is any doubt. 
    Make sure that the provided response makes sense, i.e. the city of San Jose should not be associated with the county of Alameda or San Mateo, but Santa Clara.
    
    Here are two examples with correct outputs:

    Example 1: article text:
    The Dixie Fire started on July 13, 2021 in Feather River Canyon southeast of Lassen Volcanic National Park. The fire entered 
    the southeast corner of the park near Juniper Lake on August 5, 2021 at which point Lassen Volcanic National Park entered into 
    unified command with USFS and CAL FIRE to implement a full suppression strategy.
    The Dixie Fire reached its final size of 73,240 acres within the park on September 30. On October 26, the Dixie Fire reached 100% 
    containment with a total size of 963,309 acres making it the largest single fire in California history.

    Example 1: valid Json response for the example 1 article text:
    {{
        "cities": ["None", "None", "None"],
        "provinces_counties": ["Lassen","Lassen","Lassen"],
        "states": ["California","California","California"],
        "countries": ["USA", "USA", "USA"],
        "landmarks": ["Feather River Canyon", "Lassen Volcanic National Park", "Juniper Lake"],
        "summary": ["Dixie Fire ignition point (July 13, 2021)", "Major impact area. Dixie Fire entered Aug 5 and burned 73,240 acres inside the park.", "Entry point where the fire crossed into the park"]
    }}

    Example 2: article text:
    The Eras Tour by the numbers:
    Swift performed 149 shows between March 2023 and December 2024. The tour traveled to 51 cities across 21 countries. A typical Eras show featured 44-46 songs and ran for 3 hours and 15 minutes.
    and ran for 3 hours and 15 minutes. Swift spent a total of roughly 25 hours performing her 10-minute version of "All Too Well." A total of 10,168,008 people purchased $2,077,618,725 in tickets — averaging about $204 per seat, Swift's company told the NYT.
    Eighteen opening acts warmed up the crowd for Swift, including Sabrina Carpenter, Paramore and Phoebe Bridgers. Fifteen special guests, mostly musicians, joined her onstage in occasional surprise appearances.
    Swift wore more than 60 outfits throughout the tour and more than 250 custom pairs of shoes by designer Christian Louboutin. Swift's biggest crowd (of both the tour and her entire career) was 96,000 people at the Melbourne Cricket Ground in Australia in February.
    In July 2023, Seattle fans danced so hard that they created the seismic equivalent of a 2.3 magnitude earthquake.

    Example 2: valid Json response for the example 2 article text:
    {{
        "cities": ["Melbourne", "Seattle"],
        "provinces_counties": ["None","King"],
        "states": ["Victoria","Washington"],
        "countries": ["Australia", "USA"],
        "landmarks": ["Melbourne Cricket Ground", "None"],
        "summary": ["Hosted Swift’s biggest crowd ever: 96,000 people (February).", "Fans’ dancing created a seismic event equivalent to magnitude 2.3 (July 2023)."]
    }}

    Example 3: article text:
    Scientists have long known that the brain’s visual system isn’t fully hardwired from the start — it becomes refined by what babies see — but the authors of a new study still weren’t prepared for the degree of rewiring they observed when they took a first-ever look at the process in mice as it happened in real-time.
    As the researchers tracked hundreds of “spine” structures housing individual network connections, or “synapses,” on the dendrite branches of neurons in the visual cortex over 10 days, they saw that only 40 percent of the ones that started the process survived. Refining binocular vision (integrating input from both eyes) required numerous additions and removals of spines along the dendrites to establish an eventual set of connections.
    Former graduate student Katya Tsimring led the study, published this month in Nature Communications, which the team says is the first in which scientists tracked the same connections all the way through the “critical period,” when binocular vision becomes refined.
    “What Katya was able to do is to image the same dendrites on the same neurons repeatedly over 10 days in the same live mouse through a critical period of development, to ask, what happens to the synapses or spines on them?,” says senior author Mriganka Sur. “We were surprised by how much change there is.”

    Example 3: valid Json response for the example 3 article text:
    {{}}

    Article text:
    {text[:10000]}  # Limit text length for API limits
    """
    
    for attempt in range(1, 4):  # retry up to 3 times
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            gen_result = response.text
            if not gen_result or str(gen_result).strip().lower() == "none":  # ADDED: treat empty/None as failure
                raise ValueError("Gemini returned empty response.text")
            if test_mode:
                print(f"\n{'#'*20}\nresults from gemini:\n{gen_result}\n{'#'*20}")
            
            # Try to extract JSON from the response
            try:
                # Look for JSON in the response
                json_match = re.search(r'\{.*\}', gen_result, re.DOTALL)
                if json_match:
                    locations_data = json.loads(json_match.group())
                    return locations_data
                else:
                    # Fallback: parse the response manually
                    return parse_fallback_response(gen_result)
                    
            except json.JSONDecodeError:
                return parse_fallback_response(gen_result)
                
        except Exception as e:
            print(f"Attempt {attempt}/3 failed: {e}")  # log attempt
            if attempt < 3:                             # wait then retry
                time.sleep(3)
                continue
            else:
                return {}     
        
    
def parse_fallback_response(text: str) -> Dict:
    """Fallback parser if JSON extraction fails."""
    locations = {
        "cities": [],
        "states_provinces": [],
        "countries": [],
        "landmarks": [],
        "regions": []
    }
    
    # Simple pattern matching as fallback
    lines = text.split('\n')
    current_category = None
    
    for line in lines:
        line = line.strip()
        if 'cities' in line.lower():
            current_category = 'cities'
        elif 'states' in line.lower() or 'provinces' in line.lower():
            current_category = 'states_provinces'
        elif 'countries' in line.lower():
            current_category = 'countries'
        elif 'landmarks' in line.lower():
            current_category = 'landmarks'
        elif 'regions' in line.lower():
            current_category = 'regions'
        elif current_category and line:
            # Extract location names from line
            items = re.findall(r'[A-Z][a-zA-Z\s]+', line)
            locations[current_category].extend(items)
    
    return locations
    

if __name__ == "__main__":
    text = input("Enter text to analyze: ").strip()
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    locations = extract_locations_with_gemini( text, client,  model_name = "gemini-2.5-pro")
    print("\nExtracted locations:\n")
    for loct, loc in locations.items():
        print(f"{loct}: {loc}\n")
