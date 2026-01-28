# 📝 Changelog - Système d'Incubation

## [2.0.0] - 28 Janvier 2025

### ✨ Nouvelles Fonctionnalités

#### Authentification & Sécurité
- ✅ Système de login avec JWT tokens
- ✅ Mots de passe hachés avec bcrypt
- ✅ Protection des endpoints sensibles
- ✅ Endpoints `/api/auth/login` et `/api/auth/verify`

#### Paramètres Incubateur
- ✅ Formulaire complet pour 6 espèces (poule, canard, dinde, autre)
- ✅ Sélection dynamique avec conseils pour chaque espèce
- ✅ Température cible et actuelle
- ✅ Humidité cible et actuelle avec guides par stade
- ✅ Configuration du moteur et nombre de tourneurs
- ✅ Sélection de date/heure de cycle

#### Persistance en Base de Données
- ✅ Sauvegarde en PostgreSQL (table `parameter_data`)
- ✅ Historique des paramètres (colonne `updated_at`)
- ✅ Association utilisateur (colonne `user_id`)
- ✅ Endpoint `GET /api/parameter` pour récupérer la configuration
- ✅ Endpoint `POST /api/parameter` pour sauvegarder
- ✅ Endpoint `GET /api/parameters/history` pour l'historique

#### Mode Sombre
- ✅ Toggle mode clair/sombre en interface
- ✅ CSS variables pour thème adaptable
- ✅ Persistance en localStorage
- ✅ Application globale à toute l'application
- ✅ Transitions fluides entre thèmes

#### Frontend (React)
- ✅ Intégration Zustand pour state management (auth + theme)
- ✅ Formulaire Settings complet (6 sections)
- ✅ Messages d'erreur et de succès
- ✅ Loading states pendant les API calls
- ✅ Support localStorage pour persistence
- ✅ Design responsive mobile/desktop

### 🔧 Améliorations Techniques

- **Backend**:
  - Utilisation de Pydantic models pour validation
  - Contexte de session SQLAlchemy sécurisé
  - Gestion des erreurs améliorée
  - Support de JWT avec PyJWT

- **Frontend**:
  - Build production avec Vite optimisé
  - TypeScript strict mode
  - CSS variables pour thème global
  - Composants fonctionnels + hooks

- **Database**:
  - 5 nouvelles colonnes dans `parameter_data`: `temp_incubation`, `humidity_target`, `rotation_count`, `user_id`, `updated_at`
  - Índexes pour performance
  - Migration 0001: Schéma initial

### 🗑️ Supprimé

- ❌ Ancien système de stockage JSON (`parameters.json`)
- ❌ Import Jinja2 (non utilisé)
- ❌ Fichiers statiques legacy (HTML templates)
- ❌ Chart.js (remplacé par Recharts)

### 📚 Documentation

- ✅ [USER_GUIDE.md](USER_GUIDE.md) - Guide complet utilisateur
- ✅ [TEST_PLAN.md](TEST_PLAN.md) - Plan de test détaillé
- ✅ README.md mis à jour avec nouvelles features
- ✅ Inline comments dans le code

## [1.0.0] - Septembre 2024

### Initial Release
- Architecture frontend/backend séparée
- React 18 + TypeScript + Vite
- FastAPI + PostgreSQL
- Docker Compose setup
- Dashboard avec graphiques Recharts
- Système de capteurs basique

---

## Migration depuis v1.0 vers v2.0

### Pour les utilisateurs
1. Aucune action requise - la migration de données est automatique
2. Première connexion: utiliser credentials `admin` / `test123456`
3. Configurer les paramètres dans l'onglet "Paramètres"

### Pour les développeurs
1. `git pull` pour les derniers changements
2. `docker compose up -d` pour redémarrer les services
3. Lancer les tests avec le `TEST_PLAN.md`

### Base de données
```sql
-- Migration automatique effectuée:
ALTER TABLE parameter_data ADD COLUMN temp_incubation NUMERIC(5,2) DEFAULT 37.5;
ALTER TABLE parameter_data ADD COLUMN humidity_target NUMERIC(5,2) DEFAULT 60;
ALTER TABLE parameter_data ADD COLUMN rotation_count INTEGER DEFAULT 5;
ALTER TABLE parameter_data ADD COLUMN user_id INTEGER;
ALTER TABLE parameter_data ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();

-- Utilisateur admin créé:
INSERT INTO login (user_name, password, mail_id, status) VALUES 
('admin', '$2b$12$1o6AivzrWUHg2gLpMyQtqudLlfWow18z1P7UZV/JJUzSu9wAI94tm', 'admin@smartelia.local', true);
```

---

## Roadmap v2.1 (Prochaines Étapes)

- [ ] Plusieurs utilisateurs avec permissions
- [ ] Alertes email/SMS si anomalies
- [ ] Export PDF des rapports
- [ ] API mobile optimisée
- [ ] Cache Redis pour performance
- [ ] WebSocket pour real-time updates
- [ ] Support multi-langues (FR/EN)

---

**Dernière mise à jour**: 28 Janvier 2025
**Mainteneur**: Smartelia Project Team
