class GroceryService:
    @staticmethod
    def get_item_details(item_id):
        """
        Get details for a specific grocery item.
        In the future, this should fetch from a real database.
        """
        # Temporary mock data
        item_details = {
            'id': item_id,
            'name': 'Sample Item',
            'quantity': '2',
            'unit': 'pieces',
            'category': 'Produce',
            'notes': 'Fresh and organic preferred'
        }
        return item_details
    
    @staticmethod
    def remove_item(item_id, user):
        """
        Remove a grocery item.
        In the future, this should interact with a real database.
        """
        # TODO: Replace with actual database query
        # item = GroceryItem.objects.get(id=item_id, user=user)
        # item.delete()
        return True 