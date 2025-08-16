#!/usr/bin/env python3
"""
Script para verificar e configurar dados necessários no banco MariaDB
"""

from database import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verificar_plataformas():
    """Verifica e insere plataformas se necessário"""
    logger.info("🔍 Verificando plataformas...")
    
    # Verificar se VivaReal existe
    result = db.execute_query("SELECT * FROM plataformas WHERE nome = 'VivaReal'")
    
    if not result:
        logger.info("❌ VivaReal não encontrado. Inserindo...")
        try:
            db.execute_update(
                """INSERT INTO plataformas (nome, url_base, ativo, created_at) 
                   VALUES (%s, %s, %s, NOW())""",
                ("VivaReal", "https://www.vivareal.com.br", 1)
            )
            logger.info("✅ VivaReal inserido com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inserir VivaReal: {e}")
    else:
        logger.info(f"✅ VivaReal já existe: ID={result[0]['id']}, Ativo={result[0]['ativo']}")
        
        # Garantir que está ativo
        if result[0]['ativo'] != 1:
            db.execute_update(
                "UPDATE plataformas SET ativo = 1 WHERE id = %s",
                (result[0]['id'],)
            )
            logger.info("✅ VivaReal ativado")
    
    # Listar todas as plataformas
    todas = db.execute_query("SELECT id, nome, ativo FROM plataformas")
    logger.info(f"📋 Total de plataformas: {len(todas)}")
    for p in todas:
        logger.info(f"   - {p['nome']}: ID={p['id']}, Ativo={p['ativo']}")

def verificar_tipos_busca():
    """Verifica e insere tipos de busca se necessário"""
    logger.info("\n🔍 Verificando tipos de busca...")
    
    tipos_necessarios = ["VENDA", "ALUGUEL"]
    
    for tipo in tipos_necessarios:
        result = db.execute_query("SELECT * FROM tipos_busca WHERE nome = %s", (tipo,))
        
        if not result:
            logger.info(f"❌ {tipo} não encontrado. Inserindo...")
            try:
                db.execute_update(
                    """INSERT INTO tipos_busca (nome, created_at) 
                       VALUES (%s, NOW())""",
                    (tipo,)
                )
                logger.info(f"✅ {tipo} inserido com sucesso")
            except Exception as e:
                logger.error(f"Erro ao inserir {tipo}: {e}")
        else:
            logger.info(f"✅ {tipo} já existe: ID={result[0]['id']}")
    
    # Listar todos os tipos
    todos = db.execute_query("SELECT id, nome FROM tipos_busca")
    logger.info(f"📋 Total de tipos de busca: {len(todos)}")
    for t in todos:
        logger.info(f"   - {t['nome']}: ID={t['id']}")

def verificar_estrutura_tabela():
    """Verifica a estrutura da tabela links_duckduckgo"""
    logger.info("\n🔍 Verificando estrutura da tabela links_duckduckgo...")
    
    try:
        # Verificar se a tabela existe
        result = db.execute_query(
            """SELECT COUNT(*) as count 
               FROM information_schema.tables 
               WHERE table_schema = 'avalion_painel' 
               AND table_name = 'links_duckduckgo'"""
        )
        
        if result[0]['count'] > 0:
            logger.info("✅ Tabela links_duckduckgo existe")
            
            # Verificar colunas
            colunas = db.execute_query(
                """SELECT column_name, data_type, is_nullable, column_default
                   FROM information_schema.columns
                   WHERE table_schema = 'avalion_painel' 
                   AND table_name = 'links_duckduckgo'
                   ORDER BY ordinal_position"""
            )
            
            logger.info(f"📋 Colunas da tabela ({len(colunas)} total):")
            for col in colunas:
                logger.info(f"   - {col['column_name']}: {col['data_type']} (null={col['is_nullable']})")
            
            # Contar registros
            count = db.execute_query("SELECT COUNT(*) as total FROM links_duckduckgo")
            logger.info(f"📊 Total de registros: {count[0]['total']}")
            
        else:
            logger.error("❌ Tabela links_duckduckgo NÃO existe!")
            logger.info("Criando tabela...")
            
            create_query = """
            CREATE TABLE IF NOT EXISTS links_duckduckgo (
                id INT AUTO_INCREMENT PRIMARY KEY,
                url VARCHAR(500) NOT NULL,
                plataforma_id INT,
                tipo_busca_id INT,
                estado_id INT,
                municipio_id INT,
                distrito_id INT,
                termo_busca VARCHAR(255),
                posicao_busca INT DEFAULT 0,
                processado TINYINT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_plataforma (plataforma_id),
                INDEX idx_tipo_busca (tipo_busca_id),
                INDEX idx_local (estado_id, municipio_id),
                UNIQUE KEY uk_url (url)
            )
            """
            db.execute_update(create_query)
            logger.info("✅ Tabela criada com sucesso")
            
    except Exception as e:
        logger.error(f"Erro ao verificar estrutura: {e}")

def verificar_exemplo_cidade():
    """Verifica se existe uma cidade de exemplo (Araucária)"""
    logger.info("\n🔍 Verificando cidade de exemplo (Araucária, PR)...")
    
    result = db.execute_query(
        """SELECT m.id as municipio_id, m.nome, e.id as estado_id, e.sigla 
           FROM municipios m 
           JOIN estados e ON m.estado_id = e.id 
           WHERE m.nome LIKE %s AND e.sigla = %s""",
        ("%Araucária%", "PR")
    )
    
    if result:
        logger.info(f"✅ Cidade encontrada: {result[0]['nome']}, {result[0]['sigla']}")
        logger.info(f"   IDs: município={result[0]['municipio_id']}, estado={result[0]['estado_id']}")
    else:
        logger.warning("⚠️ Cidade Araucária/PR não encontrada no banco")
        
        # Verificar se o estado PR existe
        estado = db.execute_query("SELECT id, nome, sigla FROM estados WHERE sigla = 'PR'")
        if estado:
            logger.info(f"✅ Estado PR existe: ID={estado[0]['id']}")
            
            # Buscar cidades do PR
            cidades_pr = db.execute_query(
                """SELECT nome FROM municipios 
                   WHERE estado_id = %s AND nome LIKE 'A%' 
                   ORDER BY nome LIMIT 5""",
                (estado[0]['id'],)
            )
            
            if cidades_pr:
                logger.info("📋 Algumas cidades do PR que começam com 'A':")
                for c in cidades_pr:
                    logger.info(f"   - {c['nome']}")
        else:
            logger.error("❌ Estado PR não encontrado")

def main():
    logger.info("="*70)
    logger.info("🔧 VERIFICAÇÃO E CONFIGURAÇÃO DO BANCO MARIADB")
    logger.info("="*70)
    
    verificar_plataformas()
    verificar_tipos_busca()
    verificar_estrutura_tabela()
    verificar_exemplo_cidade()
    
    logger.info("\n" + "="*70)
    logger.info("✅ Verificação concluída!")
    logger.info("="*70)

if __name__ == "__main__":
    main()