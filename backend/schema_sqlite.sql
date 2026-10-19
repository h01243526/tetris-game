-- ======================================================================
-- 基于 Flask + HTML5 Canvas 的俄罗斯方块游戏  数据库建表脚本
-- SQLite 3.25+（PythonAnywhere 免费版等无独立数据库平台使用）
-- 表：user / game_score / operation_log / difficulty_level / login_log
-- 视图：leaderboard_view
-- ======================================================================

-- 用户表
CREATE TABLE IF NOT EXISTS `user` (
  `id`            INTEGER      PRIMARY KEY AUTOINCREMENT,
  `username`      VARCHAR(50)  NOT NULL UNIQUE,
  `password_hash` VARCHAR(255) NOT NULL,
  `nickname`      VARCHAR(50)  DEFAULT NULL,
  `email`         VARCHAR(100) DEFAULT NULL,
  `role`          VARCHAR(20)  NOT NULL DEFAULT 'player',
  `status`        INTEGER      NOT NULL DEFAULT 1,
  `created_at`    DATETIME     NOT NULL DEFAULT (datetime('now', 'localtime')),
  `last_login_at` DATETIME     DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS `idx_user_status` ON `user` (`status`);

-- 对局记录表（user 1:N game_score）
CREATE TABLE IF NOT EXISTS `game_score` (
  `id`            INTEGER  PRIMARY KEY AUTOINCREMENT,
  `user_id`       INTEGER  NOT NULL,
  `start_time`    DATETIME NOT NULL,
  `end_time`      DATETIME NOT NULL,
  `duration`      INTEGER  NOT NULL,
  `score`         INTEGER  NOT NULL DEFAULT 0,
  `lines_cleared` INTEGER  NOT NULL DEFAULT 0,
  `level`         INTEGER  NOT NULL DEFAULT 1,
  FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX IF NOT EXISTS `idx_game_user` ON `game_score` (`user_id`);
CREATE INDEX IF NOT EXISTS `idx_game_score` ON `game_score` (`score`);
CREATE INDEX IF NOT EXISTS `idx_game_end_time` ON `game_score` (`end_time`);

-- 管理员操作日志表
CREATE TABLE IF NOT EXISTS `operation_log` (
  `id`         INTEGER      PRIMARY KEY AUTOINCREMENT,
  `admin_id`   INTEGER      NOT NULL,
  `action`     VARCHAR(50)  NOT NULL,
  `target`     VARCHAR(100) DEFAULT NULL,
  `detail`     VARCHAR(255) DEFAULT NULL,
  `created_at` DATETIME     NOT NULL DEFAULT (datetime('now', 'localtime')),
  FOREIGN KEY (`admin_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX IF NOT EXISTS `idx_oplog_admin` ON `operation_log` (`admin_id`);

-- 难度等级配置表
CREATE TABLE IF NOT EXISTS `difficulty_level` (
  `id`               INTEGER     PRIMARY KEY AUTOINCREMENT,
  `level`            INTEGER     NOT NULL UNIQUE,
  `level_name`       VARCHAR(50) NOT NULL,
  `drop_interval_ms` INTEGER     NOT NULL,
  `upgrade_lines`    INTEGER     NOT NULL DEFAULT 10,
  `score_multiplier` REAL        NOT NULL DEFAULT 1.00,
  `updated_at`       DATETIME    DEFAULT NULL
);

-- 登录日志表
CREATE TABLE IF NOT EXISTS `login_log` (
  `id`           INTEGER      PRIMARY KEY AUTOINCREMENT,
  `user_id`      INTEGER      DEFAULT NULL,
  `login_time`   DATETIME     NOT NULL,
  `login_ip`     VARCHAR(50)  DEFAULT NULL,
  `login_status` INTEGER      NOT NULL DEFAULT 1,
  `fail_reason`  VARCHAR(100) DEFAULT NULL,
  FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX IF NOT EXISTS `idx_loginlog_user_time` ON `login_log` (`user_id`, `login_time`);

-- 排行榜视图：每个用户仅取其历史最高分一条记录，按分数降序生成名次
DROP VIEW IF EXISTS `leaderboard_view`;
CREATE VIEW `leaderboard_view` AS
SELECT
  ROW_NUMBER() OVER (ORDER BY t.`score` DESC, t.`end_time` ASC) AS `rank`,
  u.`username`                                                  AS `username`,
  t.`score`                                                     AS `score`,
  t.`lines_cleared`                                             AS `lines_cleared`,
  date(t.`end_time`)                                            AS `played_at`
FROM (
  SELECT `user_id`, `score`, `lines_cleared`, `end_time`,
         ROW_NUMBER() OVER (PARTITION BY `user_id` ORDER BY `score` DESC, `end_time` ASC) AS rn
  FROM `game_score`
) t
JOIN `user` u ON u.`id` = t.`user_id`
WHERE u.`status` = 1 AND t.`rn` = 1;
