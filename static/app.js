/**
 * Add a new URL input field to the form
 */
function addUrlField() {
    const container = document.getElementById("url-container");
    
    const wrapper = document.createElement("div");
    wrapper.className = "url-input-wrapper";
    
    const input = document.createElement("input");
    input.type = "url";
    input.placeholder = "https://example.com/image.jpg";
    input.className = "url-input";
    input.setAttribute("aria-label", `Image URL ${container.children.length + 1}`);
    
    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn-remove";
    removeBtn.textContent = "×";
    removeBtn.setAttribute("aria-label", "Remove URL");
    removeBtn.onclick = function(e) {
        e.preventDefault();
        removeUrlField(removeBtn);
    };
    
    wrapper.appendChild(input);
    wrapper.appendChild(removeBtn);
    container.appendChild(wrapper);
    
    // Focus on the new input
    input.focus();
}

/**
 * Remove a URL input field
 */
function removeUrlField(button) {
    const wrapper = button.parentElement;
    const container = document.getElementById("url-container");
    
    // Don't allow removing if only one URL field remains
    if (container.children.length > 1) {
        wrapper.remove();
    } else {
        showAlert("error", "Keep at least one URL field.");
    }
}

/**
 * Show alert messages
 */
function showAlert(type, message) {
    const alertId = type === "error" ? "error-alert" : "success-alert";
    const messageId = type === "error" ? "error-message" : "success-message";
    
    const alert = document.getElementById(alertId);
    const messageEl = document.getElementById(messageId);
    
    messageEl.textContent = message;
    alert.style.display = "flex";
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        if (alert.style.display !== "none") {
            closeAlert(alert.querySelector(".alert-close"));
        }
    }, 5000);
}

/**
 * Close alert
 */
function closeAlert(button) {
    const alert = button.closest(".alert");
    alert.style.display = "none";
}

/**
 * Validate theme input
 */
function validateTheme(theme) {
    if (!theme || theme.trim().length === 0) {
        showAlert("error", "Please enter an editorial theme.");
        return false;
    }
    if (theme.trim().length < 10) {
        showAlert("error", "Theme description should be at least 10 characters.");
        return false;
    }
    return true;
}

/**
 * Validate URLs (handles both HTTPS URLs and base64 data URLs)
 */
function validateUrls(urls) {
    if (urls.length === 0) {
        showAlert("error", "Please provide at least one image.");
        return false;
    }
    
    if (urls.length < 2) {
        showAlert("error", "Please provide at least 2 images for better results.");
        return false;
    }
    
    // Validate URL format - accept HTTPS URLs or base64 data URLs
    const httpsPattern = /^https?:\/\/.+/i;
    const dataUrlPattern = /^data:image\/\w+;base64,.+/i;
    
    for (const url of urls) {
        // Skip validation for data URLs (from drag-drop uploads)
        if (dataUrlPattern.test(url)) {
            continue;
        }
        
        // Validate HTTPS URLs from paste tab
        if (!httpsPattern.test(url)) {
            showAlert("error", `Invalid URL format: ${url.substring(0, 50)}...`);
            return false;
        }
    }
    
    return true;
}

/**
 * Generate the lookbook
 */
async function generateLookbook() {
    // Get form inputs
    const theme = document.getElementById("theme").value.trim();
    const urls = getAllImageSources();
    
    // Validate inputs
    if (!validateTheme(theme) || !validateUrls(urls)) {
        return;
    }
    
    // Hide previous results
    document.getElementById("results").innerHTML = "";
    document.getElementById("success-alert").style.display = "none";
    document.getElementById("error-alert").style.display = "none";
    
    // Show loading state
    const loadingEl = document.getElementById("loading");
    loadingEl.style.display = "block";
    
    // Disable generate button
    const generateBtn = document.getElementById("generate-btn");
    generateBtn.disabled = true;
    
    try {
        const response = await fetch("/generate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                theme_prompt: theme,
                image_urls: urls
            })
        });
        
        // Check if response is ok
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Failed to generate lookbook");
        }
        
        const data = await response.json();
        
        // Hide loading and show success
        loadingEl.style.display = "none";
        showAlert("success", "Lookbook generated successfully!");
        
        // Display results
        displayResults(data);
        
        // Scroll to results
        setTimeout(() => {
            document.getElementById("results").scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        }, 300);
        
    } catch (error) {
        console.error("[v0] Error generating lookbook:", error);
        
        loadingEl.style.display = "none";
        let errorMessage = error.message || "Something went wrong while generating the lookbook.";
        
        // Handle specific error cases
        if (error.message.includes("Network")) {
            errorMessage = "Network error. Please check your connection and try again.";
        } else if (error.message.includes("401") || error.message.includes("403")) {
            errorMessage = "Authentication error. Please check your API keys.";
        }
        
        showAlert("error", errorMessage);
        
    } finally {
        // Re-enable generate button
        generateBtn.disabled = false;
    }
}

