import os
from pathlib import Path
import json
import shutil
import logging

logger = logging.getLogger(__name__)

class Tools:
    def __init__(self, workspace_dir="./workspace"):
        """Initialize tools with a workspace directory."""
        self.workspace_dir = Path(workspace_dir).absolute()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized workspace at: {self.workspace_dir}")

    def write_file(self, filename: str, content: str) -> str:
        """
        Write content to a file in the workspace.
        
        Args:
            filename: Name of the file to write
            content: Content to write to the file
        Returns:
            str: Success/failure message
        """
        try:
            filepath = self.workspace_dir / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Wrote file: {filepath}")
            return f"Successfully wrote to {filename}"
        except Exception as e:
            logger.error(f"Error writing to {filepath}: {str(e)}")
            return f"Error writing to {filename}: {str(e)}"

    def read_file(self, filename: str) -> str:
        """
        Read content from a file in the workspace.
        
        Args:
            filename: Name of the file to read
        Returns:
            str: File content or error message
        """
        try:
            filepath = self.workspace_dir / filename
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading {filename}: {str(e)}"

    def list_files(self, path: str = ".") -> str:
        """
        List files in the specified workspace directory.
        
        Args:
            path: Relative path within workspace
        Returns:
            str: List of files and directories
        """
        try:
            target_path = self.workspace_dir / path
            files = list(target_path.glob('*'))
            return "\n".join(str(f.relative_to(self.workspace_dir)) for f in files)
        except Exception as e:
            return f"Error listing files: {str(e)}"

    def delete_file(self, filename: str) -> str:
        """
        Delete a file from the workspace.
        
        Args:
            filename: Name of the file to delete
        Returns:
            str: Success/failure message
        """
        try:
            filepath = self.workspace_dir / filename
            if filepath.is_file():
                filepath.unlink()
                return f"Successfully deleted {filename}"
            return f"File {filename} not found"
        except Exception as e:
            return f"Error deleting {filename}: {str(e)}"

    def create_directory(self, dirname: str) -> str:
        """
        Create a directory in the workspace.
        
        Args:
            dirname: Name of the directory to create
        Returns:
            str: Success/failure message
        """
        try:
            dirpath = self.workspace_dir / dirname
            dirpath.mkdir(parents=True, exist_ok=True)
            return f"Successfully created directory {dirname}"
        except Exception as e:
            return f"Error creating directory {dirname}: {str(e)}"

    def save_json(self, filename: str, data: dict) -> str:
        """
        Save data as JSON file.
        
        Args:
            filename: Name of the JSON file
            data: Dictionary to save
        Returns:
            str: Success/failure message
        """
        try:
            filepath = self.workspace_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return f"Successfully saved JSON to {filename}"
        except Exception as e:
            return f"Error saving JSON to {filename}: {str(e)}"

    def load_json(self, filename: str) -> dict:
        """
        Load data from JSON file.
        
        Args:
            filename: Name of the JSON file
        Returns:
            dict: Loaded JSON data or error message
        """
        try:
            filepath = self.workspace_dir / filename
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return f"Error loading JSON from {filename}: {str(e)}" 