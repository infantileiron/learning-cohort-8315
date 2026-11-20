-- MySQL 8 actual DDL; generated after acceptance, seed counters removed.
CREATE TABLE `audits` (
  `id` int NOT NULL AUTO_INCREMENT,
  `actor` varchar(100) DEFAULT NULL,
  `action` varchar(200) DEFAULT NULL,
  `created` varchar(40) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `cohorts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT NULL,
  `start_week` varchar(10) DEFAULT NULL,
  `end_week` varchar(10) DEFAULT NULL,
  `as_of` varchar(10) DEFAULT NULL,
  `horizon` int DEFAULT NULL,
  `state` varchar(20) DEFAULT NULL,
  `result` json DEFAULT NULL,
  `error` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `events` (
  `id` int NOT NULL AUTO_INCREMENT,
  `code` varchar(60) NOT NULL,
  `learner` varchar(60) NOT NULL,
  `occurred_at` varchar(40) NOT NULL,
  `course` varchar(40) DEFAULT NULL,
  `note` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`),
  KEY `ix_events_learner` (`learner`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(100) NOT NULL,
  `password` varchar(200) DEFAULT NULL,
  `role` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `interventions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cohort_id` int DEFAULT NULL,
  `scheme_id` int DEFAULT NULL,
  `source` varchar(10) DEFAULT 'cohort',
  `cohort_week` varchar(10) DEFAULT NULL,
  `week_index` int DEFAULT NULL,
  `note` text,
  `members` json DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_intervention_source_scheme` (`source`,`scheme_id`),
  KEY `cohort_id` (`cohort_id`),
  KEY `scheme_id` (`scheme_id`),
  CONSTRAINT `interventions_ibfk_1` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`id`),
  CONSTRAINT `interventions_ibfk_2` FOREIGN KEY (`scheme_id`) REFERENCES `risk_schemes` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `meta` (
  `key` varchar(40) NOT NULL,
  `value` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `risk_schemes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT NULL,
  `as_of` varchar(10) DEFAULT NULL,
  `state` varchar(20) DEFAULT 'queued',
  `threshold` double DEFAULT NULL,
  `rationale` text,
  `event_version` int DEFAULT 0,
  `result` json DEFAULT NULL,
  `error` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `risk_scores` (
  `id` int NOT NULL AUTO_INCREMENT,
  `scheme_id` int DEFAULT NULL,
  `learner` varchar(60) DEFAULT NULL,
  `score` double DEFAULT NULL,
  `level` varchar(10) DEFAULT NULL,
  `event_version` int DEFAULT NULL,
  `train_range` varchar(80) DEFAULT NULL,
  `status` varchar(20) DEFAULT 'valid',
  `reason` varchar(300) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_risk_scores_scheme_id` (`scheme_id`),
  KEY `ix_risk_scores_learner` (`learner`),
  CONSTRAINT `risk_scores_ibfk_1` FOREIGN KEY (`scheme_id`) REFERENCES `risk_schemes` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

