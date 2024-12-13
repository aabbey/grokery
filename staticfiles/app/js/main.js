console.log('main.js loaded!');

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded!');
    
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
    
    console.log('Looking for grocery list:', groceryList);
    console.log('Looking for grocery overlay:', groceryOverlay);
    
    if (groceryList && groceryOverlay) {
        console.log('Found grocery list and overlay, adding click listener');
        groceryList.addEventListener('click', async () => {
            console.log('Grocery list clicked!');
            try {
                const response = await fetch('/app/grocery-list/');
                const data = await response.json();
                console.log('Received data:', data);
                
                groceryOverlay.innerHTML = data.html;
                groceryOverlay.style.display = 'block';
                document.body.style.overflow = 'hidden';
            } catch (error) {
                console.error('Error loading grocery list:', error);
            }
        });

        groceryOverlay.addEventListener('click', (e) => {
            if (e.target === groceryOverlay) {
                groceryOverlay.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });
    } else {
        console.log('Could not find grocery list or overlay elements');
    }
});
  