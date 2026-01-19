DROP SCHEMA IF EXISTS `flytau`;
CREATE SCHEMA IF NOT EXISTS `flytau` DEFAULT CHARACTER SET utf8;
USE `flytau`;

-- =========================
-- 1) CUSTOMER & PHONE
-- =========================
CREATE TABLE `customer` (
  `email` VARCHAR(45) NOT NULL,
  `first_name` VARCHAR(45) NULL,
  `last_name` VARCHAR(45) NULL,
  PRIMARY KEY (`email`)
) ENGINE = InnoDB;

CREATE TABLE `customer_phone_number` (
  `email` VARCHAR(45) NOT NULL,
  `phone_number` INT NOT NULL,
  PRIMARY KEY (`email`, `phone_number`),
  CONSTRAINT `fk_phone_email` FOREIGN KEY (`email`) REFERENCES `customer` (`email`)
) ENGINE = InnoDB;

CREATE TABLE `registered_customer` (
  `email` VARCHAR(45) NULL,
  `password` VARCHAR(45) NULL,
  `passport_number` INT NOT NULL,
  `date_of_birth` DATE NULL,
  `registration_date` DATE NULL,
  PRIMARY KEY (`passport_number`),
  CONSTRAINT `fk_reg_cust_email` FOREIGN KEY (`email`) REFERENCES `customer` (`email`)
) ENGINE = InnoDB;

-- =========================
-- 2) EMPLOYEES
-- =========================
CREATE TABLE `manager` (
  `id_number` INT NOT NULL,
  `first_name` VARCHAR(45) NULL,
  `last_name` VARCHAR(45) NULL,
  `city` VARCHAR(45) NULL,
  `street` VARCHAR(45) NULL,
  `house_number` INT NULL,
  `phone_number` INT NULL,
  `employment_start_date` DATE NULL,
  `password` VARCHAR(45) NULL,
  PRIMARY KEY (`id_number`)
) ENGINE = InnoDB;

CREATE TABLE `pilot` (
  `id_number` INT NOT NULL,
  `first_name` VARCHAR(45) NULL,
  `last_name` VARCHAR(45) NULL,
  `city` VARCHAR(45) NULL,
  `street` VARCHAR(45) NULL,
  `house_number` INT NULL,
  `phone_number` INT NULL,
  `employment_start_date` DATE NULL,
  `long_flight_certification` TINYINT(1) NULL,
  PRIMARY KEY (`id_number`)
) ENGINE = InnoDB;

CREATE TABLE `flight_attendant` (
  `id_number` INT NOT NULL,
  `first_name` VARCHAR(45) NULL,
  `last_name` VARCHAR(45) NULL,
  `city` VARCHAR(45) NULL,
  `street` VARCHAR(45) NULL,
  `house_number` INT NULL,
  `phone_number` INT NULL,
  `employment_start_date` DATE NULL,
  `long_flight_certification` TINYINT(1) NULL,
  PRIMARY KEY (`id_number`)
) ENGINE = InnoDB;

-- =========================
-- 3) INFRASTRUCTURE & SEATS
-- =========================
CREATE TABLE `aircraft` (
  `aircraft_id_number` INT NOT NULL,
  `size` VARCHAR(45) NULL,
  `manufacturer` VARCHAR(45) NULL,
  `purchase_date` DATE NULL,
  PRIMARY KEY (`aircraft_id_number`)
) ENGINE = InnoDB;

CREATE TABLE `class` (
  `aircraft_id_number` INT NOT NULL,
  `type` VARCHAR(45) NOT NULL,
  `number_of_rows` INT NULL,
  `number_of_columns` INT NULL,
  PRIMARY KEY (`aircraft_id_number`, `type`),
  CONSTRAINT `fk_class_air` FOREIGN KEY (`aircraft_id_number`) REFERENCES `aircraft` (`aircraft_id_number`)
) ENGINE = InnoDB;

CREATE TABLE `seat` (
  `aircraft_id_number` INT NOT NULL,
  `class_type` VARCHAR(45) NOT NULL,
  `row_number` INT NOT NULL,
  `column_number` INT NOT NULL,
  PRIMARY KEY (`aircraft_id_number`, `class_type`, `row_number`, `column_number`),
  CONSTRAINT `fk_seat_cls` FOREIGN KEY (`aircraft_id_number`, `class_type`) REFERENCES `class` (`aircraft_id_number`, `type`)
) ENGINE = InnoDB;

CREATE TABLE `airport` (
  `airport_name` VARCHAR(45) NOT NULL,
  `country` VARCHAR(45) NULL,
  PRIMARY KEY (`airport_name`)
) ENGINE = InnoDB;

CREATE TABLE `flight_route` (
  `origin_airport` VARCHAR(45) NOT NULL,
  `destination_airport` VARCHAR(45) NOT NULL,
  `flight_duration` INT NULL,
  PRIMARY KEY (`origin_airport`, `destination_airport`),
  CONSTRAINT `fk_rt_org` FOREIGN KEY (`origin_airport`) REFERENCES `airport` (`airport_name`),
  CONSTRAINT `fk_rt_dst` FOREIGN KEY (`destination_airport`) REFERENCES `airport` (`airport_name`)
) ENGINE = InnoDB;

-- =========================
-- 4) FLIGHTS & NEW PRICING TABLE
-- =========================
CREATE TABLE `flight` (
  `flight_number` INT NOT NULL,
  `aircraft_id_number` INT NULL,
  `origin_airport` VARCHAR(45) NULL,
  `destination_airport` VARCHAR(45) NULL,
  `departure_datetime` DATETIME NULL,
  `status` VARCHAR(45) NULL,
  PRIMARY KEY (`flight_number`),
  CONSTRAINT `fk_fl_air` FOREIGN KEY (`aircraft_id_number`) REFERENCES `aircraft` (`aircraft_id_number`),
  CONSTRAINT `fk_fl_rt` FOREIGN KEY (`origin_airport`, `destination_airport`) REFERENCES `flight_route` (`origin_airport`, `destination_airport`)
) ENGINE = InnoDB;

-- הטבלה החדשה שביקשת
CREATE TABLE `seats_in_flights` (
  `aircraft_id_number` INT NOT NULL,
  `class_type` VARCHAR(45) NOT NULL,
  `row_number` INT NOT NULL,
  `column_number` INT NOT NULL,
  `flight_number` INT NOT NULL,
  `price` FLOAT NULL,
  PRIMARY KEY (`aircraft_id_number`, `class_type`, `row_number`, `column_number`, `flight_number`),
  CONSTRAINT `fk_sif_seat` FOREIGN KEY (`aircraft_id_number`, `class_type`, `row_number`, `column_number`) REFERENCES `seat` (`aircraft_id_number`, `class_type`, `row_number`, `column_number`),
  CONSTRAINT `fk_sif_fl` FOREIGN KEY (`flight_number`) REFERENCES `flight` (`flight_number`)
) ENGINE = InnoDB;

-- =========================
-- 5) CREW ON FLIGHTS
-- =========================
CREATE TABLE `flight_attendants_on_flights` (
  `id_number` INT NOT NULL,
  `flight_number` INT NOT NULL,
  PRIMARY KEY (`id_number`, `flight_number`),
  CONSTRAINT `fk_fa_fl` FOREIGN KEY (`id_number`) REFERENCES `flight_attendant` (`id_number`),
  CONSTRAINT `fk_faf_fl` FOREIGN KEY (`flight_number`) REFERENCES `flight` (`flight_number`)
) ENGINE = InnoDB;

CREATE TABLE `pilots_on_flights` (
  `id_number` INT NOT NULL,
  `flight_number` INT NOT NULL,
  PRIMARY KEY (`id_number`, `flight_number`),
  CONSTRAINT `fk_p_fl` FOREIGN KEY (`id_number`) REFERENCES `pilot` (`id_number`),
  CONSTRAINT `fk_pf_fl` FOREIGN KEY (`flight_number`) REFERENCES `flight` (`flight_number`)
) ENGINE = InnoDB;

