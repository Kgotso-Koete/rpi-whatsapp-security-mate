/**
 * Dashboard functionality
 */

// Camera toggle
$('#camera-toggle').change(function() {
    const isChecked = $(this).is(':checked');
    const url = isChecked ? '/web/api/camera/on' : '/web/api/camera/off';
    
    $.post(url, function(response) {
        if (response.success) {
            $('#camera-status-text').text(isChecked ? 'ON' : 'OFF');
            showToast(response.message, 'success');
        } else {
            // Revert toggle on error
            $('#camera-toggle').prop('checked', !isChecked);
            showToast('Error: ' + response.error, 'danger');
        }
    }).fail(function() {
        $('#camera-toggle').prop('checked', !isChecked);
        showToast('Failed to connect to server', 'danger');
    });
});

// Notifications toggle
$('#notifications-toggle').change(function() {
    const isChecked = $(this).is(':checked');
    
    $.ajax({
        url: '/web/api/notifications/toggle',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ enable: isChecked }),
        success: function(response) {
            if (response.success) {
                $('#notifications-status-text').text(isChecked ? 'ON' : 'OFF');
                showToast(response.message, 'success');
            } else {
                $('#notifications-toggle').prop('checked', !isChecked);
                showToast('Error: ' + response.error, 'danger');
            }
        },
        error: function() {
            $('#notifications-toggle').prop('checked', !isChecked);
            showToast('Failed to connect to server', 'danger');
        }
    });
});

// Auto-detect toggle
$('#auto-detect-toggle').change(function() {
    const isChecked = $(this).is(':checked');
    
    $.ajax({
        url: '/web/api/auto-detect/toggle',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ enable: isChecked }),
        success: function(response) {
            if (response.success) {
                $('#auto-detect-status-text').text(isChecked ? 'ON' : 'OFF');
                showToast(response.message, 'success');
            } else {
                $('#auto-detect-toggle').prop('checked', !isChecked);
                showToast('Error: ' + response.error, 'danger');
            }
        },
        error: function() {
            $('#auto-detect-toggle').prop('checked', !isChecked);
            showToast('Failed to connect to server', 'danger');
        }
    });
});

// Update dashboard status
function updateDashboardStatus() {
    $.get('/web/api/status', function(response) {
        if (response.success) {
            const data = response.data;
            
            // Update toggles (without triggering change events)
            $('#camera-toggle').prop('checked', data.camera_on).off('change');
            $('#notifications-toggle').prop('checked', data.notifications_on).off('change');
            $('#auto-detect-toggle').prop('checked', data.auto_detect_on).off('change');
            
            // Re-bind change events
            $('#camera-toggle').change(function() { /* same as above */ });
            $('#notifications-toggle').change(function() { /* same as above */ });
            $('#auto-detect-toggle').change(function() { /* same as above */ });
            
            // Update status text
            $('#camera-status-text').text(data.camera_on ? 'ON' : 'OFF');
            $('#notifications-status-text').text(data.notifications_on ? 'ON' : 'OFF');
            $('#auto-detect-status-text').text(data.auto_detect_on ? 'ON' : 'OFF');
            
            // Update values
            $('#temperature').text(data.temperature + '°C');
            $('#pan-value').text(data.pan + '°');
            $('#tilt-value').text(data.tilt + '°');
        }
    });
}

// Refresh latest image
function refreshLatestImage() {
    const $img = $('#latest-image');
    const currentSrc = $img.attr('src').split('?')[0];
    $img.attr('src', currentSrc + '?t=' + new Date().getTime());
    showToast('Image refreshed', 'info');
}

// Capture photo (placeholder - would trigger camera capture)
function capturePhoto() {
    showToast('Capture feature coming soon!', 'info');
    // Future: trigger manual capture via API
}

// Update status every 10 seconds
setInterval(updateDashboardStatus, 10000);