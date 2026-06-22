from __future__ import annotations

from pathlib import Path


def test_storyboard_route_keeps_provider_parser_split() -> None:
    api_root = Path("apps/api")
    route_path = api_root / "runtime_storyboard_breakdown.py"
    parser_path = api_root / "runtime_storyboard_provider_parse.py"

    route_source = route_path.read_text(encoding="utf-8")
    parser_source = parser_path.read_text(encoding="utf-8")

    assert parser_path.is_file()
    assert "from apps.api.runtime_storyboard_provider_parse import shots_from_provider_text" in route_source
    assert "json.JSONDecoder" not in route_source
    assert "def shots_from_provider_text" in parser_source
    assert "def _first_json_object_with_shots" in parser_source
    assert len(route_source.splitlines()) <= 300
    assert len(parser_source.splitlines()) <= 300