/**
 * Display the generated lookbook results
 */
function displayResults(data) {
    const container = document.getElementById("results");
    container.innerHTML = "";
    
    // Validate data structure
    if (!data.lookbook || !data.lookbook.collection) {
        showAlert("error", "Invalid response format received.");
        return;
    }
    
    // Title
    const title = document.createElement("h2");
    title.textContent = data.lookbook.edition_title || "Generated Lookbook";
    container.appendChild(title);
    
    // Collection cards
    if (data.lookbook.collection && data.lookbook.collection.length > 0) {
        data.lookbook.collection.forEach((card, index) => {
            const div = document.createElement("div");
            div.className = "lookbook-card";
            div.style.animationDelay = `${index * 0.05}s`;
            
            // Card title
            const cardTitle = document.createElement("h3");
            cardTitle.innerHTML = `
                <span style="color: #0066cc; font-weight: 700;">Card ${card.card_number || index + 1}</span>
                <span style="color: #999;"> • </span>
                <span>${escapeHtml(card.mood_title || "")}</span>
            `;
            div.appendChild(cardTitle);
            
            // Brand/Designer
            if (card.brand_or_designer) {
                const brandP = document.createElement("p");
                brandP.innerHTML = `<strong>Brand:</strong> ${escapeHtml(card.brand_or_designer)}`;
                div.appendChild(brandP);
            }
            
            // Product Type
            if (card.product_type) {
                const productP = document.createElement("p");
                productP.innerHTML = `<strong>Product:</strong> ${escapeHtml(card.product_type)}`;
                div.appendChild(productP);
            }
            
            // Tags
            if (card.sub_tags && card.sub_tags.length > 0) {
                const tagsP = document.createElement("p");
                tagsP.innerHTML = `<strong>Tags:</strong> ${card.sub_tags.map(tag => escapeHtml(tag)).join(" • ")}`;
                div.appendChild(tagsP);
            }
            
            // Vibe description
            if (card.vibe_description) {
                const vibeP = document.createElement("p");
                vibeP.style.fontStyle = "italic";
                vibeP.style.color = "#555";
                vibeP.textContent = card.vibe_description;
                div.appendChild(vibeP);
            }
            
            container.appendChild(div);
        });
    }
    
    // Metrics card - Show only total tokens
    if (data.total_tokens !== undefined) {
        const metricsDiv = document.createElement("div");
        metricsDiv.className = "lookbook-card metrics-card";
        
        const metricsTitle = document.createElement("h3");
        metricsTitle.textContent = "Pipeline Metrics";
        metricsDiv.appendChild(metricsTitle);
        
        const tokensP = document.createElement("p");
        tokensP.innerHTML = `<strong>Total Tokens Used:</strong> ${Number(data.total_tokens).toLocaleString()}`;
        metricsDiv.appendChild(tokensP);
        
        container.appendChild(metricsDiv);
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return "";
    
    const map = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    };
    
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Store for uploaded images (using data URLs)
 */
const uploadedImages = {
    files: [],
    dataUrls: []
};

/**
 * Switch between tabs
 */
function switchTab(tabName, event) {
    if (event) {
        event.preventDefault();
    }
    
    // Remove active class from all tabs and buttons
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Add active class to selected tab and button
    const tabElement = document.getElementById(tabName);
    if (tabElement) {
        tabElement.classList.add('active');
    }
    
    const btnElement = document.querySelector(`[data-tab="${tabName}"]`);
    if (btnElement) {
        btnElement.classList.add('active');
    }
}

/**
 * Handle drag over event
 */
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    
    const dropZone = document.getElementById('drop-zone');
    dropZone.classList.add('dragover');
}

/**
 * Handle drag leave event
 */
function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    
    const dropZone = document.getElementById('drop-zone');
    dropZone.classList.remove('dragover');
}

/**
 * Handle drop event
 */
function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    
    const dropZone = document.getElementById('drop-zone');
    dropZone.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    handleFiles(files);
}

/**
 * Handle file input change
 */
function handleFileInput(e) {
    const files = e.target.files;
    handleFiles(files);
}

/**
 * Toggle between dark and light theme
 */
function toggleTheme() {
    const html = document.documentElement;
    const isDarkMode = html.classList.contains('dark-mode');
    
    if (isDarkMode) {
        html.classList.remove('dark-mode');
        localStorage.setItem('theme', 'light');
    } else {
        html.classList.add('dark-mode');
        localStorage.setItem('theme', 'dark');
    }
}

