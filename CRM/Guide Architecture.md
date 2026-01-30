# Guide d'Architecture - Système de Gestion Incubateur ESP32
## Vue d'ensemble complète du système

---

## 📋 Table des Matières

1. [Vision Globale](#vision-globale)
2. [Choix d'Architecture](#choix-darchitecture)
3. [Structure de la Base de Données](#structure-de-la-base-de-données)
4. [API Backend (FastAPI)](#api-backend-fastapi)
5. [Frontend (Next.js)](#frontend-nextjs)
6. [Flux de Données](#flux-de-données)
7. [Guide d'Implémentation](#guide-dimplémentation)

---

## 🎯 Vision Globale

### Objectif du Système
Créer une plateforme intégrée qui combine :
- **IoT** : Monitoring temps réel des incubateurs ESP32
- **CRM** : Gestion des relations clients et fournisseurs
- **Analytics** : Suivi de performance et rentabilité

### Modules Principaux

```
┌─────────────────────────────────────────────────┐
│          DASHBOARD CENTRAL                      │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐  ┌──────────────┐            │
│  │   Module     │  │   Module     │            │
│  │ Incubateurs  │  │  Commercial  │            │
│  │    (IoT)     │  │    (CRM)     │            │
│  └──────────────┘  └──────────────┘            │
│                                                 │
│  ┌──────────────┐  ┌──────────────┐            │
│  │   Module     │  │   Module     │            │
│  │  Analytics   │  │   Rapports   │            │
│  └──────────────┘  └──────────────┘            │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 🏗️ Choix d'Architecture

### Décision : Table CONTACTS Unifiée ✅

**Structure retenue** : Approche hybride avec une table `contacts` centrale

#### Pourquoi cette approche ?

**Avantages :**
1. ✅ Évite la duplication des données (nom, email, téléphone, adresse)
2. ✅ Un contact peut être client ET fournisseur simultanément
3. ✅ Facilite les mises à jour (changement d'adresse, etc.)
4. ✅ Permet de suivre l'évolution (fournisseur devient client)

**Comment ça fonctionne :**
```sql
contacts (table centrale)
    ↓
    ├── customers (informations commerciales clients)
    └── suppliers (informations commerciales fournisseurs)
```

**Exemple concret :**
```
Contact: "Ferme Razafy"
├─ Informations de base (contacts) : nom, email, téléphone, adresse
├─ En tant que CLIENT (customers) : crédit, remise, historique achats
└─ En tant que FOURNISSEUR (suppliers) : délai livraison, évaluation qualité
```

---

## 🗄️ Structure de la Base de Données

### Schéma Relationnel

```
CONTACTS (table centrale)
    │
    ├─→ CUSTOMERS (1:1)
    │       └─→ CUSTOMER_ORDERS (1:N)
    │               └─→ CUSTOMER_ORDER_ITEMS (1:N)
    │                       └─→ PRODUCTS
    │
    └─→ SUPPLIERS (1:1)
            └─→ PURCHASE_ORDERS (1:N)
                    ├─→ PURCHASE_ORDER_ITEMS (1:N)
                    │       └─→ PRODUCTS
                    └─→ BATCHES (1:N)
                            └─→ INCUBATORS
```

### Tables Principales

#### 1. Module Contacts/CRM

| Table | Description | Champs Clés |
|-------|-------------|-------------|
| `contacts` | Données de base de tous les contacts | id, code, type, name, email, phone, address |
| `customers` | Infos commerciales clients | payment_terms, credit_limit, total_revenue |
| `suppliers` | Infos commerciales fournisseurs | delivery_time, reliability_rating, quality_rating |

#### 2. Module Commercial

| Table | Description | Champs Clés |
|-------|-------------|-------------|
| `customer_orders` | Commandes clients | order_number, status, total_amount, paid_amount |
| `customer_order_items` | Lignes de commande | quantity, unit_price, line_total, batch_id |
| `purchase_orders` | Commandes fournisseurs | po_number, status, expected_delivery_date |
| `purchase_order_items` | Lignes d'achat | quantity, quantity_received, quality_rating |

#### 3. Module Incubateurs (IoT)

| Table | Description | Champs Clés |
|-------|-------------|-------------|
| `incubators` | Équipements ESP32 | device_id, capacity, status, is_online |
| `incubator_current_state` | État temps réel | temperature, humidity, has_alert |
| `incubator_telemetry` | Historique données | temperature, humidity, timestamp |
| `batches` | Lots d'incubation | batch_number, egg_quantity, hatched_count, hatch_rate |

#### 4. Module Analytics

| Table | Description | Champs Clés |
|-------|-------------|-------------|
| `daily_metrics` | KPIs quotidiens | active_batches, daily_revenue, average_hatch_rate |
| `products` | Catalogue produits | code, category, purchase_price, selling_price |

### Index Critiques pour Performance

```sql
-- Recherche rapide de contacts
CREATE INDEX idx_contacts_name ON contacts(name);
CREATE INDEX idx_contacts_type ON contacts(type);

-- Performance des requêtes temporelles
CREATE INDEX idx_telemetry_incubator_time ON incubator_telemetry(incubator_id, timestamp DESC);
CREATE INDEX idx_batches_dates ON batches(start_date, end_date);

-- Analyses commerciales
CREATE INDEX idx_customer_orders_date ON customer_orders(order_date);
CREATE INDEX idx_purchase_orders_date ON purchase_orders(order_date);
```

---

## 🔌 API Backend (FastAPI)

### Structure du Projet

```
backend/
├── app/
│   ├── main.py                 # Point d'entrée FastAPI
│   ├── config.py               # Configuration (DB, secrets)
│   ├── database.py             # Connexion SQLAlchemy
│   │
│   ├── models/                 # Modèles SQLAlchemy
│   │   ├── contacts.py
│   │   ├── orders.py
│   │   ├── incubators.py
│   │   └── batches.py
│   │
│   ├── schemas/                # Pydantic schemas (validation)
│   │   ├── contacts.py
│   │   ├── orders.py
│   │   └── incubators.py
│   │
│   ├── routers/                # Endpoints API
│   │   ├── iot/
│   │   │   ├── incubators.py   # GET/POST données ESP32
│   │   │   └── telemetry.py    # WebSocket temps réel
│   │   │
│   │   ├── crm/
│   │   │   ├── contacts.py     # CRUD contacts
│   │   │   ├── customers.py    # Gestion clients
│   │   │   └── suppliers.py    # Gestion fournisseurs
│   │   │
│   │   ├── commercial/
│   │   │   ├── orders.py       # Commandes clients
│   │   │   └── purchases.py    # Commandes fournisseurs
│   │   │
│   │   └── analytics/
│   │       ├── dashboard.py    # KPIs et stats
│   │       └── reports.py      # Génération rapports
│   │
│   └── services/               # Logique métier
│       ├── batch_service.py    # Calculs rendement
│       ├── metrics_service.py  # Calculs KPIs
│       └── notification_service.py # Alertes
│
├── alembic/                    # Migrations DB
└── tests/
```

### Exemples d'Endpoints

#### Module IoT
```python
# Données temps réel ESP32
POST /api/iot/telemetry
WebSocket /api/iot/stream/{incubator_id}

# Gestion incubateurs
GET /api/iot/incubators
POST /api/iot/incubators/{id}/state
GET /api/iot/incubators/{id}/history?start_date=...&end_date=...
```

#### Module CRM
```python
# Contacts
GET /api/crm/contacts?type=customer&search=ferme
POST /api/crm/contacts
PUT /api/crm/contacts/{id}
DELETE /api/crm/contacts/{id}

# Clients
GET /api/crm/customers
GET /api/crm/customers/{id}/orders
GET /api/crm/customers/top?limit=10

# Fournisseurs
GET /api/crm/suppliers
GET /api/crm/suppliers/{id}/performance
GET /api/crm/suppliers/preferred
```

#### Module Commercial
```python
# Commandes clients
GET /api/commercial/orders?status=pending
POST /api/commercial/orders
PUT /api/commercial/orders/{id}/status
GET /api/commercial/orders/{id}/invoice

# Achats fournisseurs
POST /api/commercial/purchases
GET /api/commercial/purchases/{id}
PUT /api/commercial/purchases/{id}/receive  # Marquer comme reçu
```

#### Module Analytics
```python
# Dashboard
GET /api/analytics/dashboard/overview
GET /api/analytics/dashboard/incubators
GET /api/analytics/dashboard/commercial

# Rapports
GET /api/analytics/reports/monthly?year=2024&month=1
GET /api/analytics/reports/supplier-performance
GET /api/analytics/reports/batch-analysis
```

### Authentification JWT

```python
# app/routers/auth.py
@router.post("/login")
async def login(credentials: LoginSchema):
    # Vérifier utilisateur
    # Générer token JWT
    return {"access_token": token, "token_type": "bearer"}

# Middleware de protection
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    # Vérifier token JWT
    # Retourner utilisateur
    pass
```

---

## 💻 Frontend (Next.js)

### Structure du Projet

```
frontend/
├── app/
│   ├── layout.tsx              # Layout principal
│   ├── page.tsx                # Page d'accueil (dashboard)
│   │
│   ├── incubators/
│   │   ├── page.tsx            # Liste incubateurs
│   │   └── [id]/
│   │       └── page.tsx        # Détail incubateur
│   │
│   ├── customers/
│   │   ├── page.tsx            # Liste clients
│   │   ├── new/page.tsx        # Nouveau client
│   │   └── [id]/
│   │       ├── page.tsx        # Profil client
│   │       └── orders/page.tsx # Commandes client
│   │
│   ├── suppliers/
│   │   └── ...                 # Structure similaire
│   │
│   ├── orders/
│   │   ├── page.tsx            # Liste commandes
│   │   └── [id]/page.tsx       # Détail commande
│   │
│   └── analytics/
│       └── page.tsx            # Tableaux de bord
│
├── components/
│   ├── ui/                     # Composants réutilisables
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Table.tsx
│   │   └── Chart.tsx
│   │
│   ├── dashboard/
│   │   ├── StatCard.tsx
│   │   ├── RevenueChart.tsx
│   │   └── IncubatorStatus.tsx
│   │
│   ├── forms/
│   │   ├── ContactForm.tsx
│   │   ├── OrderForm.tsx
│   │   └── BatchForm.tsx
│   │
│   └── layout/
│       ├── Sidebar.tsx
│       ├── Header.tsx
│       └── Breadcrumb.tsx
│
├── lib/
│   ├── api.ts                  # Client API (axios/fetch)
│   ├── websocket.ts            # WebSocket client
│   ├── utils.ts                # Fonctions utilitaires
│   └── constants.ts            # Constantes
│
├── hooks/
│   ├── useIncubators.ts        # Hook données incubateurs
│   ├── useCustomers.ts         # Hook données clients
│   └── useWebSocket.ts         # Hook WebSocket temps réel
│
└── types/
    ├── contacts.ts
    ├── orders.ts
    └── incubators.ts
```

### Composants Clés

#### 1. Dashboard Principal
```typescript
// app/page.tsx
import StatCard from '@/components/dashboard/StatCard'
import RevenueChart from '@/components/dashboard/RevenueChart'
import IncubatorStatus from '@/components/dashboard/IncubatorStatus'

export default function DashboardPage() {
  const { data: stats } = useStats()
  
  return (
    <div className="grid gap-6">
      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="Incubateurs actifs" value={stats.activeIncubators} />
        <StatCard title="Taux de réussite" value={`${stats.hatchRate}%`} />
        <StatCard title="Revenus du jour" value={stats.dailyRevenue} />
        <StatCard title="Commandes en attente" value={stats.pendingOrders} />
      </div>
      
      {/* Graphiques */}
      <div className="grid grid-cols-2 gap-4">
        <RevenueChart />
        <IncubatorStatus />
      </div>
    </div>
  )
}
```

#### 2. Formulaire Contact (Client/Fournisseur)
```typescript
// components/forms/ContactForm.tsx
interface ContactFormProps {
  mode: 'create' | 'edit'
  type: 'customer' | 'supplier' | 'both'
  initialData?: Contact
}

export function ContactForm({ mode, type, initialData }: ContactFormProps) {
  const [contactData, setContactData] = useState(initialData)
  
  return (
    <form onSubmit={handleSubmit}>
      {/* Informations de base */}
      <section>
        <h3>Informations de base</h3>
        <Input name="name" label="Nom" required />
        <Input name="email" label="Email" type="email" />
        <Input name="phone" label="Téléphone" />
        <Textarea name="address" label="Adresse" />
      </section>
      
      {/* Informations spécifiques CLIENT */}
      {(type === 'customer' || type === 'both') && (
        <section>
          <h3>Informations client</h3>
          <Input name="paymentTerms" label="Délai paiement (jours)" type="number" />
          <Input name="creditLimit" label="Limite crédit" type="number" />
          <Select name="category" label="Catégorie">
            <option>Détaillant</option>
            <option>Grossiste</option>
          </Select>
        </section>
      )}
      
      {/* Informations spécifiques FOURNISSEUR */}
      {(type === 'supplier' || type === 'both') && (
        <section>
          <h3>Informations fournisseur</h3>
          <Input name="deliveryTime" label="Délai livraison (jours)" type="number" />
          <Select name="supplierCategory" label="Type">
            <option>Œufs</option>
            <option>Aliments</option>
            <option>Équipement</option>
          </Select>
        </section>
      )}
      
      <Button type="submit">Enregistrer</Button>
    </form>
  )
}
```

#### 3. WebSocket Temps Réel
```typescript
// hooks/useWebSocket.ts
export function useIncubatorWebSocket(incubatorId: number) {
  const [data, setData] = useState<TelemetryData | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/api/iot/stream/${incubatorId}`)
    
    ws.onopen = () => setIsConnected(true)
    ws.onmessage = (event) => {
      const telemetry = JSON.parse(event.data)
      setData(telemetry)
    }
    ws.onclose = () => setIsConnected(false)
    
    return () => ws.close()
  }, [incubatorId])
  
  return { data, isConnected }
}
```

---

## 🔄 Flux de Données

### 1. Cycle de Vie d'une Commande Client

```
┌─────────────────┐
│ Client passe    │
│ commande        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ CREATE          │────▶│ Vérifier stock  │
│ customer_order  │     │ disponible      │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Assigner à un   │────▶│ UPDATE batch    │
│ lot existant    │     │ (réservé)       │
│ OU créer lot    │     └─────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Production      │
│ (incubation)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Éclosion        │────▶│ UPDATE order    │
│ réussie         │     │ status='ready'  │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Livraison       │────▶│ UPDATE order    │
│                 │     │ status='delivered'│
└─────────────────┘     └─────────────────┘
```

### 2. Flux IoT (ESP32 → Dashboard)

```
┌─────────────┐
│   ESP32     │
│ (Incubateur)│
└──────┬──────┘
       │ HTTP POST /api/iot/telemetry
       │ { temp: 37.5, humidity: 65 }
       ▼
┌─────────────┐
│  FastAPI    │
│  Backend    │
└──────┬──────┘
       │
       ├─→ INSERT incubator_telemetry (historique)
       │
       ├─→ UPDATE incubator_current_state (état actuel)
       │
       └─→ WebSocket broadcast (temps réel)
              │
              ▼
       ┌─────────────┐
       │  Next.js    │
       │  Dashboard  │
       └─────────────┘
```

### 3. Calcul Automatique des Métriques

```
TRIGGER sur batches (UPDATE)
  │
  ├─→ Calculer hatch_rate = (hatched_count / egg_quantity) * 100
  │
  ├─→ Calculer cost_per_chick = total_cost / hatched_count
  │
  └─→ UPDATE suppliers.reliability_rating (évaluation fournisseur)

CRON Quotidien (00:00)
  │
  └─→ INSERT daily_metrics
        ├─→ Compter active_batches
        ├─→ Sommer daily_revenue
        ├─→ Calculer average_hatch_rate
        └─→ Compter chicks_produced
```

---

## 🚀 Guide d'Implémentation

### Phase 1 : Infrastructure de Base (Semaine 1-2)

1. **Setup Base de Données**
```bash
# Créer la base PostgreSQL
createdb incubator_management

# Exécuter le script SQL
psql -d incubator_management -f database_schema.sql
```

2. **Setup Backend FastAPI**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic python-jose

# Structure de base
mkdir -p app/{models,schemas,routers,services}
```

3. **Setup Frontend Next.js**
```bash
npx create-next-app@latest frontend --typescript --tailwind --app
cd frontend
npm install axios recharts lucide-react
```

### Phase 2 : Module IoT (Semaine 3-4)

1. **Backend IoT**
   - Créer endpoints pour ESP32
   - Implémenter WebSocket pour temps réel
   - Système d'alertes (température hors plage)

2. **Frontend Monitoring**
   - Dashboard temps réel
   - Graphiques température/humidité
   - Liste des incubateurs avec statut

### Phase 3 : Module CRM (Semaine 5-6)

1. **Backend CRM**
   - CRUD contacts (unifiés)
   - CRUD clients avec infos commerciales
   - CRUD fournisseurs avec évaluations

2. **Frontend CRM**
   - Formulaire contact intelligent (client/fournisseur/les deux)
   - Liste contacts avec filtres
   - Profils détaillés

### Phase 4 : Module Commercial (Semaine 7-8)

1. **Backend Commercial**
   - Gestion commandes clients
   - Gestion achats fournisseurs
   - Système de facturation

2. **Frontend Commercial**
   - Formulaire de commande
   - Suivi des commandes
   - Génération de factures PDF

### Phase 5 : Analytics & Reporting (Semaine 9-10)

1. **Backend Analytics**
   - Calcul KPIs quotidiens
   - Génération rapports
   - Vues matérialisées pour performance

2. **Frontend Analytics**
   - Dashboard multi-vues
   - Graphiques de tendances
   - Export Excel/PDF

### Phase 6 : Optimisation & Tests (Semaine 11-12)

1. **Performance**
   - Mise en cache (Redis)
   - Optimisation requêtes SQL
   - Compression données temps réel

2. **Tests & Documentation**
   - Tests unitaires backend
   - Tests E2E frontend
   - Documentation API (Swagger)

---

## 📊 Exemples de Requêtes Utiles

### Statistiques Client
```sql
-- Top 5 clients par revenus
SELECT 
    c.name,
    cu.total_revenue,
    cu.total_orders,
    cu.average_order_value
FROM customers cu
JOIN contacts c ON cu.contact_id = c.id
ORDER BY cu.total_revenue DESC
LIMIT 5;
```

### Performance Fournisseur
```sql
-- Évaluation globale fournisseurs
SELECT 
    c.name,
    s.supplier_category,
    s.reliability_rating,
    s.quality_rating,
    s.on_time_delivery_rate,
    COUNT(po.id) as total_orders
FROM suppliers s
JOIN contacts c ON s.contact_id = c.id
LEFT JOIN purchase_orders po ON s.id = po.supplier_id
GROUP BY c.name, s.supplier_category, s.reliability_rating, 
         s.quality_rating, s.on_time_delivery_rate
ORDER BY s.reliability_rating DESC;
```

### Rentabilité par Lot
```sql
-- Analyse coût/bénéfice des lots
SELECT 
    batch_number,
    egg_quantity,
    hatched_count,
    hatch_rate,
    total_cost,
    cost_per_chick,
    (hatched_count * (SELECT selling_price FROM products WHERE code = 'CHICK-001')) as estimated_revenue,
    (hatched_count * (SELECT selling_price FROM products WHERE code = 'CHICK-001')) - total_cost as estimated_profit
FROM batches
WHERE status = 'completed'
ORDER BY estimated_profit DESC;
```

---

## 🔐 Sécurité & Bonnes Pratiques

### 1. Variables d'Environnement
```bash
# .env
DATABASE_URL=postgresql://user:password@localhost:5432/incubator_management
SECRET_KEY=votre_clé_secrète_jwt
ALLOWED_ORIGINS=http://localhost:3000,https://votre-domaine.com
```

### 2. Validation des Données
```python
# Utiliser Pydantic pour validation
from pydantic import BaseModel, EmailStr, validator

class ContactCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    
    @validator('phone')
    def validate_phone(cls, v):
        # Valider format téléphone Madagascar
        if not v.startswith('+261') and not v.startswith('0'):
            raise ValueError('Numéro invalide')
        return v
```

### 3. Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/iot/telemetry")
@limiter.limit("100/minute")  # Max 100 requêtes/minute
async def receive_telemetry(data: TelemetryData):
    pass
```

---

## 📈 KPIs à Suivre

### Opérationnels
- Taux d'éclosion moyen (objectif : >85%)
- Temps d'utilisation incubateurs (objectif : >80%)
- Durée moyenne cycle (objectif : 21 jours)

### Commerciaux
- Chiffre d'affaires mensuel
- Marge bénéficiaire (objectif : >35%)
- Délai moyen de livraison (objectif : <3 jours)
- Taux de satisfaction client

### Qualité
- Note moyenne fournisseurs (objectif : >4/5)
- Taux de livraison à temps (objectif : >90%)
- Taux de qualité œufs (objectif : >95%)

---

## 🎓 Conclusion

Ce système vous offre :
- ✅ Vision 360° de votre activité
- ✅ Traçabilité complète (œuf → poussin → client)
- ✅ Décisions basées sur les données
- ✅ Optimisation continue des coûts
- ✅ Scalabilité pour croissance future

**Prochaines Étapes :**
1. Valider ce schéma avec vos besoins spécifiques
2. Commencer l'implémentation phase par phase
3. Tester avec données réelles
4. Itérer et améliorer

Bon développement ! 🚀