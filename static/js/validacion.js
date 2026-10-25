document.addEventListener("DOMContentLoaded", () => {
  const accountMenu = document.querySelector(".account-menu");
  const accountToggle = accountMenu?.querySelector(".account-menu-toggle");
  const accountPanel = accountMenu?.querySelector(".account-menu-panel");

  if (accountToggle && accountPanel) {
    const closeAccountMenu = (restoreFocus = false) => {
      accountPanel.hidden = true;
      accountToggle.setAttribute("aria-expanded", "false");
      accountToggle.setAttribute("aria-label", "Abrir opciones de cuenta");
      if (restoreFocus) accountToggle.focus();
    };

    accountToggle.addEventListener("click", () => {
      const isOpen = accountToggle.getAttribute("aria-expanded") === "true";
      if (isOpen) {
        closeAccountMenu();
        return;
      }

      accountPanel.hidden = false;
      accountToggle.setAttribute("aria-expanded", "true");
      accountToggle.setAttribute("aria-label", "Cerrar opciones de cuenta");
    });

    document.addEventListener("click", (event) => {
      if (!accountMenu.contains(event.target)) closeAccountMenu();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !accountPanel.hidden) {
        closeAccountMenu(true);
      }
    });

    accountPanel.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => closeAccountMenu());
    });
  }

  document.querySelectorAll("[data-password-toggle]").forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const input = toggle.closest(".input-icon")?.querySelector("input");
      if (!input) return;

      const isVisible = input.type === "password";
      input.type = isVisible ? "text" : "password";
      toggle.classList.toggle("is-visible", isVisible);
      toggle.setAttribute("aria-pressed", String(isVisible));
      toggle.setAttribute(
        "aria-label",
        isVisible ? "Ocultar contraseña" : "Mostrar contraseña"
      );
    });
  });

  const authPanel = document.querySelector(".auth-layout[data-auth-screen]");
  if (authPanel) {
    const transitionKey = "ecoRetoAuthTransition";
    const supportsNativeTransition =
      typeof document.startViewTransition === "function" &&
      CSS.supports("view-transition-name: eco-auth");
    let isTransitioning = false;
    const planet = authPanel.querySelector(".auth-planet");
    const planetFeedback = authPanel.querySelector("#planet-feedback");
    let planetAnimationTimer;

    planet?.addEventListener("click", () => {
      planet.classList.remove("is-activated");
      requestAnimationFrame(() => planet.classList.add("is-activated"));
      planetFeedback.textContent = "¡Gracias por cuidar nuestro planeta!";
      window.clearTimeout(planetAnimationTimer);
      planetAnimationTimer = window.setTimeout(() => {
        planet.classList.remove("is-activated");
      }, 1100);
    });

    const incomingScreen = sessionStorage.getItem(transitionKey);
    sessionStorage.removeItem(transitionKey);

    if (incomingScreen === authPanel.dataset.authScreen) {
      authPanel.classList.add(
        supportsNativeTransition
          ? "auth-native-transition"
          : incomingScreen === "register"
            ? "auth-enter-from-right"
            : "auth-enter-from-left"
      );
    }

    authPanel.querySelectorAll("[data-auth-target]").forEach((link) => {
      link.addEventListener("click", (event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
          return;
        }

        const targetScreen = link.dataset.authTarget;
        if (targetScreen !== "login" && targetScreen !== "register") return;

        if (
          isTransitioning ||
          window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ) {
          return;
        }

        event.preventDefault();
        isTransitioning = true;
        sessionStorage.setItem(transitionKey, targetScreen);

        if (supportsNativeTransition) {
          window.location.assign(link.href);
          return;
        }

        authPanel.classList.add(
          targetScreen === "register" ? "auth-exit-to-register" : "auth-exit-to-login"
        );
        window.setTimeout(() => window.location.assign(link.href), 260);
      });
    });
  }

  const updateActiveSection = () => {
    const section = window.location.hash.slice(1);
    if (!section) return;

    document.querySelectorAll(".nav-menu [data-section]").forEach((link) => {
      const isActive = link.dataset.section === section;
      link.classList.toggle("active", isActive);
      if (isActive) {
        link.setAttribute("aria-current", "location");
      } else {
        link.removeAttribute("aria-current");
      }
    });
  };

  updateActiveSection();
  window.addEventListener("hashchange", updateActiveSection);

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.dataset.confirm || "¿Deseas continuar?";
      if (!window.confirm(message)) event.preventDefault();
    });
  });

  document.querySelectorAll("form[data-validate]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const title = form.querySelector('[name="titulo"]');
      const description = form.querySelector('[name="descripcion"]');
      if (title && !title.value.trim()) {
        event.preventDefault();
        title.focus();
        alert("Escribe el nombre de la acción.");
      } else if (description && !description.value.trim()) {
        event.preventDefault();
        description.focus();
        alert("Escribe una descripción para la acción.");
      }
    });
  });

  document.querySelectorAll(".flash").forEach((message) => {
    window.setTimeout(() => {
      message.classList.add("flash-out");
      window.setTimeout(() => message.remove(), 350);
    }, 5000);
  });
});
