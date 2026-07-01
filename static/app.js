/* ==========================================================================
   AINAA — Editorial Lookbook Generator
   Frontend interaction logic. Consumes the existing /generate and
   /generate-from-data pipeline output as-is and presents it as a
   magazine-style lookbook.
   ========================================================================== */

const uploadedImages = {
    files: [],
    dataUrls: []
};

const PROGRESS_STEPS = ["upload", "curator", "stylist", "editor", "director", "visual", "render", "done"];

/* ---------------------------------------------------------------------- */
/* Theme                                                                    */
/* ---------------------------------------------------------------------- */

function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.classList.toggle("dark-mode");
    try {
        localStorage.setItem("ainaa-theme", isDark ? "dark" : "light");
    } catch (e) { /* storage unavailable — safe to ignore */ }
}

function initializeTheme() {
    let saved = null;
    try {
        saved = localStorage.getItem("ainaa-theme");
    } catch (e) { /* storage unavailable — safe to ignore */ }
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (saved === "dark" || (!saved && prefersDark)) {
        document.documentElement.classList.add("dark-mode");
    }
}

/* ---------------------------------------------------------------------- */
/* Tabs                                                                      */
/* ---------------------------------------------------------------------- */

function switchTab(tabName, event) {
    if (event) event.preventDefault();

    document.querySelectorAll(".tab-content").forEach((tab) => tab.classList.remove("active"));
    document.querySelectorAll(".source-tab").forEach((btn) => {
        btn.classList.remove("active");
        btn.setAttribute("aria-selected", "false");
    });

    const tabElement = document.getElementById(tabName);
    if (tabElement) tabElement.classList.add("active");

    const btnElement = document.querySelector(`[data-tab="${tabName}"]`);
    if (btnElement) {
        btnElement.classList.add("active");
        btnElement.setAttribute("aria-selected", "true");
    }
}

/* ---------------------------------------------------------------------- */
/* Alerts                                                                    */
/* ---------------------------------------------------------------------- */

function showAlert(message) {
    const alert = document.getElementById("error-alert");
    const messageEl = document.getElementById("error-message");
    messageEl.textContent = message;
    alert.classList.add("show");
}

function closeAlert(button) {
    const alert = button.closest(".alert");
    alert.classList.remove("show");
}

/* ---------------------------------------------------------------------- */
/* Image sources — drag & drop / file picker                                */
/* ---------------------------------------------------------------------- */

function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById("drop-zone").classList.add("dragover");
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById("drop-zone").classList.remove("dragover");
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById("drop-zone").classList.remove("dragover");
    handleFiles(e.dataTransfer.files);
}

function handleFileInput(e) {
    handleFiles(e.target.files);
}

async function handleFiles(files) {
    const errors = [];
    const validFiles = [];

    for (const file of files) {
        if (!file.type.startsWith("image/")) {
            errors.push(`${file.name} is not an image file.`);
            continue;
        }
        if (file.size > 5 * 1024 * 1024) {
            errors.push(`${file.name} is larger than 5MB.`);
            continue;
        }
        validFiles.push(file);
    }

    if (errors.length > 0) showAlert(errors.join(" "));

    for (const file of validFiles) {
        await processFile(file);
    }
}

function processFile(file) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            uploadedImages.files.push(file);
            uploadedImages.dataUrls.push(e.target.result);
            addImagePreview(e.target.result, uploadedImages.files.length - 1);
            resolve();
        };
        reader.onerror = () => {
            showAlert(`Couldn't read ${file.name}.`);
            resolve();
        };
        reader.readAsDataURL(file);
    });
}

function addImagePreview(dataUrl, index) {
    const previewsContainer = document.getElementById("image-previews");

    const preview = document.createElement("div");
    preview.className = "image-preview";
    preview.dataset.index = index;

    const img = document.createElement("img");
    img.src = dataUrl;
    img.alt = `Upload ${index + 1}`;

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "image-preview-remove";
    removeBtn.textContent = "\u00D7";
    removeBtn.setAttribute("aria-label", "Remove image");
    removeBtn.onclick = (e) => {
        e.preventDefault();
        removeImagePreview(index);
    };

    preview.appendChild(img);
    preview.appendChild(removeBtn);
    previewsContainer.appendChild(preview);
}

function removeImagePreview(index) {
    uploadedImages.files.splice(index, 1);
    uploadedImages.dataUrls.splice(index, 1);

    const previewsContainer = document.getElementById("image-previews");
    previewsContainer.innerHTML = "";
    uploadedImages.dataUrls.forEach((url, i) => addImagePreview(url, i));
}

