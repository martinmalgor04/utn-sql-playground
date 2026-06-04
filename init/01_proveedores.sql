-- ============================================================
-- ESCENARIO 1: Proveedores / Parts / Catalog
-- ============================================================

CREATE TABLE Proveedores (
    sid     INTEGER PRIMARY KEY,
    sname   VARCHAR(100) NOT NULL,
    address VARCHAR(200) NOT NULL
);

CREATE TABLE Parts (
    pid     INTEGER PRIMARY KEY,
    pname   VARCHAR(100) NOT NULL,
    color   VARCHAR(50)  NOT NULL
);

CREATE TABLE Catalog (
    sid     INTEGER REFERENCES Proveedores(sid),
    pid     INTEGER REFERENCES Parts(pid),
    cost    REAL NOT NULL,
    PRIMARY KEY (sid, pid)
);

-- ------- DATOS -------

INSERT INTO Proveedores VALUES
(1, 'Yosemite Sham',   '221 Packer Street'),
(2, 'Supply Co',       '10 Main Ave'),
(3, 'Parts Plus',      '99 Industrial Blvd'),
(4, 'RedGreen Ltd',    '45 Commerce St'),
(5, 'AllParts Inc',    '7 Warehouse Rd'),
(6, 'CheapParts',      '33 Budget Lane');

INSERT INTO Parts VALUES
(101, 'Tuerca',      'roja'),
(102, 'Tornillo',    'verde'),
(103, 'Arandela',    'azul'),
(104, 'Perno',       'roja'),
(105, 'Clavo',       'verde'),
(106, 'Resorte',     'azul'),
(107, 'Engranaje',   'roja'),
(108, 'Palanca',     'verde');

-- Yosemite Sham (sid=1) provee varias partes a distintos precios
INSERT INTO Catalog VALUES
(1, 101, 150.00),
(1, 102, 220.00),
(1, 103,  80.00),
(1, 104, 310.00),
(1, 105, 190.00);

-- Supply Co (sid=2): solo partes rojas y verdes, todas bajo $200
INSERT INTO Catalog VALUES
(2, 101, 180.00),
(2, 102, 195.00),
(2, 104, 175.00);

-- Parts Plus (sid=3): provee TODAS las partes (necesario para ej 5)
INSERT INTO Catalog VALUES
(3, 101,  90.00),
(3, 102, 110.00),
(3, 103, 130.00),
(3, 104, 120.00),
(3, 105, 140.00),
(3, 106, 100.00),
(3, 107, 115.00),
(3, 108, 125.00);

-- RedGreen Ltd (sid=4): provee todas las partes rojas (101,104,107)
INSERT INTO Catalog VALUES
(4, 101, 200.00),
(4, 104, 210.00),
(4, 107, 230.00),
(4, 102,  95.00);

-- AllParts Inc (sid=5): parte roja más cara que algún otro proveedor
INSERT INTO Catalog VALUES
(5, 101, 500.00),
(5, 103,  75.00),
(5, 106,  85.00);

-- CheapParts (sid=6): todas las partes verdes (102, 105, 108)
INSERT INTO Catalog VALUES
(6, 102, 105.00),
(6, 105,  99.00),
(6, 108, 110.00),
(6, 101, 155.00);
