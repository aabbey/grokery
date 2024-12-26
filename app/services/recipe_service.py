import os
import json
import asyncio
import logging
from openai import OpenAI
from typing import Dict, List, Any
import aiohttp

logger = logging.getLogger(__name__)

class RecipeService:
    @staticmethod
    def _create_openai_client() -> OpenAI:
        """Create and return an OpenAI client instance."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        return OpenAI(api_key=api_key)

    @staticmethod
    async def _generate_recipe_image(recipe_text: str) -> str:
        """Generate an image for a recipe using GetImg API."""
        url = "https://api.getimg.ai/v1/flux-schnell/text-to-image"
        
        api_key = os.getenv('GETIMG_API_KEY')
        if not api_key:
            logger.error("GETIMG_API_KEY environment variable is not set")
            return ''
        
        logger.info(f"Generating image for recipe: {recipe_text[:100]}...")
        
        payload = {
            "prompt": f"A realistic, appetizing photo of the following recipe after completion: {recipe_text}",
            "width": 512,
            "height": 512,
            "response_format": "b64",
            "steps": 2
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}"
        }

        try:
            async with aiohttp.ClientSession() as session:
                logger.info("Making request to GetImg API...")
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        image_data = result.get('image', '')
                        logger.info(f"Successfully generated image, received {len(image_data)} bytes of base64 data")
                        return image_data
                    else:
                        error_text = await response.text()
                        logger.error(f"Error generating image. Status: {response.status}, Response: {error_text}")
                        return ''
        except Exception as e:
            logger.error(f"Exception in image generation: {str(e)}", exc_info=True)
            return ''

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

    @staticmethod
    def get_recipe_templates():
        """
        Get basic recipe templates for the week.
        """
        client = RecipeService._create_openai_client()

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
            template_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that always responds with valid JSON."},
                    {"role": "user", "content": template_prompt}
                ],
                temperature=0.7
            )
            
            if not template_response.choices or not template_response.choices[0].message.content:
                raise ValueError("No response content from OpenAI")
            
            templates_data = RecipeService._validate_json_response(template_response.choices[0].message.content)
            return templates_data.get('recipes', [])
        except Exception as e:
            print(f"Error getting recipe templates: {str(e)}")
            raise

    @staticmethod
    async def get_recipe_details(recipe_template):
        """
        Get detailed ingredients and instructions for a specific recipe.
        """
        logger.info(f"Getting details for recipe: {recipe_template['title']}")
        client = RecipeService._create_openai_client()

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

        try:
            detail_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that always responds with valid JSON objects only, no markdown formatting or additional text."},
                    {"role": "user", "content": detail_prompt}
                ],
                temperature=0.7
            )
            
            if not detail_response.choices or not detail_response.choices[0].message.content:
                raise ValueError("No response content from OpenAI")
            
            details = RecipeService._validate_json_response(detail_response.choices[0].message.content)
            logger.info(f"Successfully got recipe details for {recipe_template['title']}")
            
            # Generate image in parallel with recipe details
            recipe_text = f"{recipe_template['title']} - {recipe_template['description']}"
            image_data = await RecipeService._generate_recipe_image(recipe_text)
            
            result = {
                **recipe_template,
                'ingredients': details.get('ingredients', []),
                'instructions': details.get('instructions', []),
                'image': image_data
            }
            logger.info(f"Completed recipe details with image for {recipe_template['title']}")
            logger.debug(f"Recipe data: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            logger.error(f"Error getting recipe details for {recipe_template['title']}: {str(e)}", exc_info=True)
            raise

    @staticmethod
    async def get_all_recipe_details(recipe_templates):
        """
        Asynchronously get details for all recipes.
        """
        logger.info(f"Getting details for {len(recipe_templates)} recipes")
        tasks = []
        for template in recipe_templates:
            tasks.append(asyncio.create_task(RecipeService.get_recipe_details(template)))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out any failed recipes
        successful_recipes = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to get details for recipe {recipe_templates[i]['title']}: {str(result)}")
            else:
                successful_recipes.append(result)
        
        logger.info(f"Successfully got details for {len(successful_recipes)} out of {len(recipe_templates)} recipes")
        return successful_recipes

    @staticmethod
    def generate_grocery_list(recipes):
        """
        Generate consolidated grocery list from all recipes.
        """
        client = RecipeService._create_openai_client()

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
            grocery_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that always responds with valid JSON objects only, no markdown formatting or additional text."},
                    {"role": "user", "content": grocery_prompt}
                ],
                temperature=0.7
            )
            
            if not grocery_response.choices or not grocery_response.choices[0].message.content:
                raise ValueError("No response content from OpenAI")
            
            grocery_data = RecipeService._validate_json_response(grocery_response.choices[0].message.content)
            return grocery_data.get('grocery_list', [])
        except Exception as e:
            logger.error(f"Error generating grocery list: {str(e)}", exc_info=True)
            raise