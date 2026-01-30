#!/usr/bin/python3

import os
import logging
from typing import Optional, Generator
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, Text, TIMESTAMP, func, text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
# from pydantic import BaseSettings
from pydantic_settings import BaseSettings
from pydantic import Field, conint, constr
from sqlalchemy import Time  # Ajoute cette importation

from dotenv import load_dotenv
import bcrypt

# Chargement des variables d'environnement
load_dotenv(dotenv_path=os.getenv("ENV_PATH", ".env"))

# Configuration directe depuis les variables d'environnement
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "user": os.getenv("DB_USER", "ted"),
    "password": os.getenv("DB_PASSWORD", "ombre1235"),
    "database": os.getenv("DB_NAME", "sensor"),
    "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
    "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20"))
}

# Configuration via variables d'environnement
class DatabaseSettings(BaseSettings):
    """Configuration de la base de données via variables d'environnement"""
    # Vérifier d'abord APP_DATABASE_URL (Docker), sinon utiliser les paramètres individuels
    database_url: Optional[str] = Field(default=None, alias="APP_DATABASE_URL", description="URL de connexion complète")
    db_host: constr(strip_whitespace=True, min_length=1) = Field(default="127.0.0.1", description="Adresse de la base")
    db_port: conint(ge=1, le=65535) = Field(default=5432, description="Port de la base")
    db_user: constr(strip_whitespace=True, min_length=1) = Field(default="ted", description="Utilisateur")
    db_password: str = Field(default="ombre1235", description="Mot de passe")
    db_name: constr(strip_whitespace=True, min_length=1) = Field(default="sensor", description="Nom de la base")
    db_pool_size: conint(ge=1, le=100) = Field(default=10, description="Taille du pool")
    db_max_overflow: conint(ge=0, le=100) = Field(default=20, description="Overflow du pool")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow", # Permettre les variables non définies dans le modèle
        "populate_by_name": True  # Accepter les alias
    }

# Instance des paramètres
db_settings = DatabaseSettings()

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base SQLAlchemy
Base = declarative_base()

# Modèles de données
class LoginModel(Base):
    """Modèle pour la table login"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    mail_id = Column(String(255), nullable=True)
    user_name = Column(String(100), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    status = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default='NOW()')

class StepperModel(Base):
    """Modèle pour la table stepper"""
    __tablename__ = 'stepper'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    start_date = Column(Time, nullable=True)  # Modifie ici: DateTime -> Time
    status = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default='NOW()')

class ParameterDataModel(Base):
    """Modèle pour la table parameter_data"""
    __tablename__ = 'parameter_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    start_date = Column(DateTime, nullable=False)
    stat_stepper = Column(Boolean, default=False)
    number_stepper = Column(Integer, default=1)
    espece = Column(String(50), nullable=False)
    timetoclose = Column(Integer, default=28)
    temp_incubation = Column(Float, default=37.5)
    humidity_target = Column(Float, default=60.0)
    rotation_count = Column(Integer, default=5)
    user_id = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, server_default='NOW()')
    updated_at = Column(DateTime, nullable=True)

class DataTempModel(Base):
    """Modèle pour la table data_temp"""
    __tablename__ = 'data_temp'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sensor = Column(String(100), nullable=False)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    date_serveur = Column(TIMESTAMP, server_default='NOW()')
    average_temperature = Column(Float, nullable=True)
    average_humidity = Column(Float, nullable=True)
    fan_status = Column(Boolean, default=False)
    humidifier_status = Column(Boolean, default=False)
    numfailedsensors = Column(Integer, default=0)

# --- Nouveaux modèles CRM & IoT ---

class ContactModel(Base):
    """Table centrale des contacts"""
    __tablename__ = 'contacts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    type = Column(String(20), nullable=False) # 'customer', 'supplier', 'both'
    name = Column(String(255), nullable=False)
    legal_name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(50), nullable=True)
    mobile = Column(String(50), nullable=True)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), default='Madagascar')
    tax_id = Column(String(50), nullable=True)
    stat = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default='NOW()')
    updated_at = Column(TIMESTAMP, server_default='NOW()', onupdate=func.now())
    created_by = Column(Integer, nullable=True)

class CustomerModel(Base):
    """Table spécifique CLIENTS"""
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey('contacts.id', ondelete='CASCADE'), nullable=False, unique=True)
    payment_terms = Column(Integer, default=30)
    credit_limit = Column(Float, default=0)
    discount_rate = Column(Float, default=0)
    customer_category = Column(String(50), nullable=True)
    priority_level = Column(String(20), default='standard')
    total_orders = Column(Integer, default=0)
    total_revenue = Column(Float, default=0)
    last_order_date = Column(DateTime, nullable=True)
    average_order_value = Column(Float, default=0)
    created_at = Column(TIMESTAMP, server_default='NOW()')
    updated_at = Column(TIMESTAMP, server_default='NOW()', onupdate=func.now())

class SupplierModel(Base):
    """Table spécifique FOURNISSEURS"""
    __tablename__ = 'suppliers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey('contacts.id', ondelete='CASCADE'), nullable=False, unique=True)
    payment_terms = Column(Integer, default=30)
    minimum_order_amount = Column(Float, default=0)
    delivery_time_days = Column(Integer, default=7)
    supplier_category = Column(String(50), nullable=True)
    reliability_rating = Column(Float, default=0)
    total_purchases = Column(Integer, default=0)
    total_spent = Column(Float, default=0)
    last_purchase_date = Column(DateTime, nullable=True)
    average_delivery_time = Column(Float, nullable=True)
    on_time_delivery_rate = Column(Float, nullable=True)
    quality_rating = Column(Float, default=0)
    is_preferred = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default='NOW()')
    updated_at = Column(TIMESTAMP, server_default='NOW()', onupdate=func.now())

class ProductModel(Base):
    """Catalogue produits"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)
    unit = Column(String(20), default='unit')
    purchase_price = Column(Float, default=0)
    selling_price = Column(Float, default=0)
    current_stock = Column(Integer, default=0)
    minimum_stock = Column(Integer, default=0)
    maximum_stock = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default='NOW()')
    updated_at = Column(TIMESTAMP, server_default='NOW()', onupdate=func.now())

