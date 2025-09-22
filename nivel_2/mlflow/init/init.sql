-- Borrar si ya existe
DROP TABLE IF EXISTS credit_data;

-- Crear tabla
CREATE TABLE credit_data (
    id INTEGER PRIMARY KEY,
    age INTEGER,
    income FLOAT,
    education_level VARCHAR(50),
    credit_score INTEGER
);

-- Importar datos desde CSV
COPY credit_data(id, age, income, education_level, credit_score)
FROM '/docker-entrypoint-initdb.d/sample_data.csv'
DELIMITER ','
CSV HEADER;
