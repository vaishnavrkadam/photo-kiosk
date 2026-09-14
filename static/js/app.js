// Smart Photo Kiosk Frontend Controller
// Supports Standard Prints (4x6, 5x7, Polaroids) and Passport 8-Photo Grid Studio

let currentMode = 'standard'; // 'standard' | 'passport'
let uploadedPhotos = []; // List of photos for Standard Mode
let passportPhoto = null; // Single photo object for Passport Mode
let currentCroppingIndex = null;
let cropperInstance = null;
let isPassportCropping = false;

// DOM Elements
const tabStandardMode = document.getElementById('tabStandardMode');
const tabPassportMode = document.getElementById('tabPassportMode');
const passportBanner = document.getElementById('passportBanner');
const photoInput = document.getElementById('photoInput');
const dropZone = document.getElementById('dropZone');
const dropZoneTitle = document.getElementById('dropZoneTitle');
const dropZoneSubtitle = document.getElementById('dropZoneSubtitle');
const uploadStepTitle = document.getElementById('uploadStepTitle');
const uploadProgressContainer = document.getElementById('uploadProgressContainer');
const uploadProgressBar = document.getElementById('uploadProgressBar');
const uploadPercent = document.getElementById('uploadPercent');

const customizationSection = document.getElementById('customizationSection');
const photosList = document.getElementById('photosList');
const photoCountBadge = document.getElementById('photoCountBadge');

// Passport Preview Elements
const passportPreviewSection = document.getElementById('passportPreviewSection');
const passportPreviewImg = document.getElementById('passportPreviewImg');
const passportRecropBtn = document.getElementById('passportRecropBtn');
const passportColorBtn = document.getElementById('passportColorBtn');
const passportBwBtn = document.getElementById('passportBwBtn');
const passportCopiesText = document.getElementById('passportCopiesText');

// Checkout Bar Elements
const checkoutBar = document.getElementById('checkoutBar');
const barTotalAmount = document.getElementById('barTotalAmount');
const barDiscountBadge = document.getElementById('barDiscountBadge');
const barPrintSummary = document.getElementById('barPrintSummary');
const payNowBtn = document.getElementById('payNowBtn');
const customerDetailsSection = document.getElementById('customerDetailsSection');

// Crop Modal Elements
const cropModal = document.getElementById('cropModal');
const cropModalTitle = document.getElementById('cropModalTitle');
const cropModalSubtitle = document.getElementById('cropModalSubtitle');
const cropImage = document.getElementById('cropImage');
const passportFaceGuide = document.getElementById('passportFaceGuide');
const closeCropBtn = document.getElementById('closeCropBtn');
const applyCropBtn = document.getElementById('applyCropBtn');
const rotateCropBtn = document.getElementById('rotateCropBtn');

// ==========================================
// 1. Mode Switching
// ==========================================
function switchMode(mode) {
    if (currentMode === mode) return;
    currentMode = mode;

    if (mode === 'standard') {
        tabStandardMode.className = 'flex-1 py-2.5 px-3 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all bg-amber-500 text-slate-950 shadow-md';
        tabPassportMode.className = 'flex-1 py-2.5 px-3 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all text-slate-400 hover:text-white';
        passportBanner.classList.add('hidden');
        passportPreviewSection.classList.add('hidden');
        photoInput.multiple = true;
        uploadStepTitle.innerText = "Upload Your Photos";
        dropZoneTitle.innerText = "Tap here to choose photos";
        dropZoneSubtitle.innerText = "Supports camera photos, JPEG, PNG, HEIC";
        renderPhotosList();
    } else {
        tabPassportMode.className = 'flex-1 py-2.5 px-3 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all bg-amber-500 text-slate-950 shadow-md';
        tabStandardMode.className = 'flex-1 py-2.5 px-3 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all text-slate-400 hover:text-white';
        passportBanner.classList.remove('hidden');
        customizationSection.classList.add('hidden');
        photoInput.multiple = false;
        uploadStepTitle.innerText = "Upload Your Portrait Photo";
        dropZoneTitle.innerText = "Tap here to choose your portrait photo";
        dropZoneSubtitle.innerText = "Upload 1 clear front-facing portrait photo";
        renderPassportUI();
    }
    updatePrice();
}

