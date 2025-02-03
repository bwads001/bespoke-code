"""Ollama API client using official Python client."""
import logging
from typing import AsyncGenerator
from ollama import AsyncClient
from ollama import ResponseError

logger = logging.getLogger(__name__)

class OllamaClient:
    """Client for interacting with Ollama API using official SDK."""
    
    def __init__(self, base_url: str, model_name: str):
        # Ensure base URL doesn't have trailing slash
        cleaned_url = base_url.rstrip('/')
        self.client = AsyncClient(host=cleaned_url)
        self.model_name = model_name
        logger.info(f"Initialized Ollama client for model: {model_name}")
        
    async def generate_text(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Generate text using the Ollama API with official client."""
        try:
            response = await self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    'num_predict': max_tokens,
                    'temperature': temperature,
                },
                stream=stream
            )
            
            async for chunk in response:
                if chunk.get('done', False):
                    break
                yield chunk.get('response', '')
                
        except ResponseError as e:
            logger.error(f"Ollama API Error: {e.error}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise 