    ; (function () {
      const modalElement = document.getElementById("modal")
      if (!modalElement) return
      const modal = new bootstrap.Modal(modalElement)

      htmx.on("htmx:afterSwap", (e) => {
        // Response targeting #dialog => show the modal
        if (e.detail.target.id == "dialog") {
          modal.show()
        }
      })

      htmx.on("htmx:beforeSwap", (e) => {
        // Empty response targeting #dialog => hide the modal
        if (e.detail.target.id == "dialog" && !e.detail.xhr.response) {
          modal.hide()
          e.detail.shouldSwap = false
        }
      })

      // Remove dialog content after hiding
      htmx.on("hidden.bs.modal", () => {
        document.getElementById("dialog").innerHTML = ""
      })
    })()

