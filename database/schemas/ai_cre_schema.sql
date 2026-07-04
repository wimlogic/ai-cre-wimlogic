-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: ai_cre
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `api_usage_logs`
--

DROP TABLE IF EXISTS `api_usage_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `api_usage_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `provider` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `api_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `endpoint` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `request_count` int DEFAULT '1',
  `estimated_cost` decimal(10,4) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_concept_designs`
--

DROP TABLE IF EXISTS `cre_concept_designs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_concept_designs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` varchar(100) NOT NULL,
  `property_id` bigint NOT NULL,
  `scenario_id` int DEFAULT NULL,
  `title` varchar(255) DEFAULT NULL,
  `concept_prompt` text NOT NULL,
  `concept_notes` text,
  `image_reference_ids` json DEFAULT NULL,
  `status` varchar(50) NOT NULL DEFAULT 'draft',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `workflow_execution_id` bigint DEFAULT NULL,
  `design_version` varchar(30) DEFAULT NULL,
  `approved_by` bigint DEFAULT NULL,
  `approved_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_concepts_project_property` (`project_id`,`property_id`),
  KEY `idx_concepts_scenario_id` (`scenario_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_estimates`
--

DROP TABLE IF EXISTS `cre_estimates`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_estimates` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `property_id` bigint NOT NULL,
  `scenario` enum('cosmetic','heavy_remodel','demo_rebuild','custom') COLLATE utf8mb4_unicode_ci NOT NULL,
  `proposed_use` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proposed_building_sqft` int DEFAULT NULL,
  `proposed_units` int DEFAULT NULL,
  `low_cost` decimal(14,2) DEFAULT NULL,
  `mid_cost` decimal(14,2) DEFAULT NULL,
  `high_cost` decimal(14,2) DEFAULT NULL,
  `cost_per_sqft_low` decimal(10,2) DEFAULT NULL,
  `cost_per_sqft_high` decimal(10,2) DEFAULT NULL,
  `assumptions` text COLLATE utf8mb4_unicode_ci,
  `risk_level` enum('low','medium','high') COLLATE utf8mb4_unicode_ci DEFAULT 'medium',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `workflow_execution_id` bigint DEFAULT NULL,
  `estimate_source` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estimate_version` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `property_id` (`property_id`),
  CONSTRAINT `cre_estimates_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `cre_properties` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_generated_assets`
--

DROP TABLE IF EXISTS `cre_generated_assets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_generated_assets` (
  `asset_id` bigint NOT NULL AUTO_INCREMENT,
  `execution_id` bigint NOT NULL,
  `property_id` bigint NOT NULL,
  `asset_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `asset_category` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `file_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `storage_path` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `thumbnail_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mime_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `file_size` bigint DEFAULT NULL,
  `version` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`asset_id`),
  KEY `idx_asset_execution` (`execution_id`),
  KEY `idx_asset_property` (`property_id`),
  CONSTRAINT `fk_asset_execution` FOREIGN KEY (`execution_id`) REFERENCES `cre_workflow_executions` (`execution_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_project_properties`
--

DROP TABLE IF EXISTS `cre_project_properties`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_project_properties` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` varchar(100) NOT NULL,
  `property_id` bigint NOT NULL,
  `scan_id` varchar(100) DEFAULT NULL,
  `role` varchar(100) DEFAULT NULL,
  `selected` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_project_property` (`project_id`,`property_id`),
  KEY `idx_project_properties_project_id` (`project_id`),
  KEY `idx_project_properties_property_id` (`property_id`),
  KEY `idx_project_properties_scan_id` (`scan_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1802 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_projects`
--

DROP TABLE IF EXISTS `cre_projects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_projects` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` varchar(100) NOT NULL,
  `project_name` varchar(255) NOT NULL,
  `description` text,
  `status` varchar(50) NOT NULL DEFAULT 'active',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `default_city` varchar(120) DEFAULT NULL,
  `default_state` varchar(50) DEFAULT NULL,
  `main_street` varchar(255) DEFAULT NULL,
  `beginning_address` varchar(255) DEFAULT NULL,
  `ending_address` varchar(255) DEFAULT NULL,
  `side` varchar(50) DEFAULT NULL,
  `scan_mode` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `project_id` (`project_id`),
  KEY `idx_cre_projects_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_properties`
--

DROP TABLE IF EXISTS `cre_properties`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_properties` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `property_uid` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `address` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `state` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `zip` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `apn` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `latitude` decimal(10,7) DEFAULT NULL,
  `longitude` decimal(10,7) DEFAULT NULL,
  `lot_sqft` int DEFAULT NULL,
  `building_sqft` int DEFAULT NULL,
  `year_built` int DEFAULT NULL,
  `zoning_code` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `existing_use` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `business_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `land_value` decimal(14,2) DEFAULT NULL,
  `improvement_value` decimal(14,2) DEFAULT NULL,
  `total_assessed_value` decimal(14,2) DEFAULT NULL,
  `data_source` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `street_number` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `street_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `side_of_street` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phase2_source` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `display_address` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  `confidence_score` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `raw_api_json` longtext COLLATE utf8mb4_unicode_ci,
  `api_source_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `property_uid` (`property_uid`),
  KEY `idx_address` (`address`),
  KEY `idx_apn` (`apn`),
  KEY `idx_city_street` (`city`,`address`),
  KEY `idx_cre_properties_street_number` (`street_number`),
  KEY `idx_cre_properties_street_name` (`street_name`)
) ENGINE=InnoDB AUTO_INCREMENT=926 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_property_analysis_reports`
--

DROP TABLE IF EXISTS `cre_property_analysis_reports`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_property_analysis_reports` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` varchar(100) NOT NULL,
  `property_id` bigint NOT NULL,
  `scenario_id` int DEFAULT NULL,
  `estimate_low` decimal(14,2) DEFAULT NULL,
  `estimate_high` decimal(14,2) DEFAULT NULL,
  `zoning_notes` text,
  `risk_notes` text,
  `recommendation` text,
  `score` decimal(5,2) DEFAULT NULL,
  `report_json` json DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `workflow_execution_id` bigint DEFAULT NULL,
  `workflow_result_id` bigint DEFAULT NULL,
  `analysis_version` varchar(30) DEFAULT NULL,
  `confidence_score` decimal(5,2) DEFAULT NULL,
  `workflow_status` varchar(30) DEFAULT NULL,
  `completed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_reports_project_property` (`project_id`,`property_id`),
  KEY `idx_reports_scenario_id` (`scenario_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_property_images`
--

DROP TABLE IF EXISTS `cre_property_images`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_property_images` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `property_id` bigint NOT NULL,
  `image_type` enum('street_view','satellite','parcel_map','uploaded') COLLATE utf8mb4_unicode_ci NOT NULL,
  `image_url` text COLLATE utf8mb4_unicode_ci,
  `provider` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `heading` decimal(8,3) DEFAULT NULL,
  `pitch` decimal(8,3) DEFAULT NULL,
  `fov` decimal(8,3) DEFAULT NULL,
  `cached_path` text COLLATE utf8mb4_unicode_ci,
  `last_checked_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `project_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `original_file_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `file_size` int DEFAULT NULL,
  `file_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `image_role` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `property_id` (`property_id`),
  CONSTRAINT `cre_property_images_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `cre_properties` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_renovation_scenarios`
--

DROP TABLE IF EXISTS `cre_renovation_scenarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_renovation_scenarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` varchar(100) NOT NULL,
  `property_id` bigint NOT NULL,
  `renovation_type` varchar(100) NOT NULL,
  `scenario_type` varchar(100) DEFAULT NULL,
  `scenario_name` varchar(255) DEFAULT NULL,
  `rationale` text,
  `risk_level` varchar(50) DEFAULT NULL,
  `estimated_complexity` varchar(50) DEFAULT NULL,
  `custom_notes` text,
  `status` varchar(50) NOT NULL DEFAULT 'draft',
  `source` varchar(100) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_scenarios_project_property` (`project_id`,`property_id`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_result_sections`
--

DROP TABLE IF EXISTS `cre_result_sections`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_result_sections` (
  `section_id` bigint NOT NULL AUTO_INCREMENT,
  `result_id` bigint NOT NULL,
  `section_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `display_order` int NOT NULL DEFAULT '0',
  `title` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `content` longtext COLLATE utf8mb4_unicode_ci,
  `confidence_score` decimal(5,2) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`section_id`),
  KEY `idx_section_result` (`result_id`),
  CONSTRAINT `fk_section_result` FOREIGN KEY (`result_id`) REFERENCES `cre_workflow_results` (`result_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_scan_jobs`
--

DROP TABLE IF EXISTS `cre_scan_jobs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_scan_jobs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `scan_id` varchar(100) NOT NULL,
  `project_id` varchar(100) NOT NULL,
  `project_name` varchar(255) NOT NULL,
  `main_street` varchar(255) NOT NULL,
  `beginning_address` varchar(255) NOT NULL,
  `ending_address` varchar(255) NOT NULL,
  `side_selection` varchar(50) NOT NULL DEFAULT 'both',
  `status` varchar(50) NOT NULL DEFAULT 'created',
  `found_count` int NOT NULL DEFAULT '0',
  `notes` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `scan_source` varchar(120) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `scan_id` (`scan_id`),
  KEY `idx_scan_jobs_project_id` (`project_id`),
  KEY `idx_scan_jobs_scan_id` (`scan_id`)
) ENGINE=InnoDB AUTO_INCREMENT=44 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_scan_properties`
--

DROP TABLE IF EXISTS `cre_scan_properties`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_scan_properties` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `scan_id` bigint NOT NULL,
  `property_id` bigint NOT NULL,
  `scan_order` int DEFAULT NULL,
  `side_of_street` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `frontage_street` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `included_reason` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_scan_property` (`scan_id`,`property_id`),
  KEY `property_id` (`property_id`),
  CONSTRAINT `cre_scan_properties_ibfk_1` FOREIGN KEY (`scan_id`) REFERENCES `cre_scans` (`id`),
  CONSTRAINT `cre_scan_properties_ibfk_2` FOREIGN KEY (`property_id`) REFERENCES `cre_properties` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3126 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_scans`
--

DROP TABLE IF EXISTS `cre_scans`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_scans` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `scan_uid` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `state` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `main_street` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `start_address` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `end_address` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `side` enum('north','south','east','west','both') COLLATE utf8mb4_unicode_ci DEFAULT 'both',
  `scan_mode` enum('quick','full') COLLATE utf8mb4_unicode_ci DEFAULT 'quick',
  `status` enum('pending','processing','complete','failed') COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `project_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `project_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `scan_source` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `scan_uid` (`scan_uid`)
) ENGINE=InnoDB AUTO_INCREMENT=44 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_workflow_events`
--

DROP TABLE IF EXISTS `cre_workflow_events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_workflow_events` (
  `event_id` bigint NOT NULL AUTO_INCREMENT,
  `execution_id` bigint NOT NULL,
  `event_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `message` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`event_id`),
  KEY `idx_event_execution` (`execution_id`),
  CONSTRAINT `fk_event_execution` FOREIGN KEY (`execution_id`) REFERENCES `cre_workflow_executions` (`execution_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_workflow_executions`
--

DROP TABLE IF EXISTS `cre_workflow_executions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_workflow_executions` (
  `execution_id` bigint NOT NULL AUTO_INCREMENT,
  `execution_number` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `project_id` bigint NOT NULL,
  `property_id` bigint NOT NULL,
  `scenario_id` bigint DEFAULT NULL,
  `workflow_code` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `workflow_version` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `devtools_execution_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Submitted',
  `priority` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Normal',
  `requested_by` bigint DEFAULT NULL,
  `submitted_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `started_at` datetime DEFAULT NULL,
  `completed_at` datetime DEFAULT NULL,
  `retry_count` int NOT NULL DEFAULT '0',
  `error_message` text COLLATE utf8mb4_unicode_ci,
  `metadata_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`execution_id`),
  UNIQUE KEY `execution_number` (`execution_number`),
  KEY `idx_exec_project` (`project_id`),
  KEY `idx_exec_property` (`property_id`),
  KEY `idx_exec_status` (`status`),
  KEY `idx_exec_submitted` (`submitted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_workflow_results`
--

DROP TABLE IF EXISTS `cre_workflow_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_workflow_results` (
  `result_id` bigint NOT NULL AUTO_INCREMENT,
  `execution_id` bigint NOT NULL,
  `result_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `result_version` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `response_json` longtext COLLATE utf8mb4_unicode_ci,
  `normalized` tinyint(1) NOT NULL DEFAULT '0',
  `received_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`result_id`),
  KEY `idx_result_execution` (`execution_id`),
  CONSTRAINT `fk_result_execution` FOREIGN KEY (`execution_id`) REFERENCES `cre_workflow_executions` (`execution_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cre_zoning_notes`
--

DROP TABLE IF EXISTS `cre_zoning_notes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cre_zoning_notes` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `property_id` bigint NOT NULL,
  `zoning_code` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `allowed_use_summary` text COLLATE utf8mb4_unicode_ci,
  `conditional_use_notes` text COLLATE utf8mb4_unicode_ci,
  `parking_notes` text COLLATE utf8mb4_unicode_ci,
  `entitlement_risk` enum('low','medium','high') COLLATE utf8mb4_unicode_ci DEFAULT 'medium',
  `source_url` text COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `property_id` (`property_id`),
  CONSTRAINT `cre_zoning_notes_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `cre_properties` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-28 16:07:58
