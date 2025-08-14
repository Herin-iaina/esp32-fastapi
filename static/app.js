// Configuration
const API_CONFIG = {
    baseUrl: '', // URL de base de l'API
    headers: {
        'Content-Type': 'application/json',
        'X-API-KEY': 'votre_cle_api_1' // Remplacer par la vraie clé API
    }
};

// Variables globales
let historyChart;
let isLoggedIn = false;
let accessToken = null;

// Fonction utilitaire pour les appels API
async function apiCall(endpoint, options = {}) {
    try {
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
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Fonction d'affichage des erreurs
function showError(message) {
    console.error('Error:', message);
    // Vous pouvez ajouter ici une notification toast ou autre système d'alerte
}

// --- Données capteurs temps réel ---
async function fetchRealtimeSensors() {
    try {
        const response = await apiCall('/WeatherData');
        if (!response) {
            throw new Error('Aucune donnée disponible');
        }

        const sensorGrid = document.getElementById('sensorCards');
        if (!sensorGrid) {
            console.error('Element sensorCards not found');
            return;
        }
        
        sensorGrid.innerHTML = '';
        
        // Mise à jour des données en temps réel
        if (response.sensor_data && response.sensor_data.length > 0) {
            response.sensor_data.forEach((sensor, idx) => {
                const cardHTML = `
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
                sensorGrid.innerHTML += cardHTML;
                
                // Créer le graphique après un court délai pour s'assurer que l'élément est dans le DOM
                setTimeout(() => {
                    drawDonut(`donut${idx}`, sensor.temperature, sensor.humidity);
                }, 100);
            });
        } else {
            sensorGrid.innerHTML = '<p>Aucune donnée de capteur disponible.</p>';
        }
    } catch (error) {
        console.error('Erreur lors de la récupération des données:', error);
        const sensorGrid = document.getElementById('sensorCards');
        if (sensorGrid) {
            sensorGrid.innerHTML = '<p>Erreur de connexion au serveur. Tentative de reconnexion...</p>';
        }
        showError('Erreur de connexion au serveur');
    }
}

// Fonction pour créer les graphiques donut
function drawDonut(canvasId, temp, hum) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas ${canvasId} not found`);
        return;
    }
    
    const ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Température', 'Humidité'],
            datasets: [{
                data: [temp, hum],
                backgroundColor: ['#f9d923', '#36a2eb'],
                borderWidth: 0,
                cutout: '70%'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: { 
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label;
                            const value = context.parsed;
                            const unit = label === 'Température' ? '°C' : '%';
                            return `${label}: ${value}${unit}`;
                        }
                    }
                }
            }
        }
    });
}

// --- Graphique historique ---
async function fetchHistoryData() {
    try {
        const startDate = document.getElementById('startDate')?.value;
        const endDate = document.getElementById('endDate')?.value;
        
        if (!startDate || !endDate) {
            console.log('Dates non définies, utilisation des dates par défaut');
            return;
        }
        
        const response = await apiCall(`/alldata?date_int=${startDate}&date_end=${endDate}`);
        
        if (!response || !Array.isArray(response) || response.length === 0) {
            console.log('Aucune donnée historique disponible');
            return;
        }
        
        const labels = response.map(item => item.date);
        const tempData = response.map(item => item.temperature_moyenne);
        const humData = response.map(item => item.humidite_moyenne);

        // Détruire le graphique existant s'il existe
        if (historyChart) {
            historyChart.destroy();
        }
        
        const ctx = document.getElementById('historyChart');
        if (!ctx) {
            console.error('Canvas historyChart not found');
            return;
        }
        
        historyChart = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Température (°C)',
                        data: tempData,
                        borderColor: '#f9d923',
                        backgroundColor: 'rgba(249,217,35,0.1)',
                        tension: 0.3,
                        fill: false
                    },
                    {
                        label: 'Humidité (%)',
                        data: humData,
                        borderColor: '#36a2eb',
                        backgroundColor: 'rgba(54,162,235,0.1)',
                        tension: 0.3,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Valeur'
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    } catch (error) {
        console.error('Erreur lors de la récupération des données historiques:', error);
        showError('Erreur de chargement des données historiques');
    }
}

// Fonction de téléchargement du graphique
function downloadChart() {
    if (historyChart) {
        const link = document.createElement('a');
        link.download = `historique_capteurs_${new Date().toISOString().split('T')[0]}.png`;
        link.href = historyChart.toBase64Image('image/png', 1.0);
        link.click();
    } else {
        showError('Aucun graphique disponible pour le téléchargement');
    }
}

