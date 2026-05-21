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
    telefono VARCHAR(30) NULL,
    fecha_reserva DATE NULL,
    asiento VARCHAR(8) NULL,
    metodo_pago VARCHAR(30) NULL,
    estado_pago VARCHAR(20) NOT NULL DEFAULT 'pagado',
    UNIQUE KEY idx_reservas_ruta_asiento (ruta_id, asiento),
    FOREIGN KEY (ruta_id) REFERENCES rutas(id)
);

INSERT INTO rutas (id, origen, destino, capacidad) VALUES
    ('751fb729-eebd-4798-9c8d-fa87edb90adc', 'Cartago', 'Cerritos', 1),
    ('8845b5d3-f9bb-4051-bd21-b484141e2332', 'Bogota', 'Medellin', 40),
    ('9d921ee0-8677-4805-8d55-18c029174661', 'Cartago', 'Pereira', 4),
    ('b2534bed-d3c4-4053-bce3-9441e1eeb936', 'Pereira', 'Medellin', 20),
    ('bd802dc3-3a52-45d5-97fe-123d415968cf', 'prueba', 'prueba', 1),
    ('c53df87f-a145-4906-8933-072f96791598', 'Bogota', 'Medellin', 2)
ON DUPLICATE KEY UPDATE
    origen = VALUES(origen),
    destino = VALUES(destino),
    capacidad = VALUES(capacidad);
