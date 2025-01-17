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
    // Add event listeners for rebuild buttons
    const rebuildButton = document.querySelector('.rebuild-recipes');
    if (rebuildButton) {
        rebuildButton.addEventListener('click', async (e) => {
            e.preventDefault();
            showPreferencesModal();
        });
    }

    const buildRecipesBtn = document.getElementById('buildRecipesBtn');
    if (buildRecipesBtn) {
        buildRecipesBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            showPreferencesModal();
        });
    }
});

// Helper function to setup plus buttons
function setupPlusButtons(container) {
    const plusButtons = container.querySelectorAll('.plus-btn');
    
    plusButtons.forEach(btn => {
        const targetId = btn.getAttribute('data-target');
        const lineContainer = document.getElementById(targetId);
        if (!lineContainer) return;

        // Initialize state
        btn.setAttribute('data-state', '0');
        
        btn.addEventListener('click', () => {
            const lines = lineContainer.querySelectorAll('.line');
            const activeLines = lineContainer.querySelectorAll('.line.active');
    
            // If all lines are active, reset them
            if (activeLines.length === lines.length) {
                lines.forEach(line => line.classList.remove('active'));
                btn.setAttribute('data-state', '0');
                return;
            }
    
            // Otherwise, activate the next line
            const nextIndex = activeLines.length;
            if (nextIndex < lines.length) {
                lines[nextIndex].classList.add('active');
                btn.setAttribute('data-state', (nextIndex + 1).toString());
            }
        });
    });
}

// Helper function to show preferences modal
async function showPreferencesModal() {
    try {
        // Fetch the preferences modal content
        const response = await fetch('/preferences-modal/');
        const modalHtml = await response.text();
        
        // Remove any existing modal
        const existingModal = document.querySelector('.preferences-modal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Insert modal into the page
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Get modal elements
        const modal = document.querySelector('.preferences-modal');
        const closeBtn = modal.querySelector('.close-modal-btn');
        const rebuildBtn = modal.querySelector('#rebuildWithPreferences');
        
        // Setup close button
        closeBtn.addEventListener('click', () => {
            modal.remove();
        });
        
        // Setup click outside to close
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
        
        // Setup rebuild button
        rebuildBtn.addEventListener('click', () => {
            modal.remove();
            // Start recipe generation when rebuild button is clicked
            setupRecipeStream();
        });
        
        // Setup plus buttons in modal
        setupPlusButtons(modal);
        
    } catch (error) {
        console.error('Error loading preferences modal:', error);
    }
}

function setupRecipeStream() {
    console.log('Setting up recipe generation stream');
    const eventSource = new EventSource('/api/recipes/generate/');
    const recipesContent = document.getElementById('recipesContent');
    const recipesLoading = document.getElementById('recipesLoading');
    const recipesEmpty = document.getElementById('recipesEmpty');
    const groceryListContent = document.getElementById('groceryListContent');
    const groceryListLoading = document.getElementById('groceryListLoading');
    const groceryListEmpty = document.getElementById('groceryListEmpty');
    const groceryListStatus = document.getElementById('groceryListStatus');
    const recipesById = new Map();
    
    // Show loading states
    if (recipesContent) recipesContent.style.display = 'none';
    if (recipesEmpty) recipesEmpty.style.display = 'none';
    if (recipesLoading) recipesLoading.style.display = 'block';
    if (groceryListContent) groceryListContent.style.display = 'none';
    if (groceryListEmpty) groceryListEmpty.style.display = 'none';
    if (groceryListLoading) groceryListLoading.style.display = 'block';
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('Received stream update:', data);

            switch (data.type) {
                case 'templates':
                    // Initialize recipes with templates
                    data.recipes.forEach(recipe => {
                        recipesById.set(recipe.id, recipe);
                    });
                    recipesContent.innerHTML = Array.from(recipesById.values())
                        .map(recipe => createRecipeTemplateHTML(recipe))
                        .join('');
                    recipesContent.style.display = 'block';
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
                    groceryListContent.style.display = 'block';
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
            eventSource.close();
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
    const recipesLoading = document.getElementById('recipesLoading');
    const recipesEmpty = document.getElementById('recipesEmpty');
    
    // Hide loading states
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

function createGroceryItemHTML(item) {
    return `
        <li class="grocery-item">
            <span>${item.quantity} ${item.unit} ${item.name}</span>
            <button class="item-menu-btn" data-item-id="${item.id || '0'}">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="1" />
                    <circle cx="12" cy="5" r="1" />
                    <circle cx="12" cy="19" r="1" />
                </svg>
            </button>
        </li>
    `;
} 