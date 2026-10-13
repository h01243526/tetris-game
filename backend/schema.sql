-- ======================================================================
-- 基于 Flask + HTML5 Canvas 的俄罗斯方块游戏  数据库建表脚本
-- MySQL 8.0+
-- 表：user / game_score / operation_log / difficulty_level / login_log
-- 视图：leaderboard_view
-- ======================================================================

-- ----------------------------------------------------------------------
-- 用户表
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user` (
  `id`            INT          NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username`      VARCHAR(50)  NOT NULL                COMMENT '用户名（唯一）',
  `password_hash` VARCHAR(255) NOT NULL                COMMENT 'Werkzeug.security 密码哈希密文',
  `nickname`      VARCHAR(50)  DEFAULT NULL            COMMENT '昵称',
  `email`         VARCHAR(100) DEFAULT NULL            COMMENT '邮箱（预留找回密码）',
  `role`          VARCHAR(20)  NOT NULL DEFAULT 'player' COMMENT '角色：player 玩家 / admin 管理员',
  `status`        TINYINT      NOT NULL DEFAULT 1      COMMENT '账号状态：1 正常 / 0 禁用',
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
  `last_login_at` DATETIME     DEFAULT NULL            COMMENT '最后登录时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_username` (`username`),
  KEY `idx_user_status` (`status`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '用户表';

-- ----------------------------------------------------------------------
-- 对局记录表（user 1:N game_score）
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `game_score` (
  `id`            INT      NOT NULL AUTO_INCREMENT COMMENT '对局ID',
  `user_id`       INT      NOT NULL                COMMENT '用户ID（外键 -> user.id）',
  `start_time`    DATETIME NOT NULL                COMMENT '对局开始时间',
  `end_time`      DATETIME NOT NULL                COMMENT '对局结束时间',
  `duration`      INT      NOT NULL                COMMENT '游戏时长（秒）',
  `score`         INT      NOT NULL DEFAULT 0      COMMENT '本局得分',
  `lines_cleared` INT      NOT NULL DEFAULT 0      COMMENT '消除行数',
  `level`         INT      NOT NULL DEFAULT 1      COMMENT '对局结束时等级',
  PRIMARY KEY (`id`),
  KEY `idx_game_user` (`user_id`),
  KEY `idx_game_score` (`score`),
  KEY `idx_game_end_time` (`end_time`),
  CONSTRAINT `fk_game_user` FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '对局记录表';

-- ----------------------------------------------------------------------
-- 管理员操作日志表
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `operation_log` (
  `id`         INT          NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `admin_id`   INT          NOT NULL                COMMENT '操作管理员ID（外键 -> user.id）',
  `action`     VARCHAR(50)  NOT NULL                COMMENT '操作类型，如 delete_user / update_status',
  `target`     VARCHAR(100) DEFAULT NULL            COMMENT '操作对象，如 user:3',
  `detail`     VARCHAR(255) DEFAULT NULL            COMMENT '操作详情',
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  PRIMARY KEY (`id`),
  KEY `idx_oplog_admin` (`admin_id`),
  CONSTRAINT `fk_oplog_admin` FOREIGN KEY (`admin_id`)
    REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '管理员操作日志表';

-- ----------------------------------------------------------------------
-- 难度等级配置表（独立配置表，不建外键）
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `difficulty_level` (
  `id`               INT          NOT NULL AUTO_INCREMENT COMMENT '难度ID',
  `level`            TINYINT      NOT NULL                COMMENT '等级号',
  `level_name`       VARCHAR(50)  NOT NULL                COMMENT '等级名称（简单/普通/困难/专家）',
  `drop_interval_ms` INT          NOT NULL                COMMENT '方块下落间隔（毫秒，越小越快）',
  `upgrade_lines`    INT          NOT NULL DEFAULT 10     COMMENT '升级所需消除行数',
  `score_multiplier` DECIMAL(3,2) NOT NULL DEFAULT 1.00   COMMENT '计分倍率',
  `updated_at`      DATETIME     DEFAULT NULL            COMMENT '配置更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_diff_level` (`level`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '难度等级配置表';

-- ----------------------------------------------------------------------
-- 登录日志表（用户名为空的失败登录 user_id 记 NULL，用于安全审计）
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `login_log` (
  `id`           INT          NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `user_id`      INT          DEFAULT NULL            COMMENT '用户ID（外键 -> user.id）',
  `login_time`   DATETIME     NOT NULL                COMMENT '登录时间',
  `login_ip`     VARCHAR(50)  DEFAULT NULL            COMMENT '登录IP',
  `login_status` TINYINT      NOT NULL DEFAULT 1      COMMENT '登录结果：1 成功 / 0 失败',
  `fail_reason`  VARCHAR(100) DEFAULT NULL            COMMENT '失败原因',
  PRIMARY KEY (`id`),
  KEY `idx_loginlog_user_time` (`user_id`, `login_time`),
  CONSTRAINT `fk_loginlog_user` FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '登录日志表';

-- ----------------------------------------------------------------------
-- 排行榜视图：每个用户仅取其历史最高分一条记录，按分数降序生成名次
-- 不存储实际数据；played_at 精确到日期（YYYY-MM-DD）
-- ----------------------------------------------------------------------
CREATE OR REPLACE VIEW `leaderboard_view` AS
SELECT
  ROW_NUMBER() OVER (ORDER BY t.`score` DESC, t.`end_time` ASC) AS `rank`,
  u.`username`                                                  AS `username`,
  t.`score`                                                     AS `score`,
  t.`lines_cleared`                                             AS `lines_cleared`,
  DATE_FORMAT(t.`end_time`, '%Y-%m-%d')                          AS `played_at`
FROM (
  SELECT `user_id`, `score`, `lines_cleared`, `end_time`,
         ROW_NUMBER() OVER (PARTITION BY `user_id` ORDER BY `score` DESC, `end_time` ASC) AS rn
  FROM `game_score`
) t
JOIN `user` u ON u.`id` = t.`user_id`
WHERE u.`status` = 1 AND t.`rn` = 1;
