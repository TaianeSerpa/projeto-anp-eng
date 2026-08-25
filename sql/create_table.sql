CREATE TABLE IF NOT EXISTS d_produto (
    id INTEGER PRIMARY KEY,
    produto VARCHAR(255),
    unidade_medida VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS d_localizacao (
    id INTEGER PRIMARY KEY,
    estado_sigla VARCHAR(10),
    municipio VARCHAR(255),
    regiao_sigla VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS d_posto (
    id INTEGER PRIMARY KEY,
    id_localizacao INTEGER,
    cnpj_revenda VARCHAR(50),
    revenda TEXT,
    bandeira VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS f_pesquisa_preco (
    id INTEGER PRIMARY KEY,
    id_posto INTEGER,
    id_produto INTEGER,
    valor_venda NUMERIC(10, 3),
    data_coleta TIMESTAMP,
    data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);