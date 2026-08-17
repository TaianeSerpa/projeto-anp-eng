import os
import io
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from minio import Minio
from datetime import datetime

env_path= Path(__file__).parent.parent/'.env'
load_dotenv(dotenv_path=env_path)


def conect_minio():
    print("Iniciando a Conexão com o Minio.")
    client = Minio(
        'localhost:9005',
        access_key= os.getenv("MINIO_ROOT_USER"),
        secret_key= os.getenv("MINIO_ROOT_PASSWORD"),
        secure= False,)

    bucket_nome = "dados-anp"
    print("Buscando a lista de objetos dentro da pasta.")
    object = list(client.list_objects(bucket_name=bucket_nome, recursive=True))
    print(f"Foram encontrados {len(object)} arquivos na pasta Bronze.")
    for obj in object:
        print(obj.object_name)
    return client, object, bucket_nome

def ler_csv(client,bucket_nome,lista_objetos):
    lista_csv = []

    for obj in lista_objetos:
        response = client.get_object(bucket_nome, obj.object_name)

        df_bruto = pd.read_csv(
        io.BytesIO(response.read()), sep=';', encoding='latin1', low_memory=False) 

        response.close()
        lista_csv.append(df_bruto)
    return lista_csv

def padroniza_colunas(lista_csv):
     print("Iniciando a padronização das Colunas.")
     lista_padronizadas = []

     for i,df in enumerate(lista_csv, start=1):
          print(f"  -> Processando arquivo {i} de {len(lista_csv)}")
          df_renomeado = df.rename(columns={
              'ï»¿Regiao - Sigla': 'regiao_sigla',
              'Regiao - Sigla' : 'regiao_sigla',
              'Estado - Sigla' : 'estado_sigla',
              'Municipio' : 'municipio',
              'Revenda': 'revenda',
              'CNPJ da Revenda': 'cnpj_revenda',
              'Nome da Rua' : 'nome_rua',
              'Numero Rua' : 'numero_rua',
              'Complemento' : 'complemento',
              'Bairro' : 'bairro',
              'Cep' : 'cep',
              'Produto' : 'produto',
              'Data da Coleta' : 'data_coleta',
              'Valor de Venda' : 'valor_venda',
              'Valor de Compra' : 'valor_compra',
              'Unidade de Medida' : 'unidade_medida',
              'Bandeira' : 'bandeira'
           })
          print("Removendo a Coluna 'valor_compra'")
          df_renomeado = df_renomeado.drop(columns=['valor_compra'], errors='ignore')
          print("Coluna valor_compra removida com sucesso!")
          
          lista_padronizadas.append(df_renomeado)
          print("Padronização de colunas concluída com sucesso!")
     return lista_padronizadas 

def tratar_valores_nulos(lista_colunas):
    print("Iniciando o tratamento de valores nulos...")
    lista_nulos_tratados = []

    for i, df in enumerate(lista_colunas, start=1):
        print(f"  -> Tratando nulos no arquivo {i} de {len(lista_colunas)}")

        df = df.dropna(subset=['valor_venda'])

        if 'complemento' in df.columns:
            df['complemento'] = df['complemento'].fillna('NÃO INFORMADO')

        if 'numero_rua' in df.columns:
            df['numero_rua'] = df['numero_rua'].fillna('S/N')

        if 'bairro' in df.columns:
            df['bairro'] = df['bairro'].fillna('NÃO INFORMADO')

        lista_nulos_tratados.append(df)

    print("Tratamento de nulos concluído com sucesso!")
    return lista_nulos_tratados


def altera_coluna(lista_padronizadas):
    print("Inicando a alteração de tipo de coluna")
    lista_colunas = []

    for i,df in enumerate(lista_padronizadas, start=1):
        print(f"  -> Processando arquivo {i} de {len(lista_padronizadas)}")

        df["valor_venda"] = df["valor_venda"].str.replace(",",".").astype(float)

        df["data_coleta"] = pd.to_datetime(df["data_coleta"], format = "%d/%m/%Y")

        if "cnpj_revenda" in df.columns:
            df["cnpj_revenda"] = df["cnpj_revenda"].astype(str)

        lista_colunas.append(df)
    print("Alterações de tipos concluída!")
    return lista_colunas


def tratar_textos(lista_colunas):
    print("Iniciando a normalização de textos")
    lista_final = []

    colunas_texto = ['produto', 'municipio', 'estado_sigla', 'bandeira', 'revenda']
    for i, df in enumerate(lista_colunas):
        print(f"-> Normalizando textos no arquivo {i} de {len(lista_colunas)}")

        for coluna in colunas_texto:
            if coluna in df.columns:
                df[coluna] = df[coluna].str.strip().str.upper()
        lista_final.append(df)
    print("Normalização de textos concluída com sucesso!")
    return lista_final


def consolidar_camada_silver(lista_final):
    df_silver = pd.concat(lista_final, ignore_index=True)

    df_silver["data_processamento"] = datetime.now()

    print(f"Camada Silver consolidada com sucesso! Total de linhas: {len(df_silver)}")
    return df_silver

def subir_arquivo(df_silver, bucket_nome,client):
    nome_arquivo = "anp_combustiveis_consolidado.parquet"

    df_silver.to_parquet(nome_arquivo, engine='pyarrow', compression='snappy')

    print(f"Subindo {nome_arquivo} para o Minio.")
    client.fput_object(
        bucket_nome,
        f"silver/{nome_arquivo}",
        nome_arquivo
    )
    print(f"Arquivo {nome_arquivo} enviado com sucesso para a camada Silver!")

    if os.path.exists(nome_arquivo):
        os.remove(nome_arquivo)

def main():
   
    client, lista_objetos, bucket_nome = conect_minio()

    lista_csv = ler_csv(client, bucket_nome, lista_objetos)

    
    lista_padronizada = padroniza_colunas(lista_csv)
    lista_sem_nulos   = tratar_valores_nulos(lista_padronizada)
    lista_tipada      = altera_coluna(lista_sem_nulos)
    lista_final       = tratar_textos(lista_tipada)

    
    df_silver = consolidar_camada_silver(lista_final)

    
    subir_arquivo(df_silver, bucket_nome, client)


if __name__ == "__main__":
    main()