-- =========================
-- 6) RESERVATIONS
-- =========================
CREATE TABLE `reservations` (
  `reservation_code` INT NOT NULL,
  `reservations_status` VARCHAR(45) NULL,
  `reservation_date` DATE NULL,
  `total_payment` FLOAT NULL,
  `email` VARCHAR(45) NULL,
  `flight_number` INT NULL,
  PRIMARY KEY (`reservation_code`),
  CONSTRAINT `fk_res_em` FOREIGN KEY (`email`) REFERENCES `customer` (`email`),
  CONSTRAINT `fk_res_fl` FOREIGN KEY (`flight_number`) REFERENCES `flight` (`flight_number`)
) ENGINE = InnoDB;

CREATE TABLE `seats_in_reservation` (
  `reservation_code` INT NOT NULL,
  `aircraft_id_number` INT NOT NULL,
  `class_type` VARCHAR(45) NOT NULL,
  `row_number` INT NOT NULL,
  `column_number` INT NOT NULL,
  PRIMARY KEY (`reservation_code`, `aircraft_id_number`, `class_type`, `row_number`, `column_number`),
  CONSTRAINT `fk_sir_r` FOREIGN KEY (`reservation_code`) REFERENCES `reservations` (`reservation_code`),
  CONSTRAINT `fk_sir_s` FOREIGN KEY (`aircraft_id_number`, `class_type`, `row_number`, `column_number`) REFERENCES `seat` (`aircraft_id_number`, `class_type`, `row_number`, `column_number`)
) ENGINE = InnoDB;

USE `flytau`;


-- ============================================================
-- DATA LOAD
-- ============================================================

-- 1) AIRPORTS (10)
INSERT INTO `airport` (`airport_name`, `country`) VALUES
('TLV','Israel'),
('LCA','Cyprus'),
('ATH','Greece'),
('IST','Turkey'),
('DXB','UAE'),
('LHR','UK'),
('CDG','France'),
('JFK','USA'),
('FCO','Italy'),
('AMS','Netherlands');

-- 2) FLIGHT ROUTES (15)
INSERT INTO `flight_route` (`origin_airport`,`destination_airport`,`flight_duration`) VALUES
('TLV','LCA',60),
('TLV','ATH',150),
('TLV','IST',120),
('TLV','DXB',210),
('TLV','CDG',270),
('TLV','LHR',330),
('TLV','FCO',190),
('TLV','AMS',270),
('ATH','TLV',150),
('DXB','TLV',210),
('CDG','TLV',270),
('LHR','TLV',330),
('FCO','TLV',190),
('TLV','JFK',660),
('JFK','TLV',650);

-- 3) AIRCRAFT (21)
INSERT INTO `aircraft` (`aircraft_id_number`,`size`,`manufacturer`,`purchase_date`) VALUES
(1001,'LARGE','AIRBUS','2019-03-15'),
(1002,'LARGE','AIRBUS','2020-06-20'),
(1003,'LARGE','AIRBUS','2021-09-10'),
(1101,'SMALL','AIRBUS','2022-01-12'),
(1102,'SMALL','AIRBUS','2022-02-18'),
(1103,'SMALL','AIRBUS','2022-04-05'),
(1104,'SMALL','AIRBUS','2023-07-22'),
(1105,'SMALL','AIRBUS','2023-11-30'),

(2001,'LARGE','DASSAULT','2018-05-03'),
(2002,'LARGE','DASSAULT','2020-12-14'),
(2101,'SMALL','DASSAULT','2021-08-08'),
(2102,'SMALL','DASSAULT','2022-05-17'),
(2103,'SMALL','DASSAULT','2023-01-29'),
(2104,'SMALL','DASSAULT','2023-09-13'),

(3001,'LARGE','BOEING','2017-02-11'),
(3002,'LARGE','BOEING','2018-10-21'),
(3003,'LARGE','BOEING','2019-12-02'),
(3004,'LARGE','BOEING','2021-03-26'),
(3005,'LARGE','BOEING','2024-04-19'),
(3101,'SMALL','BOEING','2022-10-10'),
(3102,'SMALL','BOEING','2024-01-08');

-- 4) CLASSES
INSERT INTO `class` (`aircraft_id_number`,`type`,`number_of_rows`,`number_of_columns`) VALUES
(1001,'ECONOMY',5,4),
(1001,'BUSINESS',2,4),

(1002,'ECONOMY',5,4),
(1002,'BUSINESS',2,4),

(3001,'ECONOMY',5,4),
(3001,'BUSINESS',2,4),

(1101,'ECONOMY',3,4),
(2101,'ECONOMY',3,4),
(3101,'ECONOMY',3,4),

-- aircraft 2001 (כמו שביקשת)
(2001,'ECONOMY',5,4),
(2001,'BUSINESS',2,4);

-- 5) SEATS (ללא מחיר)
-- 1001
INSERT INTO `seat` (`aircraft_id_number`,`class_type`,`row_number`,`column_number`) VALUES
(1001,'ECONOMY',1,1),(1001,'ECONOMY',1,2),(1001,'ECONOMY',1,3),(1001,'ECONOMY',1,4),
(1001,'ECONOMY',2,1),(1001,'ECONOMY',2,2),(1001,'ECONOMY',2,3),(1001,'ECONOMY',2,4),
(1001,'ECONOMY',3,1),(1001,'ECONOMY',3,2),(1001,'ECONOMY',3,3),(1001,'ECONOMY',3,4),
(1001,'ECONOMY',4,1),(1001,'ECONOMY',4,2),(1001,'ECONOMY',4,3),(1001,'ECONOMY',4,4),
(1001,'ECONOMY',5,1),(1001,'ECONOMY',5,2),(1001,'ECONOMY',5,3),(1001,'ECONOMY',5,4),
(1001,'BUSINESS',1,1),(1001,'BUSINESS',1,2),(1001,'BUSINESS',1,3),(1001,'BUSINESS',1,4),
(1001,'BUSINESS',2,1),(1001,'BUSINESS',2,2),(1001,'BUSINESS',2,3),(1001,'BUSINESS',2,4);

-- 1002
INSERT INTO `seat` (`aircraft_id_number`,`class_type`,`row_number`,`column_number`) VALUES
(1002,'ECONOMY',1,1),(1002,'ECONOMY',1,2),(1002,'ECONOMY',1,3),(1002,'ECONOMY',1,4),
(1002,'ECONOMY',2,1),(1002,'ECONOMY',2,2),(1002,'ECONOMY',2,3),(1002,'ECONOMY',2,4),
(1002,'ECONOMY',3,1),(1002,'ECONOMY',3,2),(1002,'ECONOMY',3,3),(1002,'ECONOMY',3,4),
(1002,'ECONOMY',4,1),(1002,'ECONOMY',4,2),(1002,'ECONOMY',4,3),(1002,'ECONOMY',4,4),
(1002,'ECONOMY',5,1),(1002,'ECONOMY',5,2),(1002,'ECONOMY',5,3),(1002,'ECONOMY',5,4),
(1002,'BUSINESS',1,1),(1002,'BUSINESS',1,2),(1002,'BUSINESS',1,3),(1002,'BUSINESS',1,4),
(1002,'BUSINESS',2,1),(1002,'BUSINESS',2,2),(1002,'BUSINESS',2,3),(1002,'BUSINESS',2,4);

-- 3001
INSERT INTO `seat` (`aircraft_id_number`,`class_type`,`row_number`,`column_number`) VALUES
(3001,'ECONOMY',1,1),(3001,'ECONOMY',1,2),(3001,'ECONOMY',1,3),(3001,'ECONOMY',1,4),
(3001,'ECONOMY',2,1),(3001,'ECONOMY',2,2),(3001,'ECONOMY',2,3),(3001,'ECONOMY',2,4),
(3001,'ECONOMY',3,1),(3001,'ECONOMY',3,2),(3001,'ECONOMY',3,3),(3001,'ECONOMY',3,4),
(3001,'ECONOMY',4,1),(3001,'ECONOMY',4,2),(3001,'ECONOMY',4,3),(3001,'ECONOMY',4,4),
(3001,'ECONOMY',5,1),(3001,'ECONOMY',5,2),(3001,'ECONOMY',5,3),(3001,'ECONOMY',5,4),
(3001,'BUSINESS',1,1),(3001,'BUSINESS',1,2),(3001,'BUSINESS',1,3),(3001,'BUSINESS',1,4),
(3001,'BUSINESS',2,1),(3001,'BUSINESS',2,2),(3001,'BUSINESS',2,3),(3001,'BUSINESS',2,4);