// ==========================================
// 2. File Upload Handling
// ==========================================
photoInput.addEventListener('change', handleFileSelect);

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('border-amber-500', 'bg-amber-500/10');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('border-amber-500', 'bg-amber-500/10');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('border-amber-500', 'bg-amber-500/10');
    if (e.dataTransfer.files.length > 0) {
        uploadFiles(e.dataTransfer.files);
    }
});

document.getElementById('addMorePhotosBtn')?.addEventListener('click', () => {
    photoInput.click();
});

function handleFileSelect(e) {
    if (e.target.files.length > 0) {
        uploadFiles(e.target.files);
    }
}

async function uploadFiles(files) {
    const formData = new FormData();
    const count = currentMode === 'passport' ? 1 : files.length;
    for (let i = 0; i < count; i++) {
        formData.append('photos', files[i]);
    }

    uploadProgressContainer.classList.remove('hidden');
    uploadProgressBar.style.width = '25%';
    uploadPercent.innerText = '25%';

    try {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/upload', true);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                uploadProgressBar.style.width = percent + '%';
                uploadPercent.innerText = percent + '%';
            }
        };

        xhr.onload = () => {
            uploadProgressContainer.classList.add('hidden');
            if (xhr.status === 200) {
                const res = JSON.parse(xhr.responseText);
                if (res.success && res.files.length > 0) {
                    if (currentMode === 'standard') {
                        const startIndex = uploadedPhotos.length;
                        res.files.forEach(f => {
                            uploadedPhotos.push({
                                original_name: f.original_name,
                                raw_filename: f.raw_filename,
                                url: f.url,
                                width: f.width,
                                height: f.height,
                                paper_size: '4x6',
                                layout_mode: 'borderless',
                                color_mode: 'color',
                                copies: 1,
                                caption: '',
                                crop_box: null,
                                preview_url: null
                            });
                        });
                        renderPhotosList();
                        updatePrice();

                        // Automatically open framing adjustment modal for newly uploaded photo!
                        openStandardCropper(startIndex);

                    } else {
                        // Passport Mode: single photo
                        const f = res.files[0];
                        passportPhoto = {
                            original_name: f.original_name,
                            raw_filename: f.raw_filename,
                            url: f.url,
                            width: f.width,
                            height: f.height,
                            crop_box: null,
                            color_mode: 'color',
                            copies: 1,
                            preview_url: null
                        };
                        // Automatically open Cropper with passport ratio (3.5 : 4.5)
                        openPassportCropper();
                    }
                }
            } else {
                alert('Upload failed. Please try again.');
            }
        };

        xhr.onerror = () => {
            uploadProgressContainer.classList.add('hidden');
            alert('Network error while uploading.');
        };

        xhr.send(formData);
    } catch (err) {
        uploadProgressContainer.classList.add('hidden');
        console.error(err);
        alert('Upload error: ' + err.message);
    }
}

// ==========================================
// 3. Passport Photo Handling & Preview
// ==========================================
function openPassportCropper() {
    if (!passportPhoto) return;
    isPassportCropping = true;
    cropModalTitle.innerText = "Crop to Passport Size (3.5 cm × 4.5 cm)";
    cropModalSubtitle.innerText = "Position face centered inside the dashed oval frame. Use Rotate if required.";
    passportFaceGuide.classList.remove('hidden');

    cropImage.src = passportPhoto.url;
    cropModal.classList.remove('hidden');

    if (cropperInstance) {
        cropperInstance.destroy();
    }

    // Fixed 3.5cm x 4.5cm ratio (35 / 45 = 7 / 9 = ~0.77778)
    const passportRatio = 35 / 45;

    cropperInstance = new Cropper(cropImage, {
        aspectRatio: passportRatio,
        viewMode: 1,
        autoCropArea: 0.85,
        responsive: true
    });
}

