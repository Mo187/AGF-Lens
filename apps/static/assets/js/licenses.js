// Ensure this script is loaded after Bootstrap's JS is available

// Cache for fetched data to prevent duplicate requests
const dataCache = {
    categories: null,
    licenses: null,
    lastCategoryFetch: 0,
    lastLicensesFetch: 0
};

// Helper function to fetch data only if needed (with cache timeout)
async function fetchWithCache(url, cacheKey, cacheTimeKey, cacheTimeoutMs = 10000) {
    const now = Date.now();
    const timeSinceLastFetch = now - dataCache[cacheTimeKey];
    
    // Use cached data if it exists and is recent
    if (dataCache[cacheKey] && timeSinceLastFetch < cacheTimeoutMs) {
        console.log(`Using cached ${cacheKey} data`);
        return dataCache[cacheKey];
    }
    
    console.log(`Fetching fresh ${cacheKey} data`);
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    dataCache[cacheKey] = data;
    dataCache[cacheTimeKey] = now;
    
    return data;
}

// Helper function to invalidate cache
function invalidateCache() {
    dataCache.categories = null;
    dataCache.lastCategoryFetch = 0;
    dataCache.licenses = null;
    dataCache.lastLicensesFetch = 0;
}

// Add Category button event listener
document.getElementById('addCategoryBtn').addEventListener('click', async () => {
    const categoryName = prompt('Enter new category name:');
    if (!categoryName || categoryName.trim() === '') return;
    
    showSpinner();
    try {
        const response = await fetch('/ict-license/categories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: categoryName.trim() })
        });
        
        if (response.ok) {
            alert('Category added successfully!');
            invalidateCache(); // Clear cache to ensure fresh data
            
            // Reload all data
            await loadCategoryCards();
            await loadCategories();
            await loadLicenses();
        } else {
            const errorData = await response.json().catch(() => ({}));
            alert(`Failed to add category: ${errorData.message || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error adding category:', error);
        alert(`Error adding category: ${error.message}`);
    } finally {
        hideSpinner();
    }
});

// Delete Category function with improved error handling
async function deleteCategory(id, name) {
    if (!id || !name) {
        alert('Invalid category information');
        return;
    }
    
    if (!confirm(`Are you sure you want to delete category "${name}"? All licenses in this category will be moved to the default category.`)) {
        return;
    }
    
    showSpinner();
    try {
        // Check if any licenses are assigned to this category
        const licensesData = await fetch('/ict-license/licenses');
        const licenses = await licensesData.json();
        const licensesInCategory = (licenses.licenses || licenses).filter(
            lic => lic.category_name === name
        );
        
        if (licensesInCategory.length > 0) {
            // Check if a default category exists
            const categoriesData = await fetch('/ict-license/categories');
            const categories = await categoriesData.json();
            const defaultCategory = categories.find(cat => cat.is_default === true);
            
            if (!defaultCategory) {
                const createDefault = confirm("No default category exists to move licenses to. Would you like to create one?");
                if (createDefault) {
                    const defaultResponse = await fetch('/ict-license/categories', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: "Uncategorized", is_default: true })
                    });
                    
                    if (!defaultResponse.ok) {
                        throw new Error("Failed to create default category");
                    }
                } else {
                    alert("Cannot delete category with assigned licenses without a default category.");
                    return;
                }
            }
        }
        
        // Now proceed with deletion
        const res = await fetch(`/ict-license/categories?id=${id}`, { method: 'DELETE' });
        
        if (res.ok) {
            alert('Category deleted successfully.');
            invalidateCache(); // Clear cache to ensure fresh data
            
            await loadCategoryCards();
            await loadCategories();
            await loadLicenses(currentPage);
        } else {
            const errorText = await res.text();
            console.error('Server error:', errorText);
            alert(`Failed to delete category. ${errorText}`);
        }
    } catch (error) {
        console.error('Error deleting category:', error);
        alert(`Error deleting category: ${error.message}`);
    } finally {
        hideSpinner();
    }
}

// Reset the license form when closing the modal
function resetLicenseForm() {
    const form = document.getElementById('addLicenseForm');
    if (form) {
        form.reset();
        document.getElementById('licenseId').value = "";
        
        // Reset modal header and button text
        const modalTitleElem = document.getElementById('modalTitle');
        if (modalTitleElem) {
            modalTitleElem.innerHTML = '<span class="fw-mediumbold">Add</span> <span class="fw-light">License</span>';
        }
        
        const licenseSubmitBtn = document.getElementById('licenseSubmitBtn');
        if (licenseSubmitBtn) {
            licenseSubmitBtn.textContent = "Save";
        }
    }
}

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

// Load initial data efficiently (combining API calls)
async function loadInitialData() {
    showSpinner();
    try {
        // Fetch categories and license data in parallel
        const [categories, licenseData] = await Promise.all([
            fetchWithCache('/ict-license/categories', 'categories', 'lastCategoryFetch'),
            fetchWithCache('/ict-license/licenses?limit=100', 'licenses', 'lastLicensesFetch')
        ]);
        
        // Update UI with the fetched data
        updateCategoryCards(categories);
        updateCategoryDropdowns(categories);
        extractAndUpdateLicenseTypes(licenseData);
        setupFilterHandlers();
        
        // Now load the licenses with pagination for display
        loadLicenses(1);
        
        return { categories, licenseData };
    } catch (error) {
        console.error('Error loading initial data:', error);
        alert(`Failed to load initial data: ${error.message}`);
    } finally {
        hideSpinner();
    }
}

// Update category cards with data (without making another API call)
function updateCategoryCards(categories) {
    console.log("Updating category cards...");
    const container = document.getElementById('categoryCardsContainer');
    if (!container) return;
    
    container.innerHTML = ''; // Clear previous cards
    
    if (!categories || categories.length === 0) {
        container.innerHTML = '<div class="col-12 text-center p-4"><p class="text-muted">No categories found. Add a category to get started.</p></div>';
        return;
    }
    
    categories.forEach(cat => {
        const col = document.createElement('div');
        col.className = "col-md-4 mb-3";
        col.innerHTML = `
        <div class="card">
        <div class="card-body">
            <div class="d-flex justify-content-between align-items-center">
            <h5 class="card-title mb-0">${cat.name}</h5>
            <div>
                <span class="badge bg-primary text-white">${cat.total || 0} total</span>
                <button class="btn btn-outline-danger btn-xs ms-4" onclick="deleteCategory(${cat.id}, '${cat.name}')">
                <i class="fas fa-trash"></i>
                </button>
            </div>
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
}

// Update category dropdowns with data (without making another API call)
function updateCategoryDropdowns(categories) {
    // Update filter dropdown
    const filterCategory = document.getElementById('filterCategory');
    if (filterCategory) {
        filterCategory.innerHTML = '<option value="">All Categories</option>';
        
        categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.name;
            option.textContent = cat.name;
            filterCategory.appendChild(option);
        });
    }
    
    // Update modal dropdown
    const licenseCategory = document.getElementById('licenseCategory');
    if (licenseCategory) {
        licenseCategory.innerHTML = '<option value="" disabled selected>Select Category</option>';
        
        categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.name;
            option.textContent = cat.name;
            licenseCategory.appendChild(option);
        });
    }
}

