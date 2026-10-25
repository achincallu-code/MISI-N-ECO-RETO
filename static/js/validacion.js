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

  const gardenScene = document.querySelector("[data-garden-placement]");
  if (gardenScene) {
    const marker = gardenScene.querySelector("[data-garden-marker]");
    const status = document.querySelector("[data-garden-status]");
    const placementForms = [...document.querySelectorAll(".garden-placement-form")];
    const placedItems = [...gardenScene.querySelectorAll(".garden-placed-item")];
    const moveConfirm = document.querySelector("[data-garden-move-confirm]");
    const moveForm = document.querySelector("[data-garden-move-form]");
    const cancelButton = document.querySelector("[data-garden-cancel]");
    let activeSelection = null;
    let markerX = 50;
    let markerY = 70;
    let hasChosenPosition = false;

    const updatePlacement = (x, y) => {
      markerX = Math.min(95, Math.max(5, x));
      markerY = Math.min(88, Math.max(42, y));
      marker.style.setProperty("--placed-x", `${markerX}%`);
      marker.style.setProperty("--placed-y", `${markerY}%`);
      const form = activeSelection.type === "new" ? activeSelection.form : moveForm;
      form.querySelector('[name="position_x"]').value = markerX.toFixed(2);
      form.querySelector('[name="position_y"]').value = markerY.toFixed(2);
      marker.hidden = false;
    };

    const positionFromPointer = (event) => {
      const bounds = gardenScene.getBoundingClientRect();
      updatePlacement(
        ((event.clientX - bounds.left) / bounds.width) * 100,
        ((event.clientY - bounds.top) / bounds.height) * 100
      );
    };

    const selectPlacement = (selection, x = 50, y = 70) => {
      activeSelection?.element?.setAttribute("aria-pressed", "false");
      activeSelection = selection;
      hasChosenPosition = false;
      selection.element?.setAttribute("aria-pressed", "true");
      gardenScene.dataset.placementActive = "true";
      cancelButton.hidden = false;
      moveConfirm.hidden = selection.type !== "existing";
      moveConfirm.disabled = true;
      if (selection.type === "existing") {
        moveForm.action = selection.element.dataset.moveUrl;
        updatePlacement(Number(selection.element.dataset.positionX), Number(selection.element.dataset.positionY));
        status.textContent = `Seleccionaste ${selection.name}. Elige el nuevo lugar en el jardín y luego pulsa “Mover objeto a esta posición”.`;
      } else {
        updatePlacement(x, y);
        status.textContent = `Colocando ${selection.name}. Pulsa o toca el jardín para elegir el lugar.`;
      }
      gardenScene.focus({ preventScroll: true });
    };

    const cancelPlacement = () => {
      activeSelection?.element?.setAttribute("aria-pressed", "false");
      activeSelection = null;
      hasChosenPosition = false;
      gardenScene.dataset.placementActive = "false";
      marker.hidden = true;
      moveConfirm.hidden = true;
      moveConfirm.disabled = true;
      cancelButton.hidden = true;
      status.textContent = "Elige un artículo nuevo o selecciona uno ya colocado para moverlo.";
    };

    placementForms.forEach((form) => {
      form.querySelector(".garden-select-item")?.addEventListener("click", (event) => {
        selectPlacement({
          type: "new",
          name: form.dataset.gardenItem,
          form,
          element: event.currentTarget,
        });
      });
    });

    placedItems.forEach((item) => {
      item.addEventListener("click", (event) => {
        event.stopPropagation();
        selectPlacement({
          type: "existing",
          name: item.dataset.gardenItemName,
          element: item,
        });
      });
    });

    gardenScene.addEventListener("pointermove", (event) => {
      if (activeSelection && event.pointerType !== "touch") positionFromPointer(event);
    });

    gardenScene.addEventListener("click", (event) => {
      if (!activeSelection || event.target.closest(".garden-stage-label")) return;
      positionFromPointer(event);
      if (activeSelection.type === "new") {
        activeSelection.form.requestSubmit();
        return;
      }

      hasChosenPosition = true;
      moveConfirm.disabled = false;
      status.textContent = `Nueva posición elegida para ${activeSelection.name}. Confirma para guardar el movimiento.`;
    });

    moveConfirm.addEventListener("click", () => {
      if (activeSelection?.type === "existing" && hasChosenPosition) {
        moveForm.requestSubmit();
      }
    });

    cancelButton.addEventListener("click", cancelPlacement);

    gardenScene.addEventListener("keydown", (event) => {
      if (!activeSelection) return;
      const increments = {
        ArrowUp: [0, -2],
        ArrowDown: [0, 2],
        ArrowLeft: [-2, 0],
        ArrowRight: [2, 0],
      };
      if (increments[event.key]) {
        event.preventDefault();
        updatePlacement(markerX + increments[event.key][0], markerY + increments[event.key][1]);
        if (activeSelection.type === "existing") {
          hasChosenPosition = true;
          moveConfirm.disabled = false;
          status.textContent = `Nueva posición elegida para ${activeSelection.name}. Confirma para guardar el movimiento.`;
        }
      } else if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (activeSelection.type === "new") {
          activeSelection.form.requestSubmit();
        } else if (hasChosenPosition) {
          moveConfirm.focus();
        } else {
          status.textContent = "Usa las flechas para elegir primero la nueva posición del objeto.";
        }
      } else if (event.key === "Escape") {
        event.preventDefault();
        cancelPlacement();
      }
    });
  }

  document.querySelectorAll(".flash").forEach((message) => {
    window.setTimeout(() => {
      message.classList.add("flash-out");
      window.setTimeout(() => message.remove(), 350);
    }, 5000);
  });
});
