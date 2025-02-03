"""Interactive mode for the code assistant."""
from pathlib import Path
import logging
from typing import Optional
from .token_management import ConversationState, format_workspace_state
from .operations import OperationManager
from .api import OllamaClient
from .utils import Colors
from config.config import (
    OLLAMA_URL,
    MODEL_NAME,
    DEFAULT_TEMPERATURE,
    GENERATION_MAX_TOKENS
)
from config.prompts import SYSTEM_PROMPT, TOOL_INSTRUCTIONS
from .base import ToolResult

logger = logging.getLogger(__name__)

MAX_AGENT_TOOL_LOOPS = 25

class InteractiveSession:
    """Manages an interactive session with the code assistant."""
    
    def __init__(self, workspace_dir: Path, temperature: float = DEFAULT_TEMPERATURE):
        self.workspace_dir = workspace_dir
        self.temperature = temperature
        self.conversation_state = ConversationState(workspace_dir)
        self.operation_manager = OperationManager(workspace_dir)
        self.api_client = OllamaClient(OLLAMA_URL, MODEL_NAME)
        
    async def process_input(self, user_input: str, context: str = "") -> None:
        """Process user input and generate response."""
        try:
            # Capture workspace state before operation
            self.operation_manager.environment_state.capture_workspace()
            
            # Initialize loop counter for agent-tool interactions
            loop_count = 0
            last_response = None
            
            while loop_count < MAX_AGENT_TOOL_LOOPS:
                # Ensure workspace state is current
                self.operation_manager.environment_state.capture_workspace()
                workspace_state = format_workspace_state(self.operation_manager.environment_state)
                
                # Build conversation history with validation
                history = []
                for exchange in self.conversation_state.exchanges[-5:]:
                    if not isinstance(exchange, dict):
                        logger.warning(f"Invalid exchange format: {exchange}")
                        continue
                    history.append(f"User: {exchange.get('user', 'No user input')}")
                    history.append(f"Assistant: {exchange.get('assistant', 'No assistant response')}")
                    if exchange.get('result'):
                        history.append(f"Result: {exchange['result']}")
                    if exchange.get('operation'):
                        history.append(f"Operation: {exchange['operation']}")
                history_text = "\n".join(history) if history else "No conversation history"
                
                # Construct the full prompt with validated components
                if loop_count == 0:
                    current_input = f"""{SYSTEM_PROMPT}

{TOOL_INSTRUCTIONS}

Current Workspace State:
{workspace_state}

Context Files:
{context if context else "No additional context provided"}

Conversation History:
{history_text}

User Request:
{user_input}"""
                else:
                    # Ensure last_response has content
                    if not last_response:
                        last_response = "No previous operation results"
                    
                    current_input = f"""{SYSTEM_PROMPT}

{TOOL_INSTRUCTIONS}

Previous Operation Results:
{last_response}

Current Task Context:
- Original Request: {user_input}
- Current State: {workspace_state}
- Available Context: {context if context else "No additional context"}

Conversation History:
{history_text}

Remember:
1. Always start responses with 🤖
2. If tools were just executed, provide ONLY a brief summary of what was done and ask if anything else is needed
3. If continuing with a task, use tool commands for any file operations
4. Keep responses focused and concise"""
                
                # Generate agent response
                try:
                    full_response = ""
                    print(f"\n{Colors.AI}> ", end='', flush=True)  # Start AI response line
                    async for chunk in self.api_client.generate_text(
                        current_input,
                        max_tokens=GENERATION_MAX_TOKENS,
                        temperature=self.temperature
                    ):
                        print(chunk, end='', flush=True)  # Stream each chunk
                        full_response += chunk
                    
                    if not full_response:
                        break
                    
                    # Execute tools and get operation results
                    tool_result = await self._execute_tools(full_response)
                    
                    # Update conversation state with exchange
                    if isinstance(tool_result, ToolResult):
                        self.conversation_state.add_exchange(
                            user_input=user_input,
                            assistant_response=full_response,
                            operation_result=tool_result.result,
                            operation=self.operation_manager.current_operation if self.operation_manager.current_operation else "Tool Execution"
                        )
                    else:
                        # Handle non-tool responses
                        self.conversation_state.add_exchange(
                            user_input=user_input,
                            assistant_response=full_response,
                            operation_result="No tool executed"
                        )
                    
                    # Update workspace state capture
                    self.operation_manager.environment_state.capture_workspace()
                    
                    # Increment loop counter
                    loop_count += 1
                    if loop_count >= MAX_AGENT_TOOL_LOOPS:
                        print(f"\n{Colors.WARNING}Maximum number of agent-tool interactions ({MAX_AGENT_TOOL_LOOPS}) reached.{Colors.RESET}")
                        return
                    
                    # If no tools were found in the response, we're done
                    if tool_result is None:
                        return
                    
                    # After tool execution
                    if not hasattr(tool_result, 'success') or not hasattr(tool_result, 'result'):
                        logger.error(f"Invalid tool result format: {type(tool_result)}")
                        print(f"{Colors.ERROR}Invalid tool response format{Colors.RESET}")
                        return

                    # Handle tool success/failure
                    if tool_result.success:
                        # Build a more comprehensive last_response with operation context
                        last_response = f"""Previous Operation Complete ✓
Operation: {self.operation_manager.current_operation if self.operation_manager.current_operation else 'Tool Execution'}
Status: Success - No further action needed
Result: {tool_result.result}
Note: This operation has completed successfully. Unless the user has requested additional actions, no further tool calls are needed."""
                    else:
                        print(f"\n{Colors.ERROR}Tool execution failed: {tool_result.result}{Colors.RESET}")
                        # Include error context in last_response
                        last_response = f"""Last Operation Results:
Operation: {self.operation_manager.current_operation if self.operation_manager.current_operation else 'Tool Execution'}
Status: Failed
Error: {tool_result.result}
Details: {tool_result.diagnostics.get('error', 'No additional details')}
"""
                        break
                    
                except Exception as e:
                    logger.error(f"Error processing input: {e}")
                    print(f"\n{Colors.ERROR}Error: {str(e)}{Colors.RESET}")
                    break
            
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            print(f"\n{Colors.ERROR}Error: {str(e)}{Colors.RESET}")
    
    async def _execute_tools(self, response: str) -> Optional[ToolResult]:
        """Execute tool commands found in the response."""
        from .tools import execute_tool  # Import here to avoid circular dependency
        
        result = await execute_tool(
            response,
            self.workspace_dir,
            conversation_history=self.conversation_state
        )
        
        # If no tools were found, execute_tool returns None
        if result is None:
            return None
        
        # If we got a string result, tools were executed successfully
        if isinstance(result, str):
            return ToolResult(
                success=True,
                result=result
            )
            
        return result if hasattr(result, 'result') else ToolResult(
            success=False,
            result=str(result)
        )

async def interactive_mode(context: str = "", temperature: float = DEFAULT_TEMPERATURE):
    """Run an interactive conversation session."""
    workspace_dir = Path("./workspace")
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    session = InteractiveSession(workspace_dir, temperature)
    
    print(f"\n{Colors.LOG}Entering interactive mode. Type 'exit' or 'quit' to end the session.")
    print(f"Type 'clear' to clear conversation history.{Colors.RESET}")
    print("----------------------------------------")
    
    while True:
        try:
            print(f"\n{Colors.USER}> {Colors.RESET}", end='', flush=True)
            user_input = input().strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit']:
                break
                
            if user_input.lower() == 'clear':
                session = InteractiveSession(workspace_dir, temperature)
                print(f"{Colors.LOG}Conversation history cleared.{Colors.RESET}")
                continue
            
            await session.process_input(user_input, context)
            
        except KeyboardInterrupt:
            print(f"\n{Colors.LOG}Generation cancelled.{Colors.RESET}")
            continue
            
        except Exception as e:
            print(f"\n{Colors.ERROR}Error: {str(e)}{Colors.RESET}")
            continue 