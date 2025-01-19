document.addEventListener('DOMContentLoaded', () => {
    // Plus button functionality
    const plusButtons = document.querySelectorAll('.plus-btn');
  
    plusButtons.forEach(btn => {
        const targetId = btn.getAttribute('data-target');
        const lineContainer = document.getElementById(targetId);
        if (!lineContainer) return;

        // Initialize state
        btn.setAttribute('data-state', '0');
        
        // Remove any existing click listeners
        btn.replaceWith(btn.cloneNode(true));
        const newBtn = document.querySelector(`[data-target="${targetId}"]`);
        
        newBtn.addEventListener('click', () => {
            const lines = lineContainer.querySelectorAll('.line');
            const activeLines = lineContainer.querySelectorAll('.line.active');
    
            // If all lines are active, reset them
            if (activeLines.length === lines.length) {
                lines.forEach(line => line.classList.remove('active'));
                newBtn.setAttribute('data-state', '0');
                return;
            }
    
            // Otherwise, activate the next line
            const nextIndex = activeLines.length;
            if (nextIndex < lines.length) {
                lines[nextIndex].classList.add('active');
                newBtn.setAttribute('data-state', (nextIndex + 1).toString());
            }
        });
    });

    // Grocery list functionality
    const groceryList = document.getElementById('groceryList');
    const groceryOverlay = document.getElementById('groceryOverlay');
    
    if (groceryList && groceryOverlay) {
        groceryList.addEventListener('click', async () => {
            try {
                const response = await fetch('/api/grocery-list/');
                const data = await response.json();
                
                groceryOverlay.innerHTML = data.html;
                groceryOverlay.style.display = 'block';
                document.body.style.overflow = 'hidden';

                // Add event listeners to the newly added elements
                setupGroceryListHandlers(groceryOverlay);
            } catch (error) {
                console.error('Error loading grocery list:', error);
            }
        });

        groceryOverlay.addEventListener('click', (e) => {
            if (e.target === groceryOverlay) {
                closeGroceryList(groceryOverlay);
            }
        });
    }

    // Settings dropdown functionality
    const settingsDropdown = document.querySelector('.settings-dropdown');
    const settingsBtn = document.querySelector('.settings-btn');

    if (settingsBtn) {
        settingsBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            settingsDropdown.classList.toggle('active');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!settingsDropdown.contains(e.target)) {
                settingsDropdown.classList.remove('active');
            }
        });
    }
});

function setupGroceryListHandlers(overlay) {
    // Close button handler
    const closeBtn = overlay.querySelector('#closeGroceryList');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => closeGroceryList(overlay));
    }

    // Menu button handlers
    const itemMenuBtns = overlay.querySelectorAll('.item-menu-btn');
    itemMenuBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const menu = btn.nextElementSibling;
            
            // Close all other open menus
            overlay.querySelectorAll('.item-menu.active').forEach(m => {
                if (m !== menu) m.classList.remove('active');
            });
            
            menu.classList.toggle('active');
        });
    });

    // Menu option handlers
    const menuOptions = overlay.querySelectorAll('.item-menu-option');
    menuOptions.forEach(option => {
        option.addEventListener('click', async (e) => {
            e.stopPropagation();
            const action = option.dataset.action;
            const itemId = option.closest('.grocery-item')
                .querySelector('.item-menu-btn').dataset.itemId;
            
            if (action === 'remove') {
                await handleRemoveItem(itemId);
            } else if (action === 'details') {
                handleShowDetails(itemId);
            }
        });
    });
}

function closeGroceryList(overlay) {
    overlay.style.display = 'none';
    document.body.style.overflow = 'auto';
    // Close any open menus
    overlay.querySelectorAll('.item-menu.active').forEach(menu => {
        menu.classList.remove('active');
    });
}

async function handleRemoveItem(itemId) {
    try {
        const response = await fetch(`/api/grocery-item/${itemId}/remove/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Remove the item from the DOM
            const itemElement = document.querySelector(`[data-item-id="${itemId}"]`).closest('.grocery-item');
            itemElement.remove();
            
            // If section is empty, remove it
            const section = itemElement.closest('.grocery-section');
            if (section && !section.querySelector('.grocery-item')) {
                section.remove();
            }
        } else {
            console.error('Error removing item:', data.message);
        }
    } catch (error) {
        console.error('Error removing item:', error);
    }
}

async function handleShowDetails(itemId) {
    try {
        const response = await fetch(`/api/grocery-item/${itemId}/`);
        const data = await response.json();
        
        if (data.status === 'success') {
            const overlay = document.getElementById('groceryOverlay');
            const existingDetails = overlay.querySelector('.item-details');
            
            if (existingDetails) {
                existingDetails.remove();
            }
            
            overlay.insertAdjacentHTML('beforeend', data.html);
            
            // Add close handler
            const closeBtn = overlay.querySelector('#closeItemDetails');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    overlay.querySelector('.item-details').remove();
                });
            }
        } else {
            console.error('Error fetching item details:', data.message);
        }
    } catch (error) {
        console.error('Error fetching item details:', error);
    }
}

// Shared utility functions
function getCsrfToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue;
}

// Plus button functionality
function setupPlusButtons(container) {
    const plusButtons = container.querySelectorAll('.plus-btn');
    
    plusButtons.forEach(btn => {
        const targetId = btn.getAttribute('data-target');
        const lineContainer = document.getElementById(targetId);
        if (!lineContainer) return;

        // Initialize state
        btn.setAttribute('data-state', '0');
        
        // Remove any existing click listeners
        btn.replaceWith(btn.cloneNode(true));
        const newBtn = document.querySelector(`[data-target="${targetId}"]`);
        
        newBtn.addEventListener('click', () => {
            const lines = lineContainer.querySelectorAll('.line');
            const activeLines = lineContainer.querySelectorAll('.line.active');
    
            // If all lines are active, reset them
            if (activeLines.length === lines.length) {
                lines.forEach(line => line.classList.remove('active'));
                newBtn.setAttribute('data-state', '0');
                return;
            }
    
            // Otherwise, activate the next line
            const nextIndex = activeLines.length;
            if (nextIndex < lines.length) {
                lines[nextIndex].classList.add('active');
                newBtn.setAttribute('data-state', (nextIndex + 1).toString());
            }
        });
    });
}

// Preferences modal functionality
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
            window.setupRecipeStream();
        });
        
        // Setup plus buttons in modal
        setupPlusButtons(modal);
        
    } catch (error) {
        console.error('Error loading preferences modal:', error);
    }
}

// Export shared functions
window.getCsrfToken = getCsrfToken;
window.setupPlusButtons = setupPlusButtons;
window.showPreferencesModal = showPreferencesModal;
  