/* ---------------------------------------------------------------------- */
/* URL fields                                                                */
/* ---------------------------------------------------------------------- */

function addUrlField() {
    const container = document.getElementById("url-container");

    const wrapper = document.createElement("div");
    wrapper.className = "url-input-wrapper";

    const input = document.createElement("input");
    input.type = "url";
    input.placeholder = "https://example.com/garment.jpg";
    input.className = "url-input";
    input.setAttribute("aria-label", `Image URL ${container.children.length + 1}`);

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn-remove";
    removeBtn.textContent = "\u00D7";
    removeBtn.setAttribute("aria-label", "Remove URL");
    removeBtn.onclick = (e) => {
        e.preventDefault();
        removeUrlField(removeBtn);
    };

    wrapper.appendChild(input);
    wrapper.appendChild(removeBtn);
    container.appendChild(wrapper);
    input.focus();
}

function removeUrlField(button) {
    const container = document.getElementById("url-container");
    if (container.children.length > 1) {
        button.parentElement.remove();
    } else {
        showAlert("Keep at least one link field.");
    }
}

function getAllImageSources() {
    const dragDropTab = document.getElementById("drag-drop");

    if (dragDropTab.classList.contains("active")) {
        return [...uploadedImages.dataUrls];
    }

    return Array.from(document.querySelectorAll(".url-input"))
        .map((input) => input.value.trim())
        .filter((url) => url !== "");
}

/* ---------------------------------------------------------------------- */
/* Validation                                                                */
/* ---------------------------------------------------------------------- */

function validateTheme(theme) {
    if (!theme || theme.trim().length === 0) {
        showAlert("Please enter an editorial theme.");
        return false;
    }
    if (theme.trim().length < 5) {
        showAlert("The theme should be at least 5 characters.");
        return false;
    }
    return true;
}

function validateUrls(urls) {
    if (urls.length < 2) {
        showAlert("Please provide at least 2 images.");
        return false;
    }

    const httpsPattern = /^https?:\/\/.+/i;
    const dataUrlPattern = /^data:image\/\w+;base64,.+/i;

    for (const url of urls) {
        if (dataUrlPattern.test(url)) continue;
        if (!httpsPattern.test(url)) {
            showAlert(`Invalid image URL: ${url.substring(0, 60)}`);
            return false;
        }
    }

    return true;
}

/* ---------------------------------------------------------------------- */
/* Progress rail                                                            */
/* ---------------------------------------------------------------------- */

let progressTimer = null;

function resetProgress() {
    document.querySelectorAll("#progress-rail li").forEach((li) => {
        li.classList.remove("active", "complete");
    });
}

function setProgressStep(stepName) {
    const index = PROGRESS_STEPS.indexOf(stepName);
    document.querySelectorAll("#progress-rail li").forEach((li) => {
        const liIndex = PROGRESS_STEPS.indexOf(li.dataset.step);
        li.classList.remove("active", "complete");
        if (liIndex < index) li.classList.add("complete");
        if (liIndex === index) li.classList.add("active");
    });

    const counter = document.getElementById("progress-counter");
    if (counter) counter.textContent = `${index + 1} / ${PROGRESS_STEPS.length}`;
}

function startProgressSimulation() {
    resetProgress();
    let i = 0;
    setProgressStep(PROGRESS_STEPS[0]);

    // Advance through agent steps at a believable pace while the pipeline
    // runs server-side. The real response can arrive at any point; when it
    // does, finishProgress() jumps straight to "Done".
    const durations = [500, 1400, 1300, 1600, 1700, 1600, 1800];

    function advance() {
        i += 1;
        if (i >= PROGRESS_STEPS.length - 1) return;
        setProgressStep(PROGRESS_STEPS[i]);
        progressTimer = setTimeout(advance, durations[i] || 1500);
    }

    progressTimer = setTimeout(advance, durations[0]);
}

function finishProgress() {
    if (progressTimer) clearTimeout(progressTimer);
    setProgressStep("done");
}

/* ---------------------------------------------------------------------- */
/* Generate                                                                  */
/* ---------------------------------------------------------------------- */

