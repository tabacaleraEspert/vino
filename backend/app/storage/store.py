"""Almacenamiento JSON para categorías, presupuestos, comercios y reglas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_STORE_PATH = Path(__file__).resolve().parent.parent.parent / "data.json"

_DEFAULT: Dict[str, List[Dict[str, Any]]] = {
    "categories": [],
    "budgets": [],
    "merchants": [],
    "merchantRules": [],
}


def _load() -> Dict[str, List[Dict[str, Any]]]:
    if not _STORE_PATH.exists():
        return _DEFAULT.copy()
    try:
        with open(_STORE_PATH, encoding="utf-8") as f:
            data = json.load(f)
            return {
                "categories": data.get("categories", []),
                "budgets": data.get("budgets", []),
                "merchants": data.get("merchants", []),
                "merchantRules": data.get("merchantRules", []),
            }
    except Exception:
        return _DEFAULT.copy()


def _save(data: Dict[str, List[Dict[str, Any]]]) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_all(key: str) -> List[Dict[str, Any]]:
    data = _load()
    return data.get(key, [])


def _generate_id(prefix: str) -> str:
    import time
    import random
    return f"{prefix}_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"


def add_item(
    key: str,
    item: Dict[str, Any],
    id_field: str = "id",
    custom_id: Optional[str] = None,
) -> Dict[str, Any]:
    data = _load()
    items = data.get(key, [])
    prefix = "cat" if key == "categories" else "bud" if key == "budgets" else "mer" if key == "merchants" else "rule"
    new_id = custom_id if custom_id else _generate_id(prefix)
    new_item = {**item, id_field: new_id}
    items.append(new_item)
    data[key] = items
    _save(data)
    return new_item


def update_item(key: str, item_id: str, updates: Dict[str, Any], id_field: str = "id") -> Dict[str, Any] | None:
    data = _load()
    items = data.get(key, [])
    for i, it in enumerate(items):
        if str(it.get(id_field, "")) == str(item_id):
            items[i] = {**it, **updates, id_field: it[id_field]}
            data[key] = items
            _save(data)
            return items[i]
    return None


def delete_item(key: str, item_id: str, id_field: str = "id") -> bool:
    data = _load()
    items = data.get(key, [])
    new_items = [it for it in items if str(it.get(id_field, "")) != str(item_id)]
    if len(new_items) == len(items):
        return False
    data[key] = new_items
    _save(data)
    return True
