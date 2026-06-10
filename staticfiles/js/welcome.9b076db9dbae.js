document.addEventListener('DOMContentLoaded', function () {
    const audio = document.getElementById('welcome-audio')
    const playButton = document.getElementById('play-audio')
    const pauseButton = document.getElementById('pause-audio')
    const carousel = document.querySelector('[data-app-hero-carousel]')

    // Automatically play the audio on page load
    if (audio) {
        audio.play().catch((error) => {
            console.log('Autoplay blocked. User interaction required.')
        })
    }

    // Play button
    if (playButton && audio) playButton.addEventListener('click', () => {
        audio.play()
    })

    // Pause button
    if (pauseButton && audio) pauseButton.addEventListener('click', () => {
        audio.pause()
    })

    if (carousel) {
        const slides = Array.from(carousel.querySelectorAll('[data-app-slide]'))
        const dots = Array.from(carousel.querySelectorAll('[data-app-dot]'))
        const previousButton = carousel.querySelector('[data-app-prev]')
        const nextButton = carousel.querySelector('[data-app-next]')
        const autoplayDelay = 5500
        let activeIndex = slides.findIndex((slide) => slide.classList.contains('is-active'))
        let autoplayTimer

        if (activeIndex < 0) activeIndex = 0

        const showSlide = (nextIndex) => {
            if (!slides.length) return

            activeIndex = (nextIndex + slides.length) % slides.length

            slides.forEach((slide, index) => {
                slide.classList.toggle('is-active', index === activeIndex)
            })

            dots.forEach((dot, index) => {
                const isActive = index === activeIndex
                dot.classList.toggle('is-active', isActive)
                if (isActive) {
                    dot.setAttribute('aria-current', 'true')
                } else {
                    dot.removeAttribute('aria-current')
                }
            })
        }

        const stopAutoplay = () => {
            if (autoplayTimer) window.clearInterval(autoplayTimer)
        }

        const startAutoplay = () => {
            stopAutoplay()
            if (slides.length > 1 && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                autoplayTimer = window.setInterval(() => showSlide(activeIndex + 1), autoplayDelay)
            }
        }

        const moveManually = (nextIndex) => {
            showSlide(nextIndex)
            startAutoplay()
        }

        if (slides.length <= 1) {
            if (previousButton) previousButton.hidden = true
            if (nextButton) nextButton.hidden = true
            dots.forEach((dot) => { dot.hidden = true })
        } else {
            if (previousButton) previousButton.addEventListener('click', () => moveManually(activeIndex - 1))
            if (nextButton) nextButton.addEventListener('click', () => moveManually(activeIndex + 1))
            dots.forEach((dot, index) => {
                dot.addEventListener('click', () => moveManually(index))
            })

            carousel.addEventListener('mouseenter', stopAutoplay)
            carousel.addEventListener('mouseleave', startAutoplay)
            carousel.addEventListener('focusin', stopAutoplay)
            carousel.addEventListener('focusout', startAutoplay)
        }

        showSlide(activeIndex)
        startAutoplay()
    }
})

// Disable right-click on images
document.querySelectorAll('.disable-right-click').forEach(function (image) {
    image.addEventListener('contextmenu', function (event) {
        event.preventDefault();
    });
});
