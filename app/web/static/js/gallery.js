/**
 * Gallery page functionality
 */

let allImages = [];
let currentView = 'grid';

// Load gallery on page load
$(document).ready(function() {
    loadGallery();
});

// Search filter
$('#search-filter').on('input', function() {
    filterGallery();
});

// Sort filter
$('#sort-filter').change(function() {
    sortGallery($(this).val());
});

function loadGallery() {
    $('#loading-gallery').show();
    $('#empty-gallery').hide();
    $('#gallery-container').hide();
    $('#gallery-list').hide();
    
    $.get('/rpi-security-cam/web/api/images/list', function(response) {
        if (response.success && response.data.images.length > 0) {
            allImages = response.data.images;
            displayGallery(allImages);
        } else {
            $('#loading-gallery').hide();
            $('#empty-gallery').show();
        }
    }).fail(function() {
        $('#loading-gallery').hide();
        showToast('Failed to load images', 'danger');
    });
}

function displayGallery(images) {
    $('#loading-gallery').hide();
    
    if (currentView === 'grid') {
        displayGridView(images);
    } else {
        displayListView(images);
    }
}

function displayGridView(images) {
    $('#gallery-list').hide();
    $('#gallery-container').show().empty();
    
    images.forEach(function(image) {
        const date = new Date(image.created * 1000);
        const dateStr = date.toLocaleString();
        const sizeKB = (image.size / 1024).toFixed(1);
        
        const card = $(`
            <div class="gallery-item" data-filename="${image.filename}">
                <img src="/rpi-security-cam/web/api/image/${image.filename}" 
                     alt="${image.filename}"
                     loading="lazy">
                <div class="gallery-item-overlay">
                    <div>${image.filename}</div>
                    <div class="small">${dateStr} • ${sizeKB} KB</div>
                </div>
            </div>
        `);
        
        card.click(function() {
            showImageModal(image);
        });
        
        $('#gallery-container').append(card);
    });
}

function displayListView(images) {
    $('#gallery-container').hide();
    $('#gallery-list').show().empty();
    
    images.forEach(function(image) {
        const date = new Date(image.created * 1000);
        const dateStr = date.toLocaleString();
        const sizeKB = (image.size / 1024).toFixed(1);
        
        const item = $(`
            <a href="#" class="list-group-item list-group-item-action" data-filename="${image.filename}">
                <div class="d-flex w-100 justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">${image.filename}</h6>
                        <small class="text-muted">${dateStr} • ${sizeKB} KB</small>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-primary me-2" onclick="event.preventDefault(); viewImage('${image.filename}')">
                            <i class="bi bi-eye"></i>
                        </button>
                        <a href="/rpi-security-cam/web/api/image/${image.filename}" 
                           class="btn btn-sm btn-success" download>
                            <i class="bi bi-download"></i>
                        </a>
                    </div>
                </div>
            </a>
        `);
        
        item.click(function(e) {
            e.preventDefault();
            showImageModal(image);
        });
        
        $('#gallery-list').append(item);
    });
}

function showImageModal(image) {
    const date = new Date(image.created * 1000);
    const dateStr = date.toLocaleString();
    const sizeKB = (image.size / 1024).toFixed(1);
    
    $('#modal-image').attr('src', `/rpi-security-cam/web/api/image/${image.filename}`);
    $('#modal-filename').text(image.filename);
    $('#modal-date').text(dateStr);
    $('#modal-size').text(sizeKB + ' KB');
    $('#modal-download').attr('href', `/rpi-security-cam/web/api/image/${image.filename}`);
    $('#modal-download').attr('download', image.filename);
    
    const modal = new bootstrap.Modal($('#imageModal')[0]);
    modal.show();
}

function viewImage(filename) {
    const image = allImages.find(img => img.filename === filename);
    if (image) {
        showImageModal(image);
    }
}

function filterGallery() {
    const searchTerm = $('#search-filter').val().toLowerCase();
    
    const filtered = allImages.filter(function(image) {
        return image.filename.toLowerCase().includes(searchTerm);
    });
    
    displayGallery(filtered);
}

function sortGallery(sortType) {
    let sorted = [...allImages];
    
    switch(sortType) {
        case 'newest':
            sorted.sort((a, b) => b.created - a.created);
            break;
        case 'oldest':
            sorted.sort((a, b) => a.created - b.created);
            break;
        case 'name':
            sorted.sort((a, b) => a.filename.localeCompare(b.filename));
            break;
    }
    
    displayGallery(sorted);
}

function changeView(view) {
    currentView = view;
    
    // Update button states
    $('button[data-view]').removeClass('active');
    $(`button[data-view="${view}"]`).addClass('active');
    
    // Display in new view
    displayGallery(allImages);
}

function refreshGallery() {
    loadGallery();
    showToast('Gallery refreshed', 'info');
}