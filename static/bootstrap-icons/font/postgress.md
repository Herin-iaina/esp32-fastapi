Crée un fichier docker-compose.yml :
version: '3.8'
services:
  db:
    image: postgres:16
    restart: always
    environment:
      POSTGRES_USER: ted
      POSTGRES_PASSWORD: ombre1235
      POSTGRES_DB: sensor
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:

Crée un fichier docker-compose.yml :
docker-compose up -d

2. Connexion à la base depuis ton application
DB_HOST=localhost
DB_PORT=5432
DB_USER=ted
DB_PASSWORD=ombre1235
DB_NAME=sensor
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

Dans ton code Python (avec Pydantic) :
from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "ted"
    db_password: str = "ombre1235"
    db_name: str = "sensor"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }


3. Connexion manuelle à la base pour vérifier
Depuis le terminal :
docker exec -it <container_id> psql -U ted -d sensor

ou depuis l’hôte :
psql -h localhost -U ted -d sensor

4. Gestion des permissions
Par défaut, l’utilisateur ted créé par Docker est propriétaire de la base et du schéma public.
Mais si tu crées d’autres utilisateurs ou schémas, il faut :

S’assurer que l’utilisateur a les droits sur le schéma :
GRANT ALL ON SCHEMA public TO ted;
GRANT ALL PRIVILEGES ON DATABASE sensor TO ted;
ALTER SCHEMA public OWNER TO ted;
ALTER DATABASE sensor OWNER TO ted;

Si des tables existent déjà, s’assurer que ted en est propriétaire :
ALTER TABLE public.login OWNER TO ted;
ALTER TABLE public.stepper OWNER TO ted;
ALTER TABLE public.parameter_data OWNER TO ted;
ALTER TABLE public.data_temp OWNER TO ted;