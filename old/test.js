// Variables globales
let accessToken = null;
let isLoggedIn = false;

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

// Gestion de l'authentification
function initializeAuth() {
    const loginBtn = document.getElementById('loginBtn');
    const loginModal = document.getElementById('loginModal');
    const closeLogin = document.getElementById('closeLogin');
    const loginForm = document.getElementById('loginForm');
    const logoutBtn = document.getElementById('logoutBtn');

    console.log('Initializing auth system...');

    if (!loginBtn || !loginModal) {
        console.error('Éléments de login manquants');
        return;
    }

    // Gestion de l'ouverture et de la fermeture du modal
    loginBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        loginModal.classList.add('show');
    });

    if (closeLogin) {
        closeLogin.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            loginModal.classList.remove('show');
        });
    }

    loginModal.addEventListener('click', function(e) {
        if (e.target === loginModal) {
            loginModal.classList.remove('show');
        }
    });

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
            
            if (errorDiv) { errorDiv.textContent = ''; }

            if (!username || !password) {
                if (errorDiv) { errorDiv.textContent = 'Veuillez remplir tous les champs'; }
                return;
            }

            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password, rememberMe })
                });

                if (response.ok) {
                    const data = await response.json();
                    console.log('Login successful', data);
                    
                    isLoggedIn = true;
                    accessToken = data.access_token;
                    
                    // Stocker le refresh token si "rememberMe" est coché
                    if (data.refresh_token) {
                        localStorage.setItem('refreshToken', data.refresh_token);
                    }
                    
                    loginModal.classList.remove('show');
                    updateUI(true);

                } else {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Erreur de connexion');
                }
                
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
            logout();
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
    
    // Mettre à jour l'état de connexion initial
    checkLoginStatus(); // <-- Nouvelle fonction pour vérifier le token de rafraîchissement
    
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

// Nouvelle fonction pour vérifier si un refresh token est déjà présent
async function checkLoginStatus() {
    const storedRefreshToken = localStorage.getItem('refreshToken');
    if (storedRefreshToken) {
        const newAccessToken = await refreshAccessToken();
        if (newAccessToken) {
            isLoggedIn = true;
            updateUI(true);
        } else {
            logout(); // Si le refresh token est invalide, déconnecter
        }
    } else {
        updateUI(false); // Pas de token, donc déconnecter
    }
}