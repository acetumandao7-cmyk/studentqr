CREATE DATABASE IF NOT EXISTS `student_attendance_qr`
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE `student_attendance_qr`;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `full_name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `role` ENUM('Administrator', 'Teacher') NOT NULL DEFAULT 'Teacher',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `last_login` DATETIME NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_username` (`username`),
    INDEX `idx_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `sessions`;
CREATE TABLE `sessions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `start_time` TIME NOT NULL,
    `late_threshold_time` TIME NOT NULL,
    `end_time` TIME NOT NULL,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `students`;
CREATE TABLE `students` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` VARCHAR(50) NOT NULL UNIQUE,
    `first_name` VARCHAR(50) NOT NULL,
    `last_name` VARCHAR(50) NOT NULL,
    `gender` ENUM('Male', 'Female', 'Other') NOT NULL DEFAULT 'Male',
    `year_level` VARCHAR(20) NOT NULL DEFAULT '1st Year',
    `course_grade` VARCHAR(100) NOT NULL,
    `section` VARCHAR(50) NOT NULL,
    `teacher_id` INT NULL,
    `subject` VARCHAR(100) NULL,
    `class_time` VARCHAR(100) NULL,
    `guardian_name` VARCHAR(100) NULL,
    `guardian_contact` VARCHAR(30) NULL,
    `qr_code_token` VARCHAR(128) NOT NULL UNIQUE,
    `qr_image_path` VARCHAR(255) NULL,
    `status` ENUM('Active', 'Inactive') NOT NULL DEFAULT 'Active',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_students_teacher`
        FOREIGN KEY (`teacher_id`) REFERENCES `users` (`id`)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX `idx_student_id` (`student_id`),
    INDEX `idx_qr_token` (`qr_code_token`),
    INDEX `idx_section` (`section`),
    INDEX `idx_course_grade` (`course_grade`),
    INDEX `idx_teacher_id` (`teacher_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `attendance_records`;
CREATE TABLE `attendance_records` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `session_id` INT NOT NULL,
    `date` DATE NOT NULL,
    `timestamp` DATETIME NOT NULL,
    `status` ENUM('Present', 'Late', 'Absent') NOT NULL DEFAULT 'Present',
    `scanned_by` INT NULL,
    `scan_method` ENUM('QR_SCAN', 'MANUAL_OVERRIDE') NOT NULL DEFAULT 'QR_SCAN',
    `remarks` VARCHAR(255) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT `fk_attendance_student`
        FOREIGN KEY (`student_id`) REFERENCES `students` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_attendance_session`
        FOREIGN KEY (`session_id`) REFERENCES `sessions` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_attendance_scanned_by`
        FOREIGN KEY (`scanned_by`) REFERENCES `users` (`id`)
        ON DELETE SET NULL ON UPDATE CASCADE,

    UNIQUE KEY `unique_student_session_date` (`student_id`, `session_id`, `date`),

    INDEX `idx_date` (`date`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `system_logs`;
CREATE TABLE `system_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NULL,
    `action` VARCHAR(100) NOT NULL,
    `details` TEXT NULL,
    `ip_address` VARCHAR(45) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT `fk_logs_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX `idx_action` (`action`),
    INDEX `idx_log_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
