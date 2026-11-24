const copyButton = document.querySelector(".copy-button");
if (copyButton) {
  copyButton.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(copyButton.dataset.copy || "");
      copyButton.textContent = "Copied";
      window.setTimeout(() => { copyButton.textContent = "Copy"; }, 1600);
    } catch {
      copyButton.textContent = "Select text";
    }
  });
}
