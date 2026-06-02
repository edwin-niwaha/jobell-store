(function () {
  'use strict'

  const MOBILE_QUERY = '(max-width: 991.98px)'
  const XL_QUERY = '(max-width: 1199.98px)'

  function isBootstrapCollapseReady() {
    return Boolean(window.bootstrap && window.bootstrap.Collapse)
  }

  function closeBootstrapMenu(menu, toggle) {
    if (!menu || !menu.classList.contains('show')) return
    if (isBootstrapCollapseReady()) {
      window.bootstrap.Collapse.getOrCreateInstance(menu, { toggle: false }).hide()
    } else {
      menu.classList.remove('show')
    }
    if (toggle) toggle.setAttribute('aria-expanded', 'false')
  }

  function initResponsiveNavbar(navbar) {
    const toggle = navbar.querySelector('[data-bs-toggle="collapse"][data-bs-target]')
    const targetSelector = toggle ? toggle.getAttribute('data-bs-target') : ''
    const menu = targetSelector ? navbar.querySelector(targetSelector) : navbar.querySelector('[data-navbar-menu], .navbar-collapse')
    if (!toggle || !menu) return

    menu.addEventListener('shown.bs.collapse', function () {
      toggle.setAttribute('aria-expanded', 'true')
    })
    menu.addEventListener('hidden.bs.collapse', function () {
      toggle.setAttribute('aria-expanded', 'false')
    })

    navbar.addEventListener('click', function (event) {
      const link = event.target.closest('a')
      if (!link || !menu.contains(link)) return
      if (link.classList.contains('dropdown-toggle') || link.getAttribute('data-bs-toggle') === 'dropdown') return
      closeBootstrapMenu(menu, toggle)
    })

    document.addEventListener('click', function (event) {
      if (!menu.classList.contains('show')) return
      if (navbar.contains(event.target)) return
      closeBootstrapMenu(menu, toggle)
    })

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') closeBootstrapMenu(menu, toggle)
    })

    window.addEventListener('pageshow', function () {
      closeBootstrapMenu(menu, toggle)
    })

    window.addEventListener('resize', function () {
      if (!window.matchMedia(XL_QUERY).matches) closeBootstrapMenu(menu, toggle)
    })
  }

  function setDashboardMenuOpen(sidebar, toggle, isOpen) {
    if (!sidebar) return
    sidebar.classList.toggle('active', isOpen)
    document.body.classList.toggle('dashboard-menu-open', isOpen)
    if (toggle) toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false')
  }

  function initDashboardNavbar(navbar) {
    const sidebar = document.querySelector('.sidebar-offcanvas')
    const toggle = navbar.querySelector('[data-dashboard-menu-toggle], [data-toggle="offcanvas"]')
    if (!sidebar || !toggle) return

    toggle.addEventListener('click', function (event) {
      event.preventDefault()
      event.stopPropagation()
      setDashboardMenuOpen(sidebar, toggle, !sidebar.classList.contains('active'))
    })

    sidebar.addEventListener('click', function (event) {
      const link = event.target.closest('a')
      if (!link) return
      const isCollapseToggle = link.getAttribute('data-bs-toggle') === 'collapse' || link.getAttribute('data-toggle') === 'collapse'
      const href = link.getAttribute('href') || ''
      if (isCollapseToggle || href === '#' || href.startsWith('javascript:')) return
      if (window.matchMedia(MOBILE_QUERY).matches) {
        setDashboardMenuOpen(sidebar, toggle, false)
      }
    })

    document.addEventListener('click', function (event) {
      if (!sidebar.classList.contains('active')) return
      if (sidebar.contains(event.target) || navbar.contains(event.target)) return
      setDashboardMenuOpen(sidebar, toggle, false)
    })

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') setDashboardMenuOpen(sidebar, toggle, false)
    })

    window.addEventListener('pageshow', function () {
      setDashboardMenuOpen(sidebar, toggle, false)
    })

    window.addEventListener('resize', function () {
      if (!window.matchMedia(MOBILE_QUERY).matches) {
        setDashboardMenuOpen(sidebar, toggle, false)
      }
    })
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-responsive-navbar]').forEach(initResponsiveNavbar)
    document.querySelectorAll('[data-dashboard-navbar]').forEach(initDashboardNavbar)
  })
})()