-- 1101 (SMALL)
INSERT INTO `seat` (`aircraft_id_number`,`class_type`,`row_number`,`column_number`) VALUES
(1101,'ECONOMY',1,1),(1101,'ECONOMY',1,2),(1101,'ECONOMY',1,3),(1101,'ECONOMY',1,4),
(1101,'ECONOMY',2,1),(1101,'ECONOMY',2,2),(1101,'ECONOMY',2,3),(1101,'ECONOMY',2,4),
(1101,'ECONOMY',3,1),(1101,'ECONOMY',3,2),(1101,'ECONOMY',3,3),(1101,'ECONOMY',3,4);

-- 2101 (SMALL)
INSERT INTO `seat` (`aircraft_id_number`,`class_type`,`row_number`,`column_number`) VALUES
(2101,'ECONOMY',1,1),(2101,'ECONOMY',1,2),(2101,'ECONOMY',1,3),(2101,'ECONOMY',1,4),
(2101,'ECONOMY',2,1),(2101,'ECONOMY',2,2),(2101,'ECONOMY',2,3),(2101,'ECONOMY',2,4),
(2101,'ECONOMY',3,1),(2101,'ECONOMY',3,2),(2101,'ECONOMY',3,3),(2101,'ECONOMY',3,4);

-- 3101 (SMALL)
INSERT INTO `seat` (`aircraft_id_number`,`class_type`,`row_number`,`column_number`) VALUES
(3101,'ECONOMY',1,1),(3101,'ECONOMY',1,2),(3101,'ECONOMY',1,3),(3101,'ECONOMY',1,4),
(3101,'ECONOMY',2,1),(3101,'ECONOMY',2,2),(3101,'ECONOMY',2,3),(3101,'ECONOMY',2,4),
(3101,'ECONOMY',3,1),(3101,'ECONOMY',3,2),(3101,'ECONOMY',3,3),(3101,'ECONOMY',3,4);

-- 2001 (LARGE) כדי ש-9200 יעבוד עם מושבים
INSERT INTO `seat` (`aircraft_id_number`,`class_type`,`row_number`,`column_number`) VALUES
(2001,'ECONOMY',1,1),(2001,'ECONOMY',1,2),(2001,'ECONOMY',1,3),(2001,'ECONOMY',1,4),
(2001,'ECONOMY',2,1),(2001,'ECONOMY',2,2),(2001,'ECONOMY',2,3),(2001,'ECONOMY',2,4),
(2001,'ECONOMY',3,1),(2001,'ECONOMY',3,2),(2001,'ECONOMY',3,3),(2001,'ECONOMY',3,4),
(2001,'ECONOMY',4,1),(2001,'ECONOMY',4,2),(2001,'ECONOMY',4,3),(2001,'ECONOMY',4,4),
(2001,'ECONOMY',5,1),(2001,'ECONOMY',5,2),(2001,'ECONOMY',5,3),(2001,'ECONOMY',5,4),
(2001,'BUSINESS',1,1),(2001,'BUSINESS',1,2),(2001,'BUSINESS',1,3),(2001,'BUSINESS',1,4),
(2001,'BUSINESS',2,1),(2001,'BUSINESS',2,2),(2001,'BUSINESS',2,3),(2001,'BUSINESS',2,4);

-- 6) CUSTOMERS (25)
INSERT INTO `customer` (`email`,`first_name`,`last_name`) VALUES
('cust01@mail.com','Noa','Levi'),
('cust02@mail.com','Itay','Cohen'),
('cust03@mail.com','Maya','David'),
('cust04@mail.com','Dana','Mizrahi'),
('cust05@mail.com','Eitan','Peretz'),
('cust06@mail.com','Shira','Avraham'),
('cust07@mail.com','Omer','Biton'),
('cust08@mail.com','Yael','Amir'),
('cust09@mail.com','Lior','Shani'),
('cust10@mail.com','Gil','Katz'),
('cust11@mail.com','Hila','Yosef'),
('cust12@mail.com','Tomer','Bar'),
('cust13@mail.com','Adi','Shalom'),
('cust14@mail.com','Nitzan','Arad'),
('cust15@mail.com','Ron','Nuri'),
('cust16@mail.com','Tal','Sagi'),
('cust17@mail.com','Eli','Noy'),
('cust18@mail.com','Roni','Hazan'),
('cust19@mail.com','Amit','Shahar'),
('cust20@mail.com','Michal','Or'),
('cust21@mail.com','Yoni','Zohar'),
('cust22@mail.com','Lena','Friedman'),
('cust23@mail.com','Karim','Haddad'),
('cust24@mail.com','Sivan','Gabay'),
('cust25@mail.com','Nadav','Mor');

INSERT INTO `customer_phone_number` (`email`,`phone_number`) VALUES
('cust01@mail.com',501111111),
('cust02@mail.com',502222222),
('cust03@mail.com',503333333),
('cust04@mail.com',504444444),
('cust05@mail.com',505555555),
('cust06@mail.com',506666666),
('cust07@mail.com',507777777),
('cust08@mail.com',508888888),
('cust09@mail.com',509999999),
('cust10@mail.com',501010101);

-- 7) REGISTERED CUSTOMERS (15)
INSERT INTO `registered_customer` (`email`,`password`,`passport_number`,`date_of_birth`,`registration_date`) VALUES
('cust01@mail.com','pass01',1000001,'2001-02-10','2024-01-15'),
('cust02@mail.com','pass02',1000002,'1999-11-22','2024-02-01'),
('cust03@mail.com','pass03',1000003,'2000-05-03','2024-02-20'),
('cust04@mail.com','pass04',1000004,'2002-08-17','2024-03-10'),
('cust05@mail.com','pass05',1000005,'1998-12-30','2024-03-28'),
('cust06@mail.com','pass06',1000006,'2001-07-11','2024-04-05'),
('cust07@mail.com','pass07',1000007,'2003-09-09','2024-04-19'),
('cust08@mail.com','pass08',1000008,'1997-04-26','2024-05-02'),
('cust09@mail.com','pass09',1000009,'2000-10-14','2024-06-06'),
('cust10@mail.com','pass10',1000010,'1999-03-08','2024-06-21'),
('cust11@mail.com','pass11',1000011,'2002-01-27','2024-07-12'),
('cust12@mail.com','pass12',1000012,'2001-06-06','2024-08-03'),
('cust13@mail.com','pass13',1000013,'1998-09-19','2024-09-07'),
('cust14@mail.com','pass14',1000014,'2003-12-01','2024-10-11'),
('cust15@mail.com','pass15',1000015,'1997-02-02','2024-11-20');

-- 8) MANAGERS (4)
INSERT INTO `manager` (`id_number`,`first_name`,`last_name`,`city`,`street`,`house_number`,`phone_number`,`employment_start_date`,`password`) VALUES
(4001,'Avi','Shamir','Tel Aviv','Begin',10,520000001,'2020-01-10','m4001'),
(4002,'Yaara','Levin','Ramat Gan','Herzl',22,520000002,'2019-06-15','m4002'),
(4003,'Moshe','Adler','Jerusalem','Jaffa',5,520000003,'2021-03-01','m4003'),
(4004,'Liat','Carmi','Haifa','Hagana',18,520000004,'2022-09-12','m4004');

