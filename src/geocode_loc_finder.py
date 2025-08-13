from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import requests_cache, pandas as pd
from tqdm import tqdm


def geocode_nominatim(inp_dict, geocode, lang="en", test_mode = False):
    print(f"\n{'#'*20}\dict input to geocode: {inp_dict}\n{'#'*20}")
    assert sorted(list(inp_dict.keys())) == ['cities', 'countries','landmarks', 'provinces_counties', 'states','summary'], "Received wrong location dictionary, keys are not matching"

    #Format the input location types to Nominatim built-in types
    type_mapping = {'cities':'city', 'countries':'country','landmarks':'q', 'provinces_counties':'county', 'states':'state', 'summary':'summary'}
    f_inp_dict = {type_mapping[k]:v for k,v in inp_dict.items()}

    # heuristic to detect natural landmarks from the landmark string
    def _is_natural_landmark(name: str) -> bool:
        tokens = ("lake","river","canyon","mount","mt ","peak","forest","park","bay","sea","ocean",
                  "island","valley","falls","glacier","spring","springs","desert","dune","beach",
                  "cave","volcano","reef","gorge")
        n = (name or "").lower()
        return any(t in n for t in tokens)

    # choose best candidate by OSM class depending on natural vs man-made
    def _choose_landmark_candidate(cands, is_natural: bool):
        pref_natural = {"natural","waterway","landuse","geological","leisure","boundary","place"}
        pref_manmade = {"amenity","tourism","historic","man_made","building","railway","aeroway",
                        "highway","shop","bridge"}
        prefs = pref_natural if is_natural else pref_manmade
        for c in cands:
            if c.raw.get("class") in prefs:
                return c
        return cands[0]  # fallback to first

    out = []
    for qix in tqdm(range(len(inp_dict['cities']))):

        q = {
            # Structured query greatly improves accuracy
            place_type:place[qix] for place_type,place in f_inp_dict.items() if place[qix]!= "None"
        }

        # Handle San Francisco-like cases where city == county in non-landmark queries
        if ('city' in q and 'county' in q and 
            q['city'].lower() == q['county'].lower()):
            # Remove county from query to avoid confusion
            del q['county']
            if test_mode:
                print(f"Removed duplicate county for city: {q['city']}")

        # detect if we have a landmark this row and classify it
        lm = f_inp_dict.get("q", [None])[qix]
        has_landmark = (lm is not None and lm != "None")
        is_natural = _is_natural_landmark(lm) if has_landmark else False

    
        # --------------------------------------------------------------------------------------------
        # LANDMARK SPECIAL TREATMENT 
        # --------------------------------------------------------------------------------------------

        if has_landmark:
            # FIXED: Use free-form text queries for landmarks instead of structured queries
            loc = None
            
            # Get context for building free-form query
            city = inp_dict["cities"][qix] if inp_dict["cities"][qix] != "None" else None
            state = inp_dict["states"][qix] if inp_dict["states"][qix] != "None" else None
            country = inp_dict["countries"][qix] if inp_dict["countries"][qix] != "None" else None
            
            # Strategy 1: Free-form landmark + city, state (most specific)
            if city and state:
                freeform_query = f"{lm}, {city}, {state}"
                try:
                    cands = geocode(freeform_query, language=lang, addressdetails=True,
                                             extratags=True, exactly_one=False, limit=5, timeout=10)
                    if cands:
                        # Filter out results that are just cities/states/countries
                        filtered_cands = [c for c in cands if c.raw.get("class") not in ["place"] or 
                                        c.raw.get("type") not in ["city", "state", "country"]]
                        if filtered_cands:
                            if test_mode:
                                print(f"Strategy 1 - Found {len(filtered_cands)} landmark candidates for '{lm}'")
                            loc = _choose_landmark_candidate(filtered_cands, is_natural)
                except Exception as e:
                    if test_mode:
                        print(f"Strategy 1 failed for '{lm}': {e}")
            
            # Strategy 2: Free-form landmark + state only
            if not loc and state:
                freeform_query = f"{lm}, {state}"
                try:
                    cands = geocode(freeform_query, language=lang, addressdetails=True,
                                             extratags=True, exactly_one=False, limit=5, timeout=10)
                    if cands:
                        # Filter out state/country results
                        filtered_cands = [c for c in cands if c.raw.get("class") not in ["place"] or 
                                        c.raw.get("type") not in ["state", "country"]]
                        if filtered_cands:
                            if test_mode:
                                print(f"Strategy 2 - Found {len(filtered_cands)} landmark candidates for '{lm}'")
                            loc = _choose_landmark_candidate(filtered_cands, is_natural)
                except Exception as e:
                    if test_mode:
                        print(f"Strategy 2 failed for '{lm}': {e}")
            
            # Strategy 3: Free-form landmark + country
            if not loc and country:
                freeform_query = f"{lm}, {country}"
                try:
                    cands = geocode(freeform_query, language=lang, addressdetails=True,
                                             extratags=True, exactly_one=False, limit=5, timeout=10)
                    if cands:
                        # Filter out country results
                        filtered_cands = [c for c in cands if c.raw.get("type") != "country"]
                        if filtered_cands:
                            if test_mode:
                                print(f"Strategy 3 - Found {len(filtered_cands)} landmark candidates for '{lm}'")
                            loc = _choose_landmark_candidate(filtered_cands, is_natural)
                except Exception as e:
                    if test_mode:
                        print(f"Strategy 3 failed for '{lm}': {e}")
                    
            if not loc:
                if test_mode:
                    print(f"All strategies failed for landmark: {lm}")
                
        # --------------------------------------------------------------------------------------------
        # LANDMARK TREATMENT END 
        # --------------------------------------------------------------------------------------------
        
        else:
            loc = geocode(q, language=lang, addressdetails=False)  # simple, single best

        if loc:
            out.append({
                **{place_type:place[qix] for place_type,place in inp_dict.items()},
                "source": "nominatim",
                "display_name": loc.address,
                "lat": float(loc.latitude),
                "lon": float(loc.longitude),
                "osm_id": loc.raw.get("osm_id"),
                "class": loc.raw.get("class"),         # e.g., "place"
                "type": loc.raw.get("type"),           # e.g., "village"
                "importance": loc.raw.get("importance"),
            })
        else:
            out.append({**{place_type:place[qix] for place_type,place in inp_dict.items()}, "source": "nominatim", "display_name": None, "lat": None, "lon": None, "osm_id": None, "class": None, "type": None, "importance": None})
    df_out = pd.DataFrame(out)

    # Building map name display from available info
    df_out['dis_name_temp'] = [x.split(',')[0] if x is not None else None for x in df_out['display_name'] ]
    order = ["dis_name_temp", "landmarks", "cities", "provinces_counties", "states", "countries"]
    df_out["map_name"] = (
        df_out[order]
        .replace("None", pd.NA)   # treat "None" as missing
        .bfill(axis=1)            # take first non-missing from left to right
        .iloc[:, 0]               # that first value
        .fillna("None")           # (optional) keep "None" if all are missing
    )
    df_out.drop(columns=['source', 'dis_name_temp'], inplace=True)
    print(f"\n{'#'*20}\noutput from geocode: {pd.DataFrame(out).to_markdown()}\n{'#'*20}")
    return df_out