passportRecropBtn?.addEventListener('click', () => {
    openPassportCropper();
});

async function generatePassportPreview() {
    if (!passportPhoto) return;

    passportPreviewImg.src = '';
    passportPreviewImg.alt = 'Generating 8-photo grid preview...';

    try {
        const res = await fetch('/api/passport/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                raw_filename: passportPhoto.raw_filename,
                crop_box: passportPhoto.crop_box,
                color_mode: passportPhoto.color_mode
            })
        });

        const data = await res.json();
        if (data.success) {
            passportPhoto.preview_url = data.preview_url + '?t=' + Date.now();
            passportPreviewImg.src = passportPhoto.preview_url;
            renderPassportUI();
            updatePrice();
        } else {
            alert('Could not render passport preview: ' + data.error);
        }
    } catch (e) {
        console.error('Passport preview error', e);
    }
}

function setPassportColorTone(tone) {
    if (!passportPhoto) return;
    passportPhoto.color_mode = tone;

    if (tone === 'color') {
        passportColorBtn.className = 'py-1.5 rounded-lg border text-center font-medium bg-amber-500/20 text-amber-400 border-amber-500';
        passportBwBtn.className = 'py-1.5 rounded-lg border text-center font-medium bg-slate-950 text-slate-400 border-slate-800';
    } else {
        passportBwBtn.className = 'py-1.5 rounded-lg border text-center font-medium bg-amber-500/20 text-amber-400 border-amber-500';
        passportColorBtn.className = 'py-1.5 rounded-lg border text-center font-medium bg-slate-950 text-slate-400 border-slate-800';
    }

    generatePassportPreview();
}

function changePassportCopies(delta) {
    if (!passportPhoto) return;
    const next = passportPhoto.copies + delta;
    if (next >= 1 && next <= 10) {
        passportPhoto.copies = next;
        passportCopiesText.innerText = `${next} Sheet${next > 1 ? 's' : ''} (${next * 8} photos)`;
        updatePrice();
    }
}

function renderPassportUI() {
    if (!passportPhoto || !passportPhoto.preview_url) {
        passportPreviewSection.classList.add('hidden');
        customerDetailsSection.classList.add('hidden');
        checkoutBar.classList.add('hidden');
        photoCountBadge.classList.add('hidden');
        return;
    }

    passportPreviewSection.classList.remove('hidden');
    customerDetailsSection.classList.remove('hidden');
    checkoutBar.classList.remove('hidden');
    photoCountBadge.classList.remove('hidden');
    photoCountBadge.innerText = '1 Passport Photo';
    passportCopiesText.innerText = `${passportPhoto.copies} Sheet${passportPhoto.copies > 1 ? 's' : ''} (${passportPhoto.copies * 8} photos)`;
}

