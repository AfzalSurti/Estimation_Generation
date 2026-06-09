"""
Rate Analysis engine for civil engineering BOQ estimation.

Builds derived rates for work items not covered in SOR detailed items by
combining SOR base-input material/labour/plant rates with lead carriage costs
and overhead.
"""

from typing import Any


def calculate_lead_carriage(
    base_rate: float,
    lead_km: float,
    carriage_rate_per_km: float,
    first_5km_rate: float,
) -> float:
    """
    Compute material rate at site including lead carriage.

    Carriage for lead <= 5 km uses first_5km_rate per km.
    For lead > 5 km: first 5 km at first_5km_rate, remainder at carriage_rate_per_km.
    Returns base_rate plus total carriage cost.
    """
    try:
        lead_km = max(0.0, float(lead_km))
        if lead_km <= 5:
            carriage_cost = lead_km * first_5km_rate
        else:
            carriage_cost = (5 * first_5km_rate) + ((lead_km - 5) * carriage_rate_per_km)
        return round(float(base_rate) + carriage_cost, 4)
    except (TypeError, ValueError):
        return float(base_rate)


def calculate_ingredient_cost(ingredient: dict) -> dict:
    """
    Fill rate_at_site and cost for a single RA ingredient dict.

    Uses calculate_lead_carriage for site rate, then:
    cost = quantity × rate_at_site × conversion_factor
    """
    try:
        updated = dict(ingredient)
        rate_at_site = calculate_lead_carriage(
            base_rate=float(updated.get("base_rate", 0)),
            lead_km=float(updated.get("lead_km", 0)),
            carriage_rate_per_km=float(updated.get("carriage_rate_per_km", 0)),
            first_5km_rate=float(updated.get("first_5km_rate", 0)),
        )
        quantity = float(updated.get("quantity", 0))
        conversion = float(updated.get("conversion_factor", 1.0))
        cost = round(quantity * rate_at_site * conversion, 2)
        updated["rate_at_site"] = rate_at_site
        updated["cost"] = cost
        return updated
    except (TypeError, ValueError, KeyError) as exc:
        result = dict(ingredient)
        result["rate_at_site"] = 0.0
        result["cost"] = 0.0
        result["error"] = str(exc)
        return result


def create_ra_item(
    item_id: str,
    description: str,
    unit: str,
    ingredients: list[dict],
    overhead_percent: float,
    sor_reference: str,
) -> dict:
    """
    Build a complete Rate Analysis item from ingredient rows.

    Each ingredient is costed via calculate_ingredient_cost; subtotal is summed,
    overhead applied, and final_rate returned.
    """
    try:
        costed = [calculate_ingredient_cost(ing) for ing in ingredients]
        subtotal = round(sum(float(i.get("cost", 0)) for i in costed), 2)
        overhead_amount = round(subtotal * float(overhead_percent) / 100, 2)
        final_rate = round(subtotal + overhead_amount, 2)
        return {
            "item_id": item_id,
            "description": description,
            "unit": unit,
            "ingredients": costed,
            "subtotal": subtotal,
            "overhead_percent": float(overhead_percent),
            "overhead_amount": overhead_amount,
            "final_rate": final_rate,
            "sor_reference": sor_reference,
        }
    except (TypeError, ValueError) as exc:
        return {
            "item_id": item_id,
            "description": description,
            "unit": unit,
            "ingredients": [],
            "subtotal": 0.0,
            "overhead_percent": float(overhead_percent),
            "overhead_amount": 0.0,
            "final_rate": 0.0,
            "sor_reference": sor_reference,
            "error": str(exc),
        }


def get_ra_summary(ra_items: list[dict]) -> dict[str, Any]:
    """Return a compact summary list of Rate Analysis items and final rates."""
    items = []
    for item in ra_items:
        try:
            items.append({
                "item_id": item.get("item_id", ""),
                "description": item.get("description", ""),
                "unit": item.get("unit", ""),
                "final_rate": item.get("final_rate", 0.0),
            })
        except (TypeError, AttributeError):
            continue
    return {"total_items": len(items), "items": items}
