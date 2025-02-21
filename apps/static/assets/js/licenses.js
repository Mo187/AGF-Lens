// Ensure this script is loaded after Bootstrap’s JS is available

// Add Category button event listener
document.getElementById('addCategoryBtn').addEventListener('click', async () => {
    const categoryName = prompt('Enter new category name:');
    if (categoryName) {
        try {
            const response = await fetch('/ict-license/categories', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: categoryName })
            });
            if (response.ok) {
                alert('Category added successfully!');
                loadCategoryCards();
                loadLicenses();
            } else {
                alert('Failed to add category.');
            }
        } catch (error) {
            console.error(error);
            alert('Error adding category.');
        }
    }
});

// Spinner functions
function showSpinner() {
    const spinner = document.getElementById('spinnerOverlay');
    if (spinner) {
        spinner.classList.remove('d-none');
    }
}
function hideSpinner() {
    const spinner = document.getElementById('spinnerOverlay');
    if (spinner) {
        spinner.classList.add('d-none');
    }
}

// Helper to wrap status with colored tag using Bootstrap badges
function getStatusTag(status) {
    if (status === 'Expired') {
        return `<span class="badge bg-danger">${status}</span>`;
    } else if (status === 'Expiring Soon') {
        return `<span class="badge bg-warning text-dark">${status}</span>`;
    } else if (status === 'Active') {
        return `<span class="badge bg-success">${status}</span>`;
    } else if (status === 'Perpetual') {
        return `<span class="badge bg-primary">${status}</span>`;
    } else {
        return `<span class="badge bg-secondary">${status}</span>`;
    }
}

// Load category cards dynamically with Bootstrap card structure
async function loadCategoryCards() {
    console.log("Loading category cards...");
    showSpinner();
    try {
        const res = await fetch('/ict-license/categories');
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        const categories = await res.json();
        console.log("Fetched categories:", categories);
        const container = document.getElementById('categoryCardsContainer');
        container.innerHTML = ''; // Clear previous cards
        categories.forEach(cat => {
            const col = document.createElement('div');
            col.className = "col-md-4 mb-3";
            col.innerHTML = `
          <div class="card">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0">${cat.name}</h5>
                <span class="badge bg-secondary">${cat.total || 0} total</span>
              </div>
              <div class="mt-3 d-flex justify-content-between text-muted">
                <div><span class="fw-bold text-success">${cat.active || 0}</span> Active</div>
                <div><span class="fw-bold text-warning">${cat.expiring || 0}</span> Expiring</div>
                <div><span class="fw-bold text-danger">${cat.expired || 0}</span> Expired</div>
              </div>
            </div>
          </div>
        `;
            container.appendChild(col);
        });
    } catch (error) {
        console.error('Error loading categories:', error);
    } finally {
        hideSpinner();
    }
}

