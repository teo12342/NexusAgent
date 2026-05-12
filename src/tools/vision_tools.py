"""Vision tools for nexus_agent Agent — capture, analyze, click detection."""

import structlog
from typing import Dict, Any

logger = structlog.get_logger()


def register_vision_tools(registry: Dict):
    from ..vision import ScreenCapture, ScreenAnalyzer

    _capture: ScreenCapture = None
    _analyzer: ScreenAnalyzer = None

    def get_capture() -> ScreenCapture:
        nonlocal _capture
        if _capture is None:
            _capture = ScreenCapture()
        return _capture

    def get_analyzer() -> ScreenAnalyzer:
        nonlocal _analyzer
        if _analyzer is None:
            _analyzer = ScreenAnalyzer()
        return _analyzer

    def capture_fullscreen() -> Dict[str, Any]:
        img = get_capture().capture_fullscreen()
        b64 = get_capture().capture_to_base64()
        return {"success": True, "format": "PNG", "size_kb": len(b64) // 1024, "base64_preview": b64[:200] + "..."}

    def capture_window(window_title: str) -> Dict[str, Any]:
        img = get_capture().capture_window(window_title)
        if img:
            return {"success": True, "format": "PNG", "base64_preview": get_capture().capture_to_base64()[:200] + "..."}
        return {"success": False, "error": f"Window not found: {window_title}"}

    def capture_region(left: int, top: int, right: int, bottom: int) -> Dict[str, Any]:
        img = get_capture().capture_region((left, top, right, bottom))
        return {"success": True, "format": "PNG"}

    def analyze_screen(prompt: str = None, model: str = None) -> str:
        img = get_capture().capture_fullscreen()
        return get_analyzer().describe(image=img, prompt=prompt, model=model)

    def find_on_screen(description: str, model: str = None) -> Dict[str, Any]:
        img = get_capture().capture_fullscreen()
        result = get_analyzer().find_element(image=img, description=description, model=model)
        if result:
            return {"success": True, "x": result.get("x"), "y": result.get("y")}
        return {"success": False, "error": "Element not found or vision model unavailable"}

    def get_clickable_regions() -> list:
        return get_capture().get_clickable_regions()

    def has_screen_changed() -> bool:
        return get_capture().has_screen_changed()

    tools = {
        "capture_fullscreen": capture_fullscreen,
        "capture_window": capture_window,
        "capture_region": capture_region,
        "analyze_screen": analyze_screen,
        "find_on_screen": find_on_screen,
        "get_clickable_regions": get_clickable_regions,
        "screen_changed": has_screen_changed,
    }
    registry.update(tools)