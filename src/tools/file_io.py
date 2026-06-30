import logging
import os
from .registry import registry

# Initialize module logger
logger = logging.getLogger(__name__)

@registry.register(
    name="save_file",
    description="Save text content to a file in the workspace directory.",
    parameter_schema={
        "type": "object",
        "properties": {
            "filename": {
                "type": "string", 
                "description": "The name of the file to save (e.g. 'CEO_AI_Regulations_Brief.txt' or 'report.txt')"
            },
            "content": {
                "type": "string", 
                "description": "The text content to write to the file"
            }
        },
        "required": ["filename", "content"]
    }
)
def save_file(filename: str, content: str) -> str:
    """Saves the given content string to a file in the current workspace directory.

    Args:
        filename (str): The destination file name (only the base name is used to avoid path traversal).
        content (str): The text content to write to the file.

    Returns:
        str: Success message or error message string.
    """
    try:
        # Avoid path traversal by forcing filename to be a basename
        base_name = os.path.basename(filename)
        filepath = os.path.join(os.getcwd(), base_name)
        logger.info(f"Writing file '{base_name}' to path '{filepath}'")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
            
        logger.debug(f"File '{base_name}' successfully written.")
        return f"Successfully saved content to file '{base_name}'."
    except Exception as e:
        logger.error(f"Failed to write file '{filename}': {e}", exc_info=True)
        return f"Error writing file: {str(e)}"
