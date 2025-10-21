"""Ollama HTTP client for AI model interactions"""

import httpx
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
import asyncio
import os


class OllamaClient:
    """HTTP client for Ollama API"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 300,
        use_cloud: bool = True
    ):
        """
        Initialize Ollama client
        
        Args:
            base_url: Ollama API base URL (default: from env or localhost)
            timeout: Request timeout in seconds
            use_cloud: Use cloud endpoint for large models
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.timeout = timeout
        self.use_cloud = use_cloud
        
        # HTTP client with timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout)
        )
        
        print(f"🤖 Ollama client initialized: {self.base_url}")
    
    async def generate(
        self,
        model: str,
        prompt: str,
        images: Optional[List[str]] = None,
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate response from Ollama model
        
        Args:
            model: Model name (e.g., 'qwen3-vl:235b-cloud')
            prompt: Text prompt
            images: List of base64-encoded images
            stream: Whether to stream response
            options: Additional model options
        
        Returns:
            Model response as dict
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream
        }
        
        if images:
            payload["images"] = images
        
        if options:
            payload["options"] = options
        
        print(f"📡 Sending request to Ollama: {model}")
        print(f"   Prompt length: {len(prompt)} chars")
        if images:
            print(f"   Images: {len(images)}")
        
        try:
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ Received response from Ollama")
            
            return result
            
        except httpx.TimeoutException:
            print(f"⏱️  Ollama request timed out after {self.timeout}s")
            raise RuntimeError(f"Ollama request timed out after {self.timeout}s")
        except httpx.HTTPStatusError as e:
            print(f"❌ Ollama HTTP error: {e.response.status_code}")
            raise RuntimeError(f"Ollama HTTP error: {e.response.text}")
        except Exception as e:
            print(f"❌ Ollama request failed: {e}")
            raise
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Chat completion with Ollama model
        
        Args:
            model: Model name
            messages: List of chat messages
            stream: Whether to stream response
            options: Additional model options
        
        Returns:
            Chat response
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        
        if options:
            payload["options"] = options
        
        try:
            response = await self.client.post("/api/chat", json=payload)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"❌ Ollama chat request failed: {e}")
            raise
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models"""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            
            data = response.json()
            return data.get("models", [])
            
        except Exception as e:
            print(f"❌ Failed to list models: {e}")
            return []
    
    async def pull_model(self, model: str) -> bool:
        """
        Pull/download a model
        
        Args:
            model: Model name to pull
        
        Returns:
            True if successful
        """
        payload = {"name": model}
        
        try:
            print(f"📥 Pulling model: {model}")
            response = await self.client.post("/api/pull", json=payload)
            response.raise_for_status()
            
            print(f"✅ Model pulled: {model}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to pull model: {e}")
            return False
    
    async def check_model(self, model: str) -> bool:
        """
        Check if model is available
        
        Args:
            model: Model name
        
        Returns:
            True if model is available
        """
        models = await self.list_models()
        return any(m.get("name") == model for m in models)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    @staticmethod
    def encode_image_to_base64(image_path: Path) -> str:
        """
        Encode image file to base64 string
        
        Args:
            image_path: Path to image file
        
        Returns:
            Base64-encoded image string
        """
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        return base64.b64encode(image_bytes).decode("utf-8")
    
    @staticmethod
    def encode_numpy_to_base64(image_array) -> str:
        """
        Encode numpy array to base64 string
        
        Args:
            image_array: Numpy array (H, W, 3) uint8
        
        Returns:
            Base64-encoded image string
        """
        from PIL import Image
        from io import BytesIO
        
        # Convert numpy to PIL Image
        pil_image = Image.fromarray(image_array.astype('uint8'))
        
        # Encode to PNG bytes
        buffer = BytesIO()
        pil_image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
        
        return base64.b64encode(image_bytes).decode("utf-8")

