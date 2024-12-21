import os
import json
from openai import OpenAI

class RecipeService:
    @staticmethod
    def get_recipes_and_grocery_list():
        """
        Get recipes and associated grocery list using OpenAI's API.
        """
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # First prompt to get recipes
        recipe_prompt = """Generate 7 easy-to-make, nutritious, and cost-effective meals for the week. 
        The meals should have some ingredient overlap to minimize waste and extra purchases, while maintaining variety.
        For each recipe, provide:
        1. Title
        2. Brief description
        3. List of ingredients
        4. Simple step-by-step instructions
        
        Format the response as a JSON array of recipes, where each recipe has the fields: 
        'title', 'description', 'ingredients' (as array), 'instructions' (as array)."""

        recipe_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": recipe_prompt}
            ],
            response_format={ "type": "json_object" }
        )
        
        # Parse the JSON string and handle the response structure
        recipes_data = json.loads(recipe_response.choices[0].message.content)
        # The response might be the direct array of recipes without the 'recipes' key
        recipes = recipes_data if isinstance(recipes_data, list) else recipes_data.get('recipes', [])
        
        # Second prompt to generate consolidated grocery list
        grocery_prompt = f"""Based on these recipes: {recipes}
        Generate a consolidated grocery list with exact quantities needed for all 7 meals.
        Format the response as a JSON array where each item has:
        'name' (string), 'quantity' (string), 'unit' (string)
        Combine similar ingredients and adjust quantities accordingly."""

        grocery_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": grocery_prompt}
            ],
            response_format={ "type": "json_object" }
        )

        # Parse the JSON string and handle the response structure
        grocery_data = json.loads(grocery_response.choices[0].message.content)
        grocery_list = grocery_data if isinstance(grocery_data, list) else grocery_data.get('grocery_list', [])

        # Return the data in the expected format
        return {
            'recipes': recipes,
            'grocery_list': grocery_list
        }