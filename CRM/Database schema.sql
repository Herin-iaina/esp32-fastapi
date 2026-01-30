-- ============================================
-- SCHÉMA DE BASE DE DONNÉES - INCUBATEUR ESP32
-- Système de gestion intégré IoT + CRM
-- ============================================

-- ============================================
-- PARTIE 1: GESTION DES CONTACTS (Hybride)
-- ============================================

-- Table centrale des contacts (évite duplication)
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL, -- Code unique auto-généré (ex: CT-2024-001)
    type VARCHAR(20) NOT NULL CHECK (type IN ('customer', 'supplier', 'both')),
    
    -- Informations de base
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255), -- Raison sociale si différente
    email VARCHAR(255),
    phone VARCHAR(50),
    mobile VARCHAR(50),
    
    -- Adresse
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state_province VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'Madagascar',
    
    -- Informations fiscales
    tax_id VARCHAR(50), -- NIF
    stat VARCHAR(50), -- STAT Madagascar
    
    -- Métadonnées
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER, -- ID utilisateur
    
    -- Index pour recherche rapide
    CONSTRAINT unique_email UNIQUE (email)
);

CREATE INDEX idx_contacts_type ON contacts(type);
CREATE INDEX idx_contacts_name ON contacts(name);
CREATE INDEX idx_contacts_active ON contacts(is_active);


-- Table spécifique CLIENTS (informations commerciales)
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    
    -- Conditions commerciales
    payment_terms INTEGER DEFAULT 30, -- Délai paiement en jours
    credit_limit DECIMAL(12,2) DEFAULT 0, -- Limite de crédit
    discount_rate DECIMAL(5,2) DEFAULT 0, -- Remise habituelle (%)
    
    -- Classification
    customer_category VARCHAR(50), -- 'retail', 'wholesale', 'distributor'
    priority_level VARCHAR(20) DEFAULT 'standard', -- 'vip', 'standard', 'low'
    
    -- Statistiques (calculées)
    total_orders INTEGER DEFAULT 0,
    total_revenue DECIMAL(15,2) DEFAULT 0,
    last_order_date DATE,
    average_order_value DECIMAL(12,2) DEFAULT 0,
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_customer_contact UNIQUE (contact_id)
);

CREATE INDEX idx_customers_contact ON customers(contact_id);
CREATE INDEX idx_customers_category ON customers(customer_category);


-- Table spécifique FOURNISSEURS (informations d'approvisionnement)
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    
    -- Conditions d'achat
    payment_terms INTEGER DEFAULT 30, -- Délai paiement accordé
    minimum_order_amount DECIMAL(12,2) DEFAULT 0,
    delivery_time_days INTEGER DEFAULT 7, -- Délai de livraison standard
    
    -- Classification
    supplier_category VARCHAR(50), -- 'eggs', 'feed', 'equipment', 'supplies'
    reliability_rating DECIMAL(3,2) DEFAULT 0, -- Note sur 5
    
    -- Statistiques (calculées)
    total_purchases INTEGER DEFAULT 0,
    total_spent DECIMAL(15,2) DEFAULT 0,
    last_purchase_date DATE,
    average_delivery_time DECIMAL(5,2), -- Temps réel moyen
    on_time_delivery_rate DECIMAL(5,2), -- % livraisons à temps
    
    -- Évaluation qualité
    quality_rating DECIMAL(3,2) DEFAULT 0, -- Note sur 5
    is_preferred BOOLEAN DEFAULT false,
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_supplier_contact UNIQUE (contact_id)
);

CREATE INDEX idx_suppliers_contact ON suppliers(contact_id);
CREATE INDEX idx_suppliers_category ON suppliers(supplier_category);
CREATE INDEX idx_suppliers_preferred ON suppliers(is_preferred);


-- ============================================
-- PARTIE 2: GESTION DES PRODUITS
-- ============================================

-- Catalogue produits
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL, -- 'eggs_raw', 'chicks', 'feed', 'supplies'
    unit VARCHAR(20) DEFAULT 'unit', -- 'unit', 'kg', 'dozen', 'tray'
    
    -- Prix
    purchase_price DECIMAL(10,2) DEFAULT 0, -- Prix d'achat moyen
    selling_price DECIMAL(10,2) DEFAULT 0, -- Prix de vente
    
    -- Gestion stock
    current_stock INTEGER DEFAULT 0,
    minimum_stock INTEGER DEFAULT 0,
    maximum_stock INTEGER DEFAULT 0,
    
    -- Métadonnées
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_active ON products(is_active);