-- 9) PILOTS (20)
INSERT INTO `pilot` (`id_number`,`first_name`,`last_name`,`city`,`street`,`house_number`,`phone_number`,`employment_start_date`,`long_flight_certification`) VALUES
(5001,'Dan','Shalev','Tel Aviv','Arlozorov',3,530000001,'2018-01-01',1),
(5002,'Erez','Levi','Tel Aviv','Ibn Gabirol',14,530000002,'2019-02-01',1),
(5003,'Nir','Cohen','Ramat Gan','Bialik',7,530000003,'2017-03-01',1),
(5004,'Shai','David','Herzliya','Sokolov',9,530000004,'2016-04-01',1),
(5005,'Oded','Mizrahi','Netanya','Weizmann',11,530000005,'2015-05-01',1),
(5006,'Yaron','Peretz','Haifa','Moriah',19,530000006,'2014-06-01',1),
(5007,'Ido','Avraham','Jerusalem','Hillel',2,530000007,'2013-07-01',1),
(5008,'Tal','Biton','Beer Sheva','Rager',8,530000008,'2012-08-01',1),
(5009,'Ariel','Amir','Ashdod','HaAtzmaut',6,530000009,'2011-09-01',1),
(5010,'Gal','Katz','Eilat','Shahamon',4,530000010,'2010-10-01',1),
(5011,'Noam','Yosef','Tel Aviv','Dizengoff',21,530000011,'2021-01-10',0),
(5012,'Lior','Bar','Tel Aviv','King George',16,530000012,'2021-02-10',0),
(5013,'Eyal','Shalom','Ramat Gan','Hayarkon',12,530000013,'2021-03-10',0),
(5014,'Roi','Arad','Herzliya','HaNassi',5,530000014,'2021-04-10',0),
(5015,'Amir','Nuri','Netanya','Gdud HaAvoda',10,530000015,'2021-05-10',0),
(5016,'Itamar','Sagi','Haifa','Nordau',3,530000016,'2021-06-10',0),
(5017,'Yuval','Noy','Jerusalem','Agron',9,530000017,'2021-07-10',0),
(5018,'Assaf','Hazan','Beer Sheva','Ben Gurion',13,530000018,'2021-08-10',0),
(5019,'Omri','Shahar','Ashdod','HaPardes',2,530000019,'2021-09-10',0),
(5020,'Tzur','Or','Eilat','Ofarim',7,530000020,'2021-10-10',0);

-- 10) FLIGHT ATTENDANTS (30)
INSERT INTO `flight_attendant` (`id_number`,`first_name`,`last_name`,`city`,`street`,`house_number`,`phone_number`,`employment_start_date`,`long_flight_certification`) VALUES
(6001,'Noya','Levi','Tel Aviv','Rothschild',1,540000001,'2019-01-01',1),
(6002,'Rina','Cohen','Tel Aviv','Allenby',2,540000002,'2019-02-01',1),
(6003,'Moran','David','Ramat Gan','Herzl',3,540000003,'2019-03-01',1),
(6004,'Shani','Mizrahi','Herzliya','Sokolov',4,540000004,'2019-04-01',1),
(6005,'Keren','Peretz','Haifa','Moriah',5,540000005,'2019-05-01',1),
(6006,'Lihi','Avraham','Jerusalem','Hillel',6,540000006,'2019-06-01',1),
(6007,'Yaara','Biton','Beer Sheva','Rager',7,540000007,'2019-07-01',1),
(6008,'Dana','Amir','Ashdod','HaAtzmaut',8,540000008,'2019-08-01',1),
(6009,'Hadar','Shani','Eilat','Shahamon',9,540000009,'2019-09-01',1),
(6010,'Talya','Katz','Netanya','Weizmann',10,540000010,'2019-10-01',1),
(6011,'Or','Yosef','Tel Aviv','Dizengoff',11,540000011,'2020-01-01',1),
(6012,'Shira','Bar','Tel Aviv','King George',12,540000012,'2020-02-01',1),
(6013,'Adi','Shalom','Ramat Gan','Bialik',13,540000013,'2020-03-01',1),
(6014,'Sivan','Arad','Herzliya','HaNassi',14,540000014,'2020-04-01',1),
(6015,'Lian','Nuri','Netanya','Gdud HaAvoda',15,540000015,'2020-05-01',1),
(6016,'Mika','Sagi','Haifa','Nordau',16,540000016,'2020-06-01',1),
(6017,'Rotem','Noy','Jerusalem','Agron',17,540000017,'2020-07-01',1),
(6018,'Yasmin','Hazan','Beer Sheva','Ben Gurion',18,540000018,'2020-08-01',1),
(6019,'Hila','Shahar','Ashdod','HaPardes',19,540000019,'2020-09-01',1),
(6020,'Noam','Or','Eilat','Ofarim',20,540000020,'2020-10-01',1),
(6021,'Lee','Zohar','Tel Aviv','Frishman',21,540000021,'2022-01-01',0),
(6022,'Eden','Friedman','Tel Aviv','Bugrashov',22,540000022,'2022-02-01',0),
(6023,'Neta','Haddad','Ramat Gan','Jabotinsky',23,540000023,'2022-03-01',0),
(6024,'Tamar','Gabay','Herzliya','HaAliya',24,540000024,'2022-04-01',0),
(6025,'Bar','Mor','Netanya','Pinsker',25,540000025,'2022-05-01',0),
(6026,'Aya','Levi','Haifa','Horev',26,540000026,'2022-06-01',0),
(6027,'Lihi','Cohen','Jerusalem','King David',27,540000027,'2022-07-01',0),
(6028,'Dana','David','Beer Sheva','HaNegev',28,540000028,'2022-08-01',0),
(6029,'Shani','Mizrahi','Ashdod','HaYam',29,540000029,'2022-09-01',0),
(6030,'Keren','Peretz','Eilat','Derech HaArava',30,540000030,'2022-10-01',0);

-- 11) FLIGHTS (כולן באפריל 2026)
INSERT INTO `flight` (`flight_number`,`aircraft_id_number`,`origin_airport`,`destination_airport`,`departure_datetime`,`status`) VALUES
(9001,1101,'TLV','LCA','2025-04-01 08:10:00','ACTIVE'),
(9002,2101,'TLV','ATH','2024-04-02 09:30:00','ACTIVE'),
(9003,1001,'TLV','JFK','2024-05-03 11:00:00','ACTIVE'),
(9004,3001,'JFK','TLV','2025-04-04 19:20:00','CANCELED'),
(9005,3101,'TLV','CDG','2025-04-05 07:45:00','ACTIVE'),
(9006,1101,'TLV','IST','2024-05-06 06:25:00','ACTIVE'),
(9007,2101,'FCO','TLV','2025-12-07 14:05:00','CANCELED'),
(9008,3001,'TLV','LHR','2025-11-08 16:30:00','ACTIVE'),
(9009,1002,'DXB','TLV','2026-04-09 21:10:00','ACTIVE'),
(9010,3101,'TLV','AMS','2026-04-10 12:40:00','CANCELED'),

(9101,1101,'TLV','LCA','2026-04-11 08:10:00','ACTIVE'),
(9102,2101,'ATH','TLV','2026-04-12 10:00:00','ACTIVE'),
(9103,1001,'TLV','JFK','2026-04-13 11:00:00','ACTIVE'),
(9104,3001,'JFK','TLV','2026-04-14 19:20:00','ACTIVE'),
(9105,3101,'TLV','CDG','2026-04-15 07:45:00','ACTIVE'),
(9106,1101,'TLV','IST','2026-04-16 06:25:00','CANCELED'),
(9107,1002,'TLV','LHR','2026-04-17 16:30:00','ACTIVE'),
(9108,2101,'DXB','TLV','2026-04-18 21:10:00','ACTIVE'),
(9109,3001,'TLV','JFK','2026-04-19 11:00:00','CANCELED'),
(9110,3101,'FCO','TLV','2026-04-20 14:05:00','ACTIVE'),

-- הטיסה הנוספת
(9200,2001,'TLV','LCA','2026-04-21 10:00:00','ACTIVE');

