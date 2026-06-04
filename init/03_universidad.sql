-- ============================================================
-- ESCENARIO 3: Student / Class / Inscripto / Faculty
-- ============================================================

CREATE TABLE Faculty (
    fid    INTEGER PRIMARY KEY,
    fname  VARCHAR(100) NOT NULL,
    deptid INTEGER NOT NULL
);

CREATE TABLE Class (
    name     VARCHAR(100) PRIMARY KEY,
    meets_at VARCHAR(20)  NOT NULL,
    room     VARCHAR(20)  NOT NULL,
    fid      INTEGER REFERENCES Faculty(fid)
);

CREATE TABLE Student (
    snum  INTEGER PRIMARY KEY,
    sname VARCHAR(100) NOT NULL,
    major VARCHAR(50)  NOT NULL,
    level VARCHAR(10)  NOT NULL,  -- FR, SO, JR, SR
    age   INTEGER NOT NULL
);

CREATE TABLE Inscripto (
    snum  INTEGER REFERENCES Student(snum),
    cname VARCHAR(100) REFERENCES Class(name),
    PRIMARY KEY (snum, cname)
);

-- ------- DATOS -------

INSERT INTO Faculty VALUES
(10, 'I. Teach',   1),
(11, 'J. Smith',   2),
(12, 'A. Prof',    1),
(13, 'B. Doctor',  3);

-- Clases: incluir R128 (ejercicios b, h), misma hora para algún par (ejercicio c)
INSERT INTO Class VALUES
('Matematica I',   '08:00', 'R128', 10),
('Fisica I',       '10:00', 'R200', 11),
('Historia',       '08:00', 'R128', 10),  -- misma hora que Matematica I, mismo prof en R128
('Programacion',   '14:00', 'R300', 12),
('Base de Datos',  '16:00', 'R128', 13);

INSERT INTO Student VALUES
(1, 'Lucas Torres',    'Sistemas',  'JR', 20),
(2, 'Sofia Ramos',     'Sistemas',  'JR', 21),
(3, 'Mateo Vargas',    'Civil',     'SR', 22),
(4, 'Camila Diaz',     'Sistemas',  'FR', 18),
(5, 'Nicolas Perez',   'Industrial','SO', 19),
(6, 'Valentina Gil',   'Sistemas',  'SR', 23),
(7, 'Andres Rios',     'Civil',     'JR', 20),
(8, 'Lucia Mora',      'Sistemas',  'FR', 18),
(9, 'Diego Blanco',    'Industrial','SO', 19);

-- Inscripciones:
-- Lucas (JR, Sistemas) inscripto en I. Teach → Matematica I e Historia (ejercicio a)
INSERT INTO Inscripto VALUES
(1, 'Matematica I'),
(1, 'Historia'),       -- dos clases a la misma hora (ejercicio c)
(2, 'Matematica I'),
(2, 'Fisica I'),
(3, 'Fisica I'),
(3, 'Base de Datos'),
(4, 'Programacion'),
(5, 'Matematica I'),
(5, 'Historia'),       -- dos clases a la misma hora (ejercicio c)
(6, 'Base de Datos'),
(6, 'Fisica I'),
(7, 'Programacion'),
(7, 'Matematica I'),
(8, 'Matematica I');
-- Diego (9) no está inscripto en ninguna clase (ejercicio j)
