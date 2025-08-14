
const CSV_URL = "https://raw.githubusercontent.com/ZachLaik/compare-models/main/chatbot_arena_leaderboard_with_cost.csv";

const searchInput = document.getElementById("search");
const tableContainer = document.getElementById("table-container");
const compareButton = document.getElementById("compare-button");
const viewAllProvidersToggle = document.getElementById("view-all-providers");
const inputTokensInput = document.getElementById("input-tokens");
const outputTokensInput = document.getElementById("output-tokens");
const calculateButton = document.getElementById("calculate-costs");

let fullData = [];
let isCompareMode = false;
let showAllProviders = false;
let calculatedCosts = null;


function createTable(data) {
  console.log("Creating table with", data.length, "rows");

  const headers = [
    "", "Model", "Arena Score", "Organization", "License", "Rank",
    "Max Input Tokens", "Max Output Tokens", "Provider",
    "Input Cost ($/1M)", "Output Cost ($/1M)"
  ];

  const dataKeys = [
    "", "Model", "Arena Score", "Organization", "License", "Rank* (UB)",
    "max_input_tokens", "max_output_tokens", "litellm_provider",
    "input_cost_per_million_tokens ($)", "output_cost_per_million_tokens ($)"
  ];

  // 👇 Only add this column if costs were computed
  if (calculatedCosts && Object.keys(calculatedCosts).length) {
    headers.push("Est. Total Cost");
    dataKeys.push("__calc_total__");
  }

  const table = document.createElement("table");
  const thead = table.createTHead();
  const headerRow = thead.insertRow();
  headers.forEach(h => {
    const th = document.createElement("th");
    th.textContent = h;
    headerRow.appendChild(th);
  });

  const tbody = table.createTBody();
  data.forEach(row => {
    const tr = tbody.insertRow();
    dataKeys.forEach((key, index) => {
      const td = tr.insertCell();

      if (index === 0) {
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "model-checkbox";
        checkbox.dataset.model = row["Model"];
        td.appendChild(checkbox);
        return;
      }

      if (key === "__calc_total__") {
        const m = row["Model"];
        const c = calculatedCosts?.[m];
        if (c) {
          td.textContent = `$${c.totalCost.toFixed(4)}`;
          td.classList.add("calculated-cost");
        } else {
          td.textContent = "—";
        }
        return;
      }

      if (key.includes("cost")) {
        const raw = row[key];
        const num = typeof raw === "number" ? raw : parseFloat(raw);
        td.textContent = Number.isFinite(num) ? `$${num.toFixed(2)}` : "N/A";
        return;
      }

      if (key.includes("tokens") || key === "Rank* (UB)") {
        const v = parseInt(row[key]);
        td.textContent = Number.isFinite(v) ? v.toLocaleString() : "N/A";
        return;
      }

      td.textContent = row[key] || "N/A";
    });
  });

  tableContainer.innerHTML = "";
  tableContainer.appendChild(table);
}

// Remove duplicate models, keeping only the first provider
function removeDuplicateModels(data) {
  if (showAllProviders) return data;

  const seen = new Set();
  return data.filter((row) => {
    const modelName = row.Model;
    if (!modelName || seen.has(modelName)) {
      return false;
    }
    seen.add(modelName);
    return true;
  });
}

// Filter data
function filterData(data, query) {
  return data.filter((row) =>
    row.Model && row.Model.toLowerCase().includes(query.toLowerCase())
  );
}

// Compare selected models
function compareSelectedModels() {
  const checkboxes = document.querySelectorAll('.model-checkbox:checked');
  if (checkboxes.length === 0) {
    alert("Please select at least one model to compare.");
    return;
  }

  const selectedModels = Array.from(checkboxes).map(cb => cb.dataset.model);
  const filteredData = fullData.filter(row => selectedModels.includes(row.Model));

  isCompareMode = true;
  compareButton.textContent = "Show All Models";
  createTable(filteredData);
}

// Show all models
function showAllModels() {
  isCompareMode = false;
  compareButton.textContent = "Compare Selected Models";
  const filtered = filterData(fullData, searchInput.value);
  const processedFiltered = removeDuplicateModels(filtered);
  createTable(processedFiltered);
}