-- 12) PILOTS ON FLIGHTS (כמו אצלך)
INSERT INTO `pilots_on_flights` (`id_number`,`flight_number`) VALUES
(5011,9001),(5012,9001),
(5013,9002),(5014,9002),
(5015,9005),(5016,9005),
(5017,9006),(5018,9006),
(5019,9007),(5020,9007),
(5011,9010),(5013,9010),

(5012,9101),(5014,9101),
(5015,9102),(5017,9102),
(5016,9105),(5018,9105),
(5019,9106),(5020,9106),
(5011,9108),(5012,9108),
(5013,9110),(5014,9110),

(5006,9008),(5011,9008),(5012,9008),
(5007,9009),(5013,9009),(5014,9009),
(5008,9107),(5015,9107),(5016,9107),
(5009,9200),(5017,9200),(5018,9200),

(5001,9003),(5002,9003),(5003,9003),
(5004,9004),(5005,9004),(5006,9004),
(5007,9103),(5008,9103),(5009,9103),
(5010,9104),(5001,9104),(5002,9104),
(5003,9109),(5004,9109),(5005,9109);

-- 13) FLIGHT ATTENDANTS ON FLIGHTS (כמו אצלך)
INSERT INTO `flight_attendants_on_flights` (`id_number`,`flight_number`) VALUES
(6021,9001),(6022,9001),(6023,9001),
(6024,9002),(6025,9002),(6026,9002),
(6027,9005),(6028,9005),(6029,9005),
(6030,9006),(6021,9006),(6022,9006),
(6023,9007),(6024,9007),(6025,9007),
(6026,9010),(6027,9010),(6028,9010),

(6029,9101),(6030,9101),(6021,9101),
(6022,9102),(6023,9102),(6024,9102),
(6025,9105),(6026,9105),(6027,9105),
(6028,9106),(6029,9106),(6030,9106),
(6021,9108),(6022,9108),(6023,9108),
(6024,9110),(6025,9110),(6026,9110),

(6021,9008),(6022,9008),(6023,9008),(6024,9008),(6025,9008),(6001,9008),
(6027,9009),(6028,9009),(6029,9009),(6030,9009),(6011,9009),(6012,9009),
(6021,9107),(6022,9107),(6023,9107),(6024,9107),(6013,9107),(6014,9107),
(6025,9200),(6026,9200),(6027,9200),(6028,9200),(6001,9200),(6002,9200),

(6001,9003),(6002,9003),(6003,9003),(6004,9003),(6005,9003),(6006,9003),
(6007,9004),(6008,9004),(6009,9004),(6010,9004),(6011,9004),(6012,9004),
(6013,9103),(6014,9103),(6015,9103),(6016,9103),(6017,9103),(6018,9103),
(6019,9104),(6020,9104),(6001,9104),(6002,9104),(6003,9104),(6004,9104),
(6005,9109),(6006,9109),(6007,9109),(6008,9109),(6009,9109),(6010,9109);

-- 14) RESERVATIONS (עדכון לאפריל 2026 + בלי cancellation_datetime)
INSERT INTO `reservations`
(`reservation_code`,`reservations_status`,`total_payment`,`email`,`flight_number`,`reservation_date`) VALUES
(7001,'ACTIVE',540,'cust01@mail.com',9101,'2026-04-01'),
(7002,'ACTIVE',480,'cust02@mail.com',9102,'2026-04-01'),
(7003,'ACTIVE',300,'cust03@mail.com',9105,'2026-04-02'),
(7004,'ACTIVE',900,'cust04@mail.com',9107,'2026-04-02'),
(7005,'ACTIVE',180,'cust05@mail.com',9101,'2026-04-03'),
(7006,'ACTIVE',500,'cust06@mail.com',9108,'2026-04-03'),
(7007,'ACTIVE',280,'cust07@mail.com',9110,'2026-04-04'),
(7008,'ACTIVE',560,'cust08@mail.com',9105,'2026-04-04'),
(7009,'ACTIVE',800,'cust09@mail.com',9103,'2026-04-01'),
(7010,'ACTIVE',700,'cust10@mail.com',9104,'2026-04-02'),
(7011,'ACTIVE',360,'cust16@mail.com',9102,'2026-04-03'),

(7012,'CUSTOMER_CANCELED',12.5,'cust11@mail.com',9106,'2026-04-05'),
(7013,'CUSTOMER_CANCELED',280,'cust12@mail.com',9105,'2026-04-05'),
(7014,'SYSTEM_CANCELED',0,'cust13@mail.com',9109,'2026-04-06'),
(7015,'SYSTEM_CANCELED',0,'cust14@mail.com',9101,'2026-04-01'),

(7020,'ACTIVE',360,'cust17@mail.com',9001,'2025-01-01'),
(7021,'ACTIVE',320,'cust18@mail.com',9002,'2024-02-01'),
(7022,'ACTIVE',900,'cust19@mail.com',9003,'2024-04-02'),
(7023,'ACTIVE',340,'cust20@mail.com',9005,'2024-04-02'),
(7024,'ACTIVE',540,'cust21@mail.com',9006,'2023-12-03'),
(7025,'ACTIVE',980,'cust22@mail.com',9008,'2025-04-04'),
(7026,'ACTIVE',650,'cust23@mail.com',9009,'2026-04-04');

-- 15) SEATS IN RESERVATION (בדיוק לפי הנתונים שלך)
INSERT INTO `seats_in_reservation` (`reservation_code`,`aircraft_id_number`,`class_type`,`row_number`,`column_number`) VALUES
(7001,1101,'ECONOMY',1,1),
(7001,1101,'ECONOMY',1,2),
(7001,1101,'ECONOMY',1,3);

INSERT INTO `seats_in_reservation` VALUES
(7002,2101,'ECONOMY',1,1),
(7002,2101,'ECONOMY',1,2),
(7002,2101,'ECONOMY',2,1);

INSERT INTO `seats_in_reservation` VALUES
(7003,3101,'ECONOMY',1,1);

INSERT INTO `seats_in_reservation` VALUES
(7004,1002,'BUSINESS',1,1),
(7004,1002,'BUSINESS',1,2);

INSERT INTO `seats_in_reservation` VALUES
(7005,1101,'ECONOMY',2,2);

INSERT INTO `seats_in_reservation` VALUES
(7006,2101,'ECONOMY',2,2),
(7006,2101,'ECONOMY',2,3),
(7006,2101,'ECONOMY',3,1);

INSERT INTO `seats_in_reservation` VALUES
(7007,3101,'ECONOMY',2,1),
(7007,3101,'ECONOMY',2,2);

INSERT INTO `seats_in_reservation` VALUES
(7008,3101,'ECONOMY',1,2),
(7008,3101,'ECONOMY',1,3),
(7008,3101,'ECONOMY',1,4),
(7008,3101,'ECONOMY',2,3);

INSERT INTO `seats_in_reservation` VALUES
(7009,1001,'ECONOMY',1,1),
(7009,1001,'ECONOMY',1,2),
(7009,1001,'ECONOMY',1,3);

INSERT INTO `seats_in_reservation` VALUES
(7010,3001,'BUSINESS',1,1);

INSERT INTO `seats_in_reservation` VALUES
(7011,2101,'ECONOMY',3,2),
(7011,2101,'ECONOMY',3,3);

INSERT INTO `seats_in_reservation` VALUES
(7012,1101,'ECONOMY',3,1);

INSERT INTO `seats_in_reservation` VALUES
(7013,3101,'ECONOMY',3,1),
(7013,3101,'ECONOMY',3,2);

INSERT INTO `seats_in_reservation` VALUES
(7014,3001,'ECONOMY',2,1),
(7014,3001,'ECONOMY',2,2),
(7014,3001,'ECONOMY',2,3),
(7014,3001,'ECONOMY',2,4),
(7014,3001,'ECONOMY',3,1);

INSERT INTO `seats_in_reservation` VALUES
(7015,1101,'ECONOMY',3,2);