// Extract and update license types from data
function extractAndUpdateLicenseTypes(licenseData) {
    const licenses = licenseData.licenses || licenseData;
    const licenseTypes = new Set();
    
    // Add existing types from licenses
    licenses.forEach(lic => {
        if (lic.license_type) {
            licenseTypes.add(lic.license_type);
        }
    });
    
    // Add standard types
    ['Subscription', 'Annual', 'Perpetual', 'Password'].forEach(type => {
        licenseTypes.add(type);
    });
    
    // Update the filter dropdown
    const filterType = document.getElementById('filterType');
    if (filterType) {
        filterType.innerHTML = '<option value="">All Types</option>';
        
        // Add each unique type
        Array.from(licenseTypes).sort().forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            filterType.appendChild(option);
        });
    }
}

// Load category cards dynamically with Bootstrap card structure
// (Kept for backward compatibility, now uses cache when possible)
async function loadCategoryCards() {
    console.log("Loading category cards...");
    showSpinner();
    try {
        // Always fetch fresh category data to ensure counts are accurate
        const response = await fetch('/ict-license/categories');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const categories = await response.json();
        
        // Update cache
        dataCache.categories = categories;
        dataCache.lastCategoryFetch = Date.now();
        
        updateCategoryCards(categories);
    } catch (error) {
        console.error('Error loading categories:', error);
        alert(`Failed to load categories: ${error.message}`);
    } finally {
        hideSpinner();
    }
}

// Function to load categories and update both filter dropdown and modal dropdown
// (Kept for backward compatibility, now uses cache when possible)
async function loadCategories() {
    try {
        // Always fetch fresh data to ensure we have the latest
        const response = await fetch('/ict-license/categories');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const categories = await response.json();
        
        // Update cache
        dataCache.categories = categories;
        dataCache.lastCategoryFetch = Date.now();
        
        updateCategoryDropdowns(categories);
        return categories;
    } catch (error) {
        console.error('Error loading categories:', error);
        throw error; // Re-throw to allow calling code to handle it
    }
}

