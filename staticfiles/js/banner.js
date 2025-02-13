document.addEventListener('DOMContentLoaded', function () {
    const banner = document.getElementById('dynamicBanner');
    const closeBtn = document.getElementById('closeBanner');
    const navbar = document.querySelector('.navbar');
    const bannerText = document.getElementById('bannerText');

    // Banner messages
    const messages = [
        '🎉 Welcome to Our Online Store!🎉',
        '🎁 Check out the latest products and amazing discounts. 🛍️',
        '💸 Hot Deal Alert! Save big on your favorite products! 💰',
        // '🔥 Huge Sale! Get up to 10% off on all items. Shop now! 🔥',
        // '💥 Limited Time Offer! Free shipping on orders over UgX 200,000 ! 🚚',
        // '🎁 Exclusive Deal: Buy one, get one free on selected items! 🛍️',
        // '🚨 Flash Sale! 50% off for the next 24 hours only! ⏰⚡',
        // '🌟 New Arrivals! Discover the latest trends and discounts. ✨🛒',
        // '🥳 Big Savings! Get your favorite products at unbeatable prices! 💸',
    ];

    let currentMessageIndex = 0;

    // Show banner after a short delay
    setTimeout(() => {
        banner.classList.add('active');
    }, 500); // Delay in milliseconds

    // Cycle through messages
    setInterval(() => {
        currentMessageIndex = (currentMessageIndex + 1) % messages.length;
        bannerText.textContent = messages[currentMessageIndex];
    }, 5000); // Change message every 5 seconds

    // Close banner and adjust navbar
    closeBtn.addEventListener('click', () => {
        banner.classList.remove('active');
        navbar.classList.add('banner-closed');
    });
});