async function generateLookbook() {
    const theme = document.getElementById("theme").value.trim();
    const urls = getAllImageSources();

    if (!validateTheme(theme) || !validateUrls(urls)) return;

    document.getElementById("results").innerHTML = "";
    document.getElementById("error-alert").classList.remove("show");

    const progressEl = document.getElementById("progress");
    progressEl.classList.add("show");
    startProgressSimulation();

    const generateBtn = document.getElementById("generate-btn");
    const generateLabel = generateBtn.querySelector(".btn-label");
    const originalLabel = generateLabel ? generateLabel.textContent : "";
    generateBtn.disabled = true;
    generateBtn.classList.add("is-loading");
    if (generateLabel) generateLabel.textContent = "Generating…";

    try {
        const response = await fetch("/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ theme_prompt: theme, image_urls: urls })
        });

        if (!response.ok) {
            let detail = "Failed to generate the lookbook.";
            try {
                const errorData = await response.json();
                detail = errorData.detail || detail;
            } catch (e) { /* response body wasn't JSON — use default message */ }
            throw new Error(detail);
        }

        const data = await response.json();
        finishProgress();

        setTimeout(() => {
            progressEl.classList.remove("show");
            renderLookbook(data);
            document.getElementById("results").scrollIntoView({ behavior: "smooth", block: "start" });
        }, 500);

    } catch (error) {
        progressEl.classList.remove("show");
        showAlert(error.message || "Something went wrong while generating the lookbook.");
    } finally {
        generateBtn.disabled = false;
        generateBtn.classList.remove("is-loading");
        if (generateLabel) generateLabel.textContent = originalLabel;
    }
}

/* ---------------------------------------------------------------------- */
/* Rendering                                                                 */
/* ---------------------------------------------------------------------- */

