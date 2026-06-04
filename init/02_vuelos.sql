-- ============================================================
-- ESCENARIO 2: Vuelos / Avion / Certificados / Empleados
-- ============================================================

CREATE TABLE Avion (
    aid           INTEGER PRIMARY KEY,
    aname         VARCHAR(100) NOT NULL,
    cruisingrange INTEGER NOT NULL
);

CREATE TABLE Empleados (
    eid    INTEGER PRIMARY KEY,
    ename  VARCHAR(100) NOT NULL,
    salary INTEGER NOT NULL
);

CREATE TABLE Vuelos (
    flno      INTEGER PRIMARY KEY,
    from_city VARCHAR(100) NOT NULL,
    to_city   VARCHAR(100) NOT NULL,
    distance  INTEGER NOT NULL,
    departs   TIME NOT NULL,
    arrives   TIME NOT NULL
);

CREATE TABLE Certificados (
    eid INTEGER REFERENCES Empleados(eid),
    aid INTEGER REFERENCES Avion(aid),
    PRIMARY KEY (eid, aid)
);

-- ------- DATOS -------

INSERT INTO Avion VALUES
(1,  'Boeing 737',    3500),
(2,  'Boeing 777',    8000),
(3,  'Airbus A320',   3200),
(4,  'Airbus A380',   9000),
(5,  'Cessna 172',     800),
(6,  'Boeing 747',    8500);

INSERT INTO Empleados VALUES
(101, 'Carlos Gomez',   120000),
(102, 'Maria Lopez',     95000),
(103, 'Juan Perez',     150000),
(104, 'Ana Fernandez',   85000),
(105, 'Pedro Ruiz',     150000),
(106, 'Laura Diaz',      72000);

-- Vuelos: incluir Bonn→Madras distance ~6000 km (ejercicio c)
INSERT INTO Vuelos VALUES
(1001, 'Buenos Aires', 'Madrid',      9800, '08:00', '22:00'),
(1002, 'Bonn',         'Madras',      7500, '10:00', '23:00'),
(1003, 'Paris',        'New York',    5800, '09:00', '19:00'),
(1004, 'Madrid',       'Buenos Aires',9800, '14:00', '04:00'),
(1005, 'New York',     'Los Angeles', 2800, '06:00', '09:00'),
(1006, 'Bonn',         'Sydney',     16000, '07:00', '15:00'),
(1007, 'Tokyo',        'Los Angeles', 8800, '11:00', '07:00'),
(1008, 'Buenos Aires', 'Lima',        3100, '15:00', '18:00');

-- Certificados: pilotos con aviones Boeing y no Boeing
-- Carlos (101): Boeing 737, Boeing 777, A320 — certificado para 3 aviones
INSERT INTO Certificados VALUES
(101, 1), (101, 2), (101, 3);

-- Maria (102): solo A320 y A380 — NO certificada para Boeing
INSERT INTO Certificados VALUES
(102, 3), (102, 4);

-- Juan (103): Boeing 747, Boeing 737 — certificado para 2 aviones
INSERT INTO Certificados VALUES
(103, 6), (103, 1);

-- Ana (104): Cessna 172 — rango menor a 3000
INSERT INTO Certificados VALUES
(104, 5);

-- Pedro (105): A380, Boeing 777, Boeing 747, A320 — certificado para 4 aviones
INSERT INTO Certificados VALUES
(105, 4), (105, 2), (105, 6), (105, 3);

-- Laura (106): ningún certificado (empleada no piloto)
