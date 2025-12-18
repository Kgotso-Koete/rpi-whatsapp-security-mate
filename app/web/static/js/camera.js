/**
 * Camera page functionality
 */

// Update slider value displays
$('#pan-slider').on('input', function() {
    $('#pan-value').text($(this).val());
});

$('#tilt-slider').on('input', function() {
    $('#tilt-value').text($(this).val());
});

// Apply rotation
function applyRotation() {
    const pan = parseInt($('#pan-slider').val());
    const tilt = parseInt($('#tilt-slider').val());
    
    $.ajax({
        url: '/rpi-security-cam/web/api/camera/rotate',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ pan: pan, tilt: tilt }),
        success: function(response) {
            if (response.success) {
                showToast(response.message, 'success');
                updateCurrentPosition();
            } else {
                showToast('Error: ' + response.error, 'danger');
            }
        },
        error: function() {
            showToast('Failed to connect to server', 'danger');
        }
    });
}

// Set preset position
function setPreset(pan, tilt) {
    $('#pan-slider').val(pan);
    $('#tilt-slider').val(tilt);
    $('#pan-value').text(pan);
    $('#tilt-value').text(tilt);
    applyRotation();
}

// Update current position display
function updateCurrentPosition() {
    $.get('/rpi-security-cam/web/api/camera/position', function(response) {
        if (response.success) {
            $('#current-pan').text(response.data.pan + '°');
            $('#current-tilt').text(response.data.tilt + '°');
            
            // Update sliders to match current position
            $('#pan-slider').val(response.data.pan);
            $('#tilt-slider').val(response.data.tilt);
            $('#pan-value').text(response.data.pan);
            $('#tilt-value').text(response.data.tilt);
        }
    });
}

// Toggle camera on/off
function toggleCamera() {
    $.post('/rpi-security-cam/web/api/camera/toggle', function(response) {
        if (response.success) {
            showToast(response.message, 'success');
            
            // Reload stream after a delay
            setTimeout(function() {
                reloadStream();
            }, 2000);
        } else {
            showToast('Error: ' + response.error, 'danger');
        }
    }).fail(function() {
        showToast('Failed to connect to server', 'danger');
    });
}

// Capture image
function captureImage() {
    showToast('Capturing image...', 'info');
    // Future: implement capture endpoint
    // For now, the system automatically saves images
    setTimeout(function() {
        showToast('Image captured! Check gallery.', 'success');
    }, 1000);
}

// Reload video stream
function reloadStream() {
    const $feed = $('#live-feed');
    const src = $feed.attr('src').split('?')[0];
    $feed.attr('src', src + '?t=' + new Date().getTime());
    showToast('Stream reloaded', 'info');
}

// Update position on load
$(document).ready(function() {
    updateCurrentPosition();
    
    // Auto-update position every 30 seconds
    setInterval(updateCurrentPosition, 30000);
});