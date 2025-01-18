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
console.log('Recipe.js loaded');

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded - Starting recipe initialization');
    
    // Debug: Check if recipes exist in window
    console.log('Current window.recipes:', window.recipes);
    
    // Add event listeners for rebuild buttons
    const rebuildButton = document.querySelector('.rebuild-recipes');
    console.log('Rebuild button found:', !!rebuildButton);
    
    if (rebuildButton) {
        rebuildButton.addEventListener('click', async (e) => {
            console.log('Rebuild button clicked');
            e.preventDefault();
            showPreferencesModal();
        });
    }

    const buildRecipesBtn = document.getElementById('buildRecipesBtn');
    console.log('Build recipes button found:', !!buildRecipesBtn);
    
    if (buildRecipesBtn) {
        buildRecipesBtn.addEventListener('click', async (e) => {
            console.log('Build recipes button clicked');
            e.preventDefault();
            showPreferencesModal();
        });
    }

    // Debug: Check for recipe items on page load
    const recipeItems = document.querySelectorAll('.recipe-item');
    console.log('Recipe items found on page:', recipeItems.length);
    recipeItems.forEach((item, index) => {
        console.log(`Recipe item ${index}:`, {
            id: item.dataset.recipeId,
            html: item.innerHTML.substring(0, 100) + '...' // Log first 100 chars
        });
    });

    // Add direct click handlers to recipe items
    recipeItems.forEach(item => {
        item.addEventListener('click', function(e) {
            console.log('Direct recipe item click detected:', this.dataset.recipeId);
        });
    });

    // Add click handlers for recipe items (delegation)
    document.addEventListener('click', function(e) {
        console.log('Document click detected on:', e.target.tagName, e.target.className);
        
        const recipeItem = e.target.closest('.recipe-item');
        console.log('Closest recipe-item:', recipeItem?.dataset?.recipeId);
        
        if (recipeItem) {
            const recipeId = recipeItem.dataset.recipeId;
            console.log('Processing click for recipe ID:', recipeId);
            console.log('Recipe IDs available:', window.recipes.map(r => r.id));
            
            // Convert recipeId to number for comparison
            const recipe = window.recipes?.find(r => r.id === parseInt(recipeId, 10));
            console.log('Found recipe object:', recipe);
            
            if (recipe && recipe.ingredients && recipe.instructions) {
                console.log('Recipe has required data, showing modal');
                showRecipeModal(recipe);
            } else {
                console.log('Recipe missing required data:', {
                    hasRecipe: !!recipe,
                    hasIngredients: recipe?.ingredients?.length > 0,
                    hasInstructions: recipe?.instructions?.length > 0
                });
                if (recipe) {
                    console.log('Recipe details:', {
                        id: recipe.id,
                        title: recipe.title,
                        hasIngredients: Array.isArray(recipe.ingredients),
                        ingredientsLength: recipe.ingredients?.length,
                        hasInstructions: Array.isArray(recipe.instructions),
                        instructionsLength: recipe.instructions?.length
                    });
                }
            }
        }
    });

    // Close modal on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            console.log('Escape key pressed');
            closeRecipeModal();
        }
    });
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
    
    // Store recipes globally for click handling
    window.recipes = [];
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('Received stream update:', data);

            switch (data.type) {
                case 'templates':
                    console.log('Received recipe templates:', data.recipes);
                    // Store recipes globally
                    window.recipes = data.recipes;
                    break;
                    
                case 'updates':
                    console.log('Received recipe updates:', data.recipes);
                    // Update global recipes
                    data.recipes.forEach(recipe => {
                        const index = window.recipes.findIndex(r => r.id === recipe.id);
                        if (index !== -1) {
                            window.recipes[index] = recipe;
                        }
                    });
                    break;
            }
        } catch (error) {
            console.error('Error processing stream update:', error);
        }
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

// Recipe modal functionality
function showRecipeModal(recipe) {
    console.log('Showing modal for recipe:', recipe.title);
    
    const modal = document.getElementById('recipeDetailsModal');
    console.log('Modal element found:', !!modal);
    
    const modalImage = document.getElementById('modalRecipeImage');
    const modalTitle = document.getElementById('modalRecipeTitle');
    const modalIngredients = document.getElementById('modalRecipeIngredients');
    const modalInstructions = document.getElementById('modalRecipeInstructions');
    const closeBtn = modal.querySelector('.close-modal-btn');

    console.log('Modal elements found:', {
        image: !!modalImage,
        title: !!modalTitle,
        ingredients: !!modalIngredients,
        instructions: !!modalInstructions,
        closeBtn: !!closeBtn
    });

    // Set image and title
    if (recipe.image) {
        modalImage.src = `data:image/jpeg;base64,${recipe.image}`;
        modalImage.alt = recipe.title;
        modalImage.style.display = 'block';
    } else {
        modalImage.style.display = 'none';
    }
    modalTitle.textContent = recipe.title;

    // Set ingredients
    console.log('Setting ingredients:', recipe.ingredients);
    modalIngredients.innerHTML = recipe.ingredients
        .map(ingredient => `<li>${ingredient}</li>`)
        .join('');

    // Set instructions
    console.log('Setting instructions:', recipe.instructions);
    modalInstructions.innerHTML = recipe.instructions
        .map(instruction => `<li>${instruction}</li>`)
        .join('');

    // Show modal with flex display and add active class
    modal.style.display = 'flex';
    modal.classList.add('active');
    
    // Setup close button click handler
    closeBtn.addEventListener('click', () => {
        console.log('Close button clicked');
        closeRecipeModal();
    });

    // Setup click outside to close
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            console.log('Clicked outside modal');
            closeRecipeModal();
        }
    });
    
    console.log('Modal display style:', modal.style.display);
    console.log('Modal classes:', modal.className);
}

// Function to close the recipe modal
function closeRecipeModal() {
    console.log('Closing recipe modal');
    const modal = document.getElementById('recipeDetailsModal');
    modal.style.display = 'none';
    modal.classList.remove('active');
} 