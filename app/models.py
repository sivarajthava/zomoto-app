"""Domain models and Pydantic schemas for restaurant recommendation system."""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class Restaurant(BaseModel):
    """Domain model representing a cleaned Zomato restaurant record."""

    id: str
    name: str
    city: str
    locality: str
    address: str = ""
    cuisines_list: List[str] = Field(default_factory=list)
    cuisines_str: str = ""
    average_cost_for_two: float
    budget_tier: str  # "low", "medium", "high"
    aggregate_rating: Optional[float] = None
    votes: int = 0
    rest_type: str = ""
    dish_liked: str = ""
    online_order: str = "No"
    book_table: str = "No"
    url: str = ""


class UserPreferenceRequest(BaseModel):
    """Input request schema capturing user dining preferences and criteria."""

    location: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Target city or neighborhood (e.g., 'Bangalore', 'Koramangala', 'Indiranagar').",
    )
    budget_tier: str = Field(
        default="medium",
        description="Budget tier classification: 'low' (<= ₹500), 'medium' (₹500 - ₹1500), 'high' (> ₹1500).",
    )
    cuisines: List[str] = Field(
        default_factory=list,
        description="Preferred cuisines (e.g. ['North Indian', 'Chinese', 'Italian']).",
    )
    min_rating: float = Field(
        default=3.5,
        ge=0.0,
        le=5.0,
        description="Minimum acceptable aggregate star rating (0.0 - 5.0).",
    )
    additional_preferences: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Free-text preferences (e.g. 'romantic rooftop for anniversary', 'spacious for kids').",
    )

    @field_validator("location", mode="before")
    @classmethod
    def clean_location(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Location must be a non-empty string.")
        return v.strip()

    @field_validator("budget_tier", mode="before")
    @classmethod
    def clean_budget_tier(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("budget_tier must be a string.")
        tier = v.strip().lower()
        if tier not in {"low", "medium", "high"}:
            raise ValueError("budget_tier must be one of: 'low', 'medium', 'high'.")
        return tier

    @field_validator("additional_preferences", mode="before")
    @classmethod
    def clean_preferences(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None


class RestaurantRecommendation(BaseModel):
    """An individual ranked recommendation produced by the AI engine."""

    rank: int = Field(..., description="Rank position (1-based, e.g. 1, 2, 3).")
    restaurant_name: str = Field(..., description="Official name of the restaurant.")
    cuisine: str = Field(..., description="Primary cuisine offerings.")
    rating: float = Field(..., description="Star rating.")
    estimated_cost_for_two: float = Field(..., description="Estimated cost for two diners in INR.")
    explanation: str = Field(..., description="Humanized explanation justifying why this venue fits user preferences.")


class RecommendationResponse(BaseModel):
    """Structured response payload returned by the recommendation engine."""

    summary: str = Field(..., description="High-level overview and synthesis of the recommendations.")
    is_fallback: bool = Field(
        default=False,
        description="True if recommendations were generated via the heuristic fallback engine.",
    )
    recommendations: List[RestaurantRecommendation] = Field(
        default_factory=list,
        description="List of ranked restaurant recommendations with explanations.",
    )


class MetadataResponse(BaseModel):
    """Metadata response describing the active dataset for frontend selectors."""

    total_restaurants: int
    cities: List[str]
    localities: List[str]
    cuisines: List[str]
    budget_tiers: List[str]
