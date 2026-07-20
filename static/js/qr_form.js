// Sincroniza os seletores de cor (<input type=color>) com os campos de texto
// hexadecimais do formulário, e atualiza a prévia do degradê em tempo real.
(function () {
  const startPicker = document.getElementById("color_start_picker");
  const endPicker = document.getElementById("color_end_picker");
  const startHex = document.querySelector('input[name="color_start"]');
  const endHex = document.querySelector('input[name="color_end"]');
  const directionSelect = document.querySelector('select[name="gradient_direction"]');
  const preview = document.getElementById("gradient-preview");

  function cssDirection(dir) {
    switch (dir) {
      case "vertical": return "180deg";
      case "radial": return null; // usa radial-gradient
      case "square": return null;
      default: return "90deg";
    }
  }

  function updatePreview() {
    const start = startHex.value || "#4F46E5";
    const end = endHex.value || "#06B6D4";
    const dir = directionSelect ? directionSelect.value : "horizontal";
    const angle = cssDirection(dir);
    preview.style.background = angle
      ? `linear-gradient(${angle}, ${start}, ${end})`
      : `radial-gradient(circle, ${start}, ${end})`;
  }

  if (startPicker && startHex) {
    startPicker.addEventListener("input", () => {
      startHex.value = startPicker.value;
      updatePreview();
    });
    startHex.addEventListener("input", () => {
      if (/^#[0-9A-Fa-f]{6}$/.test(startHex.value)) startPicker.value = startHex.value;
      updatePreview();
    });
  }
  if (endPicker && endHex) {
    endPicker.addEventListener("input", () => {
      endHex.value = endPicker.value;
      updatePreview();
    });
    endHex.addEventListener("input", () => {
      if (/^#[0-9A-Fa-f]{6}$/.test(endHex.value)) endPicker.value = endHex.value;
      updatePreview();
    });
  }
  if (directionSelect) {
    directionSelect.addEventListener("change", updatePreview);
  }

  // Borda: mesmo esquema de sincronizacao entre <input type=color> e o campo hex
  const borderPicker = document.getElementById("border_color_picker");
  const borderHex = document.querySelector('input[name="border_color"]');
  if (borderPicker && borderHex) {
    borderPicker.addEventListener("input", () => { borderHex.value = borderPicker.value; });
    borderHex.addEventListener("input", () => {
      if (/^#[0-9A-Fa-f]{6}$/.test(borderHex.value)) borderPicker.value = borderHex.value;
    });
  }

  updatePreview();
})();
