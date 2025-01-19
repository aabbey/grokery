// Helper functions to create HTML
function createRecipeTemplateHTML(recipe) {
    console.log('Creating recipe template HTML for recipe:', recipe);
    return `
        <div class="recipe-item" data-recipe-id="${recipe.id}">
            <div class="recipe-image">
                ${recipe.image_loading ? 
                    `<div class="loading-spinner"></div>` :
                    recipe.image ? 
                        `<img src="data:image/jpeg;base64,${recipe.image}" alt="${recipe.title}" loading="lazy">` :
                        `<div class="placeholder-image">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                                <circle cx="8.5" cy="8.5" r="1.5"/>
                                <polyline points="21 15 16 10 5 21"/>
                            </svg>
                        </div>`
                }
            </div>
            <div class="recipe-content">
                <h3>${recipe.title}</h3>
                <p>${recipe.description}</p>
            </div>
        </div>
    `;
}

// Initialize recipe functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('Recipe.js loaded');
    
    // Add event listeners for rebuild buttons
    const rebuildButton = document.querySelector('.rebuild-recipes');
    const buildRecipesBtn = document.getElementById('buildRecipesBtn');
    
    if (rebuildButton) {
        rebuildButton.addEventListener('click', (e) => {
            console.log('Rebuild button clicked');
            e.preventDefault();
            window.showPreferencesModal();
        });
    }

    if (buildRecipesBtn) {
        buildRecipesBtn.addEventListener('click', (e) => {
            console.log('Build recipes button clicked');
            e.preventDefault();
            window.showPreferencesModal();
        });
    }

    // Add click handlers for recipe items (delegation)
    document.addEventListener('click', function(e) {
        const recipeItem = e.target.closest('.recipe-item');
        
        if (recipeItem) {
            const recipeId = recipeItem.dataset.recipeId;
            const recipe = window.recipes?.find(r => r.id === parseInt(recipeId, 10));
            
            if (recipe && recipe.ingredients && recipe.instructions) {
                showRecipeModal(recipe);
            }
        }
    });

    // Close modal on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeRecipeModal();
        }
    });
});

function setupRecipeStream() {
    console.log('Setting up recipe generation stream');
    const eventSource = new EventSource('/api/recipes/generate/');
    
    // Store recipes globally for click handling
    window.recipes = [];
    
    // Get DOM elements
    const recipesContent = document.getElementById('recipesContent');
    const recipesLoading = document.getElementById('recipesLoading');
    const recipesEmpty = document.getElementById('recipesEmpty');
    const groceryListContent = document.getElementById('groceryListContent');
    const groceryListLoading = document.getElementById('groceryListLoading');
    const groceryListEmpty = document.getElementById('groceryListEmpty');
    
    // Show loading states
    if (recipesContent) recipesContent.style.display = 'none';
    if (recipesLoading) recipesLoading.style.display = 'block';
    if (recipesEmpty) recipesEmpty.style.display = 'none';
    if (groceryListContent) groceryListContent.style.display = 'none';
    if (groceryListLoading) groceryListLoading.style.display = 'block';
    if (groceryListEmpty) groceryListEmpty.style.display = 'none';
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('Received stream update:', data);

            switch (data.type) {
                case 'templates':
                    handleTemplatesUpdate(data, recipesContent, recipesLoading);
                    break;
                    
                case 'updates':
                    handleRecipeUpdates(data);
                    break;
                    
                case 'grocery_list':
                    handleGroceryListUpdate(data, groceryListContent, groceryListLoading, groceryListEmpty);
                    eventSource.close();
                    break;
            }
        } catch (error) {
            console.error('Error processing stream update:', error);
            handleStreamError(error);
        }
    };
    
    eventSource.onerror = function(error) {
        console.error('EventSource error:', error);
        handleStreamError(error);
        eventSource.close();
    };
}

