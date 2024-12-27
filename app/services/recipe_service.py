import os
import json
import asyncio
import logging
from openai import AsyncOpenAI
from typing import Dict, List, Any
import aiohttp
import base64
from io import BytesIO
from PIL import Image
import contextlib

logger = logging.getLogger(__name__)

class RecipeService:
    _http_client = None

    @classmethod
    async def _get_openai_client(cls) -> AsyncOpenAI:
        """Get a new OpenAI client instance for each request."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        return AsyncOpenAI(api_key=api_key)

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
    async def _generate_recipe_image(cls, recipe_text: str) -> str:
        """Generate an image for a recipe using GetImg API."""
        url = "https://api.getimg.ai/v1/flux-schnell/text-to-image"
        
        api_key = os.getenv('GETIMG_API_KEY')
        if not api_key:
            logger.error("GETIMG_API_KEY environment variable is not set")
            return ''
        
        logger.info(f"Generating image for recipe: {recipe_text[:100]}...")
        
        payload = {
            "prompt": f"A realistic, appetizing photo of the following recipe after completion: {recipe_text}",
            "width": 256,
            "height": 256,
            "response_format": "b64",
            "steps": 3
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}"
        }

        try:
            # Create a new client for each request to avoid timeout issues
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
    async def get_recipe_details(cls, recipe_template):
        """Get detailed ingredients and instructions for a specific recipe."""
        # Add a unique identifier to prevent duplicate processing
        if not hasattr(cls, '_processing_recipes'):
            cls._processing_recipes = set()
        
        recipe_id = recipe_template.get('id')
        if recipe_id in cls._processing_recipes:
            logger.info(f"Skipping duplicate processing for recipe {recipe_template['title']}")
            return None, None
        
        cls._processing_recipes.add(recipe_id)
        
        try:
            logger.info(f"Getting details for recipe: {recipe_template['title']}")
            client = await cls._get_openai_client()

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

            # Get recipe details first
            detail_response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that always responds with valid JSON objects only, no markdown formatting or additional text."},
                    {"role": "user", "content": detail_prompt}
                ],
                temperature=0.7
            )
            
            if not detail_response.choices or not detail_response.choices[0].message.content:
                raise ValueError("No response content from OpenAI")
            
            details = cls._validate_json_response(detail_response.choices[0].message.content)
            
            # Create initial result without image
            result = {
                **recipe_template,
                'ingredients': details.get('ingredients', []),
                'instructions': details.get('instructions', []),
                'image': None,  # Initially no image
                'image_loading': True  # Indicate image is loading
            }
            
            # Start image generation in background
            recipe_text = f"{recipe_template['title']} - {recipe_template['description']}"
            image_task = asyncio.create_task(cls._generate_recipe_image(recipe_text))
            
            # Return initial result immediately
            logger.info(f"Returning initial recipe details for {recipe_template['title']}")
            return result, image_task
            
        except Exception as e:
            logger.error(f"Error getting recipe details for {recipe_template['title']}: {str(e)}", exc_info=True)
            raise
        finally:
            # Remove from processing set when done
            cls._processing_recipes.remove(recipe_id)

    @staticmethod
    def _validate_json_response(response_content: str) -> Dict[str, Any]:
        """Validate and parse JSON response from OpenAI."""
        try:
            # Clean up markdown formatting if present
            content = response_content.strip()
            if content.startswith('```json'):
                content = content[7:]  # Remove ```json prefix
            if content.startswith('```'):
                content = content[3:]  # Remove ``` prefix
            if content.endswith('```'):
                content = content[:-3]  # Remove ``` suffix
            
            content = content.strip()
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON response: {response_content}")
            raise ValueError(f"Failed to parse OpenAI response as JSON: {str(e)}")

    @classmethod
    async def get_recipe_templates(cls):
        """
        Get basic recipe templates for the week.
        """
        client = await cls._get_openai_client()

        template_prompt = """Generate 7 easy-to-make, nutritious, and cost-effective meals for the week. 
        For each recipe, provide just:
        1. Title
        2. Brief description
        
        Return your response as a JSON object with this exact structure (no markdown formatting):
        {
            "recipes": [
                {
                    "id": 1,
                    "title": "Recipe Title",
                    "description": "Brief description"
                },
                ...
            ]
        }
        
        Make sure to include exactly 7 recipes and return only the JSON object, no other text."""

        try:
            template_response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that always responds with valid JSON."},
                    {"role": "user", "content": template_prompt}
                ],
                temperature=0.7
            )
            
            if not template_response.choices or not template_response.choices[0].message.content:
                raise ValueError("No response content from OpenAI")
            
            templates_data = cls._validate_json_response(template_response.choices[0].message.content)
            return templates_data.get('recipes', [])
        except Exception as e:
            logger.error(f"Error getting recipe templates: {str(e)}")
            raise

    @classmethod
    async def get_all_recipe_details(cls, recipe_templates):
        """
        Asynchronously get details for all recipes.
        For grocery list generation, this waits for all recipe details but not images.
        """
        logger.info(f"Getting details for {len(recipe_templates)} recipes")
        
        # Create tasks for all recipe details in parallel
        detail_tasks = [
            cls.get_recipe_details(template)
            for template in recipe_templates
        ]
        
        # Wait for all recipe details to complete
        results = await asyncio.gather(*detail_tasks, return_exceptions=True)
        
        recipes = []
        
        # Process results, but don't wait for images
        for template, result in zip(recipe_templates, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to get details for recipe {template['title']}: {str(result)}")
                continue
            
            if result is None:
                continue
                
            recipe, _ = result  # Ignore image task for grocery list
            if recipe is not None:
                recipes.append(recipe)

        logger.info(f"Successfully processed {len(recipes)} recipes")
        return recipes

    @classmethod
    async def generate_grocery_list(cls, recipes):
        """
        Generate consolidated grocery list from all recipes.
        """
        client = await cls._get_openai_client()

        # Filter out only the needed recipe information
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

        try:
            grocery_response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that always responds with valid JSON objects only, no markdown formatting or additional text."},
                    {"role": "user", "content": grocery_prompt}
                ],
                temperature=0.7
            )
            
            if not grocery_response.choices or not grocery_response.choices[0].message.content:
                raise ValueError("No response content from OpenAI")
            
            grocery_data = cls._validate_json_response(grocery_response.choices[0].message.content)
            return grocery_data.get('grocery_list', [])
        except Exception as e:
            logger.error(f"Error generating grocery list: {str(e)}", exc_info=True)
            raise