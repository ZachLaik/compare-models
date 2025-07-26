const CSV_URL = "https://raw.githubusercontent.com/ZachLaik/compare-models/main/chatbot_arena_leaderboard_with_cost.csv";

const searchInput = document.getElementById("search");
const tableContainer = document.getElementById("table-container");
const compareButton = document.getElementById("compare-button");
const viewAllProvidersToggle = document.getElementById("view-all-providers");

let fullData = [];
let isCompareMode = false;
let showAllProviders = false;

// Columns to hide
const columnsToHide = ["max_tokens", "Rank (StyleCtrl)", "95% CI", "Votes", "model", "mode", "supports_function_calling",
  "supports_parallel_function_calling", "supports_vision", "supports_audio_input", "supports_audio_output", "supported_endpoints",	"supported_modalities",	"supported_output_modalities",
  "supports_prompt_caching", "supports_response_schema", "supports_system_messages", "supports_reasoning", 
  "supports_web_search", "search_context_cost_per_query", "file_search_cost_per_1k_calls", "file_search_cost_per_gb_per_day", 
  "vector_store_cost_per_gb_per_day", "computer_use_input_cost_per_1k_tokens", "computer_use_output_cost_per_1k_tokens", 
  "code_interpreter_cost_per_session", "supported_regions", "deprecation_date", "supports_tool_choice", "supports_pdf_input", 
  "supports_native_streaming", "input_cost_per_audio_token", "output_cost_per_audio_token", 
  "cache_creation_input_audio_token_cost", "source", "cache_creation_input_token_cost", "output_vector_size", 
  "input_cost_per_pixel", "output_cost_per_pixel", "input_cost_per_second", "output_cost_per_second", 
  "input_cost_per_character", "cache_read_input_audio_token_cost", "supports_assistant_prefill", "max_query_tokens", 
  "input_cost_per_query", "supports_embedding_image_input", "input_cost_per_token_cache_hit", "input_cost_per_image", 
  "tool_use_system_prompt_tokens", "supports_computer_use", "output_cost_per_character", 
  "input_cost_per_video_per_second", "input_cost_per_audio_per_second", 
  "input_cost_per_image_above_128k_tokens", "input_cost_per_video_per_second_above_128k_tokens","input_cost_per_audio_per_second_above_128k_tokens", "input_cost_per_token_above_128k_tokens", 
  "input_cost_per_character_above_128k_tokens", "output_cost_per_token_above_128k_tokens", 
  "output_cost_per_character_above_128k_tokens", "max_images_per_prompt", "max_videos_per_prompt", 
  "max_video_length", "max_audio_length_hours", "max_audio_per_prompt", "max_pdf_size_mb", 
  "input_cost_per_token_above_200k_tokens", "output_cost_per_token_above_200k_tokens", "supports_video_input", 
  "rpm", "tpm", "supports_url_context", "metadata", "output_cost_per_image",
  "input_cost_per_video_per_second_above_8s_interval", "input_cost_per_video_per_second_above_15s_interval", 
  "input_cost_per_token_batch_requests", "rpd", "supports_image_input", "max_document_chunks_per_query", 
  "max_tokens_per_document_chunk", "input_cost_per_request", "citation_cost_per_token", "input_dbu_cost_per_token", 
  "output_db_cost_per_token", "output_dbu_cost_per_token"];

function createTable(data) {
  const headers = [
    "", // For checkboxes
    "Rank", "Model", "Arena Score", "Organization", "License",
    "Knowledge Cutoff", "Max Input Tokens", "Max Output Tokens", "Provider",
    "Input Cost ($/1M)", "Output Cost ($/1M)",
    "Reasoning Cost ($/1M)", "Cache Read Cost", 
    "Batch Input Cost ($/1M)", "Batch Output Cost ($/1M)"
  ];
  
  const dataKeys = [
    "", // For checkboxes
    "Rank* (UB)", "Model", "Arena Score", "Organization", "License",
    "Knowledge Cutoff", "max_input_tokens", "max_output_tokens", "litellm_provider",
    "input_cost_per_million_tokens ($)", "output_cost_per_million_tokens ($)",
    "output_cost_per_reasoning_per_million_tokens ($)", "cache_read_input_token_cost",
    "input_cost_per_million_tokens_batches ($)", "output_cost_per_million_tokens_batches ($)"
  ];

  const table = document.createElement("table");

  // Table header
  const thead = table.createTHead();
  const headerRow = thead.insertRow();
  headers.forEach((h) => {
    const th = document.createElement("th");
    th.textContent = h;
    headerRow.appendChild(th);
  });

  // Table body
  const tbody = table.createTBody();
  data.forEach((row) => {
    const tr = tbody.insertRow();
    dataKeys.forEach((key, index) => {
      const td = tr.insertCell();
      if (index === 0) {
        // Checkbox column
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "model-checkbox";
        checkbox.dataset.model = row["Model"];
        td.appendChild(checkbox);
      } else if (key.includes("cost")) {
        const value = parseFloat(row[key]);
        td.textContent = isNaN(value) ? "N/A" : `$${value.toFixed(2)}`;
      } else {
        td.textContent = row[key] || "N/A";
      }
    });
  });

  tableContainer.innerHTML = "";
  tableContainer.appendChild(table);
}

// Remove duplicate models, keeping only the first provider (usually the primary one)
function removeDuplicateModels(data) {
  if (showAllProviders) return data;
  
  const seen = new Set();
  return data.filter((row) => {
    const key = `${row.Model}-${row.Organization}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
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

// Load CSV and render
Papa.parse(CSV_URL, {
  download: true,
  header: true,
  complete: (results) => {
    fullData = results.data.filter(row => row.Model); // Filter out empty rows
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
  },
});