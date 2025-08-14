import streamlit as st
from streamlit_folium import st_folium

from main_pipeline import ArticleLocationExtractor 

st.set_page_config(page_title="News → Map", page_icon="🗺️", layout="wide")
st.title("News → Map")
st.caption("Paste a news URL or text. I’ll extract locations and plot them with relevant info on an interactive map")

# Get API key from Streamlit secrets
api_key = st.secrets.get("GEMINI_API_KEY", None)

# Instantiate orchestrator
extractor = ArticleLocationExtractor(api_key=api_key)

# INIT session state
if "result" not in st.session_state:
    st.session_state["result"] = None

# --- UI ---
mode = st.radio("Input type", ["URL", "Paste text"], horizontal=True)
url = st.text_input("Article URL") if mode == "URL" else ""
text = st.text_area("Article text", height=220) if mode == "Paste text" else ""

run = st.button("Extract & Map", type="primary", use_container_width=True)

if run:
    if mode == "URL" and not url:
        st.warning("Please enter a URL.")
        st.stop()
    if mode == "Paste text" and not text.strip():
        st.warning("Please paste some text.")
        st.stop()

    try:
        with st.spinner("Processing…"):
            result = extractor.process_article(
                url if mode == "URL" else text,
                is_url=(mode == "URL"),
                for_streamlit=True
            )
        # store only the data needed to rebuild map; not the Folium map object
        st.session_state["result"] = {
            "coords_df": result["coords_df"],
            "locations": result["locations"],
            "article_text": result["article_text"],
        }
    except Exception as e:
        st.session_state["result"] = None
        st.error(f"{type(e).__name__}: {e}")

# RENDER
res = st.session_state["result"]
if res:
    # rebuild the map every render; stable key avoids remount jitter
    fmap = extractor.create_intmap(res["coords_df"], open_in_browser=False)

    st.subheader("Interactive map")
    st_folium(fmap, width=1100, height=600, key="map")

    with st.expander("Article text"):
        st.write(res["article_text"])

    # FOR DEBUGGING - UNDERLYING DATA
    # with st.expander("Resolved locations & coordinates", expanded=False):
    #     st.dataframe(res["coords_df"], use_container_width=True)

    # with st.expander("LLM-extracted raw locations (debug)"):
    #     st.write(res["locations"])