// ==========================================
// 4. Standard Photo List Rendering & Live Previews
// ==========================================
function renderPhotosList() {
    if (uploadedPhotos.length === 0) {
        customizationSection.classList.add('hidden');
        customerDetailsSection.classList.add('hidden');
        checkoutBar.classList.add('hidden');
        photoCountBadge.classList.add('hidden');
        return;
    }

    customizationSection.classList.remove('hidden');
    customerDetailsSection.classList.remove('hidden');
    checkoutBar.classList.remove('hidden');
    photoCountBadge.classList.remove('hidden');
    photoCountBadge.innerText = `${uploadedPhotos.length} Photo${uploadedPhotos.length > 1 ? 's' : ''}`;

    photosList.innerHTML = uploadedPhotos.map((photo, index) => {
        const displayThumb = photo.preview_url || photo.url;
        const isFramed = (photo.crop_box !== null);

        return `
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl space-y-3 relative">
            <button onclick="removePhoto(${index})" class="absolute top-3 right-3 text-slate-500 hover:text-rose-400 p-1">
                <i class="fa-solid fa-trash text-sm"></i>
            </button>

            <div class="flex items-start space-x-3">
                <div class="relative w-28 h-28 rounded-xl overflow-hidden bg-slate-950 flex-shrink-0 border border-slate-700 shadow-inner flex items-center justify-center">
                    <img src="${displayThumb}" alt="Preview" class="w-full h-full object-cover">
                    <button onclick="openStandardCropper(${index})" class="absolute bottom-1 right-1 px-2 py-0.5 rounded bg-black/80 hover:bg-amber-500 hover:text-slate-950 text-[10px] font-bold text-amber-400 border border-amber-400/40">
                        <i class="fa-solid fa-crop-simple mr-0.5"></i> Adjust
                    </button>
                </div>

                <div class="flex-1 min-w-0 space-y-1.5">
                    <div class="flex items-center space-x-2 pr-6">
                        <p class="text-xs font-semibold text-slate-200 truncate">${photo.original_name}</p>
                    </div>

                    <!-- Status badge -->
                    <div>
                        ${isFramed ? 
                            `<span class="inline-flex items-center text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20"><i class="fa-solid fa-check mr-1"></i>Framed Preview Ready</span>` : 
                            `<span class="inline-flex items-center text-[10px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20"><i class="fa-solid fa-triangle-exclamation mr-1"></i>Framing Needed</span>`
                        }
                    </div>
                    
                    <!-- Paper Size Picker -->
                    <div class="flex items-center space-x-2 pt-1">
                        <label class="text-[11px] text-slate-400">Size:</label>
                        <select onchange="changePaperSize(${index}, this.value)" class="bg-slate-950 text-xs text-amber-400 border border-slate-700 rounded-lg px-2 py-1 focus:outline-none">
                            <option value="4x6" ${photo.paper_size === '4x6' ? 'selected' : ''}>4 x 6" (Standard - ₹50)</option>
                            <option value="5x7" ${photo.paper_size === '5x7' ? 'selected' : ''}>5 x 7" (Large - ₹80)</option>
                        </select>
                    </div>

                    <!-- Copies Counter -->
                    <div class="flex items-center space-x-3 pt-1">
                        <label class="text-[11px] text-slate-400">Copies:</label>
                        <div class="flex items-center space-x-1.5 bg-slate-950 border border-slate-700 rounded-lg px-2 py-0.5">
                            <button onclick="changeCopies(${index}, -1)" class="text-slate-400 hover:text-white px-1 text-xs"><i class="fa-solid fa-minus"></i></button>
                            <span class="text-xs font-bold text-slate-200 w-4 text-center">${photo.copies}</span>
                            <button onclick="changeCopies(${index}, 1)" class="text-slate-400 hover:text-white px-1 text-xs"><i class="fa-solid fa-plus"></i></button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Layout Mode Options -->
            <div class="space-y-1 pt-1 border-t border-slate-800/80">
                <label class="text-[11px] text-slate-400 block">Layout Style:</label>
                <div class="grid grid-cols-3 gap-2 text-xs">
                    <button onclick="updateLayout(${index}, 'borderless')" class="py-1.5 rounded-lg border text-center font-medium ${photo.layout_mode === 'borderless' ? 'bg-amber-500/20 text-amber-400 border-amber-500' : 'bg-slate-950 text-slate-400 border-slate-800'}">
                        Borderless
                    </button>
                    <button onclick="updateLayout(${index}, 'bordered')" class="py-1.5 rounded-lg border text-center font-medium ${photo.layout_mode === 'bordered' ? 'bg-amber-500/20 text-amber-400 border-amber-500' : 'bg-slate-950 text-slate-400 border-slate-800'}">
                        Bordered
                    </button>
                    <button onclick="updateLayout(${index}, 'polaroid')" class="py-1.5 rounded-lg border text-center font-medium ${photo.layout_mode === 'polaroid' ? 'bg-amber-500/20 text-amber-400 border-amber-500' : 'bg-slate-950 text-slate-400 border-slate-800'}">
                        Polaroid
                    </button>
                </div>
            </div>

            <!-- Polaroid Caption Input -->
            <div class="${photo.layout_mode === 'polaroid' ? '' : 'hidden'} pt-1">
                <input type="text" value="${photo.caption || ''}" onchange="updateCaption(${index}, this.value)" placeholder="Write a Polaroid caption (optional)..." class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500">
            </div>

            <!-- Color Filter Mode -->
            <div class="space-y-1 pt-1 border-t border-slate-800/80">
                <label class="text-[11px] text-slate-400 block">Color Tone:</label>
                <div class="grid grid-cols-3 gap-2 text-xs">
                    <button onclick="updateColorTone(${index}, 'color')" class="py-1 rounded-lg border text-center font-medium ${photo.color_mode === 'color' ? 'bg-amber-500/20 text-amber-400 border-amber-500' : 'bg-slate-950 text-slate-400 border-slate-800'}">
                        Color
                    </button>
                    <button onclick="updateColorTone(${index}, 'bw')" class="py-1 rounded-lg border text-center font-medium ${photo.color_mode === 'bw' ? 'bg-amber-500/20 text-amber-400 border-amber-500' : 'bg-slate-950 text-slate-400 border-slate-800'}">
                        B & W
                    </button>
                    <button onclick="updateColorTone(${index}, 'sepia')" class="py-1 rounded-lg border text-center font-medium ${photo.color_mode === 'sepia' ? 'bg-amber-500/20 text-amber-400 border-amber-500' : 'bg-slate-950 text-slate-400 border-slate-800'}">
                        Sepia
                    </button>
                </div>
            </div>
        </div>
    `}).join('');
}