INSERT INTO `seats_in_reservation` VALUES
(7020,1101,'ECONOMY',1,4),
(7020,1101,'ECONOMY',2,4);

INSERT INTO `seats_in_reservation` VALUES
(7021,2101,'ECONOMY',1,3),
(7021,2101,'ECONOMY',1,4);

INSERT INTO `seats_in_reservation` VALUES
(7022,1001,'BUSINESS',2,1),
(7022,1001,'BUSINESS',2,2),
(7022,1001,'ECONOMY',5,4);

INSERT INTO `seats_in_reservation` VALUES
(7023,3101,'ECONOMY',2,4),
(7023,3101,'ECONOMY',3,4);

INSERT INTO `seats_in_reservation` VALUES
(7024,1101,'ECONOMY',3,3),
(7024,1101,'ECONOMY',3,4),
(7024,1101,'ECONOMY',2,3);

INSERT INTO `seats_in_reservation` VALUES
(7025,3001,'BUSINESS',2,4),
(7025,3001,'ECONOMY',4,4);

INSERT INTO `seats_in_reservation` VALUES
(7026,1002,'ECONOMY',5,1),
(7026,1002,'ECONOMY',5,2),
(7026,1002,'ECONOMY',5,3);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
(1101,'ECONOMY',1,1,9001,180),(1101,'ECONOMY',1,2,9001,180),(1101,'ECONOMY',1,3,9001,180),(1101,'ECONOMY',1,4,9001,180),
(1101,'ECONOMY',2,1,9001,180),(1101,'ECONOMY',2,2,9001,180),(1101,'ECONOMY',2,3,9001,180),(1101,'ECONOMY',2,4,9001,180),
(1101,'ECONOMY',3,1,9001,180),(1101,'ECONOMY',3,2,9001,180),(1101,'ECONOMY',3,3,9001,180),(1101,'ECONOMY',3,4,9001,180);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
(1101,'ECONOMY',1,1,9006,180),(1101,'ECONOMY',1,2,9006,180),(1101,'ECONOMY',1,3,9006,180),(1101,'ECONOMY',1,4,9006,180),
(1101,'ECONOMY',2,1,9006,180),(1101,'ECONOMY',2,2,9006,180),(1101,'ECONOMY',2,3,9006,180),(1101,'ECONOMY',2,4,9006,180),
(1101,'ECONOMY',3,1,9006,180),(1101,'ECONOMY',3,2,9006,180),(1101,'ECONOMY',3,3,9006,180),(1101,'ECONOMY',3,4,9006,180);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
(1101,'ECONOMY',1,1,9101,180),(1101,'ECONOMY',1,2,9101,180),(1101,'ECONOMY',1,3,9101,180),(1101,'ECONOMY',1,4,9101,180),
(1101,'ECONOMY',2,1,9101,180),(1101,'ECONOMY',2,2,9101,180),(1101,'ECONOMY',2,3,9101,180),(1101,'ECONOMY',2,4,9101,180),
(1101,'ECONOMY',3,1,9101,180),(1101,'ECONOMY',3,2,9101,180),(1101,'ECONOMY',3,3,9101,180),(1101,'ECONOMY',3,4,9101,180);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
(1101,'ECONOMY',1,1,9106,180),(1101,'ECONOMY',1,2,9106,180),(1101,'ECONOMY',1,3,9106,180),(1101,'ECONOMY',1,4,9106,180),
(1101,'ECONOMY',2,1,9106,180),(1101,'ECONOMY',2,2,9106,180),(1101,'ECONOMY',2,3,9106,180),(1101,'ECONOMY',2,4,9106,180),
(1101,'ECONOMY',3,1,9106,180),(1101,'ECONOMY',3,2,9106,180),(1101,'ECONOMY',3,3,9106,180),(1101,'ECONOMY',3,4,9106,180);

-- =========================================================
-- 2101 ECONOMY price 160
-- flights: 9002, 9007, 9102, 9108
-- =========================================================

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
(2101,'ECONOMY',1,1,9002,160),(2101,'ECONOMY',1,2,9002,160),(2101,'ECONOMY',1,3,9002,160),(2101,'ECONOMY',1,4,9002,160),
(2101,'ECONOMY',2,1,9002,160),(2101,'ECONOMY',2,2,9002,160),(2101,'ECONOMY',2,3,9002,160),(2101,'ECONOMY',2,4,9002,160),
(2101,'ECONOMY',3,1,9002,160),(2101,'ECONOMY',3,2,9002,160),(2101,'ECONOMY',3,3,9002,160),(2101,'ECONOMY',3,4,9002,160);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
(2101,'ECONOMY',1,1,9007,160),(2101,'ECONOMY',1,2,9007,160),(2101,'ECONOMY',1,3,9007,160),(2101,'ECONOMY',1,4,9007,160),
(2101,'ECONOMY',2,1,9007,160),(2101,'ECONOMY',2,2,9007,160),(2101,'ECONOMY',2,3,9007,160),(2101,'ECONOMY',2,4,9007,160),
(2101,'ECONOMY',3,1,9007,160),(2101,'ECONOMY',3,2,9007,160),(2101,'ECONOMY',3,3,9007,160),(2101,'ECONOMY',3,4,9007,160);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
(2101,'ECONOMY',1,1,9102,160),(2101,'ECONOMY',1,2,9102,160),(2101,'ECONOMY',1,3,9102,160),(2101,'ECONOMY',1,4,9102,160),
(2101,'ECONOMY',2,1,9102,160),(2101,'ECONOMY',2,2,9102,160),(2101,'ECONOMY',2,3,9102,160),(2101,'ECONOMY',2,4,9102,160),
(2101,'ECONOMY',3,1,9102,160),(2101,'ECONOMY',3,2,9102,160),(2101,'ECONOMY',3,3,9102,160),(2101,'ECONOMY',3,4,9102,160);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
(2101,'ECONOMY',1,1,9108,160),(2101,'ECONOMY',1,2,9108,160),(2101,'ECONOMY',1,3,9108,160),(2101,'ECONOMY',1,4,9108,160),
(2101,'ECONOMY',2,1,9108,160),(2101,'ECONOMY',2,2,9108,160),(2101,'ECONOMY',2,3,9108,160),(2101,'ECONOMY',2,4,9108,160),
(2101,'ECONOMY',3,1,9108,160),(2101,'ECONOMY',3,2,9108,160),(2101,'ECONOMY',3,3,9108,160),(2101,'ECONOMY',3,4,9108,160);

-- =========================================================
-- 3101 ECONOMY price 170
-- flights: 9005, 9010, 9105, 9110
-- =========================================================

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
(3101,'ECONOMY',1,1,9005,170),(3101,'ECONOMY',1,2,9005,170),(3101,'ECONOMY',1,3,9005,170),(3101,'ECONOMY',1,4,9005,170),
(3101,'ECONOMY',2,1,9005,170),(3101,'ECONOMY',2,2,9005,170),(3101,'ECONOMY',2,3,9005,170),(3101,'ECONOMY',2,4,9005,170),
(3101,'ECONOMY',3,1,9005,170),(3101,'ECONOMY',3,2,9005,170),(3101,'ECONOMY',3,3,9005,170),(3101,'ECONOMY',3,4,9005,170);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
(3101,'ECONOMY',1,1,9010,170),(3101,'ECONOMY',1,2,9010,170),(3101,'ECONOMY',1,3,9010,170),(3101,'ECONOMY',1,4,9010,170),
(3101,'ECONOMY',2,1,9010,170),(3101,'ECONOMY',2,2,9010,170),(3101,'ECONOMY',2,3,9010,170),(3101,'ECONOMY',2,4,9010,170),
(3101,'ECONOMY',3,1,9010,170),(3101,'ECONOMY',3,2,9010,170),(3101,'ECONOMY',3,3,9010,170),(3101,'ECONOMY',3,4,9010,170);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
(3101,'ECONOMY',1,1,9105,170),(3101,'ECONOMY',1,2,9105,170),(3101,'ECONOMY',1,3,9105,170),(3101,'ECONOMY',1,4,9105,170),
(3101,'ECONOMY',2,1,9105,170),(3101,'ECONOMY',2,2,9105,170),(3101,'ECONOMY',2,3,9105,170),(3101,'ECONOMY',2,4,9105,170),
(3101,'ECONOMY',3,1,9105,170),(3101,'ECONOMY',3,2,9105,170),(3101,'ECONOMY',3,3,9105,170),(3101,'ECONOMY',3,4,9105,170);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
(3101,'ECONOMY',1,1,9110,170),(3101,'ECONOMY',1,2,9110,170),(3101,'ECONOMY',1,3,9110,170),(3101,'ECONOMY',1,4,9110,170),
(3101,'ECONOMY',2,1,9110,170),(3101,'ECONOMY',2,2,9110,170),(3101,'ECONOMY',2,3,9110,170),(3101,'ECONOMY',2,4,9110,170),
(3101,'ECONOMY',3,1,9110,170),(3101,'ECONOMY',3,2,9110,170),(3101,'ECONOMY',3,3,9110,170),(3101,'ECONOMY',3,4,9110,170);

