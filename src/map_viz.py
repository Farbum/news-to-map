import folium
import pandas as pd
import os
import webbrowser

# Alternative: Create map with different marker styles
def create_styled_map(locations_data,map_center=None, zoom_start=10):
    """
    Create an interactive map with location points and hover text.
    
    Parameters:
    locations_data: list of dictionaries with keys 'lat', 'lon', 'map_name', 'summary'
    map_center: tuple (lat, lon) for map center, if None will calculate from data
    zoom_start: initial zoom level
    
    Returns:
    folium.Map object
    """
    

    locations_data = locations_data.loc[locations_data.lat.notnull() & locations_data.lon.notnull()]

    # Calculate map center if not provided
    if map_center is None:
        avg_lat = locations_data.lat.mean(skipna=True)
        avg_lon = locations_data.lon.mean(skipna=True)
        map_center = (avg_lat, avg_lon)
    
    # Create base map
    m = folium.Map(location=map_center, zoom_start=zoom_start)

    # ensure all points are visible on first load ---
    if not locations_data.empty:
        min_lat, max_lat = locations_data.lat.min(), locations_data.lat.max()
        min_lon, max_lon = locations_data.lon.min(), locations_data.lon.max()
        m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])  # adjusts center & zoom
 
    
    # Different colors for variety
    colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 
              'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']
    
    # Add markers for each location
    for i, (_, r) in enumerate(locations_data.iterrows()):
    #for i, location in enumerate(locations_data):
        color = colors[i % len(colors)]
        
        folium.Marker(
            location=[r['lat'], r['lon']],
            popup=folium.Popup(
                html=f"""
                <div style="width: 200px;">
                    <h4>{r['map_name']}</h4>
                    <p>{r['summary']}</p>
                </div>
                """,
                max_width=250
            ),
            tooltip=f"{r['map_name']} - Click for details",
            icon=folium.Icon(color=color, icon='info-sign')
        ).add_to(m)
    
    return m

def save_open_map_in_browser(map, file_path = './interactive_map.html'):
    """Save and Open the map HTML file in the default browser."""
    abs_path = os.path.abspath(file_path)
    map.save(os.path.abspath(abs_path))
    file_url = f"file://{abs_path}"
    webbrowser.open(file_url)


# Example usage with sample data
if __name__ == "__main__":
    # Sample data - replace this with your actual data
    sample_locations = [
        {
            'lat': 40.7589, 
            'lon': -73.9851, 
            'map_name': 'Times Square',
            'summary': 'Famous commercial intersection and tourist destination in NYC'
        },
        {
            'lat': 40.7505, 
            'lon': -73.9934, 
            'map_name': 'Empire State Building',
            'summary': 'Iconic Art Deco skyscraper completed in 1931'
        },
        {
            'lat': 40.7614, 
            'lon': -73.9776, 
            'map_name': 'Central Park',
            'summary': 'Large public park in Manhattan, great for walking and recreation'
        },
        {
            'lat': 40.7580, 
            'lon': -73.9855, 
            'map_name': 'Broadway Theater District',
            'summary': 'Heart of American commercial theater with numerous venues'
        }
    ]
    sample_locations_df = pd.DataFrame.from_dict(sample_locations)
    print(sample_locations_df.to_markdown())
    
    # Create the map
    interactive_map = create_styled_map(sample_locations_df, zoom_start=12)
    
    # Save the map as HTML file and open
    save_open_map_in_browser(interactive_map)
    


