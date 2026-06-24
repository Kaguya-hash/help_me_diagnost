document.addEventListener("DOMContentLoaded", () => {
  initFileUploads();
});

function initFileUploads() {
  document.querySelectorAll("[data-file-upload]").forEach((wrapper) => {
    const input = wrapper.querySelector('input[type="file"]');
    const nameEl = wrapper.querySelector("[data-file-name]");
    const defaultText = nameEl?.dataset.defaultText || "No file chosen";

    if (!input || !nameEl) return;

    input.addEventListener("change", () => {
      const file = input.files?.[0];
      nameEl.textContent = file ? file.name : defaultText;
    });
  });
}