-- =========================================================
-- LARGE aircraft seats:
-- ECONOMY 5x4 = 20, BUSINESS 2x4 = 8  (total 28)
-- =========================================================

-- 1001: ECONOMY 300, BUSINESS 800
-- flights: 9003, 9103
INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
-- 9003 ECONOMY (20)
(1001,'ECONOMY',1,1,9003,300),(1001,'ECONOMY',1,2,9003,300),(1001,'ECONOMY',1,3,9003,300),(1001,'ECONOMY',1,4,9003,300),
(1001,'ECONOMY',2,1,9003,300),(1001,'ECONOMY',2,2,9003,300),(1001,'ECONOMY',2,3,9003,300),(1001,'ECONOMY',2,4,9003,300),
(1001,'ECONOMY',3,1,9003,300),(1001,'ECONOMY',3,2,9003,300),(1001,'ECONOMY',3,3,9003,300),(1001,'ECONOMY',3,4,9003,300),
(1001,'ECONOMY',4,1,9003,300),(1001,'ECONOMY',4,2,9003,300),(1001,'ECONOMY',4,3,9003,300),(1001,'ECONOMY',4,4,9003,300),
(1001,'ECONOMY',5,1,9003,300),(1001,'ECONOMY',5,2,9003,300),(1001,'ECONOMY',5,3,9003,300),(1001,'ECONOMY',5,4,9003,300),
-- 9003 BUSINESS (8)
(1001,'BUSINESS',1,1,9003,800),(1001,'BUSINESS',1,2,9003,800),(1001,'BUSINESS',1,3,9003,800),(1001,'BUSINESS',1,4,9003,800),
(1001,'BUSINESS',2,1,9003,800),(1001,'BUSINESS',2,2,9003,800),(1001,'BUSINESS',2,3,9003,800),(1001,'BUSINESS',2,4,9003,800);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
-- 9103 ECONOMY (20)
(1001,'ECONOMY',1,1,9103,300),(1001,'ECONOMY',1,2,9103,300),(1001,'ECONOMY',1,3,9103,300),(1001,'ECONOMY',1,4,9103,300),
(1001,'ECONOMY',2,1,9103,300),(1001,'ECONOMY',2,2,9103,300),(1001,'ECONOMY',2,3,9103,300),(1001,'ECONOMY',2,4,9103,300),
(1001,'ECONOMY',3,1,9103,300),(1001,'ECONOMY',3,2,9103,300),(1001,'ECONOMY',3,3,9103,300),(1001,'ECONOMY',3,4,9103,300),
(1001,'ECONOMY',4,1,9103,300),(1001,'ECONOMY',4,2,9103,300),(1001,'ECONOMY',4,3,9103,300),(1001,'ECONOMY',4,4,9103,300),
(1001,'ECONOMY',5,1,9103,300),(1001,'ECONOMY',5,2,9103,300),(1001,'ECONOMY',5,3,9103,300),(1001,'ECONOMY',5,4,9103,300),
-- 9103 BUSINESS (8)
(1001,'BUSINESS',1,1,9103,800),(1001,'BUSINESS',1,2,9103,800),(1001,'BUSINESS',1,3,9103,800),(1001,'BUSINESS',1,4,9103,800),
(1001,'BUSINESS',2,1,9103,800),(1001,'BUSINESS',2,2,9103,800),(1001,'BUSINESS',2,3,9103,800),(1001,'BUSINESS',2,4,9103,800);

-- =========================================================
-- 1002: ECONOMY 250, BUSINESS 650
-- flights: 9009, 9107
-- =========================================================
INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
-- 9009 ECONOMY (20)
(1002,'ECONOMY',1,1,9009,250),(1002,'ECONOMY',1,2,9009,250),(1002,'ECONOMY',1,3,9009,250),(1002,'ECONOMY',1,4,9009,250),
(1002,'ECONOMY',2,1,9009,250),(1002,'ECONOMY',2,2,9009,250),(1002,'ECONOMY',2,3,9009,250),(1002,'ECONOMY',2,4,9009,250),
(1002,'ECONOMY',3,1,9009,250),(1002,'ECONOMY',3,2,9009,250),(1002,'ECONOMY',3,3,9009,250),(1002,'ECONOMY',3,4,9009,250),
(1002,'ECONOMY',4,1,9009,250),(1002,'ECONOMY',4,2,9009,250),(1002,'ECONOMY',4,3,9009,250),(1002,'ECONOMY',4,4,9009,250),
(1002,'ECONOMY',5,1,9009,250),(1002,'ECONOMY',5,2,9009,250),(1002,'ECONOMY',5,3,9009,250),(1002,'ECONOMY',5,4,9009,250),
-- 9009 BUSINESS (8)
(1002,'BUSINESS',1,1,9009,650),(1002,'BUSINESS',1,2,9009,650),(1002,'BUSINESS',1,3,9009,650),(1002,'BUSINESS',1,4,9009,650),
(1002,'BUSINESS',2,1,9009,650),(1002,'BUSINESS',2,2,9009,650),(1002,'BUSINESS',2,3,9009,650),(1002,'BUSINESS',2,4,9009,650);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
-- 9107 ECONOMY (20)
(1002,'ECONOMY',1,1,9107,250),(1002,'ECONOMY',1,2,9107,250),(1002,'ECONOMY',1,3,9107,250),(1002,'ECONOMY',1,4,9107,250),
(1002,'ECONOMY',2,1,9107,250),(1002,'ECONOMY',2,2,9107,250),(1002,'ECONOMY',2,3,9107,250),(1002,'ECONOMY',2,4,9107,250),
(1002,'ECONOMY',3,1,9107,250),(1002,'ECONOMY',3,2,9107,250),(1002,'ECONOMY',3,3,9107,250),(1002,'ECONOMY',3,4,9107,250),
(1002,'ECONOMY',4,1,9107,250),(1002,'ECONOMY',4,2,9107,250),(1002,'ECONOMY',4,3,9107,250),(1002,'ECONOMY',4,4,9107,250),
(1002,'ECONOMY',5,1,9107,250),(1002,'ECONOMY',5,2,9107,250),(1002,'ECONOMY',5,3,9107,250),(1002,'ECONOMY',5,4,9107,250),
-- 9107 BUSINESS (8)
(1002,'BUSINESS',1,1,9107,650),(1002,'BUSINESS',1,2,9107,650),(1002,'BUSINESS',1,3,9107,650),(1002,'BUSINESS',1,4,9107,650),
(1002,'BUSINESS',2,1,9107,650),(1002,'BUSINESS',2,2,9107,650),(1002,'BUSINESS',2,3,9107,650),(1002,'BUSINESS',2,4,9107,650);

