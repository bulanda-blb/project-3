
document.addEventListener("DOMContentLoaded", function () {
  const buttons = document.querySelectorAll(".toggle-btn");
  const sections = document.querySelectorAll(".job-section");

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      sections.forEach(section => section.classList.remove("active-section"));
      document.getElementById(btn.dataset.target).classList.add("active-section");
    });
  });
});
