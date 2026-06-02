document.addEventListener('DOMContentLoaded', function () {
    const banner = document.getElementById('dynamicBanner');
    const closeBtn = document.getElementById('closeBanner');
    const bannerText = document.getElementById('bannerText');

    const messages = [
        '🌸 Happy Easter! 🌼 Celebrate with 20% OFF storewide! 🐣',
        '🛍️ Hop into savings this Easter — enjoy 20% off all your favorites! 🐰',
        '🌷 Limited-Time Easter Sale! Grab your 20% discount before it’s gone! 🎁',
    ];

    let currentMessageIndex = 0;

    setTimeout(() => {
        banner.classList.add('active');
    }, 500);

    setInterval(() => {
        currentMessageIndex = (currentMessageIndex + 1) % messages.length;
        bannerText.textContent = messages[currentMessageIndex];
    }, 5000);

    closeBtn.addEventListener('click', () => {
        banner.classList.remove('active');
    });
});
