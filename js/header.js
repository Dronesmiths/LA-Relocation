document.addEventListener("DOMContentLoaded", function () {
  // 🟥 Global Header Injection
  const headerHTML = `
  <header>
    <a href="/" class="nav-brand">LA<span>Relocation</span></a>
    <!-- Mobile Nav Toggle -->
    <div class="menu-toggle">
      <i class="fas fa-bars"></i>
    </div>
    <nav>
      <ul>
        <li><a href="/">Home</a></li>
        <li><a href="/search-homes/">Search Homes</a></li>
        <li><a href="/sell-your-home/">Sell</a></li>
        <li><a href="/about/">About</a></li>
        <li><a href="/contact/">Contact</a></li>
      </ul>
    </nav>
  </header>
  `;

  // Insert header at the top of the body
  document.body.insertAdjacentHTML("afterbegin", headerHTML);

  // 📱 Re-initialize Mobile Nav Toggle
  setTimeout(() => {
    const menuToggle = document.querySelector('.menu-toggle');
    const navUl = document.querySelector('nav ul');

    if (menuToggle && navUl) {
      menuToggle.addEventListener('click', function () {
        navUl.style.display = navUl.style.display === 'flex' ? 'none' : 'flex';
      });
    }
  }, 50); // Small delay to ensuring DOM insertion
});