function escapeHtml(text) {
    if (text === null || text === undefined) return "";
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
    return String(text).replace(/[&<>"']/g, (m) => map[m]);
}

/* Scroll-reveal: elements fade/rise into place as they enter the viewport,
   with an optional stagger delay. Falls back to showing immediately if
   IntersectionObserver isn't available. */
let revealObserver = null;

function getRevealObserver() {
    if (revealObserver || !("IntersectionObserver" in window)) return revealObserver;
    revealObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("is-visible");
                revealObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    return revealObserver;
}

function reveal(el, delayMs = 0) {
    el.classList.add("reveal");
    if (delayMs) el.style.transitionDelay = `${delayMs}ms`;
    const observer = getRevealObserver();
    if (observer) {
        observer.observe(el);
    } else {
        el.classList.add("is-visible");
    }
    return el;
}

function renderLookbook(data) {
    const container = document.getElementById("results");
    container.innerHTML = "";

    if (!data || !data.lookbook || !Array.isArray(data.lookbook.collection)) {
        showAlert("The response didn't include a valid lookbook.");
        return;
    }

    const lookbook = data.lookbook;
    const visual = data.visual_lookbook || null;
    const cover = visual ? visual.cover : null;

    // Match visual artwork to each editorial card by card_number.
    const artworkByCard = {};
    if (visual && Array.isArray(visual.moods)) {
        visual.moods.forEach((m) => { artworkByCard[m.card_number] = m; });
    }

    container.appendChild(reveal(buildCoverSection(lookbook, cover)));
    container.appendChild(reveal(buildEditionInfo(lookbook, cover), 100));

    if (cover && Array.isArray(cover.color_palette) && cover.color_palette.length > 0) {
        container.appendChild(reveal(buildPaletteSection(cover.color_palette), 100));
    }

    container.appendChild(buildMoodsSection(lookbook.collection, artworkByCard));
}

function buildCoverSection(lookbook, cover) {
    const section = document.createElement("div");
    section.className = "cover";

    const imgUrl = cover && cover.image_url;

    if (imgUrl) {
        const img = document.createElement("img");
        img.src = imgUrl;
        img.alt = `Cover artwork for ${lookbook.edition_title}`;
        img.onerror = () => {
            img.remove();
            const fallback = document.createElement("div");
            fallback.className = "cover-fallback";
            fallback.textContent = "Cover artwork unavailable";
            section.insertBefore(fallback, section.firstChild);
        };
        section.appendChild(img);
    } else {
        const fallback = document.createElement("div");
        fallback.className = "cover-fallback";
        fallback.textContent = "Cover artwork unavailable";
        section.appendChild(fallback);
    }

    const scrim = document.createElement("div");
    scrim.className = "cover-scrim";
    section.appendChild(scrim);

    const overlay = document.createElement("div");
    overlay.className = "cover-overlay";
    overlay.innerHTML = `
        <p class="cover-eyebrow">AINAA Edition</p>
        <h2 class="cover-title">${escapeHtml(lookbook.edition_title || "Untitled Edition")}</h2>
    `;
    section.appendChild(overlay);

    return section;
}

function buildEditionInfo(lookbook, cover) {
    const grid = document.createElement("div");
    grid.className = "edition-info";

    const items = [
        { label: "Edition Title", value: lookbook.edition_title },
        { label: "Art Direction", value: cover ? cover.art_direction : null },
        { label: "Visual Language", value: cover ? cover.visual_language : null },
        { label: "Camera Style", value: cover ? cover.camera_style : null },
    ].filter((item) => item.value);

    items.forEach((item) => {
        const cell = document.createElement("div");
        cell.className = "edition-info-item";
        cell.innerHTML = `
            <p class="edition-info-label">${escapeHtml(item.label)}</p>
            <p class="edition-info-value">${escapeHtml(item.value)}</p>
        `;
        grid.appendChild(cell);
    });

    return grid;
}

function buildPaletteSection(colors) {
    const wrap = document.createElement("div");

    const heading = document.createElement("div");
    heading.className = "section-heading";
    heading.innerHTML = `<span class="num">03</span><h2>Color Palette</h2>`;
    wrap.appendChild(heading);

    const grid = document.createElement("div");
    grid.className = "palette";

    colors.forEach((hex) => {
        const swatch = document.createElement("div");
        swatch.className = "swatch";

        const block = document.createElement("div");
        block.className = "swatch-block";
        const safeHex = /^#([0-9a-f]{3}){1,2}$/i.test(hex) ? hex : "#cccccc";
        block.style.background = safeHex;

        const label = document.createElement("p");
        label.className = "swatch-hex";
        label.textContent = hex;

        swatch.appendChild(block);
        swatch.appendChild(label);
        grid.appendChild(swatch);
    });

    wrap.appendChild(grid);
    return wrap;
}

function buildMoodsSection(collection, artworkByCard) {
    const wrap = document.createElement("div");

    const heading = document.createElement("div");
    heading.className = "section-heading";
    heading.innerHTML = `<span class="num">04</span><h2>Mood Cards</h2>`;
    wrap.appendChild(reveal(heading));

    collection.forEach((card, index) => {
        const artwork = artworkByCard[card.card_number];
        wrap.appendChild(reveal(buildMoodCard(card, artwork), Math.min(index, 4) * 90));
    });

    return wrap;
}

function buildMoodCard(card, artwork) {
    const el = document.createElement("article");
    el.className = "mood-card";

    const media = document.createElement("div");
    media.className = "mood-media";

    const imgUrl = artwork && artwork.image_url;
    if (imgUrl) {
        const img = document.createElement("img");
        img.src = imgUrl;
        img.alt = card.mood_title || "Mood artwork";
        img.loading = "lazy";
        img.onerror = () => {
            img.remove();
            const fallback = document.createElement("div");
            fallback.className = "mood-fallback";
            fallback.textContent = "Image unavailable";
            media.appendChild(fallback);
        };
        media.appendChild(img);
    } else {
        const fallback = document.createElement("div");
        fallback.className = "mood-fallback";
        fallback.textContent = "Image unavailable";
        media.appendChild(fallback);
    }

    const body = document.createElement("div");
    body.className = "mood-body";

    const tags = Array.isArray(card.sub_tags) && card.sub_tags.length > 0
        ? `<div class="mood-tags">${card.sub_tags.map((t) => `<span class="mood-tag">${escapeHtml(t)}</span>`).join("")}</div>`
        : "";

    body.innerHTML = `
        <p class="mood-number">Card ${escapeHtml(card.card_number)}</p>
        <h3 class="mood-title">${escapeHtml(card.mood_title)}</h3>
        <p class="mood-meta"><strong>${escapeHtml(card.brand_or_designer)}</strong> — ${escapeHtml(card.product_type)}</p>
        ${tags}
        <p class="mood-vibe">${escapeHtml(card.vibe_description)}</p>
    `;

    el.appendChild(media);
    el.appendChild(body);
    return el;
}

/* ---------------------------------------------------------------------- */
/* Init                                                                      */
/* ---------------------------------------------------------------------- */

document.addEventListener("DOMContentLoaded", () => {
    initializeTheme();

    const masthead = document.querySelector(".masthead");
    if (masthead) {
        let ticking = false;
        window.addEventListener("scroll", () => {
            if (ticking) return;
            ticking = true;
            requestAnimationFrame(() => {
                masthead.classList.toggle("is-condensed", window.scrollY > 40);
                ticking = false;
            });
        });
    }

    document.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            const generateBtn = document.getElementById("generate-btn");
            if (!generateBtn.disabled) generateLookbook();
        }
    });
});
