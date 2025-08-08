#!/usr/bin/python3

import os
import logging
from typing import Optional, Generator
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, Text, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from pydantic import BaseSettings
from dotenv import load_dotenv

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
        #!/usr/bin/python3
    
    import os
    import logging
    from typing import Optional, Generator
    from contextlib import contextmanager
    
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, TIMESTAMP, func
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    from pydantic import BaseSettings
    
    # Chargement automatique du .env si présent
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.getenv("ENV_PATH", ".env"))
    
    # Configuration via variables d'environnement
    class DatabaseSettings(BaseSettings):
        db_host: str = "127.0.0.1"
        db_port: int = 5432
        db_user: str = "ted"
        db_password: str = "ombre1235"
        db_name: str = "sensor"
        db_pool_size: int = 10
        db_max_overflow: int = 20
    
        class Config:
            env_prefix = "DB_"
            case_sensitive = False
            env_file = os.getenv("ENV_PATH", ".env")
    
    db_settings = DatabaseSettings()
    
    # Configuration du logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    Base = declarative_base()
    
    class LoginModel(Base):
        __tablename__ = 'login'
        id = Column(Integer, primary_key=True, autoincrement=True)
        mail_id = Column(String(255), nullable=True)
        user_name = Column(String(100), nullable=False, unique=True)
        password = Column(String(255), nullable=False)
        status = Column(Boolean, default=True)
        created_at = Column(TIMESTAMP, server_default=func.now())
    
    class StepperModel(Base):
        __tablename__ = 'stepper'
        id = Column(Integer, primary_key=True, autoincrement=True)
        start_date = Column(DateTime, nullable=True)
        status = Column(Boolean, default=False)
        created_at = Column(TIMESTAMP, server_default=func.now())
    
    class ParameterDataModel(Base):
        __tablename__ = 'parameter_data'
        id = Column(Integer, primary_key=True, autoincrement=True)
        temperature = Column(Float, nullable=False)
        humidity = Column(Float, nullable=False)
        start_date = Column(DateTime, nullable=False)
        stat_stepper = Column(Boolean, default=False)
        number_stepper = Column(Integer, default=1)
        espece = Column(String(50), nullable=False)
        timetoclose = Column(Integer, default=28)
        created_at = Column(TIMESTAMP, server_default=func.now())
    
    class DataTempModel(Base):
        __tablename__ = 'data_temp'
        id = Column(Integer, primary_key=True, autoincrement=True)
        sensor = Column(String(100), nullable=False)
        temperature = Column(Float, nullable=False)
        humidity = Column(Float, nullable=False)
        date_serveur = Column(TIMESTAMP, server_default=func.now())
        average_temperature = Column(Float, nullable=True)
        average_humidity = Column(Float, nullable=True)
        fan_status = Column(Boolean, default=False)
        humidifier_status = Column(Boolean, default=False)
        numfailedsensors = Column(Integer, default=0)
    
    class DatabaseManager:
        def __init__(self):
            self.engine = None
            self.SessionLocal = None
            self._initialize_database()
    
        def _get_database_url(self) -> str:
            return (
                f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
                f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
            )
    
        def _initialize_database(self):
            try:
                self.engine = create_engine(
                    self._get_database_url(),
                    pool_size=db_settings.db_pool_size,
                    max_overflow=db_settings.db_max_overflow,
                    pool_pre_ping=True,
                    echo=False
                )
                self.SessionLocal = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self.engine
                )
                self._ensure_database_exists()
                self._create_tables()
                logger.info("Base de données initialisée avec succès")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
                raise
    
        def _ensure_database_exists(self):
            try:
                with self.engine.connect() as conn:
                    conn.execute("SELECT 1")
            except Exception as e:
                if "does not exist" in str(e) or "3D000" in str(e):
                    logger.info(f"Base de données {db_settings.db_name} n'existe pas, création en cours...")
                    self._create_database()
                else:
                    raise
    
        def _create_database(self):
            try:
                default_url = (
                    f"postgresql://{db_settings.db_user}:{db_settings.db_password}"
                    f"@{db_settings.db_host}:{db_settings.db_port}/postgres"
                )
                default_engine = create_engine(default_url, isolation_level='AUTOCOMMIT')
                with default_engine.connect() as conn:
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
            try:
                Base.metadata.create_all(bind=self.engine)
                logger.info("Tables créées avec succès")
                self._insert_default_data()
            except Exception as e:
                logger.error(f"Erreur lors de la création des tables: {e}")
                raise
    
        def _insert_default_data(self):
            try:
                with self.get_session() as session:
                    admin_user = session.query(LoginModel).filter_by(user_name='admin').first()
                    if not admin_user:
                        # En production, il faut hasher le mot de passe !
                        admin = LoginModel(
                            mail_id='admin@example.com',
                            user_name='admin',
                            password='admin',
                            status=True
                        )
                        session.add(admin)
                        session.commit()
                        logger.info("Utilisateur admin créé")
            except Exception as e:
                logger.error(f"Erreur lors de l'insertion des données par défaut: {e}")
    
        def get_session(self) -> Session:
            if not self.SessionLocal:
                raise RuntimeError("Base de données non initialisée")
            return self.SessionLocal()
    
        @contextmanager
        def get_session_context(self) -> Generator[Session, None, None]:
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
            try:
                conn = psycopg2.connect(
                    host=db_settings.db_host,
                    port=db_settings.db_port,
                    database=db_settings.db_name,
                    user=db_settings.db_user,
                    password=db_settings.db_password,
                    cursor_factory=RealDictCursor
                )
                return conn
            except Exception as e:
                logger.error(f"Erreur lors de la connexion brute: {e}")
                raise
    
        def close_connection(self, conn):
            if conn:
                conn.close()
    
        def health_check(self) -> bool:
            try:
                with self.get_session_context() as session:
                    session.execute("SELECT 1")
                    return True
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return False
    
    db_manager = DatabaseManager()
    
    def get_db_connection():
        return db_manager.get_raw_connection()
    
    def close_db_connection():
        pass
    
    def get_db() -> Generator[Session, None, None]:
        with db_manager.get_session_context() as session:
            yield session
    
    def init_database():
        try:
            db_manager._initialize_database()
            logger.info("Base de données initialisée")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation: {e}")
            raise
    
    def reset_database():
        try:
            Base.metadata.drop_all(bind=db_manager.engine)
            Base.metadata.create_all(bind=db_manager.engine)
            db_manager._insert_default_data()
            logger.info("Base de données réinitialisée")
        except Exception as e:
            logger.error(f"Erreur lors de la réinitialisation: {e}")
            raise
    
    def setup_database_logging():
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    
    if __name__ == "__main__":
        setup_database_logging()
        try:
            init_database()
            print("✅ Configuration de base de données réussie")
            if db_manager.health_check():
                print("✅ Health check réussi")
            else:
                print("❌ Health check échoué")
        except Exception as e:
            print(f"❌ Erreur: {e}")
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_user: str = "ted"
    db_password: str = "ombre1235"
    db_name: str = "sensor"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    class Config:
        env_prefix = "DB_"
        case_sensitive = False

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
    __tablename__ = 'login'
    
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
    start_date = Column(DateTime, nullable=True)
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
    created_at = Column(TIMESTAMP, server_default='NOW()')

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

class DatabaseManager:
    """Gestionnaire de base de données avec pool de connexions"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _get_database_url(self) -> str:
        """Construire l'URL de connexion à la base de données"""
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
                conn.execute("SELECT 1")
                
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
                        password='admin',  # En production, hasher le mot de passe
                        status=True
                    )
                    session.add(admin)
                    session.commit()
                    logger.info("Utilisateur admin créé")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'insertion des données par défaut: {e}")
    
    def get_session(self) -> Session:
        """Obtenir une session de base de données"""
        if not self.SessionLocal:
            raise RuntimeError("Base de données non initialisée")
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