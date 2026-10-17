"""Structured output models for the Campus Customs vendor desk agent."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class VendorRecommendation(BaseModel):
    """The vendor desk agent's structured recommendation for one vendor document.

    Every field is filled in strictly from the vendor document text and the
    Campus Customs Shop Handbook. When a fact is not stated in the document,
    the corresponding field is left as ``None`` instead of being guessed.
    """

    vendor: str | None = Field(
        default=None,
        description=(
            "The vendor's name exactly as it appears in the document "
            "(e.g. the company name in the letterhead, signature, or sender "
            "address). None if the document does not clearly identify a vendor."
        ),
    )
    sku: str | None = Field(
        default=None,
        description=(
            "The Campus Customs SKU being quoted (e.g. 'CC-HD-006'), taken "
            "directly from the document. None if no SKU is stated."
        ),
    )
    unit_price: float | None = Field(
        default=None,
        ge=0,
        description=(
            "The quoted unit price in US dollars for the SKU, taken directly "
            "from the document. None if no unit price is stated."
        ),
    )
    lead_time_days: int | None = Field(
        default=None,
        ge=0,
        description=(
            "The vendor's quoted lead time in days. If the document states a "
            "range (e.g. '10-18 days') or a unit other than days (e.g. "
            "'business days' or weeks), convert to a single whole number of "
            "days using the most conservative (longest) reasonable reading. "
            "None if no lead time is stated."
        ),
    )
    min_order: int | None = Field(
        default=None,
        ge=0,
        description=(
            "The vendor's minimum order quantity in units, taken directly "
            "from the document. None if no minimum order is stated."
        ),
    )
    decision: Literal["recommend", "do_not_recommend"] = Field(
        description=(
            "The purchasing decision, computed by applying the Campus "
            "Customs Shop Handbook's four purchasing checks (approved "
            "vendor, price at or below catalogue max unit cost, lead time of "
            "21 days or less, minimum order of 600 units or less) and the "
            "removed/pending vendor list. 'recommend' only if all checks "
            "pass; 'do_not_recommend' otherwise, including whenever a "
            "required fact is missing and cannot be verified against the "
            "handbook."
        ),
    )
    reason: str = Field(
        description=(
            "One sentence naming the specific purchasing check (approved "
            "vendor, price, lead time, minimum order) that decided the "
            "outcome, or noting which required fact was missing from the "
            "document."
        ),
    )
