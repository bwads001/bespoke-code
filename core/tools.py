from pathlib import Path
import json
import logging
import shutil
from typing import Dict, Any, Optional
from .base import ToolResult, EnvironmentState, ErrorResult
from .verification import get_verification_strategy, verify_file_operation

logger = logging.getLogger(__name__)

class Tool:
    """Base class for tool operations."""
    
    def __init__(self, workspace_dir: Path, initial_temperature: Optional[float] = None):
        self.workspace_dir = workspace_dir
        self.environment = EnvironmentState(workspace_dir)

    def _ensure_workspace_path(self, path: str) -> Path:
        """Ensure the path is safe and within the workspace directory."""
        try:
            # Convert to path and normalize
            path_obj = Path(path)
            
            # Resolve any ./ or ../ in the path
            # But don't allow going above workspace root
            clean_parts = []
            for part in path_obj.parts:
                if part == '.' or part == '':
                    continue
                elif part == '..':
                    if clean_parts:
                        clean_parts.pop()
                    continue
                clean_parts.append(part)
            
            # Combine with workspace directory
            return self.workspace_dir.joinpath(*clean_parts)
            
        except Exception as e:
            raise ValueError(f"Invalid path: {e}")

    async def execute(self, operation: str, **kwargs) -> ToolResult:
        """Execute tool operation."""
        try:
            # Execute the operation
            result = await self._execute_operation(operation, **kwargs)
            
            # If write operation succeeded, verify file exists
            if operation == 'write_file' and result.success:
                path = self._ensure_workspace_path(kwargs['path'])
                verification = verify_file_operation(operation, path, {'should_exist': True})
                if not verification['matches_expected']:
                    return ToolResult(
                        success=False,
                        result=verification['details']['existence'],
                        diagnostics={'error': 'Verification failed'}
                    )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing {operation}: {e}")
            return ToolResult(
                success=False,
                result=f"Failed to execute {operation}: {str(e)}",
                diagnostics={'error': str(e)}
            )

    async def _execute_operation(self, operation: str, **kwargs) -> ToolResult:
        """Execute the actual tool operation."""
        raise NotImplementedError

    def _get_expected_state(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Get expected state after operation."""
        expected_state = {}
        
        if operation == 'write_file':
            expected_state = {
                'should_exist': True,
                'size': len(kwargs.get('content', '').encode())
            }
        elif operation == 'create_directory':
            expected_state = {
                'should_exist': True,
                'contents': kwargs.get('expected_contents', [])
            }
        elif operation == 'delete_file':
            expected_state = {
                'should_exist': False
            }
        
        return expected_state

class WriteFile(Tool):
    """Write file tool."""
    
    async def _execute_operation(self, operation: str, **kwargs) -> ToolResult:
        try:
            path = self._ensure_workspace_path(kwargs['path'])
            content = kwargs['content']
            
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            path.write_text(content)
            
            return ToolResult(
                success=True,
                result=f"Successfully wrote to {path}",
                affected_files=[str(path)]
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=f"Failed to write file: {str(e)}",
                diagnostics={'error': str(e)}
            )

class ReadFile(Tool):
    """Read file tool."""
    
    async def _execute_operation(self, operation: str, **kwargs) -> ToolResult:
        try:
            path = self._ensure_workspace_path(kwargs['path'])
            
            if not path.exists():
                return ToolResult(
                    success=False,
                    result=f"File {path} does not exist",
                    diagnostics={'error': 'FileNotFoundError'}
                )
            
            content = path.read_text()
            return ToolResult(
                success=True,
                result=content,
                affected_files=[str(path)]
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=f"Failed to read file: {str(e)}",
                diagnostics={'error': str(e)}
            )

class CreateDirectory(Tool):
    """Create directory tool."""
    
    async def _execute_operation(self, operation: str, **kwargs) -> ToolResult:
        try:
            path = self._ensure_workspace_path(kwargs['path'])
            path.mkdir(parents=True, exist_ok=True)
            
            return ToolResult(
                success=True,
                result=f"Successfully created directory {path}",
                affected_files=[str(path)]
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=f"Failed to create directory: {str(e)}",
                diagnostics={'error': str(e)}
            )

class DeleteFile(Tool):
    """Delete file tool."""
    
    async def _execute_operation(self, operation: str, **kwargs) -> ToolResult:
        try:
            path = self._ensure_workspace_path(kwargs['path'])
            
            if not path.exists():
                return ToolResult(
                    success=True,
                    result=f"File {path} already does not exist",
                    affected_files=[]
                )
            
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            
            return ToolResult(
                success=True,
                result=f"Successfully deleted {path}",
                affected_files=[str(path)]
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=f"Failed to delete file: {str(e)}",
                diagnostics={'error': str(e)}
            )

class SaveJson(Tool):
    """Save JSON tool."""
    
    async def _execute_operation(self, operation: str, **kwargs) -> ToolResult:
        try:
            path = self._ensure_workspace_path(kwargs['path'])
            data = kwargs['data']
            
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write JSON
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            return ToolResult(
                success=True,
                result=f"Successfully saved JSON to {path}",
                affected_files=[str(path)]
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=f"Failed to save JSON: {str(e)}",
                diagnostics={'error': str(e)}
            )

class LoadJson(Tool):
    """Load JSON tool."""
    
    async def _execute_operation(self, operation: str, **kwargs) -> ToolResult:
        try:
            path = Path(kwargs['path'])
            
            if not path.exists():
                return ToolResult(
                    success=False,
                    result=f"File {path} does not exist",
                    diagnostics={'error': 'FileNotFoundError'}
                )
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return ToolResult(
                success=True,
                result=data,
                affected_files=[str(path)]
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                result=f"Invalid JSON in {path}: {str(e)}",
                diagnostics={'error': 'JSONDecodeError', 'details': str(e)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=f"Failed to load JSON: {str(e)}",
                diagnostics={'error': str(e)}
            )

# Factory function to get the appropriate tool
def get_tool(operation: str, workspace_dir: Path) -> Optional[Tool]:
    """Get the appropriate tool for an operation."""
    tools = {
        'write_file': WriteFile,
        'read_file': ReadFile,
        'create_directory': CreateDirectory,
        'delete_file': DeleteFile,
        'save_json': SaveJson,
        'load_json': LoadJson
    }
    
    tool_class = tools.get(operation)
    if tool_class:
        return tool_class(workspace_dir)
    return None

async def execute_tool(response: str, workspace_dir: Path, conversation_history=None) -> str:
    """Parse and execute tool commands from an AI response."""
    if isinstance(response, ErrorResult):
        return response.format_message()

    import re
    # Match %%tool blocks
    tool_pattern = r'%%tool\s+(\w+)\s*\n%%path\s+([^\n]+)\s*\n(?:%%content\s*(.*?)\s*%%end|%%end)'
    matches = list(re.finditer(tool_pattern, response, re.DOTALL))
    
    if not matches:
        return response

    operation_results = []
    
    # Execute each tool command and show user feedback
    for match in matches:
        tool_name = match.group(1).strip()
        path = match.group(2).strip()
        content = match.group(3).strip() if match.group(3) else ""
        
        # Show friendly message to user
        from .utils import Colors
        print(f"\n{Colors.AI}Agent {tool_name.replace('_', ' ')}... ({path}){Colors.RESET}")
        
        try:
            tool = get_tool(tool_name, workspace_dir)
            if not tool:
                continue
                
            kwargs = {}
            if tool_name == 'write_file':
                kwargs = {
                    'path': path,
                    'content': content
                }
            elif tool_name in ['read_file', 'delete_file', 'create_directory']:
                kwargs = {'path': path}
            
            result = await tool.execute(tool_name, **kwargs)
            
            if result.success:
                print(f"{Colors.TOOL_OUTPUT}✓ {tool_name}: {result.result}{Colors.RESET}")
                if conversation_history and hasattr(conversation_history, 'environment_state'):
                    conversation_history.environment_state.record_operation(
                        operation=tool_name,
                        result=result
                    )
            else:
                error = ErrorResult(
                    error=f"Failed to execute {tool_name}: {result.result}",
                    suggestion="Please check the arguments and try again."
                )
                print(error.format_message())
            
            operation_results.append({
                'tool': tool_name,
                'success': result.success,
                'result': result.result
            })
            
        except Exception as e:
            error_msg = f"Error executing {tool_name}: {str(e)}"
            print(f"{Colors.ERROR}{error_msg}{Colors.RESET}")
            operation_results.append({
                'tool': tool_name,
                'success': False,
                'result': str(e)
            })
            continue
    
    # Return a concise summary for the agent
    successful_ops = [op for op in operation_results if op['success']]
    failed_ops = [op for op in operation_results if not op['success']]
    
    summary = []
    if successful_ops:
        summary.append(f"Successfully completed {len(successful_ops)} operations:")
        for op in successful_ops:
            summary.append(f"- {op['tool']}: {op['result']}")
    
    if failed_ops:
        summary.append(f"\nFailed {len(failed_ops)} operations:")
        for op in failed_ops:
            summary.append(f"- {op['tool']}: {op['result']}")
    
    return "\n".join(summary) if summary else response

async def execute_tools(self, response: str) -> ToolResult:
    """Execute tool commands found in the response."""
    from .tools import execute_tool  # Import here to avoid circular dependency
    
    try:
        modified_response = await execute_tool(
            response,
            self.workspace_dir,
            conversation_history=self.conversation_state
        )
        
        # If the response was modified (tools were executed), add a prompt for the agent
        if modified_response != response:
            modified_response += "\n\nWould you like me to do anything else with the file?"
        
        return ToolResult(
            success=True,
            result=modified_response
        )
    except Exception as e:
        return ToolResult(
            success=False,
            result=str(e)
        ) 