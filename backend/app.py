from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import torch
from transformers import pipeline
import time
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set environment variables for better M1 performance
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"  # Enable fallback for operations not supported by MPS
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"  # Disable high watermark to prevent memory issues

app = FastAPI()

# Enable CORS with optimized settings for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Initialize model
MODEL_NAME = "microsoft/phi-2"  # Using smaller model

# Check for MPS availability
if torch.backends.mps.is_available():
    device = "mps"
    logger.info("Using MPS (Metal Performance Shaders) for acceleration")
elif torch.cuda.is_available():
    device = "cuda"
    logger.info("Using CUDA for acceleration")
else:
    device = "cpu"
    logger.info("Using CPU for inference")

logger.info(f"Loading model {MODEL_NAME}...")
try:
    generator = pipeline(
        "text-generation",
        model=MODEL_NAME,
        model_kwargs={
            "torch_dtype": torch.float16 if device == "cuda" else torch.float32,
            "low_cpu_mem_usage": True,
            "device_map": device,
            "load_in_8bit": True if device == "cuda" else False,  # Enable 8-bit quantization for CUDA
        },
        device_map=device
    )
    logger.info("Model loaded successfully!")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    raise

class CompletionRequest(BaseModel):
    text: str
    system_prompt: str = "You are an autocomplete assistant. Your task is to suggest ONLY the next few words that would naturally complete the user's text. IMPORTANT: Do not start suggestions with phrases like 'Based on', 'I would', 'You should', or any other filler words. Get straight to the point with the actual continuation. Do not add any context, explanations, or new sentences. Return only the direct continuation of the existing text. Keep suggestions concise and focused on completing the current thought."
    max_tokens: int = 5
    num_suggestions: int = 3
    temperature: float = 0.1

class CompletionResponse(BaseModel):
    suggestions: List[str]
    latency_ms: float
    server_processing_time_ms: float

@app.post("/api/complete", response_model=CompletionResponse)
async def get_completion(request: CompletionRequest):
    try:
        logger.info(f"Received completion request for text: {request.text[:50]}...")
        request_start_time = time.time()
        
        # Prepare messages for the model
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.text}
        ]
        
        # Generate completions
        generation_start_time = time.time()
        with torch.inference_mode():  # More efficient than no_grad for inference
            outputs = generator(
                messages,
                max_new_tokens=request.max_tokens,
                num_return_sequences=request.num_suggestions,
                temperature=request.temperature,
                do_sample=True,
                repetition_penalty=1.1,  # Reduced from 1.2
                no_repeat_ngram_size=2,  # Reduced from 3
                top_k=20,  # Reduced from 50
                top_p=0.95,  # Increased from 0.9
                early_stopping=True,  # Added early stopping
                pad_token_id=generator.tokenizer.eos_token_id  # Added explicit padding
            )
        
        # Process suggestions
        suggestions = []
        for output in outputs:
            # Extract only the new generated text
            generated_text = output["generated_text"][-1]["content"]
            # Remove any potential filler words at the start
            generated_text = generated_text.strip()
            suggestions.append(generated_text)
        
        generation_time = (time.time() - generation_start_time) * 1000  # Convert to milliseconds
        total_latency = (time.time() - request_start_time) * 1000  # Convert to milliseconds
        
        logger.info(f"Generated {len(suggestions)} suggestions in {generation_time:.2f}ms (total latency: {total_latency:.2f}ms)")
        
        return CompletionResponse(
            suggestions=suggestions,
            latency_ms=total_latency,
            server_processing_time_ms=generation_time
        )
    
    except Exception as e:
        logger.error(f"Error generating completion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",  # Use localhost instead of 0.0.0.0
        port=8000,
        loop="uvloop",  # Use uvloop for better performance
        http="httptools",  # Use httptools for better performance
        workers=1  # Single worker for local development
    ) 