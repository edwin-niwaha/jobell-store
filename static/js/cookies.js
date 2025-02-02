
// // Disable the entire page interaction initially
// document.body.style.pointerEvents = "none";
// document.body.style.opacity = "0.5";

// // Enable pointer events for the buttons only
// const cookieForm = document.getElementById('cookie-form');
// const buttons = cookieForm.querySelectorAll('button');

// // Enable the buttons' pointer events while the rest of the page is disabled
// buttons.forEach(button => {
//     button.style.pointerEvents = 'auto';
//     button.style.opacity = '1';
// });


// // Handle form submission
// cookieForm.onsubmit = function (event) {
//     event.preventDefault();

//     // Set the cookies consent in localStorage
//     if (event.target.accept) {
//         localStorage.setItem('cookies_accepted', 'true');
//     } else if (event.target.decline) {
//         localStorage.setItem('cookies_accepted', 'false');
//     }

//     // Hide the cookie banner and enable page interaction
//     document.getElementById('cookie-banner').style.display = 'none';
//     document.body.style.pointerEvents = "auto";
//     document.body.style.opacity = "1";
// };

// // Check if cookies were already accepted or declined
// if (localStorage.getItem('cookies_accepted') === 'true' || localStorage.getItem('cookies_accepted') === 'false') {
//     document.getElementById('cookie-banner').style.display = 'none';
//     document.body.style.pointerEvents = "auto";
//     document.body.style.opacity = "1";
// }

// Disable the entire page interaction initially
document.body.style.pointerEvents = "none";
document.body.style.opacity = "0.5";

// Enable pointer events for the buttons only
const cookieForm = document.getElementById('cookie-form');
const buttons = cookieForm.querySelectorAll('button');

// Enable the buttons' pointer events while the rest of the page is disabled
buttons.forEach(button => {
    button.style.pointerEvents = 'auto';
    button.style.opacity = '1';
});

// Handle form submission
cookieForm.onsubmit = function (event) {
    event.preventDefault();

    // Set the cookies consent in sessionStorage
    if (event.target.accept) {
        sessionStorage.setItem('cookies_accepted', 'true');
    } else if (event.target.decline) {
        sessionStorage.setItem('cookies_accepted', 'false');
    }

    // Hide the cookie banner and enable page interaction
    document.getElementById('cookie-banner').style.display = 'none';
    document.body.style.pointerEvents = "auto";
    document.body.style.opacity = "1";
};

// Check if cookies were already accepted or declined
if (sessionStorage.getItem('cookies_accepted') === 'true' || sessionStorage.getItem('cookies_accepted') === 'false') {
    document.getElementById('cookie-banner').style.display = 'none';
    document.body.style.pointerEvents = "auto";
    document.body.style.opacity = "1";
}

