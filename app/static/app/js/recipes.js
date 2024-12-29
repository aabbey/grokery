// Helper functions to create HTML
function createRecipeTemplateHTML(recipe) {
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
                <div class="recipe-details ${recipe.ingredients?.length && recipe.instructions?.length ? '' : 'hidden'}">
                    <button class="view-details-btn" onclick="viewRecipeDetails(${recipe.id})">
                        View Recipe Details
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Initialize recipe functionality
document.addEventListener('DOMContentLoaded', function() {
    const recipesContent = document.getElementById('recipesContent');
    const recipesLoading = document.getElementById('recipesLoading');
    const groceryListStatus = document.getElementById('groceryListStatus');
    const groceryListContent = document.getElementById('groceryListContent');
    const groceryListLoading = document.getElementById('groceryListLoading');
    
    // Set up EventSource for recipe generation stream
    setupRecipeStream();
});

function setupRecipeStream() {
    console.log('Setting up recipe generation stream');
    const eventSource = new EventSource('/api/recipes/generate/');
    const recipesContent = document.getElementById('recipesContent');
    const recipesLoading = document.getElementById('recipesLoading');
    const groceryListStatus = document.getElementById('groceryListStatus');
    const groceryListContent = document.getElementById('groceryListContent');
    const groceryListLoading = document.getElementById('groceryListLoading');
    const recipesById = new Map();
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('Received stream update:', data);

            switch (data.type) {
                case 'templates':
                    // Initial recipe templates
                    data.recipes.forEach(recipe => recipesById.set(recipe.id, recipe));
                    recipesContent.innerHTML = Array.from(recipesById.values())
                        .map(recipe => createRecipeTemplateHTML(recipe))
                        .join('');
                    recipesContent.classList.remove('content-hidden');
                    recipesLoading.style.display = 'none';
                    groceryListStatus.textContent = 'Generating recipe details...';
                    break;

                case 'updates':
                    // Recipe updates (images or details)
                    data.recipes.forEach(recipe => {
                        recipesById.set(recipe.id, recipe);
                        updateRecipe(recipe);
                    });
                    break;

                case 'grocery_list':
                    // Grocery list is ready
                    groceryListContent.innerHTML = data.grocery_list.map(item =>
                        createGroceryItemHTML(item)
                    ).join('');
                    groceryListContent.classList.remove('content-hidden');
                    groceryListLoading.style.display = 'none';
                    groceryListStatus.textContent = 'Grocery list ready!';
                    break;

                case 'complete':
                    // All processing is complete
                    console.log('Recipe generation complete');
                    eventSource.close();
                    break;

                case 'error':
                    // Handle any errors
                    console.error('Stream error:', data.error);
                    handleStreamError(data.error);
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
        handleStreamError('Connection error occurred');
        eventSource.close();
    };
}

function handleStreamError(error) {
    console.error('Handling stream error:', error);
    const recipesContent = document.getElementById('recipesContent');
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