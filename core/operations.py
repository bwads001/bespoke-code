"""Operation result handling and tracking."""
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from .base import ToolResult, ErrorResult, EnvironmentState
from .utils import Colors, estimate_tokens

class OperationManager:
    """Manages operation results and tracking."""
    
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.environment_state = EnvironmentState(workspace_dir)
        self.operation_results: List[Dict[str, Any]] = []
        self.current_operation: Optional[str] = None
        
    def add_result(self, operation: str, result: ToolResult) -> None:
        """Add an operation result and update tracking."""
        self.current_operation = operation
        operation_result = {
            'tool': operation,
            'success': result.success,
            'result': result.result,
            'timestamp': datetime.now(),
            'affected_files': result.affected_files,
            'warnings': result.warnings,
            'diagnostics': result.diagnostics
        }
        
        self.operation_results.append(operation_result)
        self.environment_state.record_operation(operation, result)
        
        # Keep only recent results
        if len(self.operation_results) > 20:
            self.operation_results.pop(0)
    
    def format_result_summary(self, recent_count: int = 5) -> str:
        """Format a summary of recent operation results."""
        if not self.operation_results:
            return "No operations performed yet."
            
        summary = []
        recent_ops = self.operation_results[-recent_count:]
        
        for op in recent_ops:
            if op['success']:
                summary.append(f"{Colors.TOOL_OUTPUT}✓ {op['tool']}: {op['result']}{Colors.RESET}")
            else:
                summary.append(f"{Colors.ERROR}✗ {op['tool']}: {op['result']}{Colors.RESET}")
                if 'diagnostics' in op and 'error' in op['diagnostics']:
                    summary.append(f"  {Colors.ERROR}{op['diagnostics']['error']}{Colors.RESET}")
        
            status_color = Colors.SUCCESS if op['success'] else Colors.ERROR
            status = "Success" if op['success'] else "Failed"
            summary += f"- {op['tool']}: {status_color}{status}{Colors.RESET}\n"
            if not op['success'] and 'diagnostics' in op:
                if 'error' in op['diagnostics']:
                    summary += f"  {Colors.ERROR}Error: {op['diagnostics']['error']}{Colors.RESET}\n"
                if 'suggestion' in op['diagnostics']:
                    summary += f"  {Colors.LOG}Suggestion: {op['diagnostics']['suggestion']}{Colors.RESET}\n"
            
        # Add workspace state
        summary += f"\n{Colors.LOG}Workspace State:{Colors.RESET}\n"
        summary += f"- Files: {', '.join(self.environment_state.file_states.keys())}\n"
        summary += f"- Recent Operations: {', '.join(op['operation'] for op in self.environment_state.recent_operations[-5:])}\n"
        summary += f"- Available Space: {self.environment_state.workspace_state['space']['available']}\n"
        
        # Add suggestions if any
        suggestions = self.environment_state.get_operation_suggestions()
        if suggestions:
            summary += f"\n{Colors.LOG}Suggestions:{Colors.RESET}\n"
            for suggestion in suggestions:
                summary += f"- {suggestion}\n"
                
        return summary
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """Get statistics about operations."""
        return {
            'total_operations': len(self.operation_results),
            'success_rate': sum(1 for op in self.operation_results if op['success']) / max(1, len(self.operation_results)),
            'common_operations': self._get_common_operations(),
            'recent_warnings': [op['warnings'] for op in self.operation_results[-5:] if op['warnings']],
            'environment_stats': self.environment_state.operation_stats
        }
        
    def _get_common_operations(self) -> Dict[str, int]:
        """Get frequency count of operations."""
        operation_counts = {}
        for op in self.operation_results:
            tool = op['tool']
            operation_counts[tool] = operation_counts.get(tool, 0) + 1
        return operation_counts 