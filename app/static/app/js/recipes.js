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
document.addEventListener('DOMContentLoaded', async function() {
    const recipesContent = document.getElementById('recipesContent');
    const recipesLoading = document.getElementById('recipesLoading');
    
    // Set up EventSource for recipe updates
    setupRecipeUpdates();
});

function setupRecipeUpdates() {
    console.log('Setting up recipe updates stream');
    const eventSource = new EventSource('/api/recipes/stream/');
    const recipesContent = document.getElementById('recipesContent');
    const recipesLoading = document.getElementById('recipesLoading');
    const recipesById = new Map();
    let retryCount = 0;
    const MAX_RETRIES = 3;
    
    eventSource.onmessage = function(event) {
        try {
            // Parse SSE data
            const data = JSON.parse(event.data);
            console.log('Received SSE update:', data);

            // If there is an error, handle it
            if (data.error) {
                console.error('Stream error:', data.error);
                handleStreamError(data.error);
                return;
            }

            // If done, clean up
            if (data.done) {
                console.log('Recipe stream completed');
                const groceryListStatus = document.getElementById('groceryListStatus');
                if (groceryListStatus) {
                    groceryListStatus.textContent = 'Generating grocery list...';
                }
                eventSource.close();
                return;
            }

            // If the server sent updated recipes
            if (data.recipes) {
                console.log(`Processing ${data.recipes.length} recipe updates`);
                // Update our local cache and the DOM
                data.recipes.forEach(recipe => {
                    console.log(`Updating recipe ${recipe.id}:`, {
                        title: recipe.title,
                        hasImage: !!recipe.image,
                        imageLoading: recipe.image_loading,
                        hasIngredients: recipe.ingredients?.length > 0,
                        hasInstructions: recipe.instructions?.length > 0
                    });
                    recipesById.set(recipe.id, recipe);
                    updateRecipe(recipe);
                });

                // If this is the first update (initial templates), show the content
                if (recipesLoading.style.display !== 'none') {
                    recipesContent.innerHTML = Array.from(recipesById.values())
                        .map(recipe => createRecipeTemplateHTML(recipe))
                        .join('');
                    recipesContent.classList.remove('content-hidden');
                    recipesLoading.style.display = 'none';
                }

                // Check if all recipes have ingredients & instructions
                const allRecipes = Array.from(recipesById.values());
                const allHaveDetails = allRecipes.length > 0 && allRecipes.every(r =>
                    r.ingredients?.length && r.instructions?.length
                );
                
                if (allHaveDetails) {
                    console.log('All recipes have complete details');
                    const groceryListStatus = document.getElementById('groceryListStatus');
                    if (groceryListStatus) {
                        groceryListStatus.textContent = 'Generating grocery list...';
                    }
                }
            }
        } catch (error) {
            console.error('Error processing recipe update:', error);
            handleStreamError(error);
        }
    };

    eventSource.onopen = function() {
        console.log('EventSource connection opened');
        retryCount = 0;  // Reset retry count on successful connection
    };

    eventSource.onerror = function(error) {
        console.error('EventSource error:', error);
        retryCount++;
        
        if (retryCount >= MAX_RETRIES) {
            console.error('Max retries reached. Closing EventSource.');
            eventSource.close();
            handleStreamError('Connection failed after multiple retries');
        } else {
            console.log(`Retry attempt ${retryCount}/${MAX_RETRIES}`);
        }
    };

    return eventSource;
}

function handleStreamError(error) {
    console.error('Handling stream error:', error);
    const recipesContent = document.getElementById('recipesContent');
    const errorMessage = document.createElement('div');
    errorMessage.className = 'error-message';
    errorMessage.innerHTML = `
        <p>Error loading recipe updates: ${error}</p>
        <button onclick="location.reload()">Retry</button>
    `;
    recipesContent.appendChild(errorMessage);
}

function updateRecipe(recipe) {
    console.log(`Updating DOM for recipe ${recipe.id}`);
    const recipeElement = document.querySelector(`[data-recipe-id="${recipe.id}"]`);
    if (recipeElement) {
        // Rewrite the entire HTML with the updated recipe data
        recipeElement.outerHTML = createRecipeTemplateHTML(recipe);
        console.log(`DOM updated for recipe ${recipe.id}`);
    } else {
        console.warn(`Could not find DOM element for recipe ${recipe.id}`);
    }
} 