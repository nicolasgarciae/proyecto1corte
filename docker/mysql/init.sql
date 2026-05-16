CREATE TABLE IF NOT EXISTS rutas (
    id VARCHAR(36) PRIMARY KEY,
    origen VARCHAR(100) NOT NULL,
    destino VARCHAR(100) NOT NULL,
    capacidad INT NOT NULL
);

CREATE TABLE IF NOT EXISTS reservas (
    id VARCHAR(36) PRIMARY KEY,
    nombre_pasajero VARCHAR(100) NOT NULL,
    ruta_id VARCHAR(36) NOT NULL,
    FOREIGN KEY (ruta_id) REFERENCES rutas(id)
);
