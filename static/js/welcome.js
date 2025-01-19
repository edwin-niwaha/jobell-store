document.addEventListener('DOMContentLoaded', function () {
    const audio = document.getElementById('welcome-audio')
    const playButton = document.getElementById('play-audio')
    const pauseButton = document.getElementById('pause-audio')

    // Automatically play the audio on page load
    audio.play().catch((error) => {
        console.log('Autoplay blocked. User interaction required.')
    })

    // Play button
    playButton.addEventListener('click', () => {
        audio.play()
    })

    // Pause button
    pauseButton.addEventListener('click', () => {
        audio.pause()
    })
})
