
document.addEventListener('DOMContentLoaded', () => {
  const gm = id => document.getElementById(id);
  const mapDiv = gm('map');
  if (!mapDiv) return;            

  const showErr = msg => { gm('error-map_location').textContent = msg; };
  const hideErr = ()  => { gm('error-map_location').textContent = ''; };
  const submitBtn = gm('submit-btn');

  
  const map = L.map('map').setView([27.7,85.3],8);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution:'&copy; OpenStreetMap'
  }).addTo(map);
  map.whenReady(() => map.invalidateSize());

  let marker;
  function placeMarker(lat,lng) {
    if (marker) marker.setLatLng([lat,lng]);
    else {
      marker = L.marker([lat,lng],{draggable:true}).addTo(map);
      marker.on('dragend', e => {
        const p = e.target.getLatLng();
        setLoc(p.lat,p.lng);
      });
    }
    setLoc(lat,lng);
  }

  function setLoc(lat,lng) {
    gm('map_location').value = JSON.stringify({lat,lng});
    hideErr();
    validateMap();
  }

  map.on('click', e => placeMarker(e.latlng.lat,e.latlng.lng));

  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      pos => {
        placeMarker(pos.coords.latitude, pos.coords.longitude);
        map.setView([pos.coords.latitude, pos.coords.longitude],12);
      },
      () => showErr('Enable location in your browser settings.')
    );
  } else {
    showErr('Geolocation not supported.');
  }

  function validateMap() {
    const v = gm('map_location').value.trim();
    if (!v) {
      showErr('Location is required.');
      return false;
    }
    hideErr();
    return true;
  }

  gm('map_location').addEventListener('change', () => {
    if (!validateMap()) submitBtn.disabled = true;
  });
});