function handleTemplatesUpdate(data, recipesContent, recipesLoading) {
    console.log('Received recipe templates:', data.recipes);
    window.recipes = data.recipes;
    
    if (recipesContent) {
        recipesContent.style.display = 'block';
        recipesContent.innerHTML = data.recipes.map(recipe => createRecipeTemplateHTML(recipe)).join('');
    }
    if (recipesLoading) recipesLoading.style.display = 'none';
}

function handleRecipeUpdates(data) {
    console.log('Received recipe updates:', data.recipes);
    data.recipes.forEach(recipe => {
        const index = window.recipes.findIndex(r => r.id === recipe.id);
        if (index !== -1) {
            window.recipes[index] = recipe;
            updateRecipe(recipe);
        }
    });
}

function handleGroceryListUpdate(data, groceryListContent, groceryListLoading, groceryListEmpty) {
    console.log('Recipe generation complete');
    if (groceryListContent && data.grocery_list) {
        groceryListContent.style.display = 'block';
        groceryListContent.innerHTML = data.grocery_list
            .map(item => window.createGroceryItemHTML(item))
            .join('');
    }
    if (groceryListLoading) groceryListLoading.style.display = 'none';
    if (groceryListEmpty && (!data.grocery_list || data.grocery_list.length === 0)) {
        groceryListEmpty.style.display = 'block';
    }
}

function handleStreamError(error) {
    console.error('Handling stream error:', error);
    const recipesContent = document.getElementById('recipesContent');
    const recipesLoading = document.getElementById('recipesLoading');
    const recipesEmpty = document.getElementById('recipesEmpty');
    
    if (recipesLoading) recipesLoading.style.display = 'none';
    if (recipesEmpty) recipesEmpty.style.display = 'none';
    
    const errorMessage = document.createElement('div');
    errorMessage.className = 'error-message';
    errorMessage.innerHTML = `
        <p>Error loading recipes: ${error}</p>
        <button onclick="location.reload()">Retry</button>
    `;
    recipesContent.appendChild(errorMessage);
}

function updateRecipe(recipe) {
    console.log(`Updating DOM for recipe ${recipe.id}`);
    const recipeElement = document.querySelector(`[data-recipe-id="${recipe.id}"]`);
    if (recipeElement) {
        recipeElement.outerHTML = createRecipeTemplateHTML(recipe);
        console.log(`DOM updated for recipe ${recipe.id}`);
    } else {
        console.warn(`Could not find DOM element for recipe ${recipe.id}`);
    }
}

// Recipe modal functionality
function showRecipeModal(recipe) {
    console.log('Showing modal for recipe:', recipe.title);
    
    const modal = document.getElementById('recipeDetailsModal');
    const modalImage = document.getElementById('modalRecipeImage');
    const modalTitle = document.getElementById('modalRecipeTitle');
    const modalIngredients = document.getElementById('modalRecipeIngredients');
    const modalInstructions = document.getElementById('modalRecipeInstructions');
    const closeBtn = modal.querySelector('.close-modal-btn');

    // Set image and title
    if (recipe.image) {
        modalImage.src = `data:image/jpeg;base64,${recipe.image}`;
        modalImage.alt = recipe.title;
        modalImage.style.display = 'block';
    } else {
        modalImage.style.display = 'none';
    }
    modalTitle.textContent = recipe.title;

    // Set ingredients and instructions
    modalIngredients.innerHTML = recipe.ingredients
        .map(ingredient => `<li>${ingredient}</li>`)
        .join('');
    modalInstructions.innerHTML = recipe.instructions
        .map(instruction => `<li>${instruction}</li>`)
        .join('');

    // Show modal
    modal.style.display = 'flex';
    modal.classList.add('active');
    
    // Setup close handlers
    closeBtn.addEventListener('click', closeRecipeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeRecipeModal();
        }
    });
}

function closeRecipeModal() {
    console.log('Closing recipe modal');
    const modal = document.getElementById('recipeDetailsModal');
    modal.style.display = 'none';
    modal.classList.remove('active');
}

// Export functions needed by other modules
window.setupRecipeStream = setupRecipeStream; 