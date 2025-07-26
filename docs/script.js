const CSV_URL = "https://raw.githubusercontent.com/ZachLaik/compare-models/main/chatbot_arena_leaderboard_with_cost.csv";

const searchInput = document.getElementById("search");
const tableContainer = document.getElementById("table-container");

function createTable(data) {
  const headers = Object.keys(data[0]);
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
    headers.forEach((h) => {
      const td = tr.insertCell();
      td.textContent = row[h];
    });
  });

  tableContainer.innerHTML = "";
  tableContainer.appendChild(table);
}

// Filter data
function filterData(data, query) {
  return data.filter((row) =>
    row.Model.toLowerCase().includes(query.toLowerCase())
  );
}

// Load CSV and render
Papa.parse(CSV_URL, {
  download: true,
  header: true,
  complete: (results) => {
    let fullData = results.data;
    createTable(fullData);

    searchInput.addEventListener("input", () => {
      const filtered = filterData(fullData, searchInput.value);
      createTable(filtered);
    });
  },
});
