"""AI Code Generator using qwen3-coder"""

import json
import re
from typing import Optional, Dict, Any
import os

from services.ollama.client import OllamaClient


class CodeGenerator:
    """
    AI-powered code generation using qwen3-coder model
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        ollama_client: Optional[OllamaClient] = None
    ):
        """
        Initialize code generator
        
        Args:
            model_name: Ollama coder model name (default: from env or qwen3-coder:480b-cloud)
            ollama_client: Existing Ollama client (creates new if None)
        """
        self.model_name = model_name or os.getenv("OLLAMA_CODER_MODEL", "qwen3-coder:480b-cloud")
        self.client = ollama_client or OllamaClient()
        
        # Coder-specific settings
        self.temperature = float(os.getenv("CODER_TEMPERATURE", "0.2"))  # Low temp for consistent code
        self.max_tokens = int(os.getenv("CODER_MAX_TOKENS", "8192"))
        
        print(f"💻 Code Generator initialized: {self.model_name}")
        print(f"   Temperature: {self.temperature} (low for deterministic code)")
    
    async def generate_code(
        self,
        prompt: str,
        language: str = "json",
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate code using AI
        
        Args:
            prompt: Code generation prompt
            language: Target language (json, lua, xml, python, etc.)
            temperature: Override default temperature
        
        Returns:
            Generated code as string
        """
        temp = temperature if temperature is not None else self.temperature
        
        print(f"💻 Generating {language} code...")
        print(f"   Prompt length: {len(prompt)} chars")
        
        try:
            response = await self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": temp,
                    "num_predict": self.max_tokens,
                    "stop": ["```", "---", "###"]  # Stop at markdown delimiters
                }
            )
            
            code = response.get("response", "")
            
            print(f"✅ Code generated: {len(code)} chars")
            
            # Clean up the response
            code = self._clean_code_response(code, language)
            
            return code
            
        except Exception as e:
            print(f"❌ Code generation failed: {e}")
            raise RuntimeError(f"Code generation error: {e}")
    
    def _clean_code_response(self, response: str, language: str) -> str:
        """
        Clean up AI response to extract just the code
        
        Args:
            response: Raw AI response
            language: Expected language
        
        Returns:
            Cleaned code
        """
        # Remove markdown code blocks if present
        patterns = [
            rf'```{language}\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # If no code blocks, return as-is (trimmed)
        return response.strip()
    
    async def generate_json(self, prompt: str) -> Dict[str, Any]:
        """
        Generate and parse JSON code
        
        Args:
            prompt: Prompt for JSON generation
        
        Returns:
            Parsed JSON as dict
        """
        code = await self.generate_code(prompt, language="json")
        
        try:
            # Try to parse as JSON
            parsed = json.loads(code)
            print(f"✅ JSON parsed successfully")
            return parsed
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parse error: {e}")
            print(f"   Attempting to fix JSON...")
            
            # Try to fix common issues
            fixed_code = self._fix_json(code)
            try:
                parsed = json.loads(fixed_code)
                print(f"✅ JSON fixed and parsed")
                return parsed
            except:
                print(f"❌ Could not fix JSON")
                raise ValueError(f"Invalid JSON generated: {e}")
    
    def _fix_json(self, json_str: str) -> str:
        """Attempt to fix common JSON issues"""
        # Remove comments
        json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        
        # Fix trailing commas
        json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
        
        # Ensure proper quotes
        json_str = json_str.replace("'", '"')
        
        return json_str
    
    async def generate_xml(self, prompt: str) -> str:
        """
        Generate XML code
        
        Args:
            prompt: Prompt for XML generation
        
        Returns:
            XML string
        """
        code = await self.generate_code(prompt, language="xml")
        
        # Basic XML validation
        if not code.strip().startswith("<?xml"):
            # Try to add XML declaration if missing
            if not code.strip().startswith("<"):
                raise ValueError("Generated code doesn't look like XML")
            code = '<?xml version="1.0" encoding="UTF-8"?>\n' + code
        
        print(f"✅ XML generated")
        return code
    
    async def generate_lua(self, prompt: str) -> str:
        """
        Generate Lua script
        
        Args:
            prompt: Prompt for Lua generation
        
        Returns:
            Lua script string
        """
        code = await self.generate_code(prompt, language="lua", temperature=0.3)
        
        # Basic Lua validation (check for function definitions)
        if "function" not in code and "local" not in code:
            print("⚠️  Generated code doesn't contain Lua keywords")
        
        print(f"✅ Lua script generated")
        return code
    
    async def validate_jbeam(self, jbeam_data: Dict[str, Any]) -> bool:
        """
        Validate JBeam structure
        
        Args:
            jbeam_data: JBeam dict
        
        Returns:
            True if valid
        """
        # Basic JBeam structure check
        if not isinstance(jbeam_data, dict):
            return False
        
        # Should have at least one part
        if len(jbeam_data) == 0:
            return False
        
        # Check first part structure
        first_key = list(jbeam_data.keys())[0]
        part = jbeam_data[first_key]
        
        if not isinstance(part, dict):
            return False
        
        # Should have nodes and/or beams
        has_nodes = "nodes" in part
        has_beams = "beams" in part
        
        if not (has_nodes or has_beams):
            return False
        
        print(f"✅ JBeam validation passed")
        return True
    
    async def close(self):
        """Close underlying client"""
        await self.client.close()