// Global pagination variables
let currentPage = 1;
let totalPages = 1;

function checkEmptyState() {
    const tableBody = document.getElementById('licensesTableBody');
    const emptyState = document.getElementById('emptyState');
    
    if (tableBody && emptyState) {
      if (tableBody.children.length === 0) {
        emptyState.classList.remove('d-none');
      } else {
        emptyState.classList.add('d-none');
      }
    }
}

// Updated loadLicenses: Accepts a page parameter.
async function loadLicenses(page = 1) {
    showSpinner();
    currentPage = page;
    const filterCategory = document.getElementById('filterCategory')?.value || '';
    const filterType = document.getElementById('filterType')?.value || '';
    const filterStatus = document.getElementById('filterStatus')?.value || '';

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
        // For consistency, always fetch fresh data when explicitly loading licenses
        const res = await fetch(url);
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        const data = await res.json();

        // Update cache if this is the default view
        if (filterCategory === '' && filterType === '' && filterStatus === '' && page === 1) {
            dataCache.licenses = data;
            dataCache.lastLicensesFetch = Date.now();
        }

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
              <td><span class="badge bg-primary text-white">${lic.category_name}</span></td>
              <td>${lic.license_type}</td>
              <td>${lic.assigned_to || ''}</td>
              <td>${lic.expiry_date || 'N/A'}</td>
              <td>${getStatusTag(lic.computed_status)}</td>
              <td>
                <div class="d-flex">
                  <button class="btn btn-outline-primary btn-xs mr-2" onclick="editLicense(${lic.id})">Edit</button>
                  <button class="btn btn-outline-danger btn-xs " onclick="deleteLicense(${lic.id})">Delete</button>
                </div>
              </td>
            `;
            tbody.appendChild(tr);
          });
          

        updatePaginationControls(currentPage, totalPages);
  
        // Add empty state check
        checkEmptyState();
    } catch (error) {
        console.error('Error loading licenses:', error);
        alert(`Failed to load licenses: ${error.message}`);
    } finally {
        hideSpinner();
    }
}

// Build or update the pagination controls
function updatePaginationControls(current, total) {
    const paginationControls = document.getElementById('paginationControls');
    if (!paginationControls) return;
    
    paginationControls.innerHTML = '';
    
    if (total <= 1) return; // Don't show pagination for a single page

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

// Fix for filter issues - we need to load license types from the existing data
async function loadLicenseTypes() {
    try {
        // Get all unique license types from the existing licenses
        const data = await fetchWithCache('/ict-license/licenses?limit=100', 'licenses', 'lastLicensesFetch');
        extractAndUpdateLicenseTypes(data);
    } catch (error) {
        console.error('Error loading license types:', error);
        alert(`Failed to load license types: ${error.message}`);
    }
}

// Function to update our filter handlers
function setupFilterHandlers() {
    // Get filter elements
    const filterCategory = document.getElementById('filterCategory');
    const filterType = document.getElementById('filterType');
    const filterStatus = document.getElementById('filterStatus');
    
    if (!filterCategory || !filterType || !filterStatus) {
        console.error('Filter elements not found');
        return;
    }
    
    // Remove old handlers (important to prevent duplicates)
    const newFilterCategory = filterCategory.cloneNode(true);
    filterCategory.parentNode.replaceChild(newFilterCategory, filterCategory);
    
    const newFilterType = filterType.cloneNode(true);
    filterType.parentNode.replaceChild(newFilterType, filterType);
    
    const newFilterStatus = filterStatus.cloneNode(true);
    filterStatus.parentNode.replaceChild(newFilterStatus, filterStatus);
    
    // Add new handlers
    newFilterCategory.addEventListener('change', () => {
        console.log('Category filter changed');
        loadLicenses(1);
    });
    
    newFilterType.addEventListener('change', () => {
        console.log('Type filter changed');
        loadLicenses(1);
    });
    
    newFilterStatus.addEventListener('change', () => {
        console.log('Status filter changed');
        loadLicenses(1);
    });
}

// Helper function to completely clean up any modal artifacts
function cleanupModalArtifacts() {
    console.log('Cleaning up modal artifacts...');
    
    // 1. Remove any modal-open class from body
    document.body.classList.remove('modal-open');
    
    // 2. Remove all backdrops
    const backdrops = document.querySelectorAll('.modal-backdrop');
    backdrops.forEach(backdrop => backdrop.remove());
    
    // 3. Reset all modals
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.classList.remove('show');
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
        modal.removeAttribute('aria-modal');
        modal.removeAttribute('role');
    });
    
    // 4. Remove inline styles that Bootstrap might have added
    document.body.style.removeProperty('overflow');
    document.body.style.removeProperty('padding-right');
    
    console.log('Modal cleanup complete');
}

// Revised closeModal function that works across all Bootstrap versions
function closeModal(modalEl) {
    if (!modalEl) {
        modalEl = document.querySelector('.modal.show');
        if (!modalEl) {
            console.warn('No active modal found to close');
            cleanupModalArtifacts(); // Clean up anyway just to be safe
            return;
        }
    }
    
    console.log('Attempting to close modal:', modalEl.id);
    
    // Method 1: Bootstrap 5
    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        try {
            // Try getInstance first (Bootstrap 5)
            if (typeof bootstrap.Modal.getInstance === 'function') {
                const bsModal = bootstrap.Modal.getInstance(modalEl);
                if (bsModal) {
                    console.log('Closing modal with Bootstrap 5 getInstance');
                    bsModal.hide();
                    return;
                }
            }
            
            // Try creating a new modal instance (Bootstrap 5)
            if (typeof bootstrap.Modal === 'function') {
                console.log('Closing modal with new Bootstrap 5 Modal instance');
                const modal = new bootstrap.Modal(modalEl);
                modal.hide();
                return;
            }
        } catch (err) {
            console.warn('Bootstrap 5 close failed:', err);
        }
    }
    
    // Method 2: jQuery (Bootstrap 4)
    if (typeof $ !== 'undefined') {
        try {
            console.log('Closing modal with jQuery');
            $(modalEl).modal('hide');
            return;
        } catch (err) {
            console.warn('jQuery modal close failed:', err);
        }
    }
    
    // Method 3: Vanilla JS
    try {
        console.log('Closing modal with vanilla JS');
        modalEl.classList.remove('show');
        modalEl.style.display = 'none';
        modalEl.setAttribute('aria-hidden', 'true');
        modalEl.removeAttribute('aria-modal');
        modalEl.removeAttribute('role');
        
        // Force cleanup of modal artifacts
        cleanupModalArtifacts();
    } catch (err) {
        console.error('Vanilla JS modal close failed:', err);
    }
}

// Updated form submission handler with improved modal closing
const addLicenseForm = document.getElementById('addLicenseForm');
if (addLicenseForm) {
    addLicenseForm.onsubmit = null; // Clear any existing handlers
    
    addLicenseForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Validate form
        const licenseName = document.getElementById('licenseName').value.trim();
        const licenseCategory = document.getElementById('licenseCategory').value;
        const licenseType = document.getElementById('licenseType').value;
        
        if (!licenseName || !licenseCategory || !licenseType) {
            alert('Please fill in all required fields');
            return;
        }
        
        // Disable the submit button to prevent double submission
        const submitBtn = document.getElementById('licenseSubmitBtn');
        if (submitBtn) submitBtn.disabled = true;
        
        showSpinner();
        
        const formData = {
            name: licenseName,
            category: licenseCategory,
            license_type: licenseType,
            assigned_to: document.getElementById('assignedTo').value.trim(),
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
                
                // First reset the form to clear any values
                resetLicenseForm();
                
                // Clear the cache so we get fresh data
                invalidateCache();
                
                // Close the modal safely
                const modalEl = document.getElementById('addLicenseModal');
                closeModal(modalEl);
                
                // Reload data to reflect changes - important to refresh category cards
                await loadCategoryCards();
                await loadLicenses(currentPage);
            } else {
                const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
                alert(`Failed to save license: ${errorData.message || response.statusText}`);
            }
        } catch (error) {
            console.error('Error saving license:', error);
            alert(`Error saving license: ${error.message}`);
        } finally {
            // Re-enable the submit button
            if (submitBtn) submitBtn.disabled = false;
            hideSpinner();
        }
    });
}

// Updated editLicense function with better modal handling
async function editLicense(id) {
    if (!id) {
        alert('Invalid license ID');
        return;
    }
    
    showSpinner();
    
    try {
        console.log(`Editing license with ID: ${id}`);
        
        // First make sure the modal exists
        const modalEl = document.getElementById('addLicenseModal');
        if (!modalEl) {
            throw new Error("Modal element not found");
        }
        
        // Load categories first
        try {
            await loadCategories();
        } catch (catError) {
            console.error("Failed to load categories:", catError);
        }
        
        // Fetch the license details
        const res = await fetch(`/ict-license/licenses/${id}`);
        
        if (!res.ok) {
            throw new Error(`Failed to fetch license details. Status: ${res.status}`);
        }
        
        const lic = await res.json();
        
        // Pre-fill form fields for editing
        document.getElementById('licenseId').value = lic.id;
        document.getElementById('licenseName').value = lic.name;
        
        // Make sure the category dropdown has the option we need
        const categorySelect = document.getElementById('licenseCategory');
        let categoryFound = false;
        
        // Check if the category exists in the dropdown
        for (let i = 0; i < categorySelect.options.length; i++) {
            if (categorySelect.options[i].value === lic.category_name) {
                categoryFound = true;
                break;
            }
        }
        
        // If category not found, add it
        if (!categoryFound && lic.category_name) {
            const newOption = document.createElement('option');
            newOption.value = lic.category_name;
            newOption.textContent = lic.category_name;
            categorySelect.appendChild(newOption);
        }
        
        // Now set the selected value
        categorySelect.value = lic.category_name;
        
        // Fill in the rest of the form
        document.getElementById('licenseType').value = lic.license_type;
        document.getElementById('assignedTo').value = lic.assigned_to || "";
        document.getElementById('expiryDate').value = lic.expiry_date || "";
        
        // Update modal header and button text for editing
        document.getElementById('modalTitle').innerHTML = 
            '<span class="fw-mediumbold">Edit</span> <span class="fw-light">License</span>';
        document.getElementById('licenseSubmitBtn').textContent = "Update";
        
        // First clean up any existing modal artifacts
        cleanupModalArtifacts();
        
        // Show the modal using the appropriate method
        if (typeof $ !== 'undefined') {
            // Bootstrap 4 with jQuery
            $(modalEl).modal('show');
        } else if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            // Bootstrap 5
            new bootstrap.Modal(modalEl).show();
        } else {
            // Vanilla fallback
            modalEl.classList.add('show');
            modalEl.style.display = 'block';
            modalEl.setAttribute('aria-hidden', 'false');
            modalEl.setAttribute('aria-modal', 'true');
            modalEl.setAttribute('role', 'dialog');
            document.body.classList.add('modal-open');
            
            // Create backdrop
            const backdrop = document.createElement('div');
            backdrop.className = 'modal-backdrop fade show';
            document.body.appendChild(backdrop);
        }
        
    } catch (error) {
        console.error("Error in editLicense function:", error);
        alert(`Error loading license details: ${error.message}`);
    } finally {
        hideSpinner();
    }
}

// Delete License: Delete the license and refresh the table
async function deleteLicense(id) {
    if (!id) {
        alert('Invalid license ID');
        return;
    }
    
    if (!confirm("Are you sure you want to delete this license?")) return;
    
    showSpinner();
    try {
        const res = await fetch(`/ict-license/licenses/${id}`, { method: 'DELETE' });
        
        if (res.ok) {
            alert('License deleted successfully.');
            
            // Clear cache to ensure fresh data
            invalidateCache();
            
            // Reload data to reflect changes - important to refresh category cards too
            await loadCategoryCards();
            await loadLicenses(currentPage);
        } else {
            const errorText = await res.text();
            alert(`Failed to delete license: ${errorText}`);
        }
    } catch (error) {
        console.error('Error deleting license:', error);
        alert(`Error deleting license: ${error.message}`);
    } finally {
        hideSpinner();
    }
}

// Set up emergency escape key handler
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        cleanupModalArtifacts();
    }
});

// Improved modal initialization code for DOMContentLoaded event
document.addEventListener('DOMContentLoaded', () => {
    // Use the optimized loading function
    loadInitialData();
    
    // Improved modal handling
    const modalEl = document.getElementById('addLicenseModal');
    if (modalEl) {
        // Set up event listeners for modal hiding
        modalEl.addEventListener('hidden.bs.modal', resetLicenseForm);
        modalEl.addEventListener('hidden', resetLicenseForm); // For older Bootstrap
        
        // Set up close button handlers
        const closeButtons = modalEl.querySelectorAll('[data-bs-dismiss="modal"], [data-dismiss="modal"], .close, .btn-close, button.close');
        closeButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                closeModal(modalEl);
            });
        });
    }
    
    // Support for Bootstrap 4's jQuery modal
    if (typeof $ !== 'undefined' && modalEl) {
        $(modalEl).on('hidden.bs.modal', resetLicenseForm);
    }
});