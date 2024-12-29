import os
import json
import asyncio
import logging
import aiohttp
import base64
from io import BytesIO
from PIL import Image
from typing import Dict, List, Any, Optional
from .llm_service import LLMService

logger = logging.getLogger(__name__)

class RecipeService:
    """Service for handling recipe-related operations."""

    # Schema definitions for different recipe operations
    RECIPE_DETAILS_SCHEMA = {
        "type": "object",
        "properties": {
            "ingredients": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "quantity": {"type": "string"},
                        "unit": {"type": "string"}
                    },
                    "required": ["name", "quantity", "unit"]
                }
            },
            "instructions": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["ingredients", "instructions"]
    }

    RECIPE_TEMPLATES_SCHEMA = {
        "type": "object",
        "properties": {
            "recipes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "visual_description": {"type": "string"}
                    },
                    "required": ["id", "title", "description", "visual_description"]
                }
            }
        },
        "required": ["recipes"]
    }

    GROCERY_LIST_SCHEMA = {
        "type": "object",
        "properties": {
            "grocery_list": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "quantity": {"type": "string"},
                        "unit": {"type": "string"}
                    },
                    "required": ["name", "quantity", "unit"]
                }
            }
        },
        "required": ["grocery_list"]
    }

    _http_client = None

    @classmethod
    async def _get_http_client(cls) -> aiohttp.ClientSession:
        """Get or create an HTTP client instance."""
        if cls._http_client is None:
            cls._http_client = aiohttp.ClientSession()
        return cls._http_client

    @classmethod
    async def cleanup(cls):
        """Cleanup resources when shutting down."""
        if cls._http_client:
            await cls._http_client.close()
            cls._http_client = None
        await LLMService.cleanup()

    @staticmethod
    def _decode_and_optimize_image(base64_string: str) -> str:
        """Decode base64 image, optimize it, and return as base64."""
        if not base64_string:
            return ''
        
        try:
            # Decode base64 to bytes
            image_data = base64.b64decode(base64_string)
            
            # Open image with PIL
            with Image.open(BytesIO(image_data)) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Create a BytesIO object to store the optimized image
                optimized = BytesIO()
                
                # Save as JPEG with optimization
                img.save(optimized, format='JPEG', quality=85, optimize=True)
                
                # Get the optimized image data and encode to base64
                optimized_data = base64.b64encode(optimized.getvalue()).decode('utf-8')
                
                return optimized_data
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            return ''

    @classmethod
    async def _generate_recipe_image(cls, recipe_text: str, visual_description: str) -> str:
        """Generate an image for a recipe using GetImg API."""
        url = "https://api.getimg.ai/v1/flux-schnell/text-to-image"
        
        api_key = os.getenv('GETIMG_API_KEY')
        if not api_key:
            logger.error("GETIMG_API_KEY environment variable is not set")
            return ''
        
        logger.info(f"Generating image for recipe: {recipe_text[:100]}...")
        
        payload = {
            "prompt": f"A professional food photography shot of: {visual_description}. The dish is: {recipe_text}. Photorealistic, high-quality food photography, soft natural lighting, shallow depth of field.",
            "width": 256,
            "height": 256,
            "response_format": "b64",
            "steps": 4
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        result = await response.json()
                        image_data = result.get('image', '')
                        logger.info(f"Successfully generated image for {recipe_text[:50]}... ({len(image_data)} bytes)")
                        return image_data
                    else:
                        error_text = await response.text()
                        logger.error(f"Error generating image. Status: {response.status}, Response: {error_text}")
                        return ''
        except Exception as e:
            logger.error(f"Exception in image generation: {str(e)}", exc_info=True)
            return ''

    @classmethod
    async def get_recipe_templates(cls):
        """Get basic recipe templates for the week."""
        template_prompt = """Generate 7 easy-to-make, nutritious, and cost-effective meals for the week. 
        For each recipe, provide:
        1. Title: The name of the dish
        2. Description: A very brief 1-sentence description of the dish
        3. Visual Description: A detailed description of how the completed dish should look, focusing on colors, textures, and presentation
        
        Return your response as a JSON object with this exact structure (no markdown formatting):
        {
            "recipes": [
                {
                    "id": 1,
                    "title": "Recipe Title",
                    "description": "One sentence description",
                    "visual_description": "Detailed visual description of the completed dish"
                },
                ...
            ]
        }
        
        Make sure to include exactly 7 recipes and return only the JSON object, no other text."""

        templates_data = await LLMService.get_completion(
            prompt=template_prompt,
            schema=cls.RECIPE_TEMPLATES_SCHEMA,
            tool_name="generate_recipes",
            tool_description="Generate a list of recipe templates for the week."
        )
        
        if not templates_data:
            raise ValueError("No response content from AI model")
        
        return templates_data.get('recipes', [])

    @classmethod
    async def get_recipe_details(cls, recipe_template):
        """Get detailed ingredients and instructions for a specific recipe."""
        detail_prompt = f"""For this recipe: {recipe_template['title']} - {recipe_template['description']}
        Generate detailed ingredients and instructions.
        
        Return your response as a JSON object with this exact structure (no markdown formatting):
        {{
            "ingredients": [
                {{
                    "name": "ingredient name",
                    "quantity": "amount",
                    "unit": "measurement unit"
                }},
                ...
            ],
            "instructions": [
                "Step 1 instruction",
                "Step 2 instruction",
                ...
            ]
        }}

        Return only the JSON object, no other text."""

        details = await LLMService.get_completion(
            prompt=detail_prompt,
            schema=cls.RECIPE_DETAILS_SCHEMA,
            tool_name="record_recipe",
            tool_description="Generate structured JSON for the given recipe prompt."
        )
        
        if not details:
            raise ValueError("No response content from AI model")
        
        return {
            **recipe_template,
            'ingredients': details.get('ingredients', []),
            'instructions': details.get('instructions', [])
        }

    @classmethod
    async def generate_grocery_list(cls, recipes):
        """Generate consolidated grocery list from all recipes."""
        recipe_data = [{
            'title': recipe['title'],
            'description': recipe['description'],
            'ingredients': recipe['ingredients']
        } for recipe in recipes]

        grocery_prompt = f"""Based on these recipes and their ingredients: {recipe_data}
        Generate a consolidated grocery list with exact quantities needed for all 7 meals.
        
        Return your response as a JSON object with this exact structure (no markdown formatting):
        {{
            "grocery_list": [
                {{
                    "name": "item name",
                    "quantity": "amount",
                    "unit": "measurement unit"
                }},
                ...
            ]
        }}
        
        Combine similar ingredients, adjust quantities accordingly, and return only the JSON object, no other text."""

        grocery_data = await LLMService.get_completion(
            prompt=grocery_prompt,
            schema=cls.GROCERY_LIST_SCHEMA,
            tool_name="generate_grocery_list",
            tool_description="Generate a consolidated grocery list from recipe ingredients."
        )
        
        if not grocery_data:
            raise ValueError("No response content from AI model")
        
        return grocery_data.get('grocery_list', [])