class CustomerOrderModel(Base):
    """Commandes clients"""
    __tablename__ = 'customer_orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(50), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    order_date = Column(DateTime, server_default='NOW()')
    expected_delivery_date = Column(DateTime, nullable=True)
    actual_delivery_date = Column(DateTime, nullable=True)
    status = Column(String(30), default='pending')
    payment_status = Column(String(30), default='unpaid')
    subtotal = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    paid_amount = Column(Float, default=0)
    notes = Column(Text, nullable=True)
    delivery_address = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default='NOW()')
    updated_at = Column(TIMESTAMP, server_default='NOW()', onupdate=func.now())
    created_by = Column(Integer, nullable=True)

class CustomerOrderItemModel(Base):
    """Lignes de commande client"""
    __tablename__ = 'customer_order_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('customer_orders.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount_percent = Column(Float, default=0)
    line_total = Column(Float, nullable=False)
    batch_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default='NOW()')

class PurchaseOrderModel(Base):
    """Commandes fournisseurs"""
    __tablename__ = 'purchase_orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    po_number = Column(String(50), unique=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    order_date = Column(DateTime, server_default='NOW()')
    expected_delivery_date = Column(DateTime, nullable=True)
    actual_delivery_date = Column(DateTime, nullable=True)
    status = Column(String(30), default='draft')
    payment_status = Column(String(30), default='unpaid')
    subtotal = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    paid_amount = Column(Float, default=0)
    notes = Column(Text, nullable=True)
    delivery_address = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default='NOW()')
    updated_at = Column(TIMESTAMP, server_default='NOW()', onupdate=func.now())
    created_by = Column(Integer, nullable=True)

class PurchaseOrderItemModel(Base):
    """Lignes de commande fournisseur"""
    __tablename__ = 'purchase_order_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    po_id = Column(Integer, ForeignKey('purchase_orders.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    line_total = Column(Float, nullable=False)
    quantity_received = Column(Integer, default=0)
    quality_rating = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default='NOW()')

class IncubatorModel(Base):
    """Équipements ESP32"""
    __tablename__ = 'incubators'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    location = Column(String(255), nullable=True)
    capacity = Column(Integer, nullable=False)
    status = Column(String(30), default='idle')
    is_online = Column(Boolean, default=False)
    last_seen = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default='NOW()')
    updated_at = Column(TIMESTAMP, server_default='NOW()', onupdate=func.now())

