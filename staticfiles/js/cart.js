document.addEventListener("DOMContentLoaded", function () {
  const quantityInput = document.getElementById("quantity");
  const hiddenQuantityInput = document.getElementById("hidden-quantity");
  const increaseButton = document.getElementById("increase-quantity");
  const decreaseButton = document.getElementById("decrease-quantity");

  if (!quantityInput || !hiddenQuantityInput || !increaseButton || !decreaseButton) {
    return;
  }

  increaseButton.addEventListener("click", function () {
      let quantity = parseInt(quantityInput.value);
      quantityInput.value = quantity + 1;
      hiddenQuantityInput.value = quantity + 1;
    });

  decreaseButton.addEventListener("click", function () {
      let quantity = parseInt(quantityInput.value);
      if (quantity > 1) {
        quantityInput.value = quantity - 1;
        hiddenQuantityInput.value = quantity - 1;
      }
    });
});

document.addEventListener("DOMContentLoaded", function () {
  const cartToastId = "cart-toast-region";

  function ensureToastRegion() {
    let region = document.getElementById(cartToastId);
    if (!region) {
      region = document.createElement("div");
      region.id = cartToastId;
      region.className = "cart-toast-region";
      region.setAttribute("aria-live", "polite");
      region.setAttribute("aria-atomic", "true");
      document.body.appendChild(region);
    }
    return region;
  }

  function showCartToast(message, options) {
    const region = ensureToastRegion();
    const toast = document.createElement("div");
    const cartUrl = options && options.cartUrl ? options.cartUrl : "/orders/cart/";

    toast.className = "cart-toast";
    toast.innerHTML = `
      <div class="cart-toast-icon" aria-hidden="true"><i class="mdi mdi-check"></i></div>
      <div class="cart-toast-body">
        <strong>${message}</strong>
        <div class="cart-toast-actions">
          <button type="button" class="cart-toast-link" data-cart-toast-close>Continue Shopping</button>
          <a class="cart-toast-link cart-toast-link-primary" href="${cartUrl}">View Cart</a>
        </div>
      </div>
      <button type="button" class="cart-toast-close" aria-label="Dismiss notification" data-cart-toast-close>&times;</button>
    `;

    region.appendChild(toast);
    window.requestAnimationFrame(function () {
      toast.classList.add("is-visible");
    });

    const dismiss = function () {
      toast.classList.remove("is-visible");
      window.setTimeout(function () {
        toast.remove();
      }, 220);
    };

    toast.querySelectorAll("[data-cart-toast-close]").forEach(function (button) {
      button.addEventListener("click", dismiss);
    });

    window.setTimeout(dismiss, 6500);
  }

  function updateCartCount(count) {
    if (count === undefined || count === null) return;
    document.querySelectorAll("[data-cart-count], .jobell-count-badge").forEach(function (badge) {
      badge.textContent = count;
    });
  }

  function setButtonLoading(button, isLoading) {
    if (!button) return;
    if (isLoading) {
      if (!button.dataset.originalHtml) {
        button.dataset.originalHtml = button.innerHTML;
      }
      button.disabled = true;
      button.classList.add("is-loading");
      button.innerHTML = '<span class="cart-button-spinner" aria-hidden="true"></span> Adding...';
    } else {
      button.disabled = false;
      button.classList.remove("is-loading");
      if (button.dataset.originalHtml) {
        button.innerHTML = button.dataset.originalHtml;
      }
    }
  }

  document.addEventListener("submit", function (event) {
    const form = event.target.closest(".js-add-to-cart-form");
    if (!form || event.defaultPrevented) return;

    event.preventDefault();
    if (form.dataset.cartPending === "true") return;

    const button = form.querySelector("[data-cart-submit]") || form.querySelector('button[type="submit"]');
    const formData = new FormData(form);

    form.dataset.cartPending = "true";
    setButtonLoading(button, true);

    fetch(form.action, {
      method: "POST",
      body: formData,
      credentials: "same-origin",
      headers: {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest"
      }
    })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok || data.ok === false) {
            throw data;
          }
          return data;
        });
      })
      .then(function (data) {
        updateCartCount(data.cart_count);
        showCartToast(data.message || "Product added to cart successfully.", {
          cartUrl: data.cart_url
        });
      })
      .catch(function (error) {
        showCartToast(error.message || "Could not add product to cart. Please try again.", {
          cartUrl: "/orders/cart/"
        });
      })
      .finally(function () {
        form.dataset.cartPending = "false";
        setButtonLoading(button, false);
      });
  });
});
