document.addEventListener("DOMContentLoaded", function () {
  const toggleButton = document.getElementById("toggleSidebar");
  const sidebar = document.getElementById("sidebar");

  // Toggle sidebar visibility
  toggleButton.addEventListener("click", function () {
    sidebar.classList.toggle("active");
  });

  // Hide sidebar when clicking outside
  document.addEventListener("click", function (event) {
    if (!sidebar.contains(event.target) && !toggleButton.contains(event.target)) {
      sidebar.classList.remove("active");
    }
  });
 
}
);


