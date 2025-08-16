import pymysql
from pymysql.cursors import DictCursor
import logging
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Gerencia conexões com o banco de dados MariaDB"""

    def __init__(self):
        self.config = {
            'host': '147.79.107.233',
            'port': 3306,
            'user': 'mariadb',
            'password': 'd94ab37eb565cbe500af',
            'database': 'avalion_painel',
            'charset': 'utf8mb4',
            'cursorclass': DictCursor
        }

    @contextmanager
    def get_connection(self):
        """Context manager para conexão com o banco"""
        connection = None
        try:
            connection = pymysql.connect(**self.config)
            yield connection
            connection.commit()
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Erro na conexão com o banco: {e}")
            raise
        finally:
            if connection:
                connection.close()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Executa uma query SELECT e retorna os resultados"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()

    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """Executa uma query INSERT/UPDATE/DELETE e retorna o número de linhas afetadas"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.rowcount

    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Executa múltiplas operações em batch"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                return cursor.rowcount


# Instância global do banco de dados
db = DatabaseConnection()


# Cache de configurações simples
class ConfigCache:
    def __init__(self):
        self._cache = {}
        self._last_update = datetime.now()

    def get(self, key):
        if (datetime.now() - self._last_update).seconds > 300:
            self._cache = {}
            self._last_update = datetime.now()
        return self._cache.get(key)

    def set(self, key, value):
        self._cache[key] = value


_config_cache = ConfigCache()


def get_config(chave: str, default: Any = None) -> Any:
    """Obtém uma configuração do banco de dados"""
    cached = _config_cache.get(chave)
    if cached is not None:
        return cached

    try:
        query = "SELECT valor, tipo FROM configuracoes WHERE chave = %s"
        result = db.execute_query(query, (chave,))

        if not result:
            return default

        valor = result[0]['valor']
        tipo = result[0]['tipo']

        if tipo == 'int':
            valor = int(valor)
        elif tipo == 'bool':
            valor = valor.lower() in ('true', '1', 'yes', 'sim')
        elif tipo == 'json':
            valor = json.loads(valor)

        _config_cache.set(chave, valor)
        return valor
    except Exception as e:
        logger.error(f"Erro ao obter configuração {chave}: {e}")
        return default


def update_config(chave: str, valor: Any, tipo: str = None) -> bool:
    """Atualiza uma configuração no banco de dados"""
    try:
        if tipo is None:
            if isinstance(valor, bool):
                tipo = 'bool'
            elif isinstance(valor, int):
                tipo = 'int'
            elif isinstance(valor, (dict, list)):
                tipo = 'json'
            else:
                tipo = 'string'

        if tipo == 'json':
            valor_str = json.dumps(valor)
        elif tipo == 'bool':
            valor_str = 'true' if valor else 'false'
        else:
            valor_str = str(valor)

        query = """
            INSERT INTO configuracoes (chave, valor, tipo) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            valor = VALUES(valor), 
            tipo = VALUES(tipo),
            updated_at = NOW()
        """

        rows = db.execute_update(query, (chave, valor_str, tipo))
        _config_cache.set(chave, None)
        return rows > 0
    except Exception as e:
        logger.error(f"Erro ao atualizar configuração {chave}: {e}")
        return False


def get_plataformas_ativas() -> List[Dict[str, Any]]:
    """Retorna plataformas ativas"""
    try:
        query = """
        SELECT id, nome, url_base 
        FROM plataformas 
        WHERE ativo = 1
        ORDER BY nome
        """
        return db.execute_query(query)
    except Exception as e:
        logger.error(f"Erro ao buscar plataformas ativas: {e}")
        return []


def salvar_links_duckduckgo_batch(links_com_dados: List[Dict[str, Any]]) -> int:
    """Salva múltiplos links do DuckDuckGo em batch"""
    try:
        if not links_com_dados:
            return 0

        query = """
            INSERT IGNORE INTO links_duckduckgo 
            (url, plataforma_id, tipo_busca_id, estado_id, municipio_id, 
             distrito_id, termo_busca, posicao_busca)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        params_list = []
        for dados in links_com_dados:
            plataforma_data = db.execute_query(
                "SELECT id FROM plataformas WHERE nome = %s",
                (dados['plataforma'],)
            )
            if plataforma_data:
                params_list.append((
                    dados['url'],
                    plataforma_data[0]['id'],
                    dados.get('tipo_busca_id'),
                    dados.get('estado_id'),
                    dados.get('municipio_id'),
                    dados.get('distrito_id'),
                    dados.get('termo_busca'),
                    dados.get('posicao_busca', 0)
                ))

        if params_list:
            rows = db.execute_many(query, params_list)
            logger.info(f"Salvos {rows} links do DuckDuckGo")
            return rows
        return 0
    except Exception as e:
        logger.error(f"Erro ao salvar links do DuckDuckGo em batch: {e}")
        return 0


