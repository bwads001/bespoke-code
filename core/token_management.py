"""Token management and conversation state handling."""
from typing import Dict, List, Optional, Any
from pathlib import Path
from .base import EnvironmentState, TokenManager
from .utils import estimate_tokens
from config.config import MODEL_MAX_TOKENS
from config.prompts import SYSTEM_PROMPT, TOOL_INSTRUCTIONS
from datetime import datetime, timedelta

def get_total_prompt_tokens(prompt: str, context: str, conversation_history) -> int:
    """Calculate total tokens in the full prompt."""
    total = 0
    
    # System components
    total += estimate_tokens(SYSTEM_PROMPT + TOOL_INSTRUCTIONS)
    
    # Current prompt
    total += estimate_tokens(prompt)
    
    # Workspace state
    if hasattr(conversation_history, 'environment_state'):
        total += get_workspace_state_tokens(conversation_history.environment_state)
    
    # Context files
    if context:
        total += estimate_tokens(context)
    
    # Operation history
    if hasattr(conversation_history, 'operation_history'):
        total += get_operation_history_tokens(conversation_history.operation_history)
    
    return total

def get_workspace_state_tokens(env_state: EnvironmentState) -> int:
    """Calculate tokens for workspace state."""
    workspace_text = format_workspace_state(env_state)
    return estimate_tokens(workspace_text)

def get_operation_history_tokens(history: List[Dict]) -> int:
    """Calculate tokens for operation history."""
    history_text = "\n".join(f"- {op.goal}: {op.status}" for op in history[-3:])
    return estimate_tokens(history_text)

def format_workspace_state(env_state: EnvironmentState) -> str:
    """Format workspace state focusing on relevant files."""
    # Files/folders to ignore
    IGNORE_PATTERNS = {
        '.git', '.gitignore', 'node_modules', '__pycache__', 
        '.vscode', '.idea', '.env', 'venv', 'env',
        '.DS_Store', '*.pyc', '*.pyo', '*.pyd', '*.so'
    }

    def should_include_file(path: str) -> bool:
        """Check if file should be included in state."""
        path_parts = Path(path).parts
        return not any(
            ignore in path_parts or any(p.endswith(ignore) for p in path_parts)
            for ignore in IGNORE_PATTERNS
        )

    # Filter and categorize files
    active_files = []
    other_files = []
    
    for file_path, state in env_state.file_states.items():
        if not should_include_file(file_path):
            continue
            
        if state.last_modified > (datetime.now() - timedelta(minutes=30)):
            active_files.append(file_path)
        else:
            other_files.append(file_path)
    
    # Format the state output, prioritizing most relevant info
    state_lines = []
    
    # Most important: Recently modified files
    if active_files:
        state_lines.append("Active Files (Last 30 min):")
        state_lines.extend(f"  - {f}" for f in sorted(active_files))
        state_lines.append("")  # Add spacing
    
    # Recent operations (last 3)
    recent_ops = [op['operation'] for op in env_state.recent_operations[-3:]]
    if recent_ops:
        state_lines.append("Recent Operations:")
        state_lines.extend(f"  - {op}" for op in recent_ops)
        state_lines.append("")  # Add spacing
    
    # Less important: Other files
    if other_files:
        state_lines.append("Other Workspace Files:")
        state_lines.extend(f"  - {f}" for f in sorted(other_files[:5]))
        if len(other_files) > 5:
            state_lines.append(f"  ... and {len(other_files) - 5} more")
    
    if not state_lines:  # If no files at all
        state_lines = ["Workspace: (Empty)"]
    else:
        state_lines.insert(0, "Workspace State:")  # Add title at the very top
    
    return "\n".join(state_lines)

