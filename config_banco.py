"""
Configurações para diferentes tipos de banco de dados
"""

# Configuração SQLite (padrão)
SQLITE_CONFIG = {
    "type": "sqlite",
    "database": "imoveis.db",
    "check_same_thread": False
}

# Configuração PostgreSQL
POSTGRES_CONFIG = {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "imoveis",
    "user": "postgres",
    "password": "sua_senha",
    "schema": "public"
}

# Configuração MySQL
MYSQL_CONFIG = {
    "type": "mysql",
    "host": "localhost",
    "port": 3306,
    "database": "imoveis",
    "user": "root",
    "password": "sua_senha",
    "charset": "utf8mb4"
}

# Configuração MongoDB
MONGODB_CONFIG = {
    "type": "mongodb",
    "host": "localhost",
    "port": 27017,
    "database": "imoveis",
    "collection": "imoveis"
}

# Configuração Redis (para cache)
REDIS_CONFIG = {
    "type": "redis",
    "host": "localhost",
    "port": 6379,
    "db": 0,
    "password": None
}

# Selecionar configuração padrão
DEFAULT_DB_CONFIG = SQLITE_CONFIG

# Função para obter configuração
def get_db_config(db_type: str = None):
    """Retorna configuração do banco de dados"""
    if db_type == "postgresql":
        return POSTGRES_CONFIG
    elif db_type == "mysql":
        return MYSQL_CONFIG
    elif db_type == "mongodb":
        return MONGODB_CONFIG
    elif db_type == "redis":
        return REDIS_CONFIG
    else:
        return DEFAULT_DB_CONFIG

# Exemplo de uso com variáveis de ambiente
import os

def get_db_config_from_env():
    """Obtém configuração do banco a partir de variáveis de ambiente"""
    db_type = os.getenv("DB_TYPE", "sqlite")
    
    if db_type == "postgresql":
        return {
            "type": "postgresql",
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "imoveis"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", ""),
            "schema": os.getenv("DB_SCHEMA", "public")
        }
    elif db_type == "mysql":
        return {
            "type": "mysql",
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "database": os.getenv("DB_NAME", "imoveis"),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "charset": "utf8mb4"
        }
    else:
        return SQLITE_CONFIG
