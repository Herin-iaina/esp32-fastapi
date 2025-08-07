// --- Gestion du menu utilisateur et du login ---
const userMenu = document.getElementById('userMenu');
const loginBtn = document.getElementById('loginBtn');
const userDropdown = document.getElementById('userDropdown');
const loginModal = document.getElementById('loginModal');
const closeLogin = document.getElementById('closeLogin');
const logoutBtn = document.getElementById('logoutBtn');
let isLoggedIn = false;

loginBtn.onclick = () => { loginModal.classList.add('active'); }
closeLogin.onclick = () => { loginModal.classList.remove('active'); }
window.onclick = (e) => {
    if (e.target === loginModal) loginModal.classList.remove('active');
}
userMenu.onclick = (e) => {
    if (isLoggedIn) userMenu.classList.toggle('open');
}
logoutBtn.onclick = () => {
    isLoggedIn = false;
    userMenu.classList.remove('open');
    loginBtn.innerHTML = '<i class="bi bi-person"></i>';
    userDropdown.style.display = 'none';
    // TODO: déconnexion côté serveur
}

// --- Login AJAX (exemple, à adapter avec ton endpoint) ---
document.getElementById('submitLogin').onclick = async function() {
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    const rememberMe = document.getElementById('rememberMe').checked;
    const errorDiv = document.getElementById('loginError');
    errorDiv.textContent = '';
    try {
        // Remplace l'URL par ton endpoint réel
        const resp = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password, rememberMe})
        });
        if (resp.ok) {
            isLoggedIn = true;
            loginModal.classList.remove('active');
            loginBtn.innerHTML = '<img src="/static/user.png" class="user-avatar" alt="user">';
            userDropdown.style.display = 'block';
        } else {
            const data = await resp.json();
            errorDiv.textContent = data.detail || "Erreur de connexion";
        }
    } catch (err) {
        errorDiv.textContent = "Erreur réseau";
    }
};

// --- Données capteurs temps réel ---
async function fetchRealtimeSensors() {
    // Remplace par ton endpoint réel
    // const resp = await fetch('/api/sensors/realtime');
    // const sensors = await resp.json();
    // Exemple statique :
    const sensors = [
        {name: "Capteur 1", temperature: 23.5, humidity: 55},
        {name: "Capteur 2", temperature: 21.2, humidity: 60},
        {name: "Capteur 3", temperature: 24.1, humidity: 52}
    ];
    const section = document.getElementById('realtimeSection');
    section.innerHTML = '';
    sensors.forEach((sensor, idx) => {
        section.innerHTML += `
        <div class="donut-card">
            <div class="donut-title">${sensor.name}</div>
            <div class="chart-container">
                <canvas id="donut${idx}"></canvas>
            </div>
            <div class="sensor-values">
                <span><i class="bi bi-thermometer-half"></i> ${sensor.temperature}°C</span><br>
                <span><i class="bi bi-droplet-half"></i> ${sensor.humidity}%</span>
            </div>
        </div>`;
        setTimeout(() => drawDonut(`donut${idx}`, sensor.temperature, sensor.humidity), 100);
    });
}
function drawDonut(canvasId, temp, hum) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Température', 'Humidité'],
            datasets: [{
                data: [temp, hum],
                backgroundColor: ['#f9d923', '#36a2eb'],
                borderWidth: 0
            }]
        },
        options: {
            cutout: '70%',
            plugins: { legend: { display: false } }
        }
    });
}

// --- Graphique historique ---
let historyChart;
async function fetchHistoryData() {
    // Remplace par ton endpoint réel et les filtres
    // const resp = await fetch('/api/sensors/history?...');
    // const data = await resp.json();
    // Exemple statique :
    const labels = ["2024-08-01", "2024-08-02", "2024-08-03", "2024-08-04"];
    const tempData = [22, 23, 21, 24];
    const humData = [55, 57, 54, 56];
    if (historyChart) historyChart.destroy();
    const ctx = document.getElementById('historyChart').getContext('2d');
    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Température (°C)',
                    data: tempData,
                    borderColor: '#f9d923',
                    backgroundColor: 'rgba(249,217,35,0.1)',
                    tension: 0.3
                },
                {
                    label: 'Humidité (%)',
                    data: humData,
                    borderColor: '#36a2eb',
                    backgroundColor: 'rgba(54,162,235,0.1)',
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' }
            }
        }
    });
}
document.getElementById('downloadGraph').onclick = function() {
    const link = document.createElement('a');
    link.download = 'historique_capteurs.png';
    link.href = historyChart.toBase64Image();
    link.click();
};

// --- Paramètres actuels ---
async function fetchParams() {
    // Remplace par ton endpoint réel
    // const resp = await fetch('/api/parameters/current');
    // const param = await resp.json();
    // Exemple statique :
    const param = {
        temperature: 23,
        humidity: 55,
        start_date: "2024-08-01",
        stat_stepper: "ON",
        number_stepper: 2,
        espece: "Champignon",
        timetoclose: 28
    };
    const tbody = document.getElementById('paramTable').querySelector('tbody');
    tbody.innerHTML = `
        <tr>
            <td>${param.temperature}°C</td>
            <td>${param.humidity}%</td>
            <td>${param.start_date}</td>
            <td>${param.stat_stepper}</td>
            <td>${param.number_stepper}</td>
            <td>${param.espece}</td>
            <td>${param.timetoclose} jours</td>
        </tr>
    `;
}

// --- Initialisation ---
window.onload = () => {
    fetchRealtimeSensors();
    fetchHistoryData();
    fetchParams();
    // TODO: charger la liste des capteurs dans #sensorSelect
};