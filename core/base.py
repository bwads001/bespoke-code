"""Base classes for the tool operations and state management."""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import hashlib
import os
import shutil

@dataclass
class ErrorResult:
    """Standardized error result structure."""
    error: str
    suggestion: Optional[str] = None
    details: Optional[dict] = None
    
    def format_message(self) -> str:
        """Format the error message with colors and icons."""
        from .utils import Colors  # Import here to avoid circular dependency
        msg = [Colors.error(self.error)]
        if self.suggestion:
            msg.append(Colors.info(f"Suggestion: {self.suggestion}"))
        return "\n".join(msg)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for conversation history."""
        return {
            'error': self.error,
            'suggestion': self.suggestion,
            'details': self.details
        }

@dataclass
class ToolResult:
    """Result of a tool operation with verification and diagnostics."""
    success: bool
    result: str
    verification: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    rollback_info: Dict[str, Any] = field(default_factory=dict)
    temperature_info: Dict[str, Any] = field(default_factory=lambda: {
        'initial': 0.0,
        'final': 0.0,
        'adjustments': [],
        'effectiveness': None
    })

@dataclass
class FileState:
    """Represents the state of a file at a point in time."""
    path: Path
    exists: bool = False
    size: int = 0
    permissions: str = ""
    owner: str = ""
    checksum: str = ""
    last_modified: datetime = field(default_factory=datetime.now)
    is_directory: bool = False

    @classmethod
    def capture(cls, path: Path) -> 'FileState':
        """Capture the current state of a file."""
        state = cls(path=path)
        if path.exists():
            stat = path.stat()
            state.exists = True
            state.size = stat.st_size
            state.permissions = oct(stat.st_mode)[-3:]
            state.owner = str(stat.st_uid)
            state.last_modified = datetime.fromtimestamp(stat.st_mtime)
            state.is_directory = path.is_dir()
            if not state.is_directory:
                state.checksum = cls._calculate_checksum(path)
        return state

    @staticmethod
    def _calculate_checksum(path: Path) -> str:
        """Calculate SHA-256 checksum of a file."""
        try:
            sha256_hash = hashlib.sha256()
            with open(path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return ""

class EnvironmentState:
    """Manages the state of the workspace environment."""
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.workspace_state = {
            'permissions': {
                'user': str(os.getuid()) if hasattr(os, 'getuid') else '',
                'group': str(os.getgid()) if hasattr(os, 'getgid') else '',
                'umask': oct(os.umask(0o022))[2:] if hasattr(os, 'umask') else ''
            },
            'space': {
                'available': self._get_available_space(),
                'required': 0
            }
        }
        self.file_states: Dict[str, FileState] = {}
        self.recent_operations: List[Dict[str, Any]] = []
        self.operation_stats = {
            'success_count': 0,
            'failure_count': 0,
            'common_errors': {},
            'successful_patterns': set()
        }
        
    def record_operation(self, operation: str, result: ToolResult):
        """Record operation result and update stats."""
        self.recent_operations.append({
            'operation': operation,
            'success': result.success,
            'timestamp': datetime.now(),
            'affected_files': result.affected_files
        })
        
        if result.success:
            self.operation_stats['success_count'] += 1
            if len(result.affected_files) > 0:
                self.operation_stats['successful_patterns'].add(
                    (operation, Path(result.affected_files[0]).parent.name)
                )
        else:
            self.operation_stats['failure_count'] += 1
            error_type = result.diagnostics.get('error', 'unknown')
            self.operation_stats['common_errors'][error_type] = \
                self.operation_stats['common_errors'].get(error_type, 0) + 1
        
        # Keep only recent operations
        if len(self.recent_operations) > 20:
            self.recent_operations.pop(0)
            
    def get_operation_suggestions(self) -> List[str]:
        """Generate suggestions based on operation history."""
        suggestions = []
        
        # Suggest based on common successful patterns
        if self.operation_stats['successful_patterns']:
            common_dirs = [p[1] for p in self.operation_stats['successful_patterns']]
            suggestions.append(f"Consider using these directories: {', '.join(common_dirs)}")
        
        # Warn about common errors
        if self.operation_stats['common_errors']:
            common_error = max(self.operation_stats['common_errors'].items(), key=lambda x: x[1])
            suggestions.append(f"Watch out for {common_error[0]} errors, seen {common_error[1]} times")
        
        return suggestions

    def capture_file_state(self, path: Path) -> FileState:
        """Capture the state of a specific file."""
        state = FileState.capture(path)
        self.file_states[str(path)] = state
        return state

    def capture_workspace(self) -> Dict[str, FileState]:
        """Capture the state of all files in the workspace."""
        for path in self.workspace_dir.rglob('*'):
            if path.is_file() or path.is_dir():
                self.capture_file_state(path)
        return self.file_states

    def _get_available_space(self) -> int:
        """Get available space in workspace directory."""
        try:
            return shutil.disk_usage(self.workspace_dir).free
        except Exception:
            return 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            'workspace_state': self.workspace_state,
            'file_states': {
                str(k): {
                    'exists': v.exists,
                    'size': v.size,
                    'permissions': v.permissions,
                    'owner': v.owner,
                    'checksum': v.checksum,
                    'last_modified': v.last_modified.isoformat(),
                    'is_directory': v.is_directory
                }
                for k, v in self.file_states.items()
            }
        }

class TokenManager:
    """Manages token usage and context trimming with priority-based approach."""
    
    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens
        self.usage = {
            'system': 0,      # System prompt and instructions (never trimmed)
            'current': 0,     # Current prompt/response (never trimmed)
            'workspace': 0,   # Workspace state (includes operations, files, stats)
            'error': 0,       # Error context from exchanges
            'active': 0,      # Active conversation exchanges
            'history': 0,     # Older conversation history
            'context': 0      # Additional context files
        }
        
        # Priority order for trimming (highest to lowest)
        self.trim_priority = [
            'workspace',  # Workspace state (files, operations, stats)
            'error',     # Error context from exchanges
            'active',    # Recent/active exchanges
            'history',   # Older conversation history
            'context'    # Additional context files
        ]
    
    def update_usage(self, category: str, tokens: int):
        """Update token usage for a category."""
        self.usage[category] = tokens
    
    def get_total_used(self) -> int:
        """Get total tokens used across all categories."""
        return sum(self.usage.values())
    
    def get_available(self) -> int:
        """Get available tokens."""
        return max(0, self.max_tokens - self.get_total_used())
    
    def get_usage_stats(self) -> Dict[str, Dict[str, int]]:
        """Get detailed token usage statistics."""
        return {
            category: {
                'used': tokens,
                'available': self.max_tokens - self.get_total_used()
            }
            for category, tokens in self.usage.items()
        } 