-- =========================================================
-- 3001: ECONOMY 280, BUSINESS 700
-- flights: 9004, 9008, 9104, 9109
-- =========================================================
INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
-- 9004 ECONOMY (20)
(3001,'ECONOMY',1,1,9004,280),(3001,'ECONOMY',1,2,9004,280),(3001,'ECONOMY',1,3,9004,280),(3001,'ECONOMY',1,4,9004,280),
(3001,'ECONOMY',2,1,9004,280),(3001,'ECONOMY',2,2,9004,280),(3001,'ECONOMY',2,3,9004,280),(3001,'ECONOMY',2,4,9004,280),
(3001,'ECONOMY',3,1,9004,280),(3001,'ECONOMY',3,2,9004,280),(3001,'ECONOMY',3,3,9004,280),(3001,'ECONOMY',3,4,9004,280),
(3001,'ECONOMY',4,1,9004,280),(3001,'ECONOMY',4,2,9004,280),(3001,'ECONOMY',4,3,9004,280),(3001,'ECONOMY',4,4,9004,280),
(3001,'ECONOMY',5,1,9004,280),(3001,'ECONOMY',5,2,9004,280),(3001,'ECONOMY',5,3,9004,280),(3001,'ECONOMY',5,4,9004,280),
-- 9004 BUSINESS (8)
(3001,'BUSINESS',1,1,9004,700),(3001,'BUSINESS',1,2,9004,700),(3001,'BUSINESS',1,3,9004,700),(3001,'BUSINESS',1,4,9004,700),
(3001,'BUSINESS',2,1,9004,700),(3001,'BUSINESS',2,2,9004,700),(3001,'BUSINESS',2,3,9004,700),(3001,'BUSINESS',2,4,9004,700);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
-- 9008 ECONOMY (20)
(3001,'ECONOMY',1,1,9008,280),(3001,'ECONOMY',1,2,9008,280),(3001,'ECONOMY',1,3,9008,280),(3001,'ECONOMY',1,4,9008,280),
(3001,'ECONOMY',2,1,9008,280),(3001,'ECONOMY',2,2,9008,280),(3001,'ECONOMY',2,3,9008,280),(3001,'ECONOMY',2,4,9008,280),
(3001,'ECONOMY',3,1,9008,280),(3001,'ECONOMY',3,2,9008,280),(3001,'ECONOMY',3,3,9008,280),(3001,'ECONOMY',3,4,9008,280),
(3001,'ECONOMY',4,1,9008,280),(3001,'ECONOMY',4,2,9008,280),(3001,'ECONOMY',4,3,9008,280),(3001,'ECONOMY',4,4,9008,280),
(3001,'ECONOMY',5,1,9008,280),(3001,'ECONOMY',5,2,9008,280),(3001,'ECONOMY',5,3,9008,280),(3001,'ECONOMY',5,4,9008,280),
-- 9008 BUSINESS (8)
(3001,'BUSINESS',1,1,9008,700),(3001,'BUSINESS',1,2,9008,700),(3001,'BUSINESS',1,3,9008,700),(3001,'BUSINESS',1,4,9008,700),
(3001,'BUSINESS',2,1,9008,700),(3001,'BUSINESS',2,2,9008,700),(3001,'BUSINESS',2,3,9008,700),(3001,'BUSINESS',2,4,9008,700);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
-- 9104 ECONOMY (20)
(3001,'ECONOMY',1,1,9104,280),(3001,'ECONOMY',1,2,9104,280),(3001,'ECONOMY',1,3,9104,280),(3001,'ECONOMY',1,4,9104,280),
(3001,'ECONOMY',2,1,9104,280),(3001,'ECONOMY',2,2,9104,280),(3001,'ECONOMY',2,3,9104,280),(3001,'ECONOMY',2,4,9104,280),
(3001,'ECONOMY',3,1,9104,280),(3001,'ECONOMY',3,2,9104,280),(3001,'ECONOMY',3,3,9104,280),(3001,'ECONOMY',3,4,9104,280),
(3001,'ECONOMY',4,1,9104,280),(3001,'ECONOMY',4,2,9104,280),(3001,'ECONOMY',4,3,9104,280),(3001,'ECONOMY',4,4,9104,280),
(3001,'ECONOMY',5,1,9104,280),(3001,'ECONOMY',5,2,9104,280),(3001,'ECONOMY',5,3,9104,280),(3001,'ECONOMY',5,4,9104,280),
-- 9104 BUSINESS (8)
(3001,'BUSINESS',1,1,9104,700),(3001,'BUSINESS',1,2,9104,700),(3001,'BUSINESS',1,3,9104,700),(3001,'BUSINESS',1,4,9104,700),
(3001,'BUSINESS',2,1,9104,700),(3001,'BUSINESS',2,2,9104,700),(3001,'BUSINESS',2,3,9104,700),(3001,'BUSINESS',2,4,9104,700);

INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
-- 9109 ECONOMY (20)
(3001,'ECONOMY',1,1,9109,280),(3001,'ECONOMY',1,2,9109,280),(3001,'ECONOMY',1,3,9109,280),(3001,'ECONOMY',1,4,9109,280),
(3001,'ECONOMY',2,1,9109,280),(3001,'ECONOMY',2,2,9109,280),(3001,'ECONOMY',2,3,9109,280),(3001,'ECONOMY',2,4,9109,280),
(3001,'ECONOMY',3,1,9109,280),(3001,'ECONOMY',3,2,9109,280),(3001,'ECONOMY',3,3,9109,280),(3001,'ECONOMY',3,4,9109,280),
(3001,'ECONOMY',4,1,9109,280),(3001,'ECONOMY',4,2,9109,280),(3001,'ECONOMY',4,3,9109,280),(3001,'ECONOMY',4,4,9109,280),
(3001,'ECONOMY',5,1,9109,280),(3001,'ECONOMY',5,2,9109,280),(3001,'ECONOMY',5,3,9109,280),(3001,'ECONOMY',5,4,9109,280),
-- 9109 BUSINESS (8)
(3001,'BUSINESS',1,1,9109,700),(3001,'BUSINESS',1,2,9109,700),(3001,'BUSINESS',1,3,9109,700),(3001,'BUSINESS',1,4,9109,700),
(3001,'BUSINESS',2,1,9109,700),(3001,'BUSINESS',2,2,9109,700),(3001,'BUSINESS',2,3,9109,700),(3001,'BUSINESS',2,4,9109,700);

-- =========================================================
-- 2001: ECONOMY 260, BUSINESS 720
-- flight: 9200
-- =========================================================
INSERT INTO seats_in_flights (aircraft_id_number, class_type, `row_number`, column_number, flight_number, price) VALUES
-- 9200 ECONOMY (20)
(2001,'ECONOMY',1,1,9200,260),(2001,'ECONOMY',1,2,9200,260),(2001,'ECONOMY',1,3,9200,260),(2001,'ECONOMY',1,4,9200,260),
(2001,'ECONOMY',2,1,9200,260),(2001,'ECONOMY',2,2,9200,260),(2001,'ECONOMY',2,3,9200,260),(2001,'ECONOMY',2,4,9200,260),
(2001,'ECONOMY',3,1,9200,260),(2001,'ECONOMY',3,2,9200,260),(2001,'ECONOMY',3,3,9200,260),(2001,'ECONOMY',3,4,9200,260),
(2001,'ECONOMY',4,1,9200,260),(2001,'ECONOMY',4,2,9200,260),(2001,'ECONOMY',4,3,9200,260),(2001,'ECONOMY',4,4,9200,260),
(2001,'ECONOMY',5,1,9200,260),(2001,'ECONOMY',5,2,9200,260),(2001,'ECONOMY',5,3,9200,260),(2001,'ECONOMY',5,4,9200,260),
-- 9200 BUSINESS (8)
(2001,'BUSINESS',1,1,9200,720),(2001,'BUSINESS',1,2,9200,720),(2001,'BUSINESS',1,3,9200,720),(2001,'BUSINESS',1,4,9200,720),
(2001,'BUSINESS',2,1,9200,720),(2001,'BUSINESS',2,2,9200,720),(2001,'BUSINESS',2,3,9200,720),(2001,'BUSINESS',2,4,9200,720);

