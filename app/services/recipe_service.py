import time

class RecipeService:
    @staticmethod
    def get_recipes_and_grocery_list():
        """
        Get recipes and associated grocery list.
        In the future, this should interact with a real database.
        """
        # Mock data for recipes and grocery list
        mock_data = {
            'recipes': [
                {
                    'title': 'Spaghetti Carbonara',
                    'description': 'A classic Italian pasta dish with eggs, cheese, pancetta, and black pepper.',
                    'ingredients': ['spaghetti', 'eggs', 'pecorino cheese', 'pancetta', 'black pepper'],
                    'instructions': ['Boil pasta', 'Cook pancetta', 'Mix eggs and cheese', 'Combine all ingredients']
                },
                {
                    'title': 'Chicken Stir Fry',
                    'description': 'Quick and healthy stir-fried chicken with vegetables.',
                    'ingredients': ['chicken breast', 'mixed vegetables', 'soy sauce', 'ginger', 'garlic'],
                    'instructions': ['Cut chicken', 'Prepare vegetables', 'Stir fry chicken', 'Add vegetables and sauce']
                }
            ],
            'grocery_list': [
                {'name': 'Spaghetti', 'quantity': '1', 'unit': 'pack'},
                {'name': 'Eggs', 'quantity': '6', 'unit': 'pieces'},
                {'name': 'Pecorino Cheese', 'quantity': '200', 'unit': 'g'},
                {'name': 'Pancetta', 'quantity': '150', 'unit': 'g'},
                {'name': 'Black Pepper', 'quantity': '1', 'unit': 'bottle'}
            ]
        }
        
        return mock_data 