-- ============================================
-- PARTIE 3: GESTION DES COMMANDES CLIENTS
-- ============================================

CREATE TABLE customer_orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL, -- CMD-2024-001
    customer_id INTEGER REFERENCES customers(id),
    
    -- Dates
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_delivery_date DATE,
    actual_delivery_date DATE,
    
    -- Statuts
    status VARCHAR(30) DEFAULT 'pending', -- 'pending', 'confirmed', 'in_production', 'ready', 'delivered', 'cancelled'
    payment_status VARCHAR(30) DEFAULT 'unpaid', -- 'unpaid', 'partial', 'paid'
    
    -- Montants
    subtotal DECIMAL(12,2) DEFAULT 0,
    discount_amount DECIMAL(12,2) DEFAULT 0,
    tax_amount DECIMAL(12,2) DEFAULT 0,
    total_amount DECIMAL(12,2) DEFAULT 0,
    paid_amount DECIMAL(12,2) DEFAULT 0,
    
    -- Informations additionnelles
    notes TEXT,
    delivery_address TEXT,
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER
);

CREATE INDEX idx_customer_orders_customer ON customer_orders(customer_id);
CREATE INDEX idx_customer_orders_status ON customer_orders(status);
CREATE INDEX idx_customer_orders_date ON customer_orders(order_date);


-- Lignes de commande client
CREATE TABLE customer_order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES customer_orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    discount_percent DECIMAL(5,2) DEFAULT 0,
    line_total DECIMAL(12,2) NOT NULL,
    
    -- Traçabilité (lié aux lots d'incubation)
    batch_id INTEGER, -- Référence au lot d'incubation si applicable
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_order_items_order ON customer_order_items(order_id);
CREATE INDEX idx_order_items_product ON customer_order_items(product_id);


-- ============================================
-- PARTIE 4: GESTION DES COMMANDES FOURNISSEURS
-- ============================================

CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    po_number VARCHAR(50) UNIQUE NOT NULL, -- PO-2024-001
    supplier_id INTEGER REFERENCES suppliers(id),
    
    -- Dates
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_delivery_date DATE,
    actual_delivery_date DATE,
    
    -- Statuts
    status VARCHAR(30) DEFAULT 'draft', -- 'draft', 'sent', 'confirmed', 'received', 'cancelled'
    payment_status VARCHAR(30) DEFAULT 'unpaid',
    
    -- Montants
    subtotal DECIMAL(12,2) DEFAULT 0,
    tax_amount DECIMAL(12,2) DEFAULT 0,
    total_amount DECIMAL(12,2) DEFAULT 0,
    paid_amount DECIMAL(12,2) DEFAULT 0,
    
    -- Informations additionnelles
    notes TEXT,
    delivery_address TEXT,
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER
);

CREATE INDEX idx_purchase_orders_supplier ON purchase_orders(supplier_id);
CREATE INDEX idx_purchase_orders_status ON purchase_orders(status);
CREATE INDEX idx_purchase_orders_date ON purchase_orders(order_date);


