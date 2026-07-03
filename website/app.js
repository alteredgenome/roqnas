/* ==============================================================================
   RoqNAS OS Landing Page Script
   ============================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  const copyBtn = document.getElementById('copy-btn');
  const installCmd = document.getElementById('install-cmd');
  const header = document.querySelector('header');

  // Copy to clipboard function
  if (copyBtn && installCmd) {
    copyBtn.addEventListener('click', () => {
      const textToCopy = installCmd.textContent;
      navigator.clipboard.writeText(textToCopy).then(() => {
        // Toggle tooltip
        copyBtn.classList.add('copy-tooltip', 'active');
        setTimeout(() => {
          copyBtn.classList.remove('active');
        }, 1500);
      }).catch(err => {
        console.error('Could not copy command to clipboard', err);
      });
    });
  }

  // Header scroll transition styling
  window.addEventListener('scroll', () => {
    if (window.scrollY > 20) {
      header.classList.add('bg-slate-950/90', 'shadow-lg', 'border-b', 'border-white/10');
      header.classList.remove('bg-slate-950/60', 'border-white/5');
    } else {
      header.classList.add('bg-slate-950/60', 'border-white/5');
      header.classList.remove('bg-slate-950/90', 'shadow-lg', 'border-b', 'border-white/10');
    }
  });

  // Animated elements on scroll reveal
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('fade-in');
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  document.querySelectorAll('.glass-panel').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
    observer.observe(el);
  });

  // Add scroll styles dynamically
  const styleSheet = document.createElement("style");
  styleSheet.type = "text/css";
  styleSheet.innerText = `
    .fade-in {
      opacity: 1 !important;
      transform: translateY(0) !important;
    }
  `;
  document.head.appendChild(styleSheet);
});
