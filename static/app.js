// Configuration
const API_CONFIG = {
    baseUrl: '', // URL de base de l'API
    headers: {
        'Content-Type': 'application/json',
        'X-API-KEY': 'votre_cle_api_1' // Remplacer par la vraie clé API
    }
};

// Fonction utilitaire pour les appels API
async function apiCall(endpoint, options = {}) {
    const response = await fetch(`${API_CONFIG.baseUrl}${endpoint}`, {
        ...options,
        headers: {
            ...API_CONFIG.headers,
            ...options.headers
        }
    });
    
    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    
    return response.json();
}

// Fonction de récupération des données en temps réel
async function fetchRealtimeData() {
    try {
        const data = await apiCall('/WeatherData');
        updateSensorCards(data);
    } catch (error) {
        console.error('Erreur lors de la récupération des données:', error);
        showError('Erreur de connexion au serveur');
    }
}

// Fonction de mise à jour du graphique historique
async function updateHistoryChart() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    try {
        const data = await apiCall(`/alldata?date_int=${startDate}&date_end=${endDate}`);
        renderHistoryChart(data);
    } catch (error) {
        console.error('Erreur lors de la récupération de l\'historique:', error);
        showError('Erreur de chargement de l\'historique');
    }
}

// Fonction de récupération des paramètres
async function fetchParameters() {
    try {
        const params = await apiCall('/parameter');
        updateParametersTable(params);
    } catch (error) {
        console.error('Erreur lors de la récupération des paramètres:', error);
        showError('Erreur de chargement des paramètres');
    }
}

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
    try {
        const response = await apiCall('/WeatherData');
        if (!response) {
            throw new Error('Aucune donnée disponible');
        }

        const section = document.getElementById('realtimeSection');
        section.innerHTML = '';
        
        // Mise à jour des données en temps réel
        if (response.sensor_data) {
            response.sensor_data.forEach((sensor, idx) => {
                section.innerHTML += `
                    <div class="donut-card">
                        <div class="donut-title">Capteur ${sensor.sensor}</div>
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
    } catch (error) {
        console.error('Erreur lors de la récupération des données:', error);
        showError('Erreur de connexion au serveur');
    }
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
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        const response = await apiCall(`/alldata?date_int=${startDate}&date_end=${endDate}`);
        
        const labels = response.map(item => item.date);
        const tempData = response.map(item => item.temperature_moyenne);
        const humData = response.map(item => item.humidite_moyenne);

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
    } catch (error) {
        console.error('Erreur lors de la récupération des données historiques:', error);
        showError('Erreur de chargement des données historiques');
    }
}
document.getElementById('downloadGraph').onclick = function() {
    const link = document.createElement('a');
    link.download = 'historique_capteurs.png';
    link.href = historyChart.toBase64Image();
    link.click();
};

// --- Paramètres actuels ---
async function fetchParams() {
    try {
        const param = await apiCall('/parameter');
        
        const tbody = document.getElementById('paramTable').querySelector('tbody');
        tbody.innerHTML = `
            <tr>
                <td>${param.temperature}°C</td>
                <td>${param.humidity}%</td>
                <td>${param.start_date}</td>
                <td>${param.stat_stepper ? 'ON' : 'OFF'}</td>
                <td>${param.number_stepper}</td>
                <td>${param.espece}</td>
                <td>${param.timetoclose} jours</td>
            </tr>
        `;
    } catch (error) {
        console.error('Erreur lors de la récupération des paramètres:', error);
        showError('Erreur de chargement des paramètres');
    }
}

// --- Initialisation ---
window.onload = () => {
    // Charger toutes les données initiales
    fetchRealtimeSensors();
    fetchHistoryData();
    fetchParams();
    
    // Configurer les rafraîchissements automatiques
    setInterval(fetchRealtimeSensors, 30000); // Mise à jour toutes les 30 secondes
    
    // Configurer les écouteurs d'événements
    document.getElementById('refreshData')?.addEventListener('click', fetchHistoryData);
    document.getElementById('downloadGraph')?.addEventListener('click', () => {
        if (historyChart) {
            const link = document.createElement('a');
            link.download = `historique_capteurs_${new Date().toISOString().split('T')[0]}.png`;
            link.href = historyChart.toBase64Image();
            link.click();
        }
    });
};


// Ajoute ce code dans app.js ou un JS global
document.getElementById('openParameterModal').addEventListener('click', async () => {
    if (!document.getElementById('parameterModal')) {
        const resp = await fetch('/parameter', { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        const html = await resp.text();
        document.body.insertAdjacentHTML('beforeend', html);
        // Charger le JS de la modale si besoin (si pas déjà chargé)
        if (typeof window.parameterModalInit === 'function') {
            window.parameterModalInit();
        }
    }
    document.getElementById('parameterModal').style.display = 'block';
});