/* ========================================================================== */
/*  FRONT API — Config & utilitaires                                          */
/*  - Aligne le front sur le backend Best-Of (FastAPI + JWT via cookies)      */
/*  - Gère les appels, erreurs, (ré-)auth & rafraîchissement access token     */
/* ========================================================================== */

/**
 * Configuration API :
 * - baseUrl : si backend sur un autre domaine (ex: https://api.mondomaine.com)
 * - headers : en-têtes “génériques” (le Bearer est ajouté dynamiquement)
 * - useCookies : true si le refresh token est en httpOnly cookie (recommandé)
 */
const API_CONFIG = {
  baseUrl: '',
  headers: { 'Content-Type': 'application/json' },
  useCookies: true
};

// État global minimal (éviter localStorage pour les tokens d'accès)
let historyChart;
let isLoggedIn = false;
let accessToken = null;

/**
 * Construit les headers avec Authorization Bearer si accessToken présent.
 * @param {Object} extra - En-têtes additionnels spécifiques à l'appel
 * @returns {Object} - En-têtes combinés
 */
function authHeaders(extra = {}) {
  const h = { ...API_CONFIG.headers, ...extra };
  if (accessToken) h['Authorization'] = `Bearer ${accessToken}`;
  return h;
}

/**
 * Appel API générique avec :
 * - gestion 401 → tentative de refresh → rejoue la requête une fois
 * - propagation des erreurs détaillées
 * @param {string} endpoint - Chemin (ex. '/sensors/realtime')
 * @param {RequestInit} options - Options fetch
 * @param {boolean} retry - Autorise un seul retry après refresh (true par défaut)
 */
async function apiCall(endpoint, options = {}, retry = true) {
  const url = `${API_CONFIG.baseUrl}${endpoint}`;
  const opts = { ...options, headers: authHeaders(options.headers || {}) };

  // Si refresh token en cookie httpOnly côté serveur, on inclut les cookies
  if (API_CONFIG.useCookies) opts.credentials = 'include';

  const res = await fetch(url, opts);

  // 401 → tente un refresh d'access token puis rejoue la requête (1 seule fois)
  if (res.status === 401 && retry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return apiCall(endpoint, options, false);
    logout();
    throw new Error('Session expirée. Merci de vous reconnecter.');
  }

  if (!res.ok) {
    // Essaye de renvoyer un message utile (texte ou JSON)
    let detail = '';
    try { detail = await res.text(); } catch {}
    throw new Error(`API ${res.status}: ${detail || res.statusText}`);
  }

  // No Content
  if (res.status === 204) return null;
  return res.json();
}

/** Petite aide UX centralisée (toast/alert personnalisable) */
function showError(message) {
  console.error('Error:', message);
  // Ici tu peux déclencher un toast visuel si tu as un composant
}

/* ========================================================================== */
/*  Capteurs — Données temps réel                                             */
/*  GET /sensors/realtime -> { sensor_data: [{sensor, temperature, humidity}]}*/
/* ========================================================================== */

/**
 * Charge les mesures “temps réel” et dessine les cartes donut.
 * - Remplace l'ancien endpoint /WeatherData
 */
async function fetchRealtimeSensors() {
  try {
    const response = await apiCall('/sensors/realtime');
    const sensorGrid = document.getElementById('sensorCards');
    if (!sensorGrid) return;

    sensorGrid.innerHTML = '';

    if (response?.sensor_data?.length) {
      response.sensor_data.forEach((sensor, idx) => {
        const cardHTML = `
          <div class="donut-card">
            <div class="donut-title">Capteur ${sensor.sensor}</div>
            <div class="chart-container"><canvas id="donut${idx}"></canvas></div>
            <div class="sensor-values">
              <span><i class="bi bi-thermometer-half"></i> ${sensor.temperature}°C</span><br>
              <span><i class="bi bi-droplet-half"></i> ${sensor.humidity}%</span>
            </div>
          </div>`;
        sensorGrid.insertAdjacentHTML('beforeend', cardHTML);
        // Attendre que le canvas soit rendu dans le DOM avant de dessiner
        setTimeout(() => drawDonut(`donut${idx}`, sensor.temperature, sensor.humidity), 0);
      });
    } else {
      sensorGrid.innerHTML = '<p>Aucune donnée de capteur disponible.</p>';
    }
  } catch (e) {
    const sensorGrid = document.getElementById('sensorCards');
    if (sensorGrid) sensorGrid.innerHTML = '<p>Erreur de connexion au serveur.</p>';
    showError(e.message);
  }
}

/**
 * Dessine un donut Chart.js “Température vs Humidité”.
 * @param {string} canvasId - ID du canvas
 * @param {number} temp - Température en °C
 * @param {number} hum - Humidité en %
 */
