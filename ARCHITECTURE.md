# 🏗️ Architecture Détaillée - Système d'Incubation v2.0

## 📐 Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER BROWSER                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  HTTP/HTTPS   http://localhost:8000                      │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │          REACT APPLICATION (v18)                  │  │  │
│  │  │  ┌──────────────────────────────────────────────┐ │  │  │
│  │  │  │ Dashboard        │ Settings (Incubation)     │ │  │  │
│  │  │  │ - Graphiques     │ - Login Form              │ │  │  │
│  │  │  │ - Temp/Humidité  │ - Parameters Config       │ │  │  │
│  │  │  │ - Capteurs       │ - Dark Mode Toggle        │ │  │  │
│  │  │  └──────────────────────────────────────────────┘ │  │  │
│  │  │         ↓                                            │  │  │
│  │  │  ┌──────────────────────────────────────────────┐ │  │  │
│  │  │  │  ZUSTAND STATE STORE                        │ │  │  │
│  │  │  │  - Auth (username, token, login/logout)     │ │  │  │
│  │  │  │  - Theme (isDarkMode, toggleDarkMode)       │ │  │  │
│  │  │  │  - localStorage persistence                 │ │  │  │
│  │  │  └──────────────────────────────────────────────┘ │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            ↓ REST API
┌─────────────────────────────────────────────────────────────────┐
│                 DOCKER COMPOSE (3 Services)                     │
│                                                                 │
│  ┌──────────────────────────┐  ┌─────────────────────────────┐ │
│  │  esp32-backend (FastAPI) │  │  esp32-frontend (Nginx)     │ │
│  │  Port: 8000              │  │  Port: 80                   │ │
│  │                          │  │                             │ │
│  │  ┌────────────────────┐  │  │  Serve:                     │ │
│  │  │  API Endpoints:    │  │  │  - index.html               │ │
│  │  │  /api/auth/login   │  │  │  - dist assets              │ │
│  │  │  /api/parameter    │  │  │  - Reverse proxy → :8000    │ │
│  │  │  /api/sensor/*     │  │  │                             │ │
│  │  │  /api/health       │  │  │                             │ │
│  │  └────────────────────┘  │  │                             │ │
│  │                          │  │                             │ │
│  │  ┌────────────────────┐  │  │                             │ │
│  │  │  Router/Handler:   │  │  │                             │ │
│  │  │  - auth.py         │  │  │                             │ │
│  │  │  - parameter.py    │  │  │                             │ │
│  │  │  - sensor_values.py│  │  │                             │ │
│  │  │  - system.py       │  │  │                             │ │
│  │  │  - pages.py        │  │  │                             │ │
│  │  └────────────────────┘  │  │                             │ │
│  │                          │  │                             │ │
│  │  ┌────────────────────┐  │  │                             │ │
│  │  │  Models:           │  │  │                             │ │
│  │  │  - LoginModel      │  │  │                             │ │
│  │  │  - SensorModel     │  │  │                             │ │
│  │  │  - ParameterModel  │  │  │                             │ │
│  │  │  (SQLAlchemy ORM)  │  │  │                             │ │
│  │  └────────────────────┘  │  │                             │ │
│  │                          │  │                             │ │
│  │  ┌────────────────────┐  │  │                             │ │
│  │  │  Security:         │  │  │                             │ │
│  │  │  - JWT tokens      │  │  │                             │ │
│  │  │  - Bcrypt hashing  │  │  │                             │ │
│  │  │  - CORS enabled    │  │  │                             │ │
│  │  └────────────────────┘  │  │                             │ │
│  └──────────────────────────┘  └─────────────────────────────┘ │
│                      ↓                                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  esp32-db (PostgreSQL 15)                                  ││
│  │  Port: 5432                                                ││
│  │                                                             ││
│  │  Database: smartelia_db                                    ││
│  │  ┌──────────────────────────────────────────────────────┐ ││
│  │  │ login                     │ parameter_data           │ ││
│  │  │ - id (PK)                 │ - id (PK)                │ ││
│  │  │ - user_name               │ - espece                 │ ││
│  │  │ - password (bcrypt hash)  │ - temp_incubation        │ ││
│  │  │ - mail_id                 │ - humidity_target        │ ││
│  │  │ - status (active/inactive)│ - rotation_count         │ ││
│  │  │                           │ - user_id (FK)           │ ││
│  │  │                           │ - created_at             │ ││
│  │  │                           │ - updated_at             │ ││
│  │  │                           │                          │ ││
│  │  │ data_temp                 │ stepper                  │ ││
│  │  │ - id (PK)                 │ - id (PK)                │ ││
│  │  │ - sensor_id (FK)          │ - motor_status           │ ││
│  │  │ - temperature             │ - step_count             │ ││
│  │  │ - humidity                │ - last_rotation          │ ││
│  │  │ - timestamp               │ - updated_at             │ ││
│  │  └──────────────────────────────────────────────────────┘ ││
│  │                                                             ││
│  │  Volumes:                                                  ││
│  │  - /var/lib/postgresql/data (persistence)                ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Flux d'Authentification

```
1. USER
   └─→ Enter credentials (admin / test123456)
       └─→ Submit login form

2. FRONTEND (React)
   └─→ POST /api/auth/login
       └─→ { username: "admin", password: "test123456" }

3. BACKEND (FastAPI)
   └─→ Route: POST /api/auth/login
       ├─→ Query: SELECT * FROM login WHERE user_name='admin'
       ├─→ Verify: bcrypt.checkpw(input_pwd, db_hash)
       └─→ If valid:
           ├─→ Create JWT token
           ├─→ Payload: { sub: username, user_id, exp: +7 days }
           └─→ Return: { access_token, token_type, username, user_id }

4. FRONTEND (React)
   └─→ Receive token
       ├─→ Store: localStorage.setItem('auth_token', token)
       ├─→ Update: useAppStore.login(username)
       ├─→ Redirect: Settings page
       └─→ Display: "Connecté en tant que admin"

5. AUTHORIZATION (Subsequent Requests)
   └─→ For POST /api/parameter:
       ├─→ Header: Authorization: Bearer <token>
       ├─→ BACKEND: jwt.decode(token, SECRET_KEY)
       └─→ If valid:
           ├─→ Extract user_id from token
           ├─→ Save with: INSERT INTO parameter_data (user_id, ...)
           └─→ Return: 200 OK

6. LOGOUT
   └─→ Click "Se Déconnecter"
       ├─→ localStorage.removeItem('auth_token')
       ├─→ useAppStore.logout()
       └─→ Redirect: Login form
```

## 📊 Flux de Sauvegarde de Paramètres

```
1. USER
   └─→ Configure settings (espece, temp, humidity, etc.)
       └─→ Click "Sauvegarder"

2. FRONTEND (React)
   └─→ Validate form data
       ├─→ Check: isAuthenticated === true
       ├─→ Get: token from localStorage
       └─→ POST /api/parameter
           ├─→ Header: Authorization: Bearer <token>
           └─→ Body: { espece, temp_incubation, humidity_target, ... }

3. BACKEND (FastAPI)
   └─→ Route: POST /api/parameter
       ├─→ Middleware: Validate JWT token
       ├─→ Extract: user_id from token
       ├─→ Validate: Pydantic model (ParameterModel)
       └─→ Database:
           ├─→ INSERT INTO parameter_data
           │   (espece, temp_incubation, humidity_target, rotation_count,
           │    user_id, created_at, updated_at)
           │   VALUES (...)
           └─→ ON CONFLICT: UPDATE updated_at

4. DATABASE (PostgreSQL)
   └─→ New record inserted
       ├─→ Timestamp: 2025-01-28 15:04:32
       ├─→ user_id: 1 (admin)
       └─→ Saved: All 10 parameters

5. FRONTEND (Response)
   └─→ Receive: 200 OK
       ├─→ Display: Success message "✓ Paramètres sauvegardés!"
       ├─→ Auto-hide: After 3 seconds
       └─→ Ready: For next modifications
```

## 🎨 Flux du Mode Sombre

```
1. FIRST VISIT
   └─→ App mounts (App.tsx)
       ├─→ Check: localStorage.getItem('darkMode')
       ├─→ If: not set
       │   └─→ Default: isDarkMode = false (light mode)
       └─→ useEffect: Apply theme
           ├─→ document.documentElement.classList.remove('dark')
           └─→ CSS: Use light theme variables

2. TOGGLE DARK MODE
   └─→ Click: Moon/Sun icon
       ├─→ Function: toggleDarkMode()
       └─→ Zustand State:
           ├─→ Update: isDarkMode = !isDarkMode
           ├─→ Save: localStorage.setItem('darkMode', String(isDarkMode))
           ├─→ DOM: document.documentElement.classList.add('dark')
           └─→ Trigger: Re-render

3. CSS VARIABLES APPLICATION
   └─→ :root (Light Mode)
       ├─→ --bg-primary: #ffffff
       ├─→ --text-primary: #1f2937
       └─→ --border-color: #e5e7eb

       :root.dark (Dark Mode)
       ├─→ --bg-primary: #1f2937
       ├─→ --text-primary: #f3f4f6
       └─→ --border-color: #374151

4. COMPONENT STYLES
   └─→ All components use CSS variables
       ├─→ background: var(--bg-primary)
       ├─→ color: var(--text-primary)
       └─→ transition: all 0.3s ease
           └─→ Smooth theme switching

5. PERSISTENCE
   └─→ Next visit
       ├─→ localStorage: darkMode = 'true'
       └─→ Theme: Restored automatically
```

## 🔐 Sécurité - Couches de Protection

```
1. FRONTEND
   ├─→ HTTPS only (in production)
   ├─→ Secure localStorage for tokens
   │   ├─→ No sensitive data in localStorage
   │   ├─→ Auto-clear on logout
   │   └─→ HttpOnly cookies (recommended upgrade)
   └─→ Input validation (Pydantic)

2. NETWORK (CORS)
   ├─→ Allow: ["http://localhost:5173", "http://localhost:8000"]
   ├─→ Credentials: true
   └─→ Production: Update to actual domains

3. API LAYER (FastAPI)
   ├─→ JWT token validation
   │   ├─→ Signature verification
   │   ├─→ Expiration check (7 days)
   │   └─→ Payload integrity
   ├─→ CORS middleware
   └─→ Request validation (Pydantic)

4. DATABASE
   ├─→ Password hashing
   │   ├─→ Algorithm: bcrypt
   │   ├─→ Salt: auto-generated
   │   └─→ Rounds: 12 (default)
   ├─→ SQL injection prevention
   │   └─→ SQLAlchemy ORM (parameterized queries)
   └─→ Access control
       ├─→ user_id field for multi-user isolation
       └─→ Future: Role-based access control (RBAC)
```

## 📈 Scalabilité & Performance

### Optimisations Actuelles
```
1. Frontend
   ├─→ Vite: Ultra-fast build
   ├─→ Code splitting: Lazy loading
   ├─→ CSS variables: No runtime calculation
   └─→ React memo: Prevent unnecessary re-renders

2. Backend
   ├─→ FastAPI: Async I/O
   ├─→ SQLAlchemy: Connection pooling
   ├─→ JWT: Stateless auth (no DB query per request)
   └─→ Caching: Ready for Redis integration

3. Database
   ├─→ Indexes: On frequently queried columns
   ├─→ Connection pooling: 20 connections default
   └─→ Query optimization: Eager loading where needed
```

### Prochaines Améliorations
```
1. Caching Layer
   ├─→ Redis: Cache parameter_data (1-hour TTL)
   └─→ Browser cache: Static assets (max-age: 1 year)

2. Database
   ├─→ Read replicas: For scaling reads
   ├─→ Partitioning: By user_id or date
   └─→ Archive old data: Keep DB lean

3. Frontend
   ├─→ Service workers: Offline support
   ├─→ WebSockets: Real-time updates
   └─→ Code splitting: Better performance
```

## 🧪 Testing Architecture

```
UNIT TESTS
├─→ Frontend: Jest + React Testing Library
│   ├─→ Components
│   ├─→ Hooks (useAppStore)
│   └─→ Utils
└─→ Backend: pytest
    ├─→ Models
    ├─→ Routes
    └─→ Services

INTEGRATION TESTS
├─→ API endpoints (with real DB)
├─→ Auth flow
└─→ Database operations

E2E TESTS
├─→ Selenium: Full user journey
├─→ Login → Configure → Save → Logout
└─→ Dark mode toggle
```

## 📝 Logging & Monitoring

```
LOGS COLLECTION
├─→ Backend: Python logging
│   ├─→ File: /app/logs/app.log
│   ├─→ Level: INFO (configurable)
│   └─→ Format: [timestamp] [level] [module] message
├─→ Database: PostgreSQL logs
│   └─→ docker logs esp32-db
└─→ Frontend: Browser console
    └─→ Dev tools → Console

MONITORING METRICS
├─→ API response time
├─→ Database query time
├─→ Error rate
├─→ User authentication attempts
└─→ Resource usage (CPU, RAM, Disk)
```

---

**Dernière mise à jour**: 28 Janvier 2025
**Version**: 2.0.0
