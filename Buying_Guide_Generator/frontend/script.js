const uploadForm = document.getElementById("uploadForm");
const exportBtn = document.getElementById("exportBtn");
// --- FIX START ---
// Select the existing "Download TXT" button from the HTML
const exportTxtBtn = document.getElementById("exportTxtBtn");
// --- FIX END ---
const progressContainer = document.getElementById("progressContainer");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const guidesContainer = document.getElementById("guidesContainer");
const overlay = document.getElementById("overlay");
const toastContainer = document.getElementById("toastContainer");
const searchInput = document.getElementById("searchInput");

let guidesGenerated = false;
let guidesData = [];

// ---------------------
// Toast function
// ---------------------
function showToast(msg) {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = msg;
  toastContainer.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// ---------------------
// Drag & Drop CSV
// ---------------------
uploadForm.addEventListener("dragover", (e) => { e.preventDefault(); uploadForm.classList.add("dragover"); });
uploadForm.addEventListener("dragleave", () => uploadForm.classList.remove("dragover"));
uploadForm.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadForm.classList.remove("dragover");
  document.getElementById("csvFile").files = e.dataTransfer.files;
});

// ---------------------
// Upload CSV
// ---------------------
uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById("csvFile");
  if (!fileInput.files.length) return showToast("Please select a CSV file!");

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  progressContainer.classList.remove("hidden");
  progressText.classList.remove("hidden");
  progressBar.style.width = "0%";
  progressText.textContent = "Generating guide... 0%";
  overlay.classList.remove("hidden");

  let progress = 0;
  const interval = setInterval(() => {
    if (progress < 90) {
      progress += 10;
      progressBar.style.width = `${progress}%`;
      progressText.textContent = `Generating guide... ${progress}%`;
    }
  }, 800);

  try {
    const response = await fetch("http://127.0.0.1:8002/upload/", { method: "POST", body: formData });
    clearInterval(interval);

    if (!response.ok) { const err = await response.json(); throw new Error(err.error || "Upload failed"); }

    const data = await response.json();
    guidesGenerated = true;
    guidesData = data.buying_guides;

    progressBar.style.width = "100%";
    progressText.textContent = "✅ Guide Generated!";
    overlay.classList.add("hidden");

    // Show guides
    guidesContainer.innerHTML = "";
    guidesData.forEach((item, idx) => {
      const card = document.createElement("div");
      card.className = "bg-white dark:bg-gray-800 p-6 rounded-xl shadow show";
      card.innerHTML = `
        <h3 class="text-xl font-bold mb-2">Guide ${idx + 1}</h3>
        <button class="toggleBtn bg-yellow-400 px-3 py-1 rounded mb-2">Toggle JSON</button>
        <pre class="text-sm whitespace-pre-wrap hidden">${JSON.stringify(item, null, 2)}</pre>
      `;
      guidesContainer.appendChild(card);

      const toggleBtn = card.querySelector(".toggleBtn");
      const pre = card.querySelector("pre");
      toggleBtn.addEventListener("click", () => pre.classList.toggle("hidden"));
    });

    showToast("Guides generated successfully!");
  } catch (error) {
    clearInterval(interval);
    progressText.textContent = "❌ Error generating guide";
    overlay.classList.add("hidden");
    console.error(error);
    showToast("Error: " + error.message);
  }
});

// ---------------------
// Export JSON
// ---------------------
exportBtn.addEventListener("click", async () => {
  if (!guidesGenerated) return showToast("Please upload CSV and generate guides first!");

  try {
    const response = await fetch("http://127.0.0.1:8002/export/");
    if (!response.ok) throw new Error("Export failed");

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "buying_guides.json";
    document.body.appendChild(a);
    a.click();
    a.remove();

    showToast("JSON downloaded successfully!");
  } catch (error) {
    console.error(error);
    showToast("Error: " + error.message);
  }
});

// ---------------------
// Search/Filter
// ---------------------
searchInput.addEventListener("input", () => {
  const query = searchInput.value.toLowerCase();
  guidesContainer.childNodes.forEach(card => {
    const jsonText = card.querySelector("pre")?.textContent.toLowerCase() || "";
    card.style.display = jsonText.includes(query) ? "block" : "none";
  });
});

// --- FIX START ---
// The old code that created a new button has been removed.
// The event listener is now correctly attached to the button from your HTML.
// --- FIX END ---

// ---------------------
// Export TXT
// ---------------------
exportTxtBtn.addEventListener("click", async () => {
  if (!guidesGenerated) return showToast("Please upload CSV and generate guides first!");

  try {
    const response = await fetch("http://127.0.0.1:8002/export-txt/");
    if (!response.ok) throw new Error("Export TXT failed");

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "buying_guides.txt";
    document.body.appendChild(a);
    a.click();
    a.remove();

    showToast("TXT downloaded successfully!");
  } catch (error) {
    console.error(error);
    showToast("Error: " + error.message);
  }
});