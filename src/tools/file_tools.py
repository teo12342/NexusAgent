"""File tools for nexus_agent Agent — read, write, list, search files."""

import os
import structlog
from typing import Dict, Any, List

logger = structlog.get_logger()


def register_file_tools(registry: Dict):

    def file_read(path: str, limit: int = None) -> Dict:
        """Read a file's contents."""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read() if limit is None else f.read(limit)
            return {"success": True, "path": path, "content": content, "size": len(content)}
        except FileNotFoundError:
            return {"success": False, "error": f"File not found: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def file_write(path: str, content: str) -> Dict:
        """Write content to a file."""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "path": path, "bytes": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def file_append(path: str, content: str) -> Dict:
        """Append content to a file."""
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "path": path, "bytes": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def file_delete(path: str) -> Dict:
        """Delete a file (not a directory)."""
        try:
            if os.path.isfile(path):
                os.remove(path)
                return {"success": True, "path": path}
            return {"success": False, "error": "Not a file"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def file_list(directory: str, pattern: str = "*", recursive: bool = False) -> Dict:
        """List files in a directory."""
        try:
            import fnmatch
            matches = []
            if recursive:
                for root, dirs, files in os.walk(directory):
                    for name in files:
                        if fnmatch.fnmatch(name, pattern):
                            full = os.path.join(root, name)
                            matches.append({
                                "path": full,
                                "name": name,
                                "size": os.path.getsize(full),
                            })
            else:
                for name in os.listdir(directory):
                    full = os.path.join(directory, name)
                    if os.path.isfile(full) and fnmatch.fnmatch(name, pattern):
                        matches.append({
                            "path": full,
                            "name": name,
                            "size": os.path.getsize(full),
                        })
            return {"success": True, "directory": directory, "pattern": pattern, "count": len(matches), "files": matches}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def file_exists(path: str) -> bool:
        return os.path.exists(path)

    def file_mkdir(path: str) -> Dict:
        try:
            os.makedirs(path, exist_ok=True)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def file_copy(src: str, dst: str) -> Dict:
        import shutil
        try:
            shutil.copy2(src, dst)
            return {"success": True, "src": src, "dst": dst}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def file_move(src: str, dst: str) -> Dict:
        import shutil
        try:
            shutil.move(src, dst)
            return {"success": True, "src": src, "dst": dst}
        except Exception as e:
            return {"success": False, "error": str(e)}

    tools = {
        "file_read": file_read,
        "file_write": file_write,
        "file_append": file_append,
        "file_delete": file_delete,
        "file_list": file_list,
        "file_exists": file_exists,
        "file_mkdir": file_mkdir,
        "file_copy": file_copy,
        "file_move": file_move,
    }
    registry.update(tools)