class IncubatorCurrentStateModel(Base):
    """État temps réel incubateurs"""
    __tablename__ = 'incubator_current_state'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    incubator_id = Column(Integer, ForeignKey('incubators.id', ondelete='CASCADE'), nullable=False, unique=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    rotation_count = Column(Integer, default=0)
    has_alert = Column(Boolean, default=False)
    alert_type = Column(String(50), nullable=True)
    updated_at = Column(TIMESTAMP, server_default='NOW()', onupdate=func.now())

class IncubatorTelemetryModel(Base):
    """Historique des données IoT"""
    __tablename__ = 'incubator_telemetry'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    incubator_id = Column(Integer, ForeignKey('incubators.id', ondelete='CASCADE'), nullable=False)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    rotation_count = Column(Integer, nullable=True)
    timestamp = Column(TIMESTAMP, server_default='NOW()')

class BatchModel(Base):
    """Lots d'incubation"""
    __tablename__ = 'batches'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_number = Column(String(50), unique=True, nullable=False)
    incubator_id = Column(Integer, ForeignKey('incubators.id'), nullable=True)
    po_id = Column(Integer, ForeignKey('purchase_orders.id'), nullable=True)
    egg_quantity = Column(Integer, nullable=False)
    egg_supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=True)
    start_date = Column(DateTime, nullable=False)
    expected_hatch_date = Column(DateTime, nullable=True)
    actual_hatch_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    status = Column(String(30), default='in_progress')
    hatched_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    hatch_rate = Column(Float, nullable=True)
    total_cost = Column(Float, default=0)
    cost_per_chick = Column(Float, nullable=True)
    avg_temperature = Column(Float, nullable=True)
    avg_humidity = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default='NOW()')
    updated_at = Column(TIMESTAMP, server_default='NOW()', onupdate=func.now())

class DailyMetricModel(Base):
    """KPIs calculés quotidiennement"""
    __tablename__ = 'daily_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_date = Column(DateTime, unique=True, nullable=False)
    active_batches = Column(Integer, default=0)
    eggs_in_incubation = Column(Integer, default=0)
    incubators_running = Column(Integer, default=0)
    daily_revenue = Column(Float, default=0)
    daily_orders = Column(Integer, default=0)
    daily_purchases = Column(Float, default=0)
    average_hatch_rate = Column(Float, nullable=True)
    chicks_produced = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default='NOW()')