// Calculate costs for all models (simplified)
function calculateCosts() {
  const inputTokens = parseFloat(inputTokensInput.value) || 0;
  const outputTokens = parseFloat(outputTokensInput.value) || 0;

  if (inputTokens <= 0 && outputTokens <= 0) {
    alert("Please enter valid token amounts.");
    return;
  }

  calculatedCosts = {};

  fullData.forEach(row => {
    const modelName = row["Model"];
    const inputCostPerMillion = parseFloat(row["input_cost_per_million_tokens ($)"]) || 0;
    const outputCostPerMillion = parseFloat(row["output_cost_per_million_tokens ($)"]) || 0;

    const totalInputCost = inputCostPerMillion * inputTokens;
    const totalOutputCost = outputCostPerMillion * outputTokens;

    calculatedCosts[modelName] = {
      totalInputCost,
      totalOutputCost,
      totalCost: totalInputCost + totalOutputCost
    };
  });

  // Refresh the current table view
  if (isCompareMode) {
    compareSelectedModels();
  } else {
    const filtered = filterData(fullData, searchInput.value);
    const processedFiltered = removeDuplicateModels(filtered);
    createTable(processedFiltered);
  }
}

// Manual CSV parser that handles the exact format
function parseCSVManually(csvText) {
  const lines = csvText.split('\n');
  if (lines.length === 0) return [];
  
  const headers = lines[0].split(',');
  console.log("CSV Headers detected:", headers.slice(0, 10)); // Show first 10 headers
  
  const data = [];
  
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    
    // Split by comma - this is a simple approach that should work for this specific CSV
    const values = line.split(',');
    
    if (values.length >= headers.length) {
      const row = {};
      headers.forEach((header, index) => {
        row[header.trim()] = values[index] ? values[index].trim() : '';
      });
      data.push(row);
    }
  }
  
  return data;
}

// Load and parse CSV
fetch(CSV_URL)
  .then(response => response.text())
  .then(csvText => {
    console.log("CSV fetched successfully, parsing manually...");
    
    const parsedData = parseCSVManually(csvText);
    console.log("CSV parsed successfully:", parsedData.length, "rows");
    
    // Debug specific models 
    const debugModels = parsedData.filter(row => 
      row.Model && (row.Model.includes('glm-4.5') || row.Model.includes('claude opus 4.1'))
    );
    console.log("Debug models found:", debugModels.map(m => ({
      model: m.Model,
      inputCost: m["input_cost_per_million_tokens ($)"],
      outputCost: m["output_cost_per_million_tokens ($)"]
    })));

    fullData = parsedData.filter(row => 
      row.Model && 
      row.Model.trim() !== ""
    );
    console.log("Filtered to", fullData.length, "rows with models");

    const processedData = removeDuplicateModels(fullData);
    createTable(processedData);

    searchInput.addEventListener("input", () => {
      if (!isCompareMode) {
        const filtered = filterData(fullData, searchInput.value);
        const processedFiltered = removeDuplicateModels(filtered);
        createTable(processedFiltered);
      }
    });

    viewAllProvidersToggle.addEventListener("change", () => {
      showAllProviders = viewAllProvidersToggle.checked;
      if (!isCompareMode) {
        const filtered = filterData(fullData, searchInput.value);
        const processedFiltered = removeDuplicateModels(filtered);
        createTable(processedFiltered);
      }
    });

    compareButton.addEventListener("click", () => {
      if (isCompareMode) {
        showAllModels();
      } else {
        compareSelectedModels();
      }
    });

    calculateButton.addEventListener("click", calculateCosts);

    // Real-time calculation on input change
    inputTokensInput.addEventListener("input", () => {
      if (calculatedCosts) calculateCosts();
    });

    outputTokensInput.addEventListener("input", () => {
      if (calculatedCosts) calculateCosts();
    });
  })
  .catch(error => {
    console.error("Error loading CSV:", error);
    tableContainer.innerHTML = "<p>Error loading data. Please try again later.</p>";
  });
