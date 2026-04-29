import streamlit as st
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (useful for local testing, Streamlit Cloud uses Secrets)
load_dotenv()

from backend.config import CATALOG_PATH, DEFAULT_MODEL
from phase3.retrieval import load_restaurant_catalog
from backend.services.pipeline import run_pipeline
from phase2.normalize_validate import ValidationError

# Set up page config
st.set_page_config(
    page_title="Zomato AI Recommendations", 
    page_icon="🍔", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better aesthetics
st.markdown("""
<style>
    .restaurant-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #334155;
    }
    .restaurant-title {
        color: #f59e0b;
        margin-top: 0 !important;
    }
    .metric-label {
        font-weight: bold;
        color: #94a3b8;
    }
    .reason-box {
        background-color: #0f172a;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #10b981;
        margin-top: 15px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def get_catalog():
    """Load the dataset and cache it in memory."""
    try:
        return load_restaurant_catalog(str(CATALOG_PATH))
    except Exception as e:
        st.error(f"Failed to load catalog from {CATALOG_PATH}. Please ensure the data foundation (Phase 1) is complete.")
        st.stop()

df = get_catalog()

# --- Header ---
st.title("🍔 Zomato AI Recommender")
st.markdown("Find the perfect place to eat based on your specific cravings, powered by AI.")

# --- Form Inputs ---
locations = sorted(df["location_norm"].dropna().unique().tolist())
cuisines_raw = df["cuisine_norm"].dropna().str.split(",").explode().str.strip()
cuisines_list = sorted(set(c for c in cuisines_raw if c))

with st.form("preference_form"):
    st.subheader("What are you looking for?")
    
    col1, col2 = st.columns(2)
    with col1:
        location = st.selectbox("📍 Location", [""] + locations, index=0)
        budget = st.selectbox("💰 Budget", ["low", "medium", "high"], index=1)
    
    with col2:
        cuisines = st.multiselect("🍲 Cuisines", cuisines_list)
        min_rating = st.slider("⭐ Minimum Rating", 0.0, 5.0, 3.5, 0.1)
    
    optional = st.text_input("✨ Optional Preferences", placeholder="e.g., romantic, family-friendly, rooftop")
    
    submit = st.form_submit_button("Find Restaurants", use_container_width=True)

# --- Process Results ---
if submit:
    if not location:
        st.warning("Please select a location to continue.")
    elif not cuisines:
        st.warning("Please select at least one cuisine.")
    else:
        payload = {
            "location": location,
            "budget": budget,
            "cuisine": ", ".join(cuisines),
            "minimum_rating": min_rating,
            "optional_preferences": optional
        }
        
        with st.spinner("Analyzing catalog and ranking with AI..."):
            try:
                # Direct backend pipeline call (no Flask API needed)
                result = run_pipeline(
                    raw_preferences=payload,
                    catalog_df=df,
                    top_k=5,
                    model=DEFAULT_MODEL
                )
                
                res_data = result.payload
                
                if res_data.get("status") == "success":
                    st.success("Recommendations ready!")
                    
                    if "comparison_summary" in res_data and res_data["comparison_summary"]:
                        st.info(res_data["comparison_summary"])
                        
                    st.markdown("### Top Picks For You")
                    
                    for rec in res_data.get("recommendations", []):
                        st.markdown(f"""
                        <div class="restaurant-card">
                            <h3 class="restaurant-title">#{rec['rank']} {rec['restaurant_name']}</h3>
                            <p><span class="metric-label">📍 Location:</span> {rec['location']}</p>
                            <p><span class="metric-label">🍲 Cuisine:</span> {rec['cuisine']}</p>
                            <p><span class="metric-label">💰 Cost for two:</span> ₹{rec.get('cost_for_two', 'N/A')}</p>
                            <p><span class="metric-label">⭐ Rating:</span> {rec['rating']} / 5.0</p>
                            <div class="reason-box">
                                <strong>🤖 Why we chose this:</strong><br/>
                                {rec.get('reason', 'Great match for your preferences.')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    # Dev/Debug metrics
                    with st.expander("Show Processing Metrics"):
                        st.json(result.timings)
                        st.json(res_data.get("applied_filters", {}))
                
                else:
                    st.error("Could not find suitable recommendations.")
                    
            except ValidationError as e:
                st.error(f"Validation Error: {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
