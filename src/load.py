import os
import logging
import io
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from minio import Minio
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

env_path= Path(__file__).parent.parent/'.env'
load_dotenv(dotenv_path=env_path)

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")

DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URI)

def conect_minio():
    logger.info("Iniciando a Conexão com o Minio.")
    client = Minio(
        'localhost:9005',
        access_key= os.getenv("MINIO_ROOT_USER"),
        secret_key= os.getenv("MINIO_ROOT_PASSWORD"),
        secure= False,)
    return client

def ler_parquet_minio(bucket_name: str, object_name: str) -> pd.DataFrame:

    client = conect_minio()
    logger.info(f"Baixando '{object_name}' do bucket '{bucket_name}' no MinIO...")
    
    response = client.get_object(bucket_name, object_name)
    data = response.read()
    response.close()
    response.release_conn()
    
    df = pd.read_parquet(io.BytesIO(data))
    logger.info(f"Dados carregados com sucesso! Linhas: {len(df)}")
    return df

def executar_script_ddl(caminho_sql:str):
    logger.info(f"Executando script DDL: {caminho_sql}")
    try:
        with open(caminho_sql,"r",encoding="UTF-8") as f:
            comandos_sql = f.read()

        with engine.begin() as conexao:
            conexao.execute(text(comandos_sql))
        logger.info("Tabelas criadas/verificadas com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao executar DDL: {e}")
        raise e

def criar_dimensoes_e_fato(df_prata: pd.DataFrame):
    logger.info("Iniciando modelagem dimensional (SNOWFLAKE Schema)...")
    df_d_produto = (
        df_prata[["produto", "unidade_medida"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    df_d_produto["id_produto"] = df_d_produto.index + 1

    df_prata = df_prata.merge(
        df_d_produto,
        on = ["produto", "unidade_medida"],
        how = "left"
    )

    df_d_localizacao = (
        df_prata[["estado_sigla","municipio","regiao_sigla"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    df_d_localizacao["id_localizacao"] = df_d_localizacao.index + 1

    df_prata = df_prata.merge(
        df_d_localizacao,
        on=["estado_sigla","municipio","regiao_sigla"],
        how= "left"
    )

    df_d_posto = (
        df_prata[["cnpj_revenda","revenda","bandeira","id_localizacao"]]
        .drop_duplicates()
        .reset_index(drop=True)
                    )
    df_d_posto["id_posto"] = df_d_posto.index + 1

    df_prata = df_prata.merge(
        df_d_posto,
        on = ["cnpj_revenda","revenda","bandeira","id_localizacao"],
        how = "left"
    )

    df_f_pesquisa_preco = (
        df_prata[["id_posto","id_produto","valor_venda","data_coleta","data_processamento"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    df_f_pesquisa_preco["id"] = df_f_pesquisa_preco.index + 1

    df_prata = df_prata.merge(
        df_f_pesquisa_preco,
        on = ["id_posto","id_produto","valor_venda","data_coleta","data_processamento"],
        how= "left"
    )

    df_d_produto = df_d_produto.rename(columns={"id_produto": "id"})
    df_d_localizacao = df_d_localizacao.rename(columns={"id_localizacao": "id"})
    df_d_posto = df_d_posto.rename(columns={"id_posto": "id"})
    logger.info("Modelagem dimensional concluída com sucesso.")
    return df_d_produto, df_d_localizacao, df_d_posto, df_f_pesquisa_preco

def carregar_tabela(df: pd.DataFrame, nome_tabela: str):
    try:
        logger.info(f"Carregando {len(df):,} registros na tabela '{nome_tabela}'...")
        df.to_sql (
            name = nome_tabela,
            con= engine,
            if_exists="append",
            index=False,
            chunksize=1000,
            method="multi" )
        logger.info(f"Tabela '{nome_tabela}' carregada com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao carregar '{nome_tabela}': {e}")
        raise e

def pipeline_load(
    bucket_name: str = "dados-anp",
    object_name: str = "silver/anp_combustiveis_consolidado.parquet",
    caminho_sql: str = "sql/create_table.sql"
):

    logger.info("INICIANDO PIPELINE DE CARGA (GOLD / DW)")
    

    executar_script_ddl(caminho_sql)

   
    df_prata = ler_parquet_minio(bucket_name, object_name)

  
    dim_produto, dim_localizacao, dim_posto, fato_preco = criar_dimensoes_e_fato(df_prata)

   
    carregar_tabela(dim_localizacao, "d_localizacao")
    carregar_tabela(dim_produto, "d_produto")
    carregar_tabela(dim_posto, "d_posto")

    
    carregar_tabela(fato_preco, "f_pesquisa_preco")

    
    logger.info("PIPELINE GOLD FINALIZADO COM SUCESSO!")
    

if __name__ == "__main__":
    pipeline_load()