function drawDonut(canvasId, temp, hum) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
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
            label: (c) => {
              const unit = c.label === 'Température' ? '°C' : '%';
              return `${c.label}: ${c.parsed}${unit}`;
            }
          }
        }
      }
    }
  });
}

/* ========================================================================== */
/*  Historique — Graphique ligne                                              */
/*  GET /sensors/history?start=YYYY-MM-DD&end=YYYY-MM-DD                      */
/* ========================================================================== */

/**
 * Récupère la série historique et trace le graphique.
 * - Remplace l’ancien endpoint /alldata?date_int=...&date_end=...
 */
async function fetchHistoryData() {
  try {
    const startDate = document.getElementById('startDate')?.value;
    const endDate = document.getElementById('endDate')?.value;
    if (!startDate || !endDate) return;

    const response = await apiCall(`/sensors/history?start=${startDate}&end=${endDate}`);
    if (!Array.isArray(response) || response.length === 0) return;

    const labels = response.map(i => i.date);
    const tempData = response.map(i => i.temperature_moyenne);
    const humData = response.map(i => i.humidite_moyenne);

    // Détruire l’ancien graphique pour éviter les leaks
    if (historyChart) historyChart.destroy();

    const ctx = document.getElementById('historyChart');
    if (!ctx) return;

    historyChart = new Chart(ctx.getContext('2d'), {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Température (°C)', data: tempData, borderColor: '#f9d923', backgroundColor: 'rgba(249,217,35,0.1)', tension: 0.3, fill: false },
          { label: 'Humidité (%)', data: humData, borderColor: '#36a2eb', backgroundColor: 'rgba(54,162,235,0.1)', tension: 0.3, fill: false }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { usePointStyle: true, padding: 20 }},
          tooltip: { mode: 'index', intersect: false }
        },
        scales: {
          x: { title: { display: true, text: 'Date' } },
          y: { title: { display: true, text: 'Valeur' } }
        },
        interaction: { mode: 'nearest', axis: 'x', intersect: false }
      }
    });
  } catch (e) {
    showError('Erreur de chargement des données historiques');
    console.error(e);
  }
}

/** Télécharge le canvas Chart.js en PNG */
function downloadChart() {
  if (!historyChart) return showError('Aucun graphique disponible pour le téléchargement');
  const link = document.createElement('a');
  link.download = `historique_capteurs_${new Date().toISOString().split('T')[0]}.png`;
  link.href = historyChart.toBase64Image('image/png', 1.0);
  link.click();
}

/* ========================================================================== */
/*  Paramètres — Tableau “état courant”                                       */
/*  GET /parameters/current -> {temperature, humidity, start_date, ...}       */
/* ========================================================================== */

/**
 * Calcule les jours restants à partir d’une date ISO (start_date) et d’une
 * durée totale (timetoclose en jours).
 */
function remainingDays(fromISO, totalDays) {
  const start = new Date(fromISO).getTime();
  const now = Date.now();
  const elapsed = Math.floor((now - start) / (1000 * 60 * 60 * 24));
  return Math.max((Number(totalDays) || 0) - elapsed, 0);
}

/** Charge et affiche la ligne “paramètres actuels”. */
async function fetchCurrentParameters() {
  try {
    const data = await apiCall('/parameters/current');
    const tbody = document.querySelector('#paramTable tbody');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (data && typeof data === 'object') {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${data.temperature != null ? `${data.temperature}°C` : 'N/A'}</td>
        <td>${data.humidity != null ? `${data.humidity}%` : 'N/A'}</td>
        <td>${data.start_date ? new Date(data.start_date).toLocaleDateString() : 'N/A'}</td>
        <td>${data.stat_stepper ? 'Actif' : 'Inactif'}</td>
        <td>${data.number_stepper ?? 'N/A'}</td>
        <td>${data.espece ?? 'N/A'}</td>
        <td>${data.start_date && data.timetoclose ? `${remainingDays(data.start_date, data.timetoclose)} jours` : 'N/A'}</td>
      `;
      tbody.appendChild(tr);
    }
  } catch (e) {
    console.error(e);
  }
}

/* ========================================================================== */
/*  Auth — Login / Refresh / Logout                                           */
/*  POST /auth/login  -> { access_token, expires_in }                          */
/*  POST /auth/refresh (httpOnly cookie) -> { access_token }                   */
/* ========================================================================== */

/** Tente de rafraîchir l’access token (refresh côté cookie httpOnly). */
async function refreshAccessToken() {
  try {
    const res = await fetch(`${API_CONFIG.baseUrl}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: API_CONFIG.useCookies ? 'include' : 'same-origin'
    });
    if (!res.ok) return false;
    const data = await res.json();
    accessToken = data.access_token || null;
    return !!accessToken;
  } catch {
    return false;
  }
}

