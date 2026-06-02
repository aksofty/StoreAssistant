import importlib.util
from pathlib import Path

from langchain_core.tools import BaseTool
from loguru import logger


def load_client_tools(tool_dir: str) -> list[BaseTool]:
    tools: list[BaseTool] = []
    tool_path = Path(tool_dir)

    if not tool_path.is_dir():
        return tools

    py_file = tool_path / "tools.py"
    if not py_file.is_file():
        return tools

    try:
        spec = importlib.util.spec_from_file_location("client_tools", py_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if isinstance(obj, BaseTool):
                tools.append(obj)

    except Exception:
        logger.exception("Failed to load client tools from {}", py_file)

    return tools
