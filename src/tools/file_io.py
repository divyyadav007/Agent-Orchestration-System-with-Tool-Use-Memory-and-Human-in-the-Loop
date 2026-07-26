import logging
import os
from .registry import registry

logger = logging.getLogger(__name__)


@registry.register(
    name="save_file",
    description="Save text content to a file in the workspace directory.",
    parameter_schema={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "The target filename (e.g. 'report.txt' or 'summary.md')"},
            "content": {"type": "string", "description": "The text content to write to the file"},
        },
        "required": ["filename", "content"],
    },
)
def save_file(filename: str, content: str) -> str:
    """Saves text content to a file in the workspace directory.

    Why os.path.basename is used: LLMs might attempt to generate absolute or relative
    file paths (e.g., ../../etc/passwd). Stripping to basename prevents security
    vulnerabilities by keeping all writes contained strictly inside the workspace.
    """
    try:
        safe_filename = os.path.basename(filename)
        filepath = os.path.join(os.getcwd(), safe_filename)
        logger.info(f"Writing file '{safe_filename}' to '{filepath}'")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully saved content to file '{safe_filename}'."
    except Exception as e:
        logger.error(f"Failed to write file '{filename}': {e}", exc_info=True)
        return f"Error writing file: {str(e)}"