if __name__ == "__main__":
    # ---- Example usage ----
    data = {
    "cities": ["Coustouge","Saint-Laurent-de-la-Cabrerisse","Jonquières","Port-la-Nouvelle","Paris",
                "None","None"]+ ["San Francisco", "None", "None"] + ["San Francisco"]*11 +["Paris"]
    ,
    "provinces_counties": ["Aude"]*4 + ["Paris", "Lassen","Lassen"] + ["San Francisco", "None", "None"] +
                            ["San Francisco"]*11 + ['Paris'],
    "states":  ["None"]*5 + ["California"]*16 + ["Île-de-France"],

    "countries": ["France"]*5 + ["USA"]*16 + ["France"],
    "landmarks": ["None"]*5  + ["Feather River Canyon", "Juniper Lake"] + 
                ["None", "Lake Tahoe", "Sequoia national park", "Golden Gate Bridge",
                "Ferry Building",
                "Bay Bridge",
                "Grace Cathedral",
                "Presidio",
                "Golden Gate Park",
                "Haight-Ashbury",
                "Chinatown",
                "North Beach",
                "Fisherman’s Wharf",
                "Alcatraz",
                "Notre Dame"],
    "summary": ["Something here"]*22
}
    # Cache responses to be kind to the service and for speed
    requests_cache.install_cache("geocode_cache", expire_after=7*24*3600)
    geolocator = Nominatim(user_agent='test', timeout=10)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.0, max_retries=2, error_wait_seconds=2.0, swallow_exceptions=True)

    df_out = geocode_nominatim(data, geocode, test_mode = True)
    print(df_out[['cities','provinces_counties','states', 'countries','landmarks','display_name', 'map_name', 'lat','lon']])
