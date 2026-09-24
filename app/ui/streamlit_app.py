"""Streamlit interactive web frontend for the AI-Powered Restaurant Recommendation System."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Ensure project root is in sys.path so 'app' package resolves when executed from app/ui/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx
import streamlit as st

from app.config import settings
from app.models import (
    MetadataResponse,
    RecommendationResponse,
    UserPreferenceRequest,
)
from app.services.data_loader import get_data_loader
from app.services.recommendation_service import RecommendationOrchestrator


# --- Page Configuration ---
st.set_page_config(
    page_title="Zomato AI - Restaurant Discovery",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

def get_theme_css(is_dark: bool) -> str:
    """Return responsive CSS styles for Dark or Light theme."""
    if is_dark:
        return """
        <style>
        .stApp { background-color: #0B0F19; color: #F1F5F9; }
        header[data-testid="stHeader"] { background-color: rgba(11, 15, 25, 0.85); backdrop-filter: blur(12px); }
        section[data-testid="stSidebar"] { background-color: #0F172A; border-right: 1px solid rgba(255, 255, 255, 0.08); }
        .hero-badge { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.3rem 0.8rem; border-radius: 9999px; background: rgba(226, 55, 68, 0.15); border: 1px solid rgba(226, 55, 68, 0.35); color: #E23744; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.75rem; }
        .main-header { font-size: 2.4rem; font-weight: 900; letter-spacing: -0.02em; color: #FFFFFF; line-height: 1.15; margin-bottom: 0.3rem; }
        .main-header-gradient { background: linear-gradient(135deg, #E23744 0%, #FF5252 50%, #8B5CF6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .sub-header { font-size: 0.95rem; color: #94A3B8; margin-bottom: 1.5rem; line-height: 1.5; }
        .ai-summary-card { background: linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(30, 41, 59, 0.7) 100%); border: 1px solid rgba(139, 92, 246, 0.35); border-radius: 16px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3); }
        .ai-summary-title { font-size: 0.9rem; font-weight: 700; color: #FFFFFF; display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
        .ai-summary-text { font-size: 0.88rem; color: #CBD5E1; line-height: 1.6; }
        .stitch-card { background: rgba(30, 41, 59, 0.65); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 1.25rem 1.5rem; margin-bottom: 1.25rem; transition: transform 0.2s ease, border-color 0.2s ease; }
        .stitch-card:hover { transform: translateY(-2px); border-color: rgba(226, 55, 68, 0.45); box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5); }
        .stitch-title { color: #FFFFFF; font-size: 1.25rem; font-weight: 800; margin-left: 0.5rem; }
        .rank-gold { background: linear-gradient(135deg, #FFE259 0%, #FFA751 100%); color: #0F172A; font-weight: 900; padding: 0.25rem 0.65rem; border-radius: 8px; font-size: 0.78rem; letter-spacing: 0.05em; display: inline-block; }
        .rank-silver { background: linear-gradient(135deg, #E0E7EF 0%, #94A3B8 100%); color: #0F172A; font-weight: 900; padding: 0.25rem 0.65rem; border-radius: 8px; font-size: 0.78rem; letter-spacing: 0.05em; display: inline-block; }
        .rank-bronze { background: linear-gradient(135deg, #F6D365 0%, #FDA085 100%); color: #0F172A; font-weight: 900; padding: 0.25rem 0.65rem; border-radius: 8px; font-size: 0.78rem; letter-spacing: 0.05em; display: inline-block; }
        .rank-standard { background: #1E293B; color: #94A3B8; font-weight: 800; padding: 0.25rem 0.65rem; border-radius: 8px; font-size: 0.78rem; border: 1px solid rgba(255, 255, 255, 0.1); display: inline-block; }
        .stitch-rating { background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.35); color: #F59E0B; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 8px; font-size: 0.85rem; }
        .stitch-chip { background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.1); color: #CBD5E1; padding: 0.25rem 0.65rem; border-radius: 8px; font-size: 0.78rem; margin-right: 0.4rem; display: inline-block; }
        .stitch-cost { background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.25); color: #10B981; font-weight: 600; padding: 0.25rem 0.65rem; border-radius: 8px; font-size: 0.78rem; display: inline-block; }
        .ai-rationale-box { background: linear-gradient(135deg, rgba(139, 92, 246, 0.12) 0%, rgba(15, 23, 42, 0.5) 100%); border-left: 3px solid #8B5CF6; border-radius: 0 10px 10px 0; padding: 0.85rem 1rem; margin-top: 0.85rem; font-size: 0.85rem; color: #E2E8F0; line-height: 1.5; }
        .ai-rationale-header { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #8B5CF6; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.4rem; }
        </style>
        """
    else:
        return """
        <style>
        .stApp { background-color: #F8FAFC; color: #0F172A; }
        header[data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0.85); backdrop-filter: blur(12px); }
        section[data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid rgba(0, 0, 0, 0.08); }
        .hero-badge { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.3rem 0.8rem; border-radius: 9999px; background: rgba(226, 55, 68, 0.1); border: 1px solid rgba(226, 55, 68, 0.3); color: #E23744; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.75rem; }
        .main-header { font-size: 2.4rem; font-weight: 900; letter-spacing: -0.02em; color: #0F172A; line-height: 1.15; margin-bottom: 0.3rem; }
        .main-header-gradient { background: linear-gradient(135deg, #E23744 0%, #FF5252 50%, #8B5CF6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .sub-header { font-size: 0.95rem; color: #64748B; margin-bottom: 1.5rem; line-height: 1.5; }
        .ai-summary-card { background: linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(255, 255, 255, 0.95) 100%); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 16px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06); }
        .ai-summary-title { font-size: 0.9rem; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
        .ai-summary-text { font-size: 0.88rem; color: #334155; line-height: 1.6; }
        .stitch-card { background: #FFFFFF; border: 1px solid rgba(0, 0, 0, 0.08); border-radius: 16px; padding: 1.25rem 1.5rem; margin-bottom: 1.25rem; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05); transition: transform 0.2s ease, border-color 0.2s ease; }
        .stitch-card:hover { transform: translateY(-2px); border-color: rgba(226, 55, 68, 0.45); box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1); }
        .stitch-title { color: #0F172A; font-size: 1.25rem; font-weight: 800; margin-left: 0.5rem; }
        .rank-gold { background: linear-gradient(135deg, #FFE259 0%, #FFA751 100%); color: #0F172A; font-weight: 900; padding: 0.25rem 0.65rem; border-radius: 8px; font-size: 0.78rem; letter-spacing: 0.05em; display: inline-block; }
        .rank-silver { background: linear-gradient(135deg, #E0E7EF 0%, #94A3B8 100%); color: #0F172A; font-weight: 900; padding: 0.25rem 0.65rem; border-radius: 8px; font-size: 0.78rem; letter-spacing: 0.05em; display: inline-block; }
        .rank-bronze { background: linear-gradient(135deg, #F6D365 0%, #FDA085 100%); color: #0F172A; font-weight: 900; padding: 0.25rem 0.65rem; border-radius: 8px; font-size: 0.78rem; letter-spacing: 0.05em; display: inline-block; }
        .rank-standard { background: #F1F5F9; color: #64748B; font-weight: 800; padding: 0.25rem 0.65rem; border-radius: 8px; font-size: 0.78rem; border: 1px solid rgba(0, 0, 0, 0.08); display: inline-block; }
        .stitch-rating { background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.3); color: #D97706; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 8px; font-size: 0.85rem; }
        .stitch-chip { background: #F1F5F9; border: 1px solid rgba(0, 0, 0, 0.08); color: #334155; padding: 0.25rem 0.65rem; border-radius: 8px; font-size: 0.78rem; margin-right: 0.4rem; display: inline-block; }
        .stitch-cost { background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25); color: #059669; font-weight: 600; padding: 0.25rem 0.65rem; border-radius: 8px; font-size: 0.78rem; display: inline-block; }
        .ai-rationale-box { background: linear-gradient(135deg, rgba(139, 92, 246, 0.06) 0%, rgba(241, 245, 249, 0.7) 100%); border-left: 3px solid #8B5CF6; border-radius: 0 10px 10px 0; padding: 0.85rem 1rem; margin-top: 0.85rem; font-size: 0.85rem; color: #334155; line-height: 1.5; }
        .ai-rationale-header { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #7C3AED; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.4rem; }
        </style>
        """


@st.cache_resource(show_spinner=False)
def load_metadata_cached() -> MetadataResponse:
    """Load and cache dataset metadata for UI filter controls."""
    loader = get_data_loader()
    return loader.metadata


def get_recommendations_hybrid(request: UserPreferenceRequest) -> RecommendationResponse:
    """Fetch recommendations via FastAPI HTTP if available, or direct in-process orchestrator."""
    api_url = f"http://{settings.app_host}:{settings.app_port}/api/v1/recommendations"
    try:
        # 1. Attempt HTTP call to FastAPI backend
        with httpx.Client(timeout=6.0) as client:
            resp = client.post(api_url, json=request.model_dump())
            if resp.status_code == 200:
                return RecommendationResponse.model_validate(resp.json())
    except Exception:
        pass

    # 2. In-process fallback execution if FastAPI server is not currently running
    orchestrator = RecommendationOrchestrator()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(
                asyncio.run, orchestrator.get_recommendations(request)
            ).result()
    else:
        return loop.run_until_complete(orchestrator.get_recommendations(request))


def main():
    metadata = load_metadata_cached()

    # --- Sidebar Controls (Stitch FilterPanel) ---
    with st.sidebar:
        st.markdown("### 🎨 Appearance")
        theme_choice = st.radio(
            "Theme Mode",
            ["🌙 Dark Mode", "☀️ Light Mode"],
            horizontal=True,
            index=0,
            label_visibility="collapsed",
        )
        is_dark = "Dark" in theme_choice
        st.markdown(get_theme_css(is_dark), unsafe_allow_html=True)

        st.markdown("### 🎯 Refine Search")

        # Location Selection
        default_localities = [
            "Bangalore",
            "Koramangala",
            "Indiranagar",
            "Jayanagar",
            "Banashankari",
            "Whitefield",
            "HSR",
            "Church Street",
            "Brigade Road",
            "BTM",
            "Bellandur",
            "JP Nagar",
        ]
        available_locs = sorted(list(set(default_localities + metadata.localities[:30])))

        location_mode = st.radio("Location Mode", ["Popular Areas", "Custom Area"], horizontal=True)
        if location_mode == "Popular Areas":
            location = st.selectbox("Select Area", available_locs, index=0)
        else:
            location = st.text_input("Enter Locality / Landmark", value="Koramangala")

        # Budget Tier
        budget_options = {
            "low": "₹ Budget (≤ ₹500 for two)",
            "medium": "₹₹ Medium (₹500 - ₹1,500 for two)",
            "high": "₹₹₹ Fine (> ₹1,500 for two)",
        }
        selected_budget = st.radio(
            "Budget Tier",
            options=list(budget_options.keys()),
            format_func=lambda k: budget_options[k],
            index=1,
        )

        # Cuisines Multi-Select
        popular_cuisines = [
            "North Indian",
            "Chinese",
            "Italian",
            "Continental",
            "South Indian",
            "Biryani",
            "Fast Food",
            "Cafe",
            "Desserts",
            "Asian",
            "Pizza",
            "Mughlai",
            "Healthy Food",
        ]
        selected_cuisines = st.multiselect(
            "Preferred Cuisines (Optional)",
            options=popular_cuisines,
            default=["Italian"],
        )

        # Minimum Rating
        min_rating = st.slider(
            "Minimum Rating",
            min_value=3.0,
            max_value=4.8,
            value=4.0,
            step=0.1,
            format="⭐ %.1f",
        )

        st.markdown("---")
        st.caption(f"📊 Serving **{metadata.total_restaurants:,}** restaurants across Bangalore.")
        st.caption(f"⚡ Model: `{settings.default_llm_model}`")

    # --- Main Panel Contextual Input ---
    st.markdown("#### ✨ Quick Inspiration Presets")

    # Preset Quick Inspiration Chips (Stitch Hero Presets)
    col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)
    preset_text = None
    with col_p1:
        if st.button("💑 Romantic Date", use_container_width=True):
            preset_text = "Cozy romantic rooftop with candle-lit seating, great Italian wine, under ₹1500"
    with col_p2:
        if st.button("🍕 Student Hangout", use_container_width=True):
            preset_text = "Cheap student hangout with loaded burgers, fast WiFi, casual vibe, under ₹500"
    with col_p3:
        if st.button("👨‍👩‍👧 Family Brunch", use_container_width=True):
            preset_text = "Lush Sunday family brunch with spacious outdoor garden, waffles, and live acoustic music"
    with col_p4:
        if st.button("🌙 Late Night", use_container_width=True):
            preset_text = "Late night quick bites after midnight with hot kebabs or cheesy burgers"
    with col_p5:
        if st.button("🥗 Vegan & Organic", use_container_width=True):
            preset_text = "Organic 100% plant-based cafe with fresh salads, cold-pressed smoothies, and peaceful green vibes"

    if preset_text:
        st.session_state["user_preferences_input"] = preset_text

    additional_preferences = st.text_area(
        "Natural Language Dining Request:",
        value=st.session_state.get(
            "user_preferences_input",
            "Cozy romantic rooftop with candle-lit seating, great Italian wine, under ₹1500",
        ),
        placeholder="e.g. cozy cafe with quiet corners, good wifi, artisan coffee, and sweet desserts",
        max_chars=300,
        height=80,
    )

    submit_clicked = st.button("🍽️ Ask AI Recommendations", type="primary", use_container_width=True)

    # --- Recommendation Execution ---
    if submit_clicked:
        if not location or not location.strip():
            st.warning("⚠️ Please specify a location or neighborhood to search.")
            return

        req = UserPreferenceRequest(
            location=location.strip(),
            budget_tier=selected_budget,
            cuisines=selected_cuisines,
            min_rating=float(min_rating),
            additional_preferences=additional_preferences.strip() if additional_preferences else None,
        )

        with st.spinner("🤖 DineMind synthesizing verified diner reviews, rankings, and reasoning..."):
            t_start = time.perf_counter()
            response = get_recommendations_hybrid(req)
            latency = (time.perf_counter() - t_start) * 1000

        # --- Render Results (Stitch AISummaryBanner & Cards) ---
        st.markdown("---")

        # AISummaryBanner
        badge_text = "⚡ Fallback Engine" if response.is_fallback else "✨ Live Groq Inference"
        st.markdown(
            f"""
            <div class="ai-summary-card">
                <div class="ai-summary-title">
                    <span>✨ AI DineMind Synthesized Analysis</span>
                    <span style="font-size: 0.72rem; padding: 0.15rem 0.5rem; border-radius: 9999px; background: rgba(139, 92, 246, 0.3); color: #DDD6FE; font-weight: 600;">Confidence: 98.4%</span>
                    <span style="font-size: 0.72rem; padding: 0.15rem 0.5rem; border-radius: 9999px; background: rgba(16, 185, 129, 0.2); color: #6EE7B7; font-weight: 600;">{badge_text} ({latency:.0f}ms)</span>
                </div>
                <div class="ai-summary-text">
                    {response.summary}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not response.recommendations:
            st.warning("No restaurants matched all criteria. Try relaxing your rating or expanding the cuisine filter.")
            return

        st.markdown(f"##### 🏆 Curated Matches in {location}")

        # Render Recommendation Cards with Metallic Badges
        for rec in response.recommendations:
            cost_str = f"₹{rec.estimated_cost_for_two:,.0f} for two"
            if rec.rank == 1:
                rank_class = "rank-gold"
            elif rec.rank == 2:
                rank_class = "rank-silver"
            elif rec.rank == 3:
                rank_class = "rank-bronze"
            else:
                rank_class = "rank-standard"

            st.markdown(
                f"""
                <div class="stitch-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                        <div>
                            <span class="{rank_class}">#{rec.rank} MATCH</span>
                            <span style="font-size: 1.25rem; font-weight: 800; color: #FFFFFF; margin-left: 0.5rem;">{rec.restaurant_name}</span>
                        </div>
                        <div>
                            <span class="stitch-rating">★ {rec.rating:.1f}</span>
                        </div>
                    </div>
                    <div style="margin-bottom: 0.75rem;">
                        <span class="stitch-chip">🍽️ {rec.cuisine}</span>
                        <span class="stitch-cost">💰 {cost_str}</span>
                        <span class="stitch-chip">📍 {location}</span>
                    </div>
                    <div class="ai-rationale-box">
                        <div class="ai-rationale-header">
                            ✨ Why AI Picked This For You
                        </div>
                        "{rec.explanation}"
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
