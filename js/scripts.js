
/* 🎞 Hero Script */
document.addEventListener("DOMContentLoaded", () => {
  // Hero Slider
  let slides = document.querySelectorAll('#laHeroSlider .slide');
  if(slides.length > 0) {
    let currentSlide = 0;
    let dotsContainer = document.getElementById('sliderDots');

    // Create dots
    slides.forEach((_, i) => {
      const dot = document.createElement('div');
      dot.classList.add('dot');
      if (i === 0) dot.classList.add('active');
      dot.addEventListener('click', () => showSlide(i));
      dotsContainer.appendChild(dot);
    });

    let dots = document.querySelectorAll('.dot');

    window.showSlide = function(next) {
      slides[currentSlide].classList.remove('active');
      dots[currentSlide].classList.remove('active');
      currentSlide = (next + slides.length) % slides.length;
      slides[currentSlide].classList.add('active');
      dots[currentSlide].classList.add('active');
    };

    // Auto-rotate slides every 6 seconds
    setInterval(() => {
      showSlide(currentSlide + 1);
    }, 6000);
  }

  // Testimonial Slider
  const tSlides = document.querySelectorAll(".testimonial-slide");
  if(tSlides.length > 0) {
    const tDotsContainer = document.querySelector(".dots");
    let tCurrent = 0;

    // Create dots
    tSlides.forEach((_,i)=>{
      const dot = document.createElement("button");
      dot.addEventListener("click", () => showTSlide(i));
      tDotsContainer.appendChild(dot);
    });
    const tDots = document.querySelectorAll(".dots button");

    function showTSlide(i){
      tSlides[tCurrent].classList.remove("active");
      if(tDots.length > tCurrent) tDots[tCurrent].classList.remove("active");
      tCurrent = (i + tSlides.length) % tSlides.length;
      tSlides[tCurrent].classList.add("active");
      if(tDots.length > tCurrent) tDots[tCurrent].classList.add("active");
    }

    const tNext = document.querySelector(".next");
    const tPrev = document.querySelector(".prev");
    if(tNext) tNext.onclick = () => showTSlide(tCurrent + 1);
    if(tPrev) tPrev.onclick = () => showTSlide(tCurrent - 1);

    // Auto play
    let tTimer = setInterval(() => showTSlide(tCurrent + 1), 7000);
    const slider = document.querySelector(".testimonial-slider");
    if(slider) {
      slider.addEventListener("mouseenter", () => clearInterval(tTimer));
      slider.addEventListener("mouseleave", () => tTimer = setInterval(() => showTSlide(tCurrent + 1), 7000));
    }
    // Init
    showTSlide(0);
  }

  // FAQ Accordion
  document.querySelectorAll('.faq-question').forEach(button => {
    button.addEventListener('click', () => {
      const faqItem = button.parentElement;
      const openItem = document.querySelector('.faq-item.open');
      if (openItem && openItem !== faqItem) openItem.classList.remove('open');
      faqItem.classList.toggle('open');
    });
  });

  // Footer Balloon Animation
  (function(){
    const canvas = document.getElementById('remaxBalloonCanvas');
    if(!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const img = new Image();
    img.src = "/images/Remax-Balloon-Transparent.webp";
    let width, height, balloons = [];
    const numBalloons = 6;

    function init(){
      width = canvas.offsetWidth;
      height = canvas.offsetHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      balloons = Array.from({length: numBalloons}, () => ({
        x: Math.random() * width,
        y: height + Math.random() * 200,
        size: 60 + Math.random() * 120,
        speed: 0.8 + Math.random() * 0.7,
        swayPhase: Math.random() * Math.PI * 2,
        swaySpeed: 0.0025 + Math.random() * 0.006,
        tilt: (Math.random() - 0.5) * 2,
        opacity: 0.4 + Math.random() * 0.4
      }));
    }

    function draw(){
      ctx.clearRect(0, 0, width, height);
      balloons.forEach(b => {
        const aspect = img.width / img.height || 1;
        const w = b.size * aspect, h = b.size;
        b.y -= b.speed;
        b.x += Math.sin(b.swayPhase += b.swaySpeed) * 0.5;
        ctx.save();
        ctx.globalAlpha = b.opacity;
        ctx.translate(b.x, b.y);
        ctx.rotate(b.tilt * Math.PI / 180);
        ctx.drawImage(img, -w / 2, -h / 2, w, h);
        ctx.restore();
        if(b.y + h < -60){
          b.y = height + Math.random() * 200;
          b.x = Math.random() * width;
        }
      });
      requestAnimationFrame(draw);
    }

    img.onload = () => { init(); draw(); };
    window.addEventListener('resize', init);
  })();

});
