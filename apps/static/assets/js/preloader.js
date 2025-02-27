document.addEventListener('DOMContentLoaded', function() {
    // Get preloader element
    const preloader = document.getElementById('preloader');
    if (!preloader) return;
    
    // Use CSS transitions instead of jQuery for smoother performance
    window.addEventListener('load', function() {
      preloader.style.opacity = '0';
      preloader.style.transition = 'opacity 0.5s ease-out';
      
      // Remove from DOM after transition
      setTimeout(function() {
        preloader.style.display = 'none';
      }, 500);
    });
  });