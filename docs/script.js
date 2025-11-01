
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
let selectedModels = new Set(); // Track selected models globally
let currentSort = { key: null, ascending: true }; // Track current sort state

// Sort data by a specific column
function sortData(data, sortKey) {
  return [...data].sort((a, b) => {
    let aVal = a[sortKey];
    let bVal = b[sortKey];
    
    // Handle calculated costs specially
    if (sortKey === "__calc_total__") {
      aVal = calculatedCosts?.[a.Model]?.totalCost ?? -Infinity;
      bVal = calculatedCosts?.[b.Model]?.totalCost ?? -Infinity;
    } else {
      // Parse numeric values
      const aNum = parseFloat(aVal);
      const bNum = parseFloat(bVal);
      
      if (Number.isFinite(aNum) && Number.isFinite(bNum)) {
        aVal = aNum;
        bVal = bNum;
      }
    }
    
    // Handle N/A or missing values (put them at the end)
    if (aVal === null || aVal === undefined || aVal === "" || !Number.isFinite(aVal)) {
      return 1;
    }
    if (bVal === null || bVal === undefined || bVal === "" || !Number.isFinite(bVal)) {
      return -1;
    }
    
    // Compare values
    if (aVal < bVal) return currentSort.ascending ? -1 : 1;
    if (aVal > bVal) return currentSort.ascending ? 1 : -1;
    return 0;
  });
}

function createTable(data) {
  console.log("Creating table with", data.length, "rows");
  console.log("Currently selected models:", Array.from(selectedModels));

  const headers = [
    "", "Rank", "Model", "Score", "Max In", "Max Out",
    "In Cost", "Out Cost", "Org", "Provider", "License", "Try"
  ];

  const dataKeys = [
    "", "Rank* (UB)", "Model", "Arena Score", "max_input_tokens", "max_output_tokens",
    "input_cost_per_million_tokens ($)", "output_cost_per_million_tokens ($)", "Organization", "litellm_provider", "License", "__try_blend__"
  ];

  // 👇 Only add this column if costs were computed
  if (calculatedCosts && Object.keys(calculatedCosts).length) {
    headers.push("Est. Total Cost");
    dataKeys.push("__calc_total__");
  }

  const table = document.createElement("table");
  const thead = table.createTHead();
  const headerRow = thead.insertRow();
  
  // Define sortable columns
  const sortableColumns = {
    "Score": "Arena Score",
    "Max In": "max_input_tokens",
    "Max Out": "max_output_tokens",
    "In Cost": "input_cost_per_million_tokens ($)",
    "Out Cost": "output_cost_per_million_tokens ($)",
    "Est. Total Cost": "__calc_total__"
  };
  
  headers.forEach((h, index) => {
    const th = document.createElement("th");
    const dataKey = dataKeys[index];
    
    // Make column sortable if it's in the sortable list
    if (sortableColumns[h]) {
      th.style.cursor = "pointer";
      th.classList.add("sortable");
      
      // Add sort indicator
      let sortIndicator = "";
      if (currentSort.key === sortableColumns[h]) {
        sortIndicator = currentSort.ascending ? " ▲" : " ▼";
      }
      th.textContent = h + sortIndicator;
      
      // Add click handler
      th.addEventListener("click", () => {
        if (currentSort.key === sortableColumns[h]) {
          currentSort.ascending = !currentSort.ascending;
        } else {
          currentSort.key = sortableColumns[h];
          currentSort.ascending = false; // Default to descending (highest first)
        }
        
        const sortedData = sortData(data, currentSort.key);
        createTable(sortedData);
      });
    } else {
      th.textContent = h;
    }
    
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
        // Restore checked state from global selectedModels
        if (selectedModels.has(row["Model"])) {
          checkbox.checked = true;
        }
        // Add event listener to track selections
        checkbox.addEventListener("change", (e) => {
          if (e.target.checked) {
            selectedModels.add(row["Model"]);
          } else {
            selectedModels.delete(row["Model"]);
          }
          console.log("Selected models:", Array.from(selectedModels));
        });
        td.appendChild(checkbox);
        return;
      }

      if (key === "__calc_total__") {
        const m = row["Model"];
        const c = calculatedCosts?.[m];
        if (c && c.hasValidPricing) {
          td.textContent = `$${c.totalCost.toFixed(2)}`;
          td.classList.add("calculated-cost");
        } else {
          td.textContent = "N/A";
        }
        return;
      }

      if (key === "__try_blend__") {
        const modelName = row["Model"];
        const organization = row["Organization"];
        
        if (modelName && organization) {
          // Construct OpenRouter ID format: organization/model-name
          const orgSlug = organization.toLowerCase().replace(/\s+/g, '');
          const modelSlug = modelName.toLowerCase().replace(/\s+/g, '-');
          const openRouterID = `${orgSlug}/${modelSlug}`;
          const blendURL = `https://tryblend.ai/?model=openrouter:${openRouterID}`;
          
          const button = document.createElement("button");
          button.textContent = "Try in Blend";
          button.className = "try-blend-btn";
          button.onclick = () => window.open(blendURL, '_blank');
          td.appendChild(button);
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

// Filter data - include selected models even if they don't match the search
function filterData(data, query) {
  if (!query || query.trim() === "") {
    return data;
  }
  return data.filter((row) => {
    const matchesSearch = row.Model && row.Model.toLowerCase().includes(query.toLowerCase());
    const isSelected = selectedModels.has(row.Model);
    return matchesSearch || isSelected;
  });
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
    const rawInputCost = row["input_cost_per_million_tokens ($)"];
    const rawOutputCost = row["output_cost_per_million_tokens ($)"];
    
    const inputCostPerMillion = parseFloat(rawInputCost);
    const outputCostPerMillion = parseFloat(rawOutputCost);
    
    // Check if the model has valid pricing data (not empty, not NaN, and not zero)
    const hasValidInputCost = rawInputCost && rawInputCost.trim() !== "" && Number.isFinite(inputCostPerMillion);
    const hasValidOutputCost = rawOutputCost && rawOutputCost.trim() !== "" && Number.isFinite(outputCostPerMillion);
    const hasValidPricing = hasValidInputCost || hasValidOutputCost;

    const totalInputCost = (hasValidInputCost ? inputCostPerMillion : 0) * inputTokens;
    const totalOutputCost = (hasValidOutputCost ? outputCostPerMillion : 0) * outputTokens;

    calculatedCosts[modelName] = {
      totalInputCost,
      totalOutputCost,
      totalCost: totalInputCost + totalOutputCost,
      hasValidPricing
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