/** Déconnexion locale (reset état UI) */
function logout() {
  isLoggedIn = false;
  accessToken = null;
  updateUI(false);
  updateNavMenu();
}

/** Met à jour quelques éléments visuels selon l’état connexion. */
function updateUI(connected = false) {
  const userDropdown = document.getElementById('userDropdown');
  const loginBtn = document.getElementById('loginBtn');
  if (userDropdown && loginBtn) {
    userDropdown.style.display = connected ? 'block' : 'none';
    loginBtn.innerHTML = connected ? '<i class="bi bi-person-check"></i>' : '<i class="bi bi-person"></i>';
    loginBtn.title = connected ? 'Connecté' : 'Se connecter';
  }
}

/** Affiche/masque le lien “Paramètres” selon connexion. */
function updateNavMenu() {
  const paramLink = document.querySelector('nav .nav-links a[href="/parameter"]');
  if (paramLink) paramLink.style.display = isLoggedIn ? 'inline-block' : 'none';
}

/**
 * Branche toute la logique du formulaire de login + ouverture/fermeture modale.
 * En cas de succès :
 *  - accessToken en mémoire
 *  - UI mise à jour (icône, menu)
 */
function initializeAuth() {
  const loginBtn = document.getElementById('loginBtn');
  const loginModal = document.getElementById('loginModal');
  const closeLogin = document.getElementById('closeLogin');
  const loginForm = document.getElementById('loginForm');
  const logoutBtn = document.getElementById('logoutBtn');

  // Ouvre la modale
  loginBtn?.addEventListener('click', (e) => {
    e.preventDefault(); e.stopPropagation();
    loginModal?.classList.add('show');
    document.getElementById('loginUsername')?.focus();
  });

  // Ferme la modale
  closeLogin?.addEventListener('click', (e) => {
    e.preventDefault();
    loginModal?.classList.remove('show');
  });

  // Ferme en cliquant sur le fond
  loginModal?.addEventListener('click', (e) => {
    if (e.target === loginModal) loginModal.classList.remove('show');
  });

  // Empêche la propagation des clics dans la boîte
  loginModal?.querySelector('.modal')?.addEventListener('click', (e) => e.stopPropagation());

  // Soumission du formulaire de login
  loginForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('loginUsername')?.value?.trim();
    const password = document.getElementById('loginPassword')?.value?.trim();
    const rememberMe = document.getElementById('rememberMe')?.checked;
    const errorDiv = document.getElementById('loginError');

    errorDiv.textContent = '';
    if (!username || !password) {
      errorDiv.textContent = 'Veuillez remplir tous les champs';
      return;
    }

    try {
      const res = await fetch(`${API_CONFIG.baseUrl}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: API_CONFIG.useCookies ? 'include' : 'same-origin',
        body: JSON.stringify({ username, password, remember_me: !!rememberMe })
      });
      if (!res.ok) {
        const err = await res.json().catch(()=>({message:'Erreur de connexion'}));
        throw new Error(err.message || 'Erreur de connexion');
      }
      const data = await res.json().catch(()=>({}));
      accessToken = data?.access_token || null;
      isLoggedIn = true;
      loginModal?.classList.remove('show');
      updateUI(true);
      updateNavMenu();
    } catch (err) {
      errorDiv.textContent = err.message || 'Erreur réseau';
    }
  });

  // Déconnexion (simple côté front — côté back tu peux aussi exposer /auth/logout)
  logoutBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    logout();
  });

  // Ferme le dropdown si on clique ailleurs
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.user-menu')) {
      document.querySelector('.user-menu')?.classList.remove('open');
    }
  });
}

/* ========================================================================== */
/*  Initialisation globale                                                     */
/* ========================================================================== */

/** Initialise les dates (J-7 → J) pour le filtre historique. */
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

/** Point d’entrée : branche les listeners et charge les données. */
function initializeApp() {
  initializeDateFilters();
  initializeAuth();
  updateNavMenu();

  // Chargements initiaux
  fetchRealtimeSensors();
  fetchHistoryData();
  fetchCurrentParameters();

  // Boutons action
  document.getElementById('refreshData')?.addEventListener('click', fetchHistoryData);
  document.getElementById('downloadGraph')?.addEventListener('click', downloadChart);

  // Rafraîchit les mesures temps réel toutes les 30 secondes
  setInterval(fetchRealtimeSensors, 30000);
}

// Lance l’app une fois le DOM prêt
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  initializeApp();
}

// Filet de sécurité : promesses non gérées
window.addEventListener('unhandledrejection', (e) => {
  console.error('Unhandled promise rejection:', e.reason);
  showError('Une erreur inattendue s’est produite');
});