class DatabaseManager:
    """Gestionnaire de base de données avec pool de connexions"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.connected = False
        self.database_url = db_settings.database_url  # Ajouter l'URL de la base
        try:
            self._initialize_database()
            self.connected = True
        except Exception as e:
            logger.warning(f"Base de données non disponible: {e}")
            logger.warning("Fonctionnement en mode développement (mock data)")
            self.connected = False
    
    
    def _get_database_url(self) -> str:
        """Construire l'URL de connexion à la base de données"""
        # Utiliser APP_DATABASE_URL si définie (Docker), sinon construire à partir des paramètres
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{db_settings.db_user}:{db_settings.db_password}"
            f"@{db_settings.db_host}:{db_settings.db_port}/{db_settings.db_name}"
        )
    
    def _initialize_database(self):
        """Initialiser la connexion à la base de données"""
        try:
            # Créer le moteur SQLAlchemy avec pool de connexions
            self.engine = create_engine(
                self._get_database_url(),
                pool_size=db_settings.db_pool_size,
                max_overflow=db_settings.db_max_overflow,
                pool_pre_ping=True,  # Vérifier les connexions avant utilisation
                echo=False  # Mettre à True pour debug SQL
            )
            
            # Créer la session
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Créer la base de données si elle n'existe pas
            self._ensure_database_exists()
            
            # Créer les tables
            self._create_tables()
            
            logger.info("Base de données initialisée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
            raise
    
    def _ensure_database_exists(self):
        """S'assurer que la base de données existe"""
        try:
            # Tester la connexion
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                
        except Exception as e:
            if "does not exist" in str(e) or "3D000" in str(e):
                logger.info(f"Base de données {db_settings.db_name} n'existe pas, création en cours...")
                self._create_database()
            else:
                raise
    
    def _create_database(self):
        """Créer la base de données"""
        try:
            # Connexion à la base postgres par défaut
            default_url = (
                f"postgresql://{db_settings.db_user}:{db_settings.db_password}"
                f"@{db_settings.db_host}:{db_settings.db_port}/postgres"
            )
            
            default_engine = create_engine(default_url, isolation_level='AUTOCOMMIT')
            
            with default_engine.connect() as conn:
                # Vérifier si la base existe déjà
                result = conn.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (db_settings.db_name,)
                )
                
                if not result.fetchone():
                    conn.execute(f"CREATE DATABASE {db_settings.db_name}")
                    logger.info(f"Base de données {db_settings.db_name} créée")
                
            default_engine.dispose()
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la base de données: {e}")
            raise
    
    def _create_tables(self):
        """Créer les tables et insérer les données par défaut"""
        try:
            # Créer toutes les tables
            Base.metadata.create_all(bind=self.engine)
            logger.info("Tables créées avec succès")
            
            # Insérer les données par défaut
            self._insert_default_data()
            
        except Exception as e:
            logger.error(f"Erreur lors de la création des tables: {e}")
            raise

    def hash_password_bcrypt(self, password: str) -> str:
        """Hash un mot de passe avec bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _insert_default_data(self):
        """Insérer les données par défaut"""
        try:
            with self.get_session() as session:
                # Vérifier si l'utilisateur admin existe
                admin_user = session.query(LoginModel).filter_by(user_name='admin').first()
                
                if not admin_user:
                    # Créer l'utilisateur admin par défaut
                    admin = LoginModel(
                        mail_id='admin@example.com',
                        user_name='admin',
                        password= self.hash_password_bcrypt("admin"),  # Mot de passe sécurisé avec bcrypt
                        status=True
                    )
                    session.add(admin)
                    session.commit()
                    logger.info("Utilisateur admin créé")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'insertion des données par défaut: {e}")
    
    def get_session(self) -> Session:
        """Obtenir une session de base de données"""
        if not self.connected or not self.SessionLocal:
            logger.warning("Base de données non disponible - retour None")
            return None
        return self.SessionLocal()
    
    @contextmanager
    def get_session_context(self) -> Generator[Session, None, None]:
        """Context manager pour les sessions de base de données"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur dans la session de base de données: {e}")
            raise
        finally:
            session.close()
    
    def get_raw_connection(self):
        """Obtenir une connexion psycopg2 brute pour compatibilité"""
        try:
            conn = psycopg2.connect(
                host=db_settings.db_host,
                port=db_settings.db_port,
                database=db_settings.db_name,
                user=db_settings.db_user,
                password=db_settings.db_password,
                cursor_factory=RealDictCursor  # Retourne des dictionnaires
            )
            return conn
        except Exception as e:
            logger.error(f"Erreur lors de la connexion brute: {e}")
            raise
    
    def close_connection(self, conn):
        """Fermer une connexion brute"""
        if conn:
            conn.close()
    
    def health_check(self) -> bool:
        """Vérifier la santé de la base de données"""
        try:
            with self.get_session_context() as session:
                session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

# Instance globale du gestionnaire de base de données
db_manager = DatabaseManager()

# Fonctions de compatibilité avec l'ancien code
def get_db_connection():
    """Fonction de compatibilité - retourne une connexion brute"""
    return db_manager.get_raw_connection()

def close_db_connection():
    """Fonction de compatibilité - ne fait rien car on utilise le pool"""
    pass

# Dependency pour FastAPI
def get_db() -> Generator[Session, None, None]:
    """Dependency pour obtenir une session de base de données dans FastAPI"""
    with db_manager.get_session_context() as session:
        yield session

# Fonctions utilitaires
def init_database():
    """Initialiser la base de données (appelé au démarrage de l'app)"""
    try:
        db_manager._initialize_database()
        logger.info("Base de données initialisée")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation: {e}")
        raise

def reset_database():
    """Réinitialiser complètement la base de données (ATTENTION: supprime tout!)"""
    try:
        Base.metadata.drop_all(bind=db_manager.engine)
        Base.metadata.create_all(bind=db_manager.engine)
        db_manager._insert_default_data()
        logger.info("Base de données réinitialisée")
    except Exception as e:
        logger.error(f"Erreur lors de la réinitialisation: {e}")
        raise

# Configuration des logs de base de données
def setup_database_logging():
    """Configurer les logs pour la base de données"""
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)

if __name__ == "__main__":
    # Test de la configuration
    setup_database_logging()
    
    try:
        init_database()
        print("✅ Configuration de base de données réussie")
        
        # Test de santé
        if db_manager.health_check():
            print("✅ Health check réussi")
        else:
            print("❌ Health check échoué")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")