// Function to load categories and update the filter dropdown
async function loadCategories() {
    try {
        const res = await fetch('/ict-license/categories');
        const categories = await res.json();
        const filterCategory = document.getElementById('filterCategory');
        filterCategory.innerHTML = '<option value="">All Categories</option>';
        categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.name;
            option.textContent = cat.name;
            filterCategory.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

// Global pagination variables
let currentPage = 1;
let totalPages = 1;

// Updated loadLicenses: Accepts a page parameter.
async function loadLicenses(page = 1) {
    showSpinner();
    currentPage = page;
    const filterCategory = document.getElementById('filterCategory').value;
    const filterType = document.getElementById('filterType').value;
    const filterStatus = document.getElementById('filterStatus').value;

    let queryParams = [];
    if (filterCategory) queryParams.push(`category=${encodeURIComponent(filterCategory)}`);
    if (filterType) queryParams.push(`type=${encodeURIComponent(filterType)}`);
    if (filterStatus) queryParams.push(`status=${encodeURIComponent(filterStatus)}`);

    // Add pagination parameters (adjust limit as needed)
    queryParams.push(`page=${page}`);
    queryParams.push(`limit=10`);

    let url = '/ict-license/licenses';
    if (queryParams.length > 0) {
        url += '?' + queryParams.join('&');
    }

    try {
        const res = await fetch(url);
        const data = await res.json();

        // Expecting data structure: { licenses: [...], totalPages: X, totalLicenses: Y }
        const licenses = data.licenses || data;  // In case your endpoint returns an array when filters are used
        totalPages = data.totalPages || 1;
        // Update stat cards using aggregated data if available; otherwise, use current page count.
        document.getElementById('totalLicenses').textContent = data.totalLicenses || licenses.length;

        let expiringSoon = 0;
        let expiredCount = 0;
        licenses.forEach(lic => {
            if (lic.computed_status === 'Expiring Soon') expiringSoon++;
            if (lic.computed_status === 'Expired') expiredCount++;
        });
        document.getElementById('expiringSoon').textContent = expiringSoon;
        document.getElementById('expiredCount').textContent = expiredCount;

        const tbody = document.getElementById('licensesTableBody');
        tbody.innerHTML = '';

        licenses.forEach(lic => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
        <td>${lic.name}</td>
        <td><span class="badge bg-secondary">${lic.category_name}</span></td>
        <td>${lic.license_type}</td>
        <td>${lic.assigned_to || ''}</td>
        <td>${lic.expiry_date || 'N/A'}</td>
        <td>${getStatusTag(lic.computed_status)}</td>
        <td>
          <button class="btn btn-outline-primary btn-sm me-1" onclick="editLicense(${lic.id})">Edit</button>
          <button class="btn btn-outline-danger btn-sm" onclick="deleteLicense(${lic.id})">Delete</button>
        </td>
      `;
            tbody.appendChild(tr);
        });

        updatePaginationControls(currentPage, totalPages);
    } catch (error) {
        console.error('Error loading licenses:', error);
    } finally {
        hideSpinner();
    }
}

// Build or update the pagination controls
function updatePaginationControls(current, total) {
    const paginationControls = document.getElementById('paginationControls');
    paginationControls.innerHTML = '';

    // Previous button
    const prevItem = document.createElement('li');
    prevItem.className = "page-item" + (current === 1 ? " disabled" : "");
    const prevLink = document.createElement('a');
    prevLink.className = "page-link";
    prevLink.href = "#";
    prevLink.textContent = "Previous";
    prevLink.addEventListener('click', (e) => {
        e.preventDefault();
        if (current > 1) loadLicenses(current - 1);
    });
    prevItem.appendChild(prevLink);
    paginationControls.appendChild(prevItem);

    // Page number buttons (for simplicity, all pages are shown; adjust if total is large)
    for (let i = 1; i <= total; i++) {
        const pageItem = document.createElement('li');
        pageItem.className = "page-item" + (i === current ? " active" : "");
        const pageLink = document.createElement('a');
        pageLink.className = "page-link";
        pageLink.href = "#";
        pageLink.textContent = i;
        pageLink.addEventListener('click', (e) => {
            e.preventDefault();
            loadLicenses(i);
        });
        pageItem.appendChild(pageLink);
        paginationControls.appendChild(pageItem);
    }

    // Next button
    const nextItem = document.createElement('li');
    nextItem.className = "page-item" + (current === total ? " disabled" : "");
    const nextLink = document.createElement('a');
    nextLink.className = "page-link";
    nextLink.href = "#";
    nextLink.textContent = "Next";
    nextLink.addEventListener('click', (e) => {
        e.preventDefault();
        if (current < total) loadLicenses(current + 1);
    });
    nextItem.appendChild(nextLink);
    paginationControls.appendChild(nextItem);
}

// Handle filters change: reload licenses (reset to page 1)
document.getElementById('filterCategory').addEventListener('change', () => loadLicenses(1));
document.getElementById('filterType').addEventListener('change', () => loadLicenses(1));
document.getElementById('filterStatus').addEventListener('change', () => loadLicenses(1));

// Handle the "Add/Edit License" form submission via fetch
const addLicenseForm = document.getElementById('addLicenseForm');
addLicenseForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const licenseType = document.getElementById('licenseType').value;
    const formData = {
        name: document.getElementById('licenseName').value,
        category: document.getElementById('licenseCategory').value,
        license_type: licenseType,
        assigned_to: document.getElementById('assignedTo').value,
        expiry_date: document.getElementById('expiryDate').value,
        is_perpetual: (licenseType === 'Perpetual')
    };
    const licenseId = document.getElementById('licenseId').value;
    try {
        let response;
        if (licenseId) {
            // Edit mode – send PUT request
            response = await fetch(`/ict-license/licenses/${licenseId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
        } else {
            // Add mode – send POST request
            response = await fetch('/ict-license/licenses', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
        }
        if (response.ok) {
            alert(licenseId ? 'License updated successfully!' : 'License saved successfully!');
            addLicenseForm.reset();
            loadLicenses(currentPage);
        } else {
            alert('Failed to save license.');
        }
    } catch (error) {
        console.error(error);
        alert('Error saving license.');
    }
    // Hide the modal using Bootstrap’s Modal API
    const modalEl = document.getElementById('addLicenseModal');
    const modalInstance = bootstrap.Modal.getInstance(modalEl);
    if (modalInstance) {
        modalInstance.hide();
    }
});

// Edit License: Populate the modal for editing and show it
async function editLicense(id) {
    try {
        const res = await fetch(`/ict-license/licenses/${id}`);
        if (!res.ok) throw new Error("Failed to fetch license details.");
        const lic = await res.json();
        // Pre-fill form fields for editing
        document.getElementById('licenseId').value = lic.id;
        document.getElementById('licenseName').value = lic.name;
        document.getElementById('licenseCategory').value = lic.category_name; // adjust if needed
        document.getElementById('licenseType').value = lic.license_type;
        document.getElementById('assignedTo').value = lic.assigned_to || "";
        document.getElementById('expiryDate').value = lic.expiry_date || "";
        // Update modal header and button text for editing
        const modalTitleElem = document.getElementById('modalTitle');
        if (modalTitleElem) {
            modalTitleElem.innerHTML = '<span class="fw-mediumbold">Edit</span> <span class="fw-light">License</span>';
        }
        const licenseSubmitBtn = document.getElementById('licenseSubmitBtn');
        if (licenseSubmitBtn) {
            licenseSubmitBtn.textContent = "Update";
        }
        // Show the modal for editing
        const modalEl = document.getElementById('addLicenseModal');
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    } catch (error) {
        console.error(error);
        alert('Error loading license details.');
    }
}

// Delete License: Delete the license and refresh the table
async function deleteLicense(id) {
    if (!confirm("Are you sure you want to delete this license?")) return;
    try {
        const res = await fetch(`/ict-license/licenses/${id}`, { method: 'DELETE' });
        if (res.ok) {
            alert('License deleted successfully.');
            loadLicenses(currentPage);
        } else {
            alert('Failed to delete license.');
        }
    } catch (error) {
        console.error(error);
        alert('Error deleting license.');
    }
}

// On page load, initialize data
document.addEventListener('DOMContentLoaded', () => {
    loadLicenses();
    loadCategoryCards();
    loadCategories();
});
