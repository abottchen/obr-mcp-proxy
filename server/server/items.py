from .websocket_server import RelayConnection


async def fetch_all_items(relay: RelayConnection) -> list[dict]:
    """Fetch all scene items in a single request."""
    items = await relay.send_request("scene.items.getItems")
    return items if isinstance(items, list) else []


async def get_item_by_id(
    relay: RelayConnection, item_id: str, *, items: list[dict] | None = None
) -> dict:
    """Fetch a single item by UUID. Raises ValueError if not found.

    Args:
        relay: The relay connection.
        item_id: The item's UUID.
        items: Optional pre-fetched item list to avoid an extra round-trip.
    """
    if items is None:
        items = await fetch_all_items(relay)
    for item in items:
        if item.get("id") == item_id:
            return item
    raise ValueError(f"No item found with ID: {item_id}")


async def resolve_item(
    relay: RelayConnection, identifier: str, *, items: list[dict] | None = None
) -> dict:
    """Find a single item by ID (exact match) or name (case-insensitive).

    Raises ValueError if not found or if multiple name matches exist.

    Args:
        relay: The relay connection.
        identifier: Item ID or name.
        items: Optional pre-fetched item list to avoid an extra round-trip.
    """
    if items is None:
        items = await fetch_all_items(relay)

    if not items:
        raise ValueError(f"Item not found: {identifier}")

    # Try exact ID match first
    for item in items:
        if item.get("id") == identifier:
            return item

    # Fall back to case-insensitive name match
    name_lower = identifier.lower()
    matches = [
        i for i in items if (i.get("name") or "").lower() == name_lower
    ]

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        names = [f"{m.get('name')} (id={m.get('id')})" for m in matches]
        raise ValueError(
            f"Ambiguous name '{identifier}', matched {len(matches)} items: {', '.join(names)}"
        )

    # Try substring match as last resort
    matches = [
        i for i in items if name_lower in (i.get("name") or "").lower()
    ]

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        names = [f"{m.get('name')} (id={m.get('id')})" for m in matches]
        raise ValueError(
            f"Ambiguous name '{identifier}', matched {len(matches)} items: {', '.join(names)}"
        )

    raise ValueError(f"Item not found: {identifier}")
