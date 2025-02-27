(function() {
  // Function to initialize the stars
  function initStars() {
    try {
      console.log("Stars animation: Initializing");
      
      // Check if canvas already exists to prevent duplicates
      if (document.getElementById('stars-canvas')) {
        console.log("Stars animation: Canvas already exists");
        return;
      }
      
      const canvas = document.createElement('canvas');
      canvas.id = 'stars-canvas';
      Object.assign(canvas.style, {
        position: 'fixed',
        top: '0',
        left: '0',
        width: '100%',
        height: '100%',
        zIndex: '-1',
        pointerEvents: 'none',
        backgroundColor: 'rgba(0, 0, 0, 1)' // Add background color to canvas itself
      });
      
      // Append to body
      document.body.appendChild(canvas);
      console.log("Stars animation: Canvas appended to body");
      
      const ctx = canvas.getContext('2d');
      const stars = [];
      const starCount = 200; // Adjust as needed

      function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        if (stars.length === 0) {
          createStars();
        } else {
          for (let i = 0; i < stars.length; i++) {
            if (stars[i].x > canvas.width) stars[i].x = Math.random() * canvas.width;
            if (stars[i].y > canvas.height) stars[i].y = Math.random() * canvas.height;
          }
        }
      }

      function createStars() {
        stars.length = 0;
        for (let i = 0; i < starCount; i++) {
          stars.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            radius: Math.random() * 0.8 + 0.2, // Smaller stars (0.2 to 1.0 pixels)
            speed: Math.random() * 0.15 + 0.05,
            opacity: Math.random() * 0.5 + 0.3
          });
        }
      }

      function drawStars() {
        // Complete clear with solid color - no trails
        ctx.fillStyle = 'rgba(0, 0, 0, 1)'; // Solid black background
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        for (let i = 0; i < starCount; i++) {
          const star = stars[i];
          ctx.beginPath();
          ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(255, 255, 255, ${star.opacity})`;
          ctx.fill();

          // Move star
          star.y += star.speed;

          // Subtle twinkling effect (optional)
          star.opacity = Math.max(0.2, Math.min(0.8, star.opacity + (Math.random() * 0.06 - 0.03)));

          // Reset star when it moves off screen
          if (star.y > canvas.height) {
            star.y = 0;
            star.x = Math.random() * canvas.width;
          }
        }
        requestAnimationFrame(drawStars);
      }

      window.addEventListener('resize', resizeCanvas);
      resizeCanvas();
      drawStars();
      
    } catch (error) {
      console.error("Stars animation error:", error);
    }
  }

  // Try multiple ways to ensure the script runs after DOM is ready
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    // DOM already ready, initialize immediately
    setTimeout(initStars, 100); // Short delay to ensure everything is really ready
  } else {
    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
      setTimeout(initStars, 100);
    });
  }
  
  // Backup initialization - if for some reason the above methods don't work
  window.addEventListener('load', function() {
    // If canvas doesn't exist yet by load event, initialize it
    if (!document.getElementById('stars-canvas')) {
      setTimeout(initStars, 500);
    }
  });
})();