-- Lignes de commande fournisseur
CREATE TABLE purchase_order_items (
    id SERIAL PRIMARY KEY,
    po_id INTEGER REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    line_total DECIMAL(12,2) NOT NULL,
    
    quantity_received INTEGER DEFAULT 0, -- Quantité réellement reçue
    quality_rating DECIMAL(3,2), -- Note qualité de cette livraison
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_po_items_po ON purchase_order_items(po_id);
CREATE INDEX idx_po_items_product ON purchase_order_items(product_id);


-- ============================================
-- PARTIE 5: GESTION DES INCUBATEURS (IoT)
-- ============================================

CREATE TABLE incubators (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(50) UNIQUE NOT NULL, -- ID ESP32
    name VARCHAR(100) NOT NULL,
    location VARCHAR(255),
    
    -- Capacité
    capacity INTEGER NOT NULL, -- Nombre d'œufs max
    
    -- Statut
    status VARCHAR(30) DEFAULT 'idle', -- 'idle', 'running', 'paused', 'maintenance', 'error'
    is_online BOOLEAN DEFAULT false,
    last_seen TIMESTAMP,
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_incubators_status ON incubators(status);
CREATE INDEX idx_incubators_online ON incubators(is_online);


-- Données temps réel incubateurs (dernières valeurs)
CREATE TABLE incubator_current_state (
    id SERIAL PRIMARY KEY,
    incubator_id INTEGER REFERENCES incubators(id) ON DELETE CASCADE,
    
    temperature DECIMAL(5,2),
    humidity DECIMAL(5,2),
    rotation_count INTEGER DEFAULT 0,
    
    -- Alertes
    has_alert BOOLEAN DEFAULT false,
    alert_type VARCHAR(50),
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_incubator_state UNIQUE (incubator_id)
);


-- Historique des données IoT (pour analytics)
CREATE TABLE incubator_telemetry (
    id SERIAL PRIMARY KEY,
    incubator_id INTEGER REFERENCES incubators(id) ON DELETE CASCADE,
    
    temperature DECIMAL(5,2),
    humidity DECIMAL(5,2),
    rotation_count INTEGER,
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Partition par mois pour optimiser les performances
CREATE INDEX idx_telemetry_incubator_time ON incubator_telemetry(incubator_id, timestamp DESC);


-- ============================================
-- PARTIE 6: GESTION DES LOTS D'INCUBATION
-- ============================================

CREATE TABLE batches (
    id SERIAL PRIMARY KEY,
    batch_number VARCHAR(50) UNIQUE NOT NULL, -- LOT-2024-001
    incubator_id INTEGER REFERENCES incubators(id),
    po_id INTEGER REFERENCES purchase_orders(id), -- Lien avec achat d'œufs
    
    -- Informations du lot
    egg_quantity INTEGER NOT NULL, -- Nombre d'œufs mis en incubation
    egg_supplier_id INTEGER REFERENCES suppliers(id), -- Fournisseur des œufs
    
    -- Dates du cycle
    start_date TIMESTAMP NOT NULL,
    expected_hatch_date DATE,
    actual_hatch_date DATE,
    end_date TIMESTAMP,
    
    -- Statut
    status VARCHAR(30) DEFAULT 'in_progress', -- 'in_progress', 'hatched', 'completed', 'failed'
    
    -- Résultats
    hatched_count INTEGER DEFAULT 0, -- Poussins éclos
    failed_count INTEGER DEFAULT 0, -- Œufs non éclos
    hatch_rate DECIMAL(5,2), -- Taux de réussite (%)
    
    -- Coûts et rendement
    total_cost DECIMAL(12,2) DEFAULT 0, -- Coût total du lot
    cost_per_chick DECIMAL(10,2), -- Coût par poussin
    
    -- Conditions moyennes du cycle
    avg_temperature DECIMAL(5,2),
    avg_humidity DECIMAL(5,2),
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_batches_incubator ON batches(incubator_id);
CREATE INDEX idx_batches_status ON batches(status);
CREATE INDEX idx_batches_dates ON batches(start_date, end_date);


-- ============================================
-- PARTIE 7: MÉTRIQUES ET ANALYTICS
-- ============================================

-- Table pour stocker les KPIs calculés quotidiennement
CREATE TABLE daily_metrics (
    id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    
    -- Métriques opérationnelles
    active_batches INTEGER DEFAULT 0,
    eggs_in_incubation INTEGER DEFAULT 0,
    incubators_running INTEGER DEFAULT 0,
    
    -- Métriques commerciales
    daily_revenue DECIMAL(12,2) DEFAULT 0,
    daily_orders INTEGER DEFAULT 0,
    daily_purchases DECIMAL(12,2) DEFAULT 0,
    
    -- Métriques de performance
    average_hatch_rate DECIMAL(5,2),
    chicks_produced INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_metric_date UNIQUE (metric_date)
);

CREATE INDEX idx_daily_metrics_date ON daily_metrics(metric_date DESC);


-- ============================================
-- PARTIE 8: VUES UTILES POUR LES DASHBOARDS
-- ============================================

-- Vue: Contacts avec leur type complet
CREATE VIEW v_all_contacts AS
SELECT 
    c.*,
    CASE 
        WHEN cu.id IS NOT NULL AND s.id IS NOT NULL THEN 'both'
        WHEN cu.id IS NOT NULL THEN 'customer'
        WHEN s.id IS NOT NULL THEN 'supplier'
        ELSE c.type
    END as actual_type,
    cu.total_revenue,
    cu.total_orders,
    s.total_spent,
    s.total_purchases,
    s.reliability_rating
FROM contacts c
LEFT JOIN customers cu ON c.id = cu.contact_id
LEFT JOIN suppliers s ON c.id = s.contact_id;


-- Vue: Commandes clients avec détails
CREATE VIEW v_customer_orders_details AS
SELECT 
    co.*,
    c.name as customer_name,
    c.email as customer_email,
    c.phone as customer_phone,
    COUNT(coi.id) as items_count,
    co.total_amount - co.paid_amount as balance_due
FROM customer_orders co
JOIN customers cu ON co.customer_id = cu.id
JOIN contacts c ON cu.contact_id = c.id
LEFT JOIN customer_order_items coi ON co.id = coi.order_id
GROUP BY co.id, c.name, c.email, c.phone;


-- Vue: Performance des fournisseurs
CREATE VIEW v_supplier_performance AS
SELECT 
    s.id as supplier_id,
    c.name as supplier_name,
    s.supplier_category,
    s.total_purchases,
    s.total_spent,
    s.reliability_rating,
    s.quality_rating,
    s.on_time_delivery_rate,
    s.is_preferred,
    COUNT(po.id) as total_orders,
    AVG(po.total_amount) as avg_order_value,
    MAX(po.order_date) as last_order_date
FROM suppliers s
JOIN contacts c ON s.contact_id = c.id
LEFT JOIN purchase_orders po ON s.id = po.supplier_id
GROUP BY s.id, c.name, s.supplier_category, s.total_purchases, 
         s.total_spent, s.reliability_rating, s.quality_rating,
         s.on_time_delivery_rate, s.is_preferred;


-- Vue: Performance des lots d'incubation
CREATE VIEW v_batch_performance AS
SELECT 
    b.*,
    i.name as incubator_name,
    c.name as supplier_name,
    CASE 
        WHEN b.egg_quantity > 0 THEN ROUND((b.hatched_count::DECIMAL / b.egg_quantity * 100), 2)
        ELSE 0 
    END as calculated_hatch_rate,
    CASE 
        WHEN b.hatched_count > 0 THEN ROUND(b.total_cost / b.hatched_count, 2)
        ELSE 0 
    END as calculated_cost_per_chick
FROM batches b
LEFT JOIN incubators i ON b.incubator_id = i.id
LEFT JOIN suppliers s ON b.egg_supplier_id = s.id
LEFT JOIN contacts c ON s.contact_id = c.id;


-- ============================================
-- PARTIE 9: TRIGGERS POUR AUTOMATISATION
-- ============================================

-- Fonction pour mettre à jour le timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Appliquer le trigger sur toutes les tables pertinentes
CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_suppliers_updated_at BEFORE UPDATE ON suppliers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customer_orders_updated_at BEFORE UPDATE ON customer_orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_purchase_orders_updated_at BEFORE UPDATE ON purchase_orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_batches_updated_at BEFORE UPDATE ON batches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- Fonction pour calculer automatiquement le hatch_rate
CREATE OR REPLACE FUNCTION calculate_batch_hatch_rate()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.egg_quantity > 0 THEN
        NEW.hatch_rate = ROUND((NEW.hatched_count::DECIMAL / NEW.egg_quantity * 100), 2);
    END IF;
    
    IF NEW.hatched_count > 0 AND NEW.total_cost > 0 THEN
        NEW.cost_per_chick = ROUND(NEW.total_cost / NEW.hatched_count, 2);
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER auto_calculate_batch_metrics BEFORE INSERT OR UPDATE ON batches
    FOR EACH ROW EXECUTE FUNCTION calculate_batch_hatch_rate();


-- ============================================
-- PARTIE 10: DONNÉES D'EXEMPLE (OPTIONNEL)
-- ============================================

-- Quelques catégories de produits standards
INSERT INTO products (code, name, category, unit, selling_price) VALUES
('EGG-FERT-001', 'Œufs fécondés poule locale', 'eggs_raw', 'unit', 500),
('CHICK-001', 'Poussin 1 jour', 'chicks', 'unit', 2000),
('FEED-001', 'Aliment démarrage', 'feed', 'kg', 1500),
('SUPPLY-001', 'Thermomètre numérique', 'supplies', 'unit', 15000);

-- Exemple de contact mixte (client ET fournisseur)
-- INSERT INTO contacts (code, type, name, email, phone, city) VALUES
-- ('CT-2024-001', 'both', 'Ferme Razafy', 'contact@fermerazafy.mg', '+261 34 12 345 67', 'Antananarivo');