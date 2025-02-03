"""Verification strategies for tool operations."""
from typing import Dict, Any, Callable
from pathlib import Path
import json
from .base import FileState, ToolResult

class VerificationError(Exception):
    """Raised when verification fails."""
    pass

def verify_file_operation(operation: str, path: Path, expected_state: Dict[str, Any]) -> Dict[str, Any]:
    """Verify a file operation based on expected state."""
    current_state = FileState.capture(path)
    verification = {
        'operation': operation,
        'path': str(path),
        'exists': current_state.exists,
        'matches_expected': True,
        'details': {}
    }

    if not current_state.exists and expected_state.get('should_exist', True):
        verification['matches_expected'] = False
        verification['details']['existence'] = 'File does not exist but should'
        return verification

    if current_state.exists and not expected_state.get('should_exist', True):
        verification['matches_expected'] = False
        verification['details']['existence'] = 'File exists but should not'
        return verification

    return verification

def verify_directory_operation(operation: str, path: Path, expected_state: Dict[str, Any]) -> Dict[str, Any]:
    """Verify a directory operation based on expected state."""
    verification = {
        'operation': operation,
        'path': str(path),
        'exists': path.exists(),
        'matches_expected': True,
        'details': {}
    }

    if not path.exists():
        verification['matches_expected'] = False
        verification['details']['existence'] = 'Directory does not exist'
        return verification

    if not path.is_dir():
        verification['matches_expected'] = False
        verification['details']['type'] = 'Path exists but is not a directory'
        return verification

    # Check permissions if specified
    if 'permissions' in expected_state:
        current_perms = oct(path.stat().st_mode)[-3:]
        perm_match = current_perms == expected_state['permissions']
        verification['details']['permissions'] = {
            'expected': expected_state['permissions'],
            'actual': current_perms,
            'matches': perm_match
        }
        verification['matches_expected'] &= perm_match

    # Check contents if specified
    if 'contents' in expected_state:
        current_contents = set(f.name for f in path.iterdir())
        expected_contents = set(expected_state['contents'])
        content_match = current_contents == expected_contents
        verification['details']['contents'] = {
            'expected': list(expected_contents),
            'actual': list(current_contents),
            'matches': content_match,
            'missing': list(expected_contents - current_contents),
            'unexpected': list(current_contents - expected_contents)
        }
        verification['matches_expected'] &= content_match

    return verification

class VerificationStrategy:
    """Base class for verification strategies."""
    
    @staticmethod
    def verify_write_file(path: Path, expected_state: Dict[str, Any]) -> Dict[str, Any]:
        """Verify write file operation."""
        return verify_file_operation('write_file', path, expected_state)

    @staticmethod
    def verify_read_file(result: ToolResult, path: Path) -> Dict[str, Any]:
        """Verify read file operation."""
        verification = {
            'operation': 'read_file',
            'path': str(path),
            'success': False,
            'details': {}
        }

        if not path.exists():
            verification['details']['error'] = 'File does not exist'
            return verification

        if not path.is_file():
            verification['details']['error'] = 'Path exists but is not a file'
            return verification

        try:
            # Verify we can actually read the file
            with open(path, 'r') as f:
                f.read()
            verification['success'] = True
        except Exception as e:
            verification['details']['error'] = f'Failed to read file: {str(e)}'

        return verification

    @staticmethod
    def verify_create_directory(path: Path, expected_state: Dict[str, Any]) -> Dict[str, Any]:
        """Verify directory creation."""
        return verify_directory_operation('create_directory', path, expected_state)

    @staticmethod
    def verify_delete_file(path: Path) -> Dict[str, Any]:
        """Verify file deletion."""
        verification = {
            'operation': 'delete_file',
            'path': str(path),
            'success': True,
            'details': {}
        }

        if path.exists():
            verification['success'] = False
            verification['details']['error'] = 'File still exists after deletion'

        return verification

    @staticmethod
    def verify_save_json(path: Path, expected_state: Dict[str, Any]) -> Dict[str, Any]:
        """Verify JSON save operation."""
        verification = {
            'operation': 'save_json',
            'path': str(path),
            'success': False,
            'details': {}
        }

        if not path.exists():
            verification['details']['error'] = 'File does not exist'
            return verification

        try:
            # Verify file contains valid JSON
            with open(path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            
            verification['success'] = True
            
            # If expected data structure provided, verify it matches
            if 'data' in expected_state:
                expected_data = expected_state['data']
                verification['details']['structure_matches'] = saved_data == expected_data
                if not verification['details']['structure_matches']:
                    verification['success'] = False
                    verification['details']['error'] = 'Saved JSON does not match expected structure'
                
        except json.JSONDecodeError as e:
            verification['details']['error'] = f'Invalid JSON format: {str(e)}'
        except Exception as e:
            verification['details']['error'] = f'Failed to verify JSON: {str(e)}'

        return verification

    @staticmethod
    def verify_load_json(result: ToolResult, path: Path) -> Dict[str, Any]:
        """Verify JSON load operation."""
        verification = {
            'operation': 'load_json',
            'path': str(path),
            'success': False,
            'details': {}
        }

        if not path.exists():
            verification['details']['error'] = 'File does not exist'
            return verification

        try:
            # Verify file contains valid JSON
            with open(path, 'r', encoding='utf-8') as f:
                json.load(f)
            verification['success'] = True
        except json.JSONDecodeError as e:
            verification['details']['error'] = f'Invalid JSON format: {str(e)}'
        except Exception as e:
            verification['details']['error'] = f'Failed to verify JSON: {str(e)}'

        return verification

def get_verification_strategy(operation: str) -> Callable:
    """Get the appropriate verification strategy for an operation."""
    strategies = {
        'write_file': VerificationStrategy.verify_write_file,
        'read_file': VerificationStrategy.verify_read_file,
        'create_directory': VerificationStrategy.verify_create_directory,
        'delete_file': VerificationStrategy.verify_delete_file,
        'save_json': VerificationStrategy.verify_save_json,
        'load_json': VerificationStrategy.verify_load_json
    }
    return strategies.get(operation) 