class ConversationState:
    """Manages the full state of a conversation including environment and history."""
    def __init__(self, workspace_dir: Path):
        self.environment_state = EnvironmentState(workspace_dir)
        self.operation_history = []
        self.exchanges = []
        self.token_manager = TokenManager(MODEL_MAX_TOKENS)
    
    def add_exchange(self, user_input: str, assistant_response: str, operation_result: Optional[Dict | str] = None, operation: Optional[str] = None):
        """Add a conversation exchange with optional operation results."""
        exchange = {
            'user': user_input,
            'assistant': assistant_response,
            'result': operation_result,
            'operation': operation
        }
        
        # Calculate tokens for this exchange
        exchange_tokens = estimate_tokens(
            f"User: {user_input}\nAssistant: {assistant_response}"
        )
        if operation_result:
            if isinstance(operation_result, dict):
                exchange_tokens += estimate_tokens(
                    f"\nError Details: {operation_result.get('error', '')}"
                    f"\nSuggested Fix: {operation_result.get('suggestion', '')}"
                )
            else:
                exchange_tokens += estimate_tokens(f"\nResult: {operation_result}")
        if operation:
            exchange_tokens += estimate_tokens(f"\nOperation: {operation}")
        
        self._trim_history_for_tokens(exchange_tokens)
        self.exchanges.append(exchange)
        self._update_history_tokens()
    
    def add_operation_result(self, result: Dict[str, Any]):
        """Add operation result with token management."""
        result_tokens = estimate_tokens(str(result))
        self._trim_operations_for_tokens(result_tokens)
        self.operation_history.append(result)
        self._update_operation_tokens()
    
    def _trim_history_for_tokens(self, required_tokens: int):
        """Trim history using priority-based strategy."""
        while (self.token_manager.get_available() < required_tokens
               and self.exchanges):
            # Don't trim if we only have active exchanges
            if len(self.exchanges) <= 3:
                break
            
            # Find oldest non-error exchange that's not in last 3
            candidate = None
            for ex in self.exchanges[:-3]:  # Skip last 3 (active)
                if not ex.get('result', {}).get('error'):
                    candidate = ex
                    break
            
            if candidate:
                self.exchanges.remove(candidate)
            else:
                # If no candidate, remove oldest exchange that's not an error
                for ex in self.exchanges[:-3]:
                    if not ex.get('result', {}).get('error'):
                        self.exchanges.remove(ex)
                        break
                else:
                    # If still no candidate, we can only remove from active
                    self.exchanges.pop(0)
            
            self.update_token_counts()
    
    def _trim_operations_for_tokens(self, required_tokens: int):
        """Trim operations using priority-based strategy."""
        while (self.token_manager.get_available() < required_tokens
               and self.operation_history):
            # Identify high-priority operations
            error_ops = [op for op in self.operation_history if not op.get('success', True)]
            active_ops = self.operation_history[-3:]  # Keep last 3 as active
            
            # Find a candidate for removal that's not in high-priority categories
            candidate = None
            for op in self.operation_history:
                if (op not in error_ops and 
                    op not in active_ops):
                    candidate = op
                    break
            
            if candidate:
                self.operation_history.remove(candidate)
                self._update_operation_tokens()
            else:
                # If no non-priority candidates, start removing from oldest error ops
                if error_ops and len(error_ops) > 1:
                    self.operation_history.remove(error_ops[0])
                elif len(self.operation_history) > 3:
                    self.operation_history.pop(0)
                else:
                    break  # Keep minimum of 3 operations
    
    def _update_history_tokens(self):
        """Update token count for conversation history."""
        history_tokens = sum(
            estimate_tokens(f"User: {ex['user']}\nAssistant: {ex['assistant']}")
            for ex in self.exchanges
        )
        self.token_manager.update_usage('history', history_tokens)
    
    def _update_operation_tokens(self):
        """Update token count for operation history."""
        operation_tokens = sum(
            estimate_tokens(str(op))
            for op in self.operation_history
        )
        self.token_manager.update_usage('operation', operation_tokens)
    
    def update_token_counts(self):
        """Update all token counts."""
        # Update workspace state first (highest priority)
        workspace_text = format_workspace_state(self.environment_state)
        self.token_manager.update_usage('workspace', estimate_tokens(workspace_text))
        
        # Update conversation history categories
        error_exchanges = [ex for ex in self.exchanges if ex.get('result', {}).get('error')]
        active_exchanges = self.exchanges[-3:] if len(self.exchanges) > 3 else self.exchanges
        older_exchanges = [ex for ex in self.exchanges if ex not in error_exchanges and ex not in active_exchanges]
        
        self.token_manager.update_usage('error', sum(
            estimate_tokens(str(ex)) for ex in error_exchanges
        ))
        self.token_manager.update_usage('active', sum(
            estimate_tokens(str(ex)) for ex in active_exchanges
        ))
        self.token_manager.update_usage('history', sum(
            estimate_tokens(str(ex)) for ex in older_exchanges
        ))
    
    def get_token_usage(self) -> Dict[str, Dict[str, int]]:
        """Get detailed token usage statistics."""
        return self.token_manager.get_usage_stats()

    def update_workspace_state(self):
        """Update workspace state with smart file selection."""
        # Get active files from recent operations
        active_files = set()
        for op in self.environment_state.recent_operations[-5:]:
            active_files.update(op.get('affected_files', []))
        
        # Add files from current context
        if hasattr(self, 'current_context_files'):
            active_files.update(self.current_context_files)
        
        # Keep important files regardless of activity
        important_files = {
            path for path, state in self.environment_state.file_states.items()
            if any([
                path in active_files,  # Currently active
                state.last_modified > (datetime.now() - timedelta(minutes=30)),  # Recently modified
                path.endswith(('.py', '.json', '.md', 'requirements.txt'))  # Important file types
            ])
        }
        
        # Remove files not in important set
        for file_path in list(self.environment_state.file_states.keys()):
            if file_path not in important_files:
                del self.environment_state.file_states[file_path]
        
        # Update token count
        workspace_text = format_workspace_state(self.environment_state)
        self.token_manager.update_usage('workspace', estimate_tokens(workspace_text)) 