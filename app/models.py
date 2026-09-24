"""Domain models and Pydantic schemas for restaurant recommendation system."""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import AliasChoices, BaseModel, Field, field_validator


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
        validation_alias=AliasChoices("location", "locality"),
        min_length=1,
        max_length=100,
        description="Target city or neighborhood (e.g., 'Bangalore', 'Koramangala', 'Indiranagar').",
    )
    budget_tier: str = Field(
        default="medium",
        validation_alias=AliasChoices("budget_tier", "budget"),
        description="Budget tier classification: 'low' (<= ₹500), 'medium' (₹500 - ₹1500), 'high' (> ₹1500).",
    )
    cuisines: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("cuisines", "cuisine"),
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
        validation_alias=AliasChoices("additional_preferences", "extras", "preferences"),
        max_length=300,
        description="Free-text preferences (e.g. 'romantic rooftop for anniversary', 'spacious for kids').",
    )

    @field_validator("cuisines", mode="before")
    @classmethod
    def clean_cuisines(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            s = v.strip()
            return [s] if s else []
        if isinstance(v, (list, tuple, set)):
            return [str(item).strip() for item in v if str(item).strip()]
        return []

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


class BudgetBand(BaseModel):
    """Classification band for budget selector in frontend."""

    id: str = Field(..., description="Band identifier ('low', 'medium', 'high').")
    label: str = Field(..., description="User-facing label for the budget segment.")
    min_cost: Optional[float] = Field(default=None, description="Minimum cost in INR.")
    max_cost: Optional[float] = Field(default=None, description="Maximum cost in INR.")


class RestaurantRecommendation(BaseModel):
    """An individual ranked recommendation produced by the AI engine."""

    rank: int = Field(..., description="Rank position (1-based, e.g. 1, 2, 3).")
    restaurant_name: str = Field(default="", description="Official name of the restaurant.")
    name: str = Field(default="", description="Alias for restaurant_name for frontend compatibility.")
    cuisine: str = Field(default="Multi-Cuisine", description="Primary cuisine offerings.")
    cuisines: List[str] = Field(default_factory=list, description="List of cuisines.")
    rating: float = Field(default=3.5, description="Star rating.")
    votes: int = Field(default=0, description="Total user review votes.")
    estimated_cost_for_two: float = Field(default=0.0, description="Estimated cost for two diners in INR.")
    estimated_cost: Optional[float] = Field(default=None, description="Alias for estimated_cost_for_two.")
    locality: str = Field(default="", description="Neighborhood locality.")
    rest_types: List[str] = Field(default_factory=list, description="Restaurant types/categories.")
    book_table: bool = Field(default=False, description="Whether table booking is available.")
    online_order: bool = Field(default=False, description="Whether online ordering is available.")
    dish_liked: List[str] = Field(default_factory=list, description="Popular dishes liked by diners.")
    explanation: str = Field(..., description="Humanized explanation justifying why this venue fits user preferences.")

    def model_post_init(self, __context: Any) -> None:
        if not self.name and self.restaurant_name:
            self.name = self.restaurant_name
        elif not self.restaurant_name and self.name:
            self.restaurant_name = self.name

        if self.estimated_cost is None and self.estimated_cost_for_two:
            self.estimated_cost = self.estimated_cost_for_two
        elif self.estimated_cost_for_two == 0.0 and self.estimated_cost is not None:
            self.estimated_cost_for_two = self.estimated_cost

        if not self.cuisines and self.cuisine:
            self.cuisines = [c.strip() for c in self.cuisine.split("•") if c.strip()] or [self.cuisine]
        elif not self.cuisine and self.cuisines:
            self.cuisine = " • ".join(self.cuisines)


class RecommendationResponse(BaseModel):
    """Structured response payload returned by the recommendation engine."""

    summary: str = Field(..., description="High-level overview and synthesis of the recommendations.")
    is_fallback: bool = Field(
        default=False,
        description="True if recommendations were generated via the heuristic fallback engine.",
    )
    llm_used: bool = Field(
        default=True,
        description="True if recommendations were ranked using live LLM inference.",
    )
    candidate_count: int = Field(
        default=0,
        description="Number of candidates screened in Stage 1 filtering.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional status message or criteria relaxation note.",
    )
    did_you_mean: List[str] = Field(
        default_factory=list,
        description="Suggested localities when no direct matches are found.",
    )
    relaxed_criteria: bool = Field(
        default=False,
        description="True if filtering criteria were expanded to find matches.",
    )
    recommendations: List[RestaurantRecommendation] = Field(
        default_factory=list,
        description="List of ranked restaurant recommendations with explanations.",
    )

    def model_post_init(self, __context: Any) -> None:
        if self.is_fallback:
            self.llm_used = False


class MetadataResponse(BaseModel):
    """Metadata response describing the active dataset for frontend selectors."""

    total_restaurants: int
    cities: List[str]
    localities: List[str]
    cuisines: List[str]
    budget_tiers: List[str] = Field(default_factory=lambda: ["low", "medium", "high"])
    budget_bands: List[BudgetBand] = Field(default_factory=list)