/**
 * Load saved theme preference on page load
 */
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.documentElement.classList.add('dark-mode');
    }
}

/**
 * Initialize on page load
 */
document.addEventListener("DOMContentLoaded", () => {
    // Initialize theme
    initializeTheme();
    
    // Make drop zone clickable to open file browser
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    
    if (dropZone && fileInput) {
        dropZone.addEventListener('click', (e) => {
            // Prevent triggering if clicking on content inside
            if (e.target === dropZone || e.target.closest('.drop-zone-content')) {
                fileInput.click();
            }
        });
    }
    
    // Add keyboard shortcut for generating (Ctrl+Enter)
    document.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            const generateBtn = document.getElementById("generate-btn");
            if (!generateBtn.disabled) {
                generateLookbook();
            }
        }
    });
    
    console.log("[v0] Agentic Lookbook Generator initialized");
});

/**
 * Process files (either from drag-drop or file input)
 */
async function handleFiles(files) {
    const validFiles = [];
    const errors = [];
    
    for (const file of files) {
        // Validate file type
        if (!file.type.startsWith('image/')) {
            errors.push(`${file.name} is not an image file`);
            continue;
        }
        
        // Validate file size (5MB)
        if (file.size > 5 * 1024 * 1024) {
            errors.push(`${file.name} is larger than 5MB`);
            continue;
        }
        
        validFiles.push(file);
    }
    
    // Show errors if any
    if (errors.length > 0) {
        showAlert("error", errors.join(", "));
    }
    
    // Process valid files
    if (validFiles.length > 0) {
        for (const file of validFiles) {
            await processFile(file);
        }
    }
}

/**
 * Convert file to data URL and add to previews
 */
function processFile(file) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            const dataUrl = e.target.result;
            
            // Store file data
            uploadedImages.files.push(file);
            uploadedImages.dataUrls.push(dataUrl);
            
            // Add to previews
            addImagePreview(dataUrl, uploadedImages.files.length - 1);
            resolve();
        };
        
        reader.onerror = () => {
            showAlert("error", `Failed to read file: ${file.name}`);
            resolve();
        };
        
        reader.readAsDataURL(file);
    });
}

/**
 * Add image preview to the gallery
 */
function addImagePreview(dataUrl, index) {
    const previewsContainer = document.getElementById('image-previews');
    
    const preview = document.createElement('div');
    preview.className = 'image-preview';
    preview.dataset.index = index;
    
    const img = document.createElement('img');
    img.src = dataUrl;
    img.alt = `Preview ${index + 1}`;
    
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'image-preview-remove';
    removeBtn.textContent = '×';
    removeBtn.setAttribute('aria-label', 'Remove image');
    removeBtn.onclick = (e) => {
        e.preventDefault();
        removeImagePreview(index);
    };
    
    preview.appendChild(img);
    preview.appendChild(removeBtn);
    previewsContainer.appendChild(preview);
}

/**
 * Remove image preview
 */
function removeImagePreview(index) {
    // Remove from storage
    uploadedImages.files.splice(index, 1);
    uploadedImages.dataUrls.splice(index, 1);
    
    // Update previews
    const previewsContainer = document.getElementById('image-previews');
    const preview = previewsContainer.querySelector(`[data-index="${index}"]`);
    
    if (preview) {
        preview.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => {
            preview.remove();
            // Re-index remaining previews
            updateImagePreviewIndices();
        }, 300);
    }
}

/**
 * Update indices of remaining image previews
 */
function updateImagePreviewIndices() {
    const previewsContainer = document.getElementById('image-previews');
    const previews = previewsContainer.querySelectorAll('.image-preview');
    
    previews.forEach((preview, index) => {
        preview.dataset.index = index;
        const removeBtn = preview.querySelector('.image-preview-remove');
        if (removeBtn) {
            removeBtn.onclick = (e) => {
                e.preventDefault();
                removeImagePreview(index);
            };
        }
    });
}

/**
 * Get all image URLs/sources (from drag-drop or URL inputs)
 */
function getAllImageSources() {
    const urls = [];
    
    // Check which tab is active
    const dragDropTab = document.getElementById('drag-drop');
    
    if (dragDropTab.classList.contains('active')) {
        // Use uploaded file data URLs
        urls.push(...uploadedImages.dataUrls);
    } else {
        // Use URL inputs
        const urlInputs = Array.from(
            document.querySelectorAll(".url-input")
        )
            .map(input => input.value.trim())
            .filter(url => url !== "");
        urls.push(...urlInputs);
    }
    
    return urls;
}
