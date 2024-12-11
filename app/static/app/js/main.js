document.addEventListener('DOMContentLoaded', () => {
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
        for (let i = 0; i < lines.length; i++) {
            if (!lines[i].classList.contains('active')) {
                lines[i].classList.add('active');
                break;
            }
        }
      });
    });
  });
  