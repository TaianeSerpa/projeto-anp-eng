import requests
import os
import zipfile
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from minio import Minio

env_path= Path(__file__).parent.parent/'.env'
load_dotenv(dotenv_path=env_path)

url_pagina = os.getenv("URL")
Lista_ano = ["2020","2021","2022","2022.1","2023","2024","2025"]

def conect_minio():
    os.makedirs("dados_anp/bronze" ,exist_ok=True)
    client = Minio(
        'localhost:9005',
        access_key= os.getenv("MINIO_ROOT_USER"),
        secret_key= os.getenv("MINIO_ROOT_PASSWORD"),
        secure= False)

    bucket_nome = 'dados-anp'.strip()
    if not client.bucket_exists(bucket_nome):
        client.make_bucket(bucket_nome, location="us-east-1")
    return client, bucket_nome

def busca_link_anp(url_pagina, Lista_ano):
    print("Inicando o processo de Extract...")

    reposta = requests.get(url_pagina,verify=False)
    soup = BeautifulSoup(reposta.text, 'html.parser')

    links_csv = []

    for link in soup.find_all('a', href=True):
        url = link['href']
        if url.endswith(('.csv', '.zip')):
            if "/ca" in url:
                tem_ano = any(ano in url for ano in Lista_ano)

                arquivo_2022 = ("precos-semestrais-ca" in url.lower())
                if tem_ano or arquivo_2022:
                    links_csv.append(url)
    links_csv = list(set(links_csv))
    
    print(f"Encontrados {len(links_csv)} arquivos para Download.")
    return links_csv

def baixar_e_subir_arquivo(links_csv,bucket_nome,client):
    for url in links_csv:
        nome_arquivo = url.split('/')[-1]
        caminho_final = os.path.join("dados_anp/bronze",nome_arquivo)

        print(f"Iniciando Download:{nome_arquivo}")

        try:
            conteudo = requests.get(url, verify=False).content
            with open(caminho_final,"wb") as f:
                f.write(conteudo)
            if nome_arquivo.endswith('.zip'):
                print(f"Descompactando arquivo zip:{nome_arquivo}")

                pasta_destino = 'dados_anp/bronze'
                with zipfile.ZipFile(caminho_final,'r') as zip_referencia:
                    arquivo_extraido = zip_referencia.namelist()
                    zip_referencia.extractall(pasta_destino)
                
                for arquivo_csv in arquivo_extraido:
                    caminho_csv_extraido = os.path.join(pasta_destino, arquivo_csv)

                    print(f"Subindo {arquivo_csv} para o MinIO")
                    client.fput_object(
                        bucket_nome,
                        f"bronze/{arquivo_csv}",
                        caminho_csv_extraido)
                    
                os.remove(caminho_final)
                print(f"Arquivo zip {nome_arquivo} removido da máquina local.")
                    
            else:
                print(f"Subindo {nome_arquivo} para o Minio.")
                client.fput_object(
                    bucket_nome,
                    f"bronze/{nome_arquivo}",
                    caminho_final)

        except Exception as e:
            print(f"Erro ao fazer o download {nome_arquivo}: {e}")


if __name__ == "__main__":
    minio_client,bucket = conect_minio()

    lista_de_links = busca_link_anp(url_pagina, Lista_ano)

    baixar_e_subir_arquivo(lista_de_links,bucket,minio_client)

print("\nConcluído!Todos os arquivos estão na pasta 'dados_anp'")








