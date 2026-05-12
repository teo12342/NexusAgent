"""
nexus_agent Agent Screen Analyzer — src/vision/analyzer.py
Send screenshots to Ollama vision models for understanding
"""

import base64
import structlog
from typing import Dict, Any, Optional, List
from PIL import Image
import io
import json

logger = structlog.get_logger()


class ScreenAnalyzer:
    """
    Analyze screenshots using local Ollama vision models.
    Supports llava, qwen2-vl, moondream2.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url
        self.available_models: List[str] = []
        self._check_models()

    def _check_models(self) -> None:
        """Check which vision models are available in Ollama."""
        import requests
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                vision_keywords = ["llava", "qwen2-vl", "moondream", "llava-llama3"]
                self.available_models = [
                    m["name"] for m in models
                    if any(vk in m["name"].lower() for vk in vision_keywords)
                ]
                if self.available_models:
                    logger.info("vision_models_available", models=self.available_models)
                else:
                    logger.warning("no_vision_models_found_in_ollama")
        except Exception as e:
            logger.warning("ollama_not_reachable", error=str(e))

    def _image_to_base64(self, img: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def describe(
        self,
        image: Image.Image,
        prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Send a screenshot to a vision model and get a description.
        Uses first available vision model if none specified.
        """
        import requests

        if not self.available_models:
            return "[Vision model not available — install llava in Ollama]"

        model = model or self.available_models[0]
        prompt = prompt or "Describe what you see in this image in detail. Focus on any clickable UI elements, text, or important content."

        try:
            b64_img = self._image_to_base64(image)

            payload = {
                "model": model,
                "prompt": prompt,
                "images": [b64_img],
                "stream": False,
            }

            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60,
            )

            if resp.status_code == 200:
                result = resp.json()
                return result.get("response", "")
            else:
                return f"[Vision error: {resp.status_code}]"
        except requests.exceptions.Timeout:
            return "[Vision timeout — image too complex]"
        except Exception as e:
            logger.error("vision_analysis_error", error=str(e))
            return f"[Vision error: {str(e)}]"

    def find_element(
        self,
        image: Image.Image,
        description: str,
        model: Optional[str] = None,
    ) -> Optional[Dict[str, int]]:
        """
        Find a UI element described by the user in the screenshot.
        Returns {center_x, center_y} coordinates if found, else None.
        """
        import requests

        model = model or self.available_models[0]

        prompt = (
            f'Look at this screenshot and find the center coordinates of the element described as: "{description}". '
            "Respond ONLY with a JSON object: {\"x\": number, \"y\": number} "
            "If you cannot find it, respond with {\"x\": -1, \"y\": -1}. "
            "Do not explain. Do not apologize. Just the JSON."
        )

        try:
            b64_img = self._image_to_base64(image)
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": model, "prompt": prompt, "images": [b64_img], "stream": False},
                timeout=60,
            )

            if resp.status_code == 200:
                result = resp.json().get("response", "").strip()
                try:
                    coords = json.loads(result)
                    if coords.get("x", -1) >= 0 and coords.get("y", -1) >= 0:
                        logger.info("element_found", description=description, x=coords["x"], y=coords["y"])
                        return coords
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.error("element_finder_error", error=str(e))

        return None

    def analyze_for_automation(
        self,
        image: Image.Image,
        task: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Given a screenshot and a task, return the action to take.
        e.g. task="click the login button" → returns {action: "click", x: 400, y: 300}
        """
        import requests

        model = model or self.available_models[0]

        prompt = (
            f'This screenshot is from a screen automation task. '
            f'The task is: "{task}". '
            'Analyze the screenshot and determine what action to take. '
            'Respond ONLY with a JSON object in this format: '
            '{"action": "click|key|type|scroll|wait", "x": number, "y": number, "key": "keyname", "text": "text", "direction": "up|down", "amount": number}. '
            'If the action requires coordinates, provide x and y. '
            'If the task is already complete or unclear, respond: {"action": "done"} or {"action": "need_more_info", "reason": "..."}. '
            'Do not explain. Just the JSON.'
        )

        try:
            b64_img = self._image_to_base64(image)
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": model, "prompt": prompt, "images": [b64_img], "stream": False},
                timeout=60,
            )

            if resp.status_code == 200:
                result = resp.json().get("response", "").strip()
                try:
                    action = json.loads(result)
                    logger.info("automation_action", task=task, action=action)
                    return action
                except json.JSONDecodeError:
                    return {"action": "parse_error", "raw": result}
        except Exception as e:
            logger.error("automation_analysis_error", error=str(e))
            return {"action": "error", "error": str(e)}

        return {"action": "error", "error": "request failed"}


# Singleton
screen_analyzer = ScreenAnalyzer()