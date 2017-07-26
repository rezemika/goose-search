// Set somes form fields with the current user position with Geolocation.

function getLocationConstant() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(onGeoSuccess, onGeoError, {timeout:10000});
    } else {
        alert("Il semblerait que votre navigateur ne supporte pas la géolocalisation.");
    }
}

// In cas of success.
function onGeoSuccess(event) {
    // Round to five decimals.
    var user_latitude = Math.round(event.coords.latitude * 100000) / 100000;
    var user_longitude = Math.round(event.coords.longitude * 100000) / 100000;
    
    document.getElementById("user_latitude").value = user_latitude;
    document.getElementById("user_longitude").value = user_longitude;
}

// In case of error.
function onGeoError(event) {
    if (event.code == event.PERMISSION_DENIED) {
        alert("Erreur : géolocalisation empêchée. Vérifiez que vous avez bien autorisés la géolocalisation.");
    }
    else {
        alert("Erreur " + event.code + ". " + event.message);
    }
}