async function generateStandardPreview(index) {
    const photo = uploadedPhotos[index];
    if (!photo) return;

    try {
        const res = await fetch('/api/photo/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                raw_filename: photo.raw_filename,
                paper_size: photo.paper_size,
                layout_mode: photo.layout_mode,
                color_mode: photo.color_mode,
                crop_box: photo.crop_box,
                caption: photo.caption
            })
        });
        const data = await res.json();
        if (data.success) {
            photo.preview_url = data.preview_url + '?t=' + Date.now();
            renderPhotosList();
        }
    } catch (e) {
        console.error("Failed to generate preview", e);
    }
}

function changePaperSize(index, newSize) {
    uploadedPhotos[index].paper_size = newSize;
    renderPhotosList();
    updatePrice();
    // Prompt framing adjustment for the new paper size aspect ratio!
    openStandardCropper(index);
}

function updateLayout(index, layout) {
    uploadedPhotos[index].layout_mode = layout;
    renderPhotosList();
    generateStandardPreview(index);
}

function updateCaption(index, caption) {
    uploadedPhotos[index].caption = caption;
    generateStandardPreview(index);
}

function updateColorTone(index, color) {
    uploadedPhotos[index].color_mode = color;
    renderPhotosList();
    generateStandardPreview(index);
}

function changeCopies(index, delta) {
    const next = uploadedPhotos[index].copies + delta;
    if (next >= 1 && next <= 10) {
        uploadedPhotos[index].copies = next;
        renderPhotosList();
        updatePrice();
    }
}

function removePhoto(index) {
    uploadedPhotos.splice(index, 1);
    renderPhotosList();
    updatePrice();
}

// ==========================================
// 5. Price Calculation
// ==========================================
async function updatePrice() {
    let itemsToPrice = [];

    if (currentMode === 'standard') {
        if (uploadedPhotos.length === 0) return;
        itemsToPrice = uploadedPhotos;
    } else {
        if (!passportPhoto) return;
        itemsToPrice = [{
            paper_size: 'passport',
            copies: passportPhoto.copies
        }];
    }

    try {
        const res = await fetch('/api/order/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ items: itemsToPrice })
        });
        const data = await res.json();

        barTotalAmount.innerText = `₹${data.total_amount}`;

        if (currentMode === 'standard') {
            barPrintSummary.innerText = `${data.total_prints} print${data.total_prints > 1 ? 's' : ''} total`;
        } else {
            const totalPhotos = passportPhoto.copies * 8;
            barPrintSummary.innerText = `${passportPhoto.copies} sheet (${totalPhotos} passport photos)`;
        }

        if (data.discount > 0) {
            barDiscountBadge.classList.remove('hidden');
        } else {
            barDiscountBadge.classList.add('hidden');
        }
    } catch (e) {
        console.error("Price calculation failed", e);
    }
}

// ==========================================
// 6. Cropping Logic (Standard & Passport)
// ==========================================
function openStandardCropper(index) {
    isPassportCropping = false;
    currentCroppingIndex = index;
    const photo = uploadedPhotos[index];
    cropModalTitle.innerText = `Adjust Framing for ${photo.paper_size === '5x7' ? '5×7' : '4×6'} Paper`;
    cropModalSubtitle.innerText = "Phone photos and photo paper have different shapes. Drag the frame to compose your print, and tap Rotate if needed.";
    passportFaceGuide.classList.add('hidden');

    cropImage.src = photo.url;
    cropModal.classList.remove('hidden');

    const aspectRatio = photo.paper_size === '5x7' ? (7 / 5) : (6 / 4);

    if (cropperInstance) {
        cropperInstance.destroy();
    }

    cropperInstance = new Cropper(cropImage, {
        aspectRatio: photo.width > photo.height ? aspectRatio : (1 / aspectRatio),
        viewMode: 1,
        autoCropArea: 0.95,
        responsive: true
    });
}

closeCropBtn.addEventListener('click', () => {
    cropModal.classList.add('hidden');
    if (cropperInstance) {
        cropperInstance.destroy();
        cropperInstance = null;
    }
});

rotateCropBtn.addEventListener('click', () => {
    if (cropperInstance) {
        cropperInstance.rotate(90);
    }
});

applyCropBtn.addEventListener('click', () => {
    if (!cropperInstance) return;

    const cropData = cropperInstance.getData(true); // coordinates and rotate

    if (isPassportCropping) {
        passportPhoto.crop_box = [cropData.x, cropData.y, cropData.width, cropData.height, cropData.rotate || 0];
        cropModal.classList.add('hidden');
        cropperInstance.destroy();
        cropperInstance = null;
        generatePassportPreview();
    } else {
        if (currentCroppingIndex !== null) {
            uploadedPhotos[currentCroppingIndex].crop_box = [cropData.x, cropData.y, cropData.width, cropData.height, cropData.rotate || 0];
            const framedIdx = currentCroppingIndex;
            cropModal.classList.add('hidden');
            cropperInstance.destroy();
            cropperInstance = null;

            // Generate print preview
            generateStandardPreview(framedIdx);

            // Check if there are other newly uploaded photos that need framing
            const nextUnframed = uploadedPhotos.findIndex(p => p.crop_box === null);
            if (nextUnframed !== -1) {
                setTimeout(() => openStandardCropper(nextUnframed), 200);
            }
        }
    }
});

// ==========================================
// 7. Checkout & Payment Handler
// ==========================================
payNowBtn.addEventListener('click', async () => {
    let orderItems = [];

    if (currentMode === 'standard') {
        if (uploadedPhotos.length === 0) return;

        // Ensure all photos have framing adjusted
        const unframedIdx = uploadedPhotos.findIndex(p => p.crop_box === null);
        if (unframedIdx !== -1) {
            alert(`Please adjust the framing for Photo #${unframedIdx + 1} (${uploadedPhotos[unframedIdx].original_name}) before proceeding.`);
            openStandardCropper(unframedIdx);
            return;
        }

        orderItems = uploadedPhotos;
    } else {
        if (!passportPhoto || !passportPhoto.preview_url) {
            alert('Please crop and confirm your passport photo first.');
            return;
        }
        orderItems = [{
            paper_size: 'passport',
            layout_mode: 'grid',
            color_mode: passportPhoto.color_mode,
            copies: passportPhoto.copies,
            crop_box: passportPhoto.crop_box,
            raw_filename: passportPhoto.raw_filename,
            original_name: passportPhoto.original_name,
            caption: ''
        }];
    }

    const nameInput = document.getElementById('custName');
    const phoneInput = document.getElementById('custPhone');
    const custName = (nameInput ? nameInput.value.trim() : '');
    const custPhone = (phoneInput ? phoneInput.value.trim() : '');

    if (!custName) {
        alert("Please enter your Name before proceeding to payment.");
        if (nameInput) {
            nameInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
            nameInput.focus();
        }
        return;
    }

    if (!custPhone) {
        alert("Please enter your Mobile Number before proceeding to payment.");
        if (phoneInput) {
            phoneInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
            phoneInput.focus();
        }
        return;
    }

    const cleanPhoneDigits = custPhone.replace(/\D/g, '');
    if (cleanPhoneDigits.length < 10) {
        alert("Please enter a valid 10-digit mobile number.");
        if (phoneInput) {
            phoneInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
            phoneInput.focus();
        }
        return;
    }

    payNowBtn.disabled = true;
    payNowBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Checking Paper Stock...';

    try {
        // Step A: Create Order on Backend (Validates Paper Inventory Stock)
        const orderRes = await fetch('/api/order/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                items: orderItems,
                customer_name: custName,
                customer_phone: custPhone
            })
        });

        const orderData = await orderRes.json();
        if (!orderRes.ok || !orderData.success) {
            throw new Error(orderData.error || 'Failed to create order');
        }

        // Step B: Razorpay Checkout
        if (orderData.is_simulation) {
            verifyAndProceed(orderData.order_id, orderData.razorpay_order_id, 'sim_pay_' + Date.now(), 'sim_sig_ok');
            return;
        }

        const options = {
            key: orderData.razorpay_key_id,
            amount: orderData.amount_paise,
            currency: orderData.currency,
            name: 'Smart Photo Kiosk',
            description: currentMode === 'passport' ? 'Passport 8-Photo Print Sheet' : `Order #${orderData.order_id}`,
            order_id: orderData.razorpay_order_id,
            prefill: {
                name: orderData.customer_name,
                contact: orderData.customer_phone
            },
            theme: {
                color: '#f59e0b'
            },
            handler: function (response) {
                verifyAndProceed(
                    orderData.order_id,
                    response.razorpay_order_id,
                    response.razorpay_payment_id,
                    response.razorpay_signature
                );
            },
            modal: {
                ondismiss: function () {
                    payNowBtn.disabled = false;
                    payNowBtn.innerHTML = '<span>Proceed to Pay</span> <i class="fa-solid fa-arrow-right text-xs"></i>';
                }
            }
        };

        const rzp = new Razorpay(options);
        rzp.open();

    } catch (err) {
        alert(err.message);
        payNowBtn.disabled = false;
        payNowBtn.innerHTML = '<span>Proceed to Pay</span> <i class="fa-solid fa-arrow-right text-xs"></i>';
    }
});

async function verifyAndProceed(orderId, rzpOrderId, rzpPaymentId, rzpSignature) {
    payNowBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Verifying Payment...';
    try {
        const verifyRes = await fetch('/api/payment/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                order_id: orderId,
                razorpay_order_id: rzpOrderId,
                razorpay_payment_id: rzpPaymentId,
                razorpay_signature: rzpSignature
            })
        });

        const verifyData = await verifyRes.json();
        if (verifyData.success) {
            window.location.href = verifyData.redirect_url;
        } else {
            alert('Payment verification failed: ' + verifyData.error);
            payNowBtn.disabled = false;
            payNowBtn.innerHTML = '<span>Proceed to Pay</span>';
        }
    } catch (e) {
        alert('Verification error: ' + e.message);
        payNowBtn.disabled = false;
        payNowBtn.innerHTML = '<span>Proceed to Pay</span>';
    }
}