// Fonction pour charger les paramètres actuels
async function fetchCurrentParameters() {
        function joursRestants(data) {
        const startTime = new Date(data.start_date).getTime();
        const now = Date.now();
        // console.log('Start time:', startTime); // Heure de début en ms
        // console.log('Current time:', now); // Heure actuelle en ms

        const totalDuration = Number(data.timetoclose); // Durée totale en jours

        // Temps restant e jours
        const remainingDays = Math.floor((now - startTime) / (1000 * 60 * 60 * 24));
        let remaining = totalDuration - remainingDays;
      
        if (remaining < 0) remaining = 0;

        // Retourner uniquement le nombre de jours
        return remaining;
    }

    try {
        const response = await fetch('/api/parameter', {
            method: 'GET',
            headers: API_CONFIG.headers
        });

        console.log('Réponse brute de l\'API :', response);

        if (!response.ok) throw new Error(`Erreur API : ${response.status}`);

        const data = await response.json();
        console.log('Données des paramètres reçues :', data);

        const paramTable = document.querySelector('#paramTable tbody');
        if (!paramTable) {
            console.error('Élément #paramTable tbody non trouvé');
            return;
        }

        // Vider le tableau
        paramTable.innerHTML = '';
        console.log('Tableau vidé');

        if (data && typeof data === 'object') {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${data.temperature + '°C'?? 'N/A'}</td>
                <td>${data.humidity != null ? data.humidity + '%' : 'N/A'}</td>
                <td>${data.start_date ? new Date(data.start_date).toLocaleDateString() : 'N/A'}</td>
                <td>${data.stat_stepper ? 'Actif' : 'Inactif'}</td>
                <td>${data.number_stepper ?? 'N/A'}</td>
                <td>${data.espece ?? 'N/A'}</td>
                <td>${joursRestants(data) + ' jours'?? 'N/A'}</td>
            `;
            paramTable.appendChild(row);
        } else {
            console.warn('Données invalides, affichage d\'une ligne par défaut');
            const defaultRow = document.createElement('tr');
            defaultRow.innerHTML = `
                <td>110</td>
                <td>60%</td>
                <td>2024-01-15</td>
                <td>Actif</td>
                <td>3</td>
                <td>Tomates</td>
                <td>5 jours</td>
            `;
            paramTable.appendChild(defaultRow);
        }
    } catch (error) {
        console.error('Erreur lors du chargement des paramètres :', error);
    }
}



// Initialisation des dates par défaut
function initializeDateFilters() {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    
    if (startDateInput && endDateInput) {
        const today = new Date();
        const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
        
        startDateInput.value = weekAgo.toISOString().split('T')[0];
        endDateInput.value = today.toISOString().split('T')[0];
    }
}


// Fonction pour rafraîchir le token d'accès
async function refreshAccessToken() {
    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) {
        console.error('No refresh token found. Logging out.');
        logout();
        return null;
    }

    try {
        const response = await fetch('/refresh-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
        
        if (response.ok) {
            const data = await response.json();
            accessToken = data.access_token;
            console.log('Access token successfully refreshed!');
            return accessToken;
        } else {
            console.error('Failed to refresh token. Logging out.');
            logout();
            return null;
        }
    } catch (error) {
        console.error('Network error while refreshing token:', error);
        logout();
        return null;
    }
}

// Fonction pour mettre à jour l'affichage de l'interface utilisateur après la connexion/déconnexion
function updateUI(connected = false) {
    const userDropdown = document.getElementById('userDropdown');
    const loginBtn = document.getElementById('loginBtn');
    
    if (userDropdown && loginBtn) {
        if (connected) {
            userDropdown.style.display = 'block';
            loginBtn.innerHTML = '<i class="bi bi-person-check"></i>';
            loginBtn.title = 'Connecté';
        } else {
            userDropdown.style.display = 'none';
            loginBtn.innerHTML = '<i class="bi bi-person"></i>';
            loginBtn.title = 'Se connecter';
        }
    }
    // Appel de la fonction pour mettre à jour le menu de navigation
    if (typeof updateNavMenu === 'function') {
        updateNavMenu();
    }
}

// Fonction de déconnexion
function logout() {
    isLoggedIn = false;
    accessToken = null;
    localStorage.removeItem('refreshToken');
    updateUI(false);
    console.log('User logged out');
}

// Fonction pour mettre à jour l'affichage du menu de navigation
function updateNavMenu() {
    const paramLink = document.querySelector('nav .nav-links a[href="/parameter"]');
    if (paramLink) {
        if (isLoggedIn) {
            paramLink.style.display = 'inline-block'; // Ou 'block'
        } else {
            paramLink.style.display = 'none';
        }
    }
}

// Gestion de l'authentification
function initializeAuth() {
    const loginBtn = document.getElementById('loginBtn');
    const loginModal = document.getElementById('loginModal');
    const closeLogin = document.getElementById('closeLogin');
    const loginForm = document.getElementById('loginForm');
    const userDropdown = document.getElementById('userDropdown');
    const logoutBtn = document.getElementById('logoutBtn');

    console.log('Initializing auth system...');

    // Vérification des éléments
    if (!loginBtn || !loginModal) {
        console.error('Elements de login manquants');
        return;
    }

    // Gestion de l'ouverture du modal
    loginBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log('Login button clicked');
        loginModal.classList.add('show');
    });

    // Gestion de la fermeture du modal
    if (closeLogin) {
        closeLogin.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Close button clicked');
            loginModal.classList.remove('show');
        });
    }

    // Fermeture en cliquant en dehors du modal
    loginModal.addEventListener('click', function(e) {
        if (e.target === loginModal) {
            console.log('Clicked outside modal');
            loginModal.classList.remove('show');
        }
    });

    // Empêcher la propagation des clics à l'intérieur du modal
    const modalContent = loginModal.querySelector('.modal');
    if (modalContent) {
        modalContent.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    

    // Gestion du formulaire de connexion
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const username = document.getElementById('loginUsername')?.value;
            const password = document.getElementById('loginPassword')?.value;
            const rememberMe = document.getElementById('rememberMe')?.checked;
            const errorDiv = document.getElementById('loginError');
            
            if (errorDiv) {
                errorDiv.textContent = '';
            }

            if (!username || !password) {
                if (errorDiv) {
                    errorDiv.textContent = 'Veuillez remplir tous les champs';
                }
                return;
            }

            try {
                // Simulation d'une connexion réussie - remplacer par l'appel API réel
                console.log('Attempting login...', { username, rememberMe });
                
                // Appel API réel (décommentez et adaptez)
                
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username,
                        password,
                        rememberMe
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    // Traitement de la réponse
                    console.log('Login successful', data);

                    // Mettre à jour l'interface après une connexion réussie
                    isLoggedIn = true;
                    accessToken = data.access_token; // Stocker le token d'accès
                    // Stocker le refresh token si "rememberMe" est coché
                    if (data.refresh_token) {
                        localStorage.setItem('refreshToken', data.refresh_token);
                    }

                    loginModal.classList.remove('show');
                    updateUI(true);
                    
                    const userDropdown = document.getElementById('userDropdown');
                    if (userDropdown) {
                        userDropdown.style.display = 'block';
                    }
                    
                    const loginBtn = document.getElementById('loginBtn');
                    if (loginBtn) {
                        loginBtn.innerHTML = '<i class="bi bi-person-check"></i>';
                        loginBtn.title = 'Connecté';
                    }

                    // Mettre à jour le menu de navigation
                    if (typeof updateNavMenu === 'function') {
                        updateNavMenu();
                    }

                } else {
                    const errorData = await response.json();
                    throw new Error(errorData.message || 'Erreur de connexion');
                }
                

                // // Simulation pour test
                // if (username === 'admin' && password === 'admin') {
                //     console.log('Login successful');
                //     loginModal.classList.remove('show');
                //     isLoggedIn = true;
                    
                //     // Mettre à jour l'interface
                //     if (userDropdown) {
                //         userDropdown.style.display = 'block';
                //         updateNavMenu();
                //     }
                    
                //     loginBtn.innerHTML = '<i class="bi bi-person-check"></i>';
                //     loginBtn.title = 'Connecté';
                // } else {
                //     throw new Error('Nom d\'utilisateur ou mot de passe incorrect');
                // }
                
            } catch (error) {
                console.error('Erreur de connexion:', error);
                if (errorDiv) {
                    errorDiv.textContent = error.message || 'Erreur réseau';
                }
            }
        });
    }

    // Gestion de la déconnexion
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            isLoggedIn = false;
            logout();
            
            if (userDropdown) {
                userDropdown.style.display = 'none';
            }
            
            loginBtn.innerHTML = '<i class="bi bi-person"></i>';
            loginBtn.title = 'Se connecter';
            
            console.log('User logged out');
        });
    }

    // Fermeture du dropdown en cliquant ailleurs
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.user-menu')) {
            document.querySelector('.user-menu')?.classList.remove('open');
        }
    });
}

// Fonction d'initialisation principale
function initializeApp() {
    console.log('Initializing application...');
    
    // Initialiser les filtres de date
    initializeDateFilters();
    
    // Initialiser l'authentification
    initializeAuth();
    updateNavMenu();
    
    // Charger les données initiales
    fetchRealtimeSensors();
    fetchHistoryData();
    fetchCurrentParameters();
    
    // Configurer les écouteurs d'événements
    const refreshBtn = document.getElementById('refreshData');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', fetchHistoryData);
    }
    
    const downloadBtn = document.getElementById('downloadGraph');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadChart);
    }
    
    // Configurer les rafraîchissements automatiques
    setInterval(fetchRealtimeSensors, 30000); // Mise à jour toutes les 30 secondes
    
    console.log('Application initialized successfully');
}

// Attendre que le DOM soit chargé
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}

// Gestionnaire d'erreur global pour les promesses non gérées
window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    showError('Une erreur inattendue s\'est produite');
});


