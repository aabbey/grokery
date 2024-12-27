// Helper functions to create HTML
function createGroceryItemHTML(item) {
    return `
        <li class="grocery-item">
            <span>${item.quantity} ${item.unit} ${item.name}</span>
            <button class="item-menu-btn" data-item-id="${item.id || '0'}" onclick="handleShowDetails('${item.id || '0'}')">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="1" />
                    <circle cx="12" cy="5" r="1" />
                    <circle cx="12" cy="19" r="1" />
                </svg>
            </button>
        </li>
    `;
}

// Initialize grocery list functionality
document.addEventListener('DOMContentLoaded', async function() {
    const groceryList = document.getElementById('groceryList');
    const groceryOverlay = document.getElementById('groceryOverlay');
    const groceryListContent = document.getElementById('groceryListContent');
    const groceryListLoading = document.getElementById('groceryListLoading');

    // Load grocery list
    await loadGroceryList();

    // Set up grocery list click handlers
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
});

async function loadGroceryList() {
    const groceryListStatus = document.getElementById('groceryListStatus');
    if (groceryListStatus) {
        groceryListStatus.textContent = 'Building grocery list...';
    }

    const groceryListContent = document.getElementById('groceryListContent');
    const groceryListLoading = document.getElementById('groceryListLoading');

    try {
        console.log('Fetching grocery list...');
        const groceryResponse = await fetch('/api/grocery-list/');
        const groceryData = await groceryResponse.json();
        
        if (groceryData.status === 'success') {
            console.log('Grocery list received:', groceryData);
            groceryListContent.innerHTML = groceryData.grocery_list.map(item =>
                createGroceryItemHTML(item)
            ).join('');
            groceryListContent.classList.remove('content-hidden');
            groceryListLoading.style.display = 'none';
        } else {
            throw new Error(groceryData.message || 'Failed to load grocery list');
        }
    } catch (error) {
        console.error('Error loading grocery list:', error);
        groceryListContent.innerHTML = `
            <div class="recipe-item loading">
                <p class="loading-text" style="color: #e74c3c;">
                    Error: ${error.message}<br>
                    Please try again later.
                </p>
            </div>
        `;
        groceryListContent.classList.remove('content-hidden');
        groceryListLoading.style.display = 'none';
    }
}

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

// Helper function to get CSRF token
function getCsrfToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue;
} 