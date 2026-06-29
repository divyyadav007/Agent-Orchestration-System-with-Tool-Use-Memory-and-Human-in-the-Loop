import os
from .registry import registry

@registry.register(
    name="save_file",
    description="Save text content to a file in the workspace directory.",
    parameter_schema={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "The name of the file to save (e.g. 'CEO_AI_Regulations_Brief.txt' or 'report.txt')"},
            "content": {"type": "string", "description": "The text content to write to the file"}
        },
        "required": ["filename", "content"]
    }
)
def save_file(filename: str, content: str) -> str:
    """
    Save the given content to a file in the current working directory.
    """
    try:
        # Avoid writing to system directories, write to current workspace directory
        # Just resolve filename relative to current working directory
        filepath = os.path.join(os.getcwd(), os.path.basename(filename))
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully saved content to file '{os.path.basename(filename)}'."
    except Exception as e:
        return f"Error writing file: {str(e)}"
