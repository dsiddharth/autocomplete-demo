import time
import re
from typing import List, Optional, NamedTuple
import httpx

class CompletionResult(NamedTuple):
    completions: List[str]
    latency_ms: float

class AutocompleteService:
    def __init__(self, model_service_url: str = "http://localhost:8000"):
        """Initialize the autocomplete service"""
        self.model_service_url = model_service_url
        self.client = httpx.AsyncClient(timeout=30.0)  # 30 second timeout
        
        # Simple cache for common completions
        self.completion_cache = {}
        self.max_cache_size = 1000
        
    def clean_input(self, text: str) -> str:
        """Clean and prepare input text"""
        # Remove excessive whitespace but preserve structure
        text = re.sub(r'\s+', ' ', text.strip())
        return text
        
    async def get_completion(self, text: str, max_suggestions: int = 1) -> CompletionResult:
        """Get autocomplete suggestions for the given text"""
        if not text.strip():
            return CompletionResult([], 0.0)
        
        # Clean input
        clean_text = self.clean_input(text)
        
        # Check cache first
        cache_key = clean_text.lower()
        if cache_key in self.completion_cache:
            return CompletionResult(self.completion_cache[cache_key], 0.0)
        
        # Limit context length to avoid performance issues
        max_context = 512  # Half of model's max length for safety
        if len(clean_text.split()) > max_context:
            words = clean_text.split()
            clean_text = ' '.join(words[-max_context:])
        
        try:
            start_time = time.time()
            
            # Make request to vLLM server
            response = await self.client.post(
                f"{self.model_service_url}/v1/completions",
                json={
                    "prompt": clean_text,
                    "max_tokens": 5,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 50,
                    "n": max_suggestions,
                    "stop": ["\n", ".", "!", "?", ";", ":", ","]
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Model service returned error: {response.text}")
            
            result = response.json()
            completions = [choice["text"] for choice in result["choices"]]
            
            inference_time = time.time() - start_time
            latency_ms = inference_time * 1000  # Convert to milliseconds
            
            # Cache the result
            if len(self.completion_cache) < self.max_cache_size:
                self.completion_cache[cache_key] = completions
            
            return CompletionResult(completions, latency_ms)
            
        except Exception as e:
            print(f"Error generating completion: {e}")
            return CompletionResult([], 0.0)
        
async def main():
    """Demo the autocomplete service"""
    print("Initializing autocomplete service...")
    autocomplete = AutocompleteService()
    
        # Demo examples
    test_prompts = [
        "The weather today is",
        "I need to buy",
        "Python is a programming language that",
        "The capital of France",
        "Machine learning is"
    ]
    
    print("\n" + "="*50)
    print("AUTOCOMPLETE DEMO")
    print("="*50)
    
    for prompt in test_prompts:
        print(f"\nInput: '{prompt}'")
        
        # Single completion
        result = await autocomplete.get_completion(prompt)
        print(f"Completion: '{result.completions[0] if result.completions else ''}'")
        print(f"Latency: {result.latency_ms:.2f}ms")
        print(f"Full text: '{prompt}{result.completions[0] if result.completions else ''}'")
        
        # Multiple suggestions
        result = await autocomplete.get_completion(prompt, max_suggestions=3)
        if len(result.completions) > 1:
            print("Alternative suggestions:")
            for i, suggestion in enumerate(result.completions[1:], 1):
                print(f"  {i}: '{suggestion}'")
    
    # Interactive mode
    print("\n" + "="*50)
    print("INTERACTIVE MODE (type 'quit' to exit)")
    print("="*50)
    
    while True:
        try:
            user_input = input("\nEnter text for completion: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if user_input:
                result = await autocomplete.get_completion(user_input)
                print(f"Suggested completion: '{result.completions[0] if result.completions else ''}'")
                print(f"Latency: {result.latency_ms:.2f}ms")
                print(f"Full text: '{user_input}{result.completions[0] if result.completions else ''}'")
            
        except KeyboardInterrupt:
            break
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())