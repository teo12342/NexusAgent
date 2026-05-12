"""
nexus_agent Agent Screen Capture — src/vision/capture.py
Screenshot capture via Pillow/PyGetWindow — full screen, window, region
"""

import structlog
from typing import Tuple, Optional, Union, List
from PIL import Image, ImageGrab
import io
import base64

logger = structlog.get_logger()


class ScreenCapture:
    """
    Capture screenshots using Pillow (cross-platform fallback).
    On Windows, also supports window-specific capture via pywin32.
    """

    def __init__(self):
        self._last_image: Optional[Image.Image] = None
        self._last_hash: Optional[int] = None

    def capture_fullscreen(self) -> Image.Image:
        """Capture the entire primary screen."""
        img = ImageGrab.grab(all_screens=False)
        self._last_image = img
        self._last_hash = hash(img.tobytes())
        return img

    def capture_all_screens(self) -> List[Image.Image]:
        """Capture all connected monitors."""
        imgs = ImageGrab.grab(all_screens=True)
        # Returns a single image stitched together — handle per-monitor if needed
        self._last_image = imgs
        return [imgs]

    def capture_window(self, window_title: str) -> Optional[Image.Image]:
        """
        Capture a specific window by title.
        Returns None if window not found.
        """
        try:
            import pywintypes
            import win32gui
            import win32ui
            import win32con
        except ImportError:
            logger.warning("pywin32 not available for window capture")
            return None

        hwnd = win32gui.FindWindow(None, window_title)
        if not hwnd:
            # Try partial match
            results = self._find_windows_by_title(window_title)
            if not results:
                return None
            hwnd = results[0]

        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            # Get window DC
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            # Create bitmap
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)

            # Print window
            result = win32gui.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)

            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )

            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)

            if result:
                self._last_image = img
                return img
        except Exception as e:
            logger.error("window_capture_error", window=window_title, error=str(e))
        return None

    def _find_windows_by_title(self, partial: str) -> List:
        """Find all windows whose title contains the partial string."""
        import win32gui
        results = []

        def enum_handler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if partial.lower() in title.lower():
                    results.append(hwnd)

        try:
            win32gui.EnumWindows(enum_handler, None)
        except Exception:
            pass
        return results

    def capture_region(self, bbox: Tuple[int, int, int, int]) -> Image.Image:
        """
        Capture a specific region of the screen.
        bbox: (left, top, right, bottom) in pixels
        """
        img = ImageGrab.grab(bbox=bbox)
        self._last_image = img
        return img

    def capture_to_bytes(self, fmt: str = "PNG") -> bytes:
        """Capture full screen and return as bytes."""
        img = self.capture_fullscreen()
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        return buf.getvalue()

    def capture_to_base64(self, fmt: str = "PNG") -> str:
        """Capture full screen and return as base64 string."""
        data = self.capture_to_bytes(fmt)
        return base64.b64encode(data).decode("utf-8")

    def get_clickable_regions(self) -> List[Dict]:
        """
        Find clickable regions in the last captured image.
        Uses edge detection to find UI elements — buttons, links, etc.
        Returns list of {x, y, width, height, label} for each region.
        """
        import cv2
        import numpy as np

        if not self._last_image:
            return []

        # Convert PIL to OpenCV
        img = cv2.cvtColor(np.array(self._last_image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect edges
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            # Filter small noise and giant backgrounds
            if 500 < area < 100000 and w > 20 and h > 10:
                regions.append({
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "center_x": x + w // 2,
                    "center_y": y + h // 2,
                    "area": area,
                })

        # Sort by area (larger = more likely to be main UI element)
        regions.sort(key=lambda r: r["area"], reverse=True)
        return regions[:20]  # Top 20 most likely clickable regions

    def has_screen_changed(self, threshold: int = 1000) -> bool:
        """
        Check if screen has changed significantly since last capture.
        threshold: number of differing pixels to count as "changed"
        Returns True if changed, False if same.
        """
        if not self._last_image:
            return True

        new_img = self.capture_fullscreen()
        new_hash = hash(new_img.tobytes())

        if new_hash != self._last_hash:
            return True

        # Also compare pixel-by-pixel as backup
        import numpy as np
        arr1 = np.array(self._last_image.resize((100, 100)))
        arr2 = np.array(new_img.resize((100, 100)))
        diff = np.sum(np.abs(arr1.astype(int) - arr2.astype(int)))
        return diff > threshold


# Singleton
screen_capture = ScreenCapture()