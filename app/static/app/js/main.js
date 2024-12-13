document.addEventListener('DOMContentLoaded', () => {
    // Plus button functionality
    const plusButtons = document.querySelectorAll('.plus-btn');
  
    plusButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            const lineContainer = document.getElementById(targetId);
            if (!lineContainer) return;
  
            const lines = lineContainer.querySelectorAll('.line');
            const activeLines = lineContainer.querySelectorAll('.line.active');
  
            // If all lines are active, reset them
            if (activeLines.length === lines.length) {
                lines.forEach(line => line.classList.remove('active'));
                return;
            }
  
            // Otherwise, activate the next line
            const nextIndex = activeLines.length;
            if (nextIndex < lines.length) {
                lines[nextIndex].classList.add('active');
            }
        });
    });

    // Grocery list functionality
    const groceryList = document.getElementById('groceryList');
    const groceryOverlay = document.getElementById('groceryOverlay');
    
    if (groceryList && groceryOverlay) {
        groceryList.addEventListener('click', async () => {
            try {
                const response = await fetch('/app/grocery-list/');
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
        const response = await fetch(`/app/grocery-item/${itemId}/remove/`, {
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
        const response = await fetch(`/app/grocery-item/${itemId}/`);
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

// Helper function to get CSRF token
function getCsrfToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue;
}
  