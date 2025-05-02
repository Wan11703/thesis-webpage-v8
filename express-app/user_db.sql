 CREATE SCHEMA `user_db` ;
 USE user_db;
 
 CREATE TABLE IF NOT EXISTS user_tbl (
     user_id INT AUTO_INCREMENT PRIMARY KEY,
     username VARCHAR(100) NOT NULL,
     email VARCHAR(150) NOT NULL,
     password VARCHAR(255) NOT NULL,
     image LONGBLOB,
     image_type VARCHAR(255)
 );

CREATE TABLE user_history_tbl (
  history_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  history_save LONGTEXT,
  history_datetime DATETIME,
  FOREIGN KEY (user_id) REFERENCES user_tbl(user_id) ON DELETE CASCADE
);

