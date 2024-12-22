import os
import json
import asyncio
from openai import OpenAI
from typing import Dict, List, Any

class RecipeService:
    @staticmethod
    def _create_openai_client() -> OpenAI:
        """Create and return an OpenAI client instance."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        return OpenAI(api_key=api_key)

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
    def get_recipe_details(recipe_template):
        """
        Get detailed ingredients and instructions for a specific recipe.
        """
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
            return {
                **recipe_template,
                'ingredients': details.get('ingredients', []),
                'instructions': details.get('instructions', [])
            }
        except Exception as e:
            print(f"Error getting recipe details for {recipe_template['title']}: {str(e)}")
            raise

    @staticmethod
    async def get_all_recipe_details(recipe_templates):
        """
        Asynchronously get details for all recipes.
        """
        tasks = []
        for template in recipe_templates:
            tasks.append(asyncio.to_thread(RecipeService.get_recipe_details, template))
        return await asyncio.gather(*tasks)

    @staticmethod
    def generate_grocery_list(recipes):
        """
        Generate consolidated grocery list from all recipes.
        """
        client = RecipeService._create_openai_client()

        grocery_prompt = f"""Based on these recipes and their ingredients: {recipes}
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
            print(f"Error generating grocery list: {str(e)}")
            raise