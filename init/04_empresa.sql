-- ============================================================
-- ESCENARIO 4: Emp / Works / Dept
-- ============================================================

CREATE TABLE Emp (
    eid    INTEGER PRIMARY KEY,
    ename  VARCHAR(100) NOT NULL,
    age    INTEGER NOT NULL,
    salary REAL NOT NULL
);

CREATE TABLE Dept (
    did       INTEGER PRIMARY KEY,
    dname     VARCHAR(100) NOT NULL,
    budget    REAL NOT NULL,
    managerid INTEGER REFERENCES Emp(eid)
);

CREATE TABLE Works (
    eid      INTEGER REFERENCES Emp(eid),
    did      INTEGER REFERENCES Dept(did),
    pct_time INTEGER NOT NULL,  -- porcentaje de tiempo en ese dept
    PRIMARY KEY (eid, did)
);

-- ------- DATOS -------

INSERT INTO Emp VALUES
(201, 'Ricardo Molina',  45, 95000.00),
(202, 'Elena Castro',    38, 82000.00),
(203, 'Gustavo Reyes',   52, 110000.00),
(204, 'Patricia Vega',   41, 78000.00),
(205, 'Fernando Solis',  35, 67000.00),
(206, 'Monica Herrera',  48, 95000.00);

-- Departamentos: incluir Hardware y Software (ejercicio a)
-- Gerentes con presupuestos variados para ejercicios b,c,d,e,f
INSERT INTO Dept VALUES
(301, 'Hardware',   1200000.00, 203),  -- Gustavo gerencia Hardware ($1.2M)
(302, 'Software',   3500000.00, 203),  -- Gustavo gerencia Software ($3.5M) → total $4.7M
(303, 'Marketing',  6000000.00, 201),  -- Ricardo gerencia Marketing ($6M)
(304, 'Finanzas',    800000.00, 206);  -- Monica gerencia Finanzas ($800k < $1M)

-- Works: empleados que trabajan en múltiples departamentos
INSERT INTO Works VALUES
(201, 301, 50),  -- Ricardo en Hardware (50%)
(201, 303, 50),  -- Ricardo en Marketing (50%)
(202, 302, 100), -- Elena solo en Software
(203, 301, 30),  -- Gustavo en Hardware (30%) — es gerente
(203, 302, 70),  -- Gustavo en Software (70%) — es gerente
(204, 302, 60),  -- Patricia en Software
(204, 304, 40),  -- Patricia en Finanzas
(205, 301, 100), -- Fernando solo en Hardware
(206, 304, 100); -- Monica en Finanzas — es gerente
