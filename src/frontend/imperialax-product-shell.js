(() => {
  const triggers = [...document.querySelectorAll("[data-dialog-target]")];
  let returnFocus = null;

  function closeDialog(dialog) {
    if (!dialog) return;
    if (typeof dialog.close === "function" && dialog.open) {
      dialog.close();
    } else {
      dialog.removeAttribute("open");
    }
  }

  function openDialog(dialog, trigger) {
    if (!dialog) return;
    returnFocus = trigger;
    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
    const firstControl = dialog.querySelector(
      "[data-dialog-close], textarea, input, select, button, a[href]",
    );
    firstControl?.focus({ preventScroll: true });
  }

  triggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      openDialog(document.getElementById(trigger.dataset.dialogTarget), trigger);
    });
  });

  document.querySelectorAll(".utility-dialog").forEach((dialog) => {
    dialog.querySelectorAll("[data-dialog-close]").forEach((button) => {
      button.addEventListener("click", () => closeDialog(dialog));
    });
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) closeDialog(dialog);
    });
    dialog.addEventListener("close", () => {
      returnFocus?.focus({ preventScroll: true });
      returnFocus = null;
    });
  });
})();
