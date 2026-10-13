# -*- coding: utf-8 -*-
"""成绩模块（三）：多维度排行榜（总榜 / 日榜 / 周榜，F-12）。"""
from flask import Blueprint, request, g

from db import query_all, query_one
from utils import success, fail, fmt_dt, parse_pagination
from auth import load_current_user

bp = Blueprint('leaderboard', __name__)

# 榜单类型 -> end_time 时间范围条件（参数由 MySQL 端计算）
TYPE_COND = {
    'total': '',
    'day': 'AND g.end_time >= CURDATE()',
    'week': 'AND g.end_time >= DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)',
}

# 每个用户只取其最高分的一条记录（rn = 1），再全局排名；
# played_at 精确到日期（DATE_FORMAT 仅返回 YYYY-MM-DD）
RANK_SUBQUERY = (
    'SELECT ROW_NUMBER() OVER (ORDER BY t.score DESC, t.end_time ASC) AS `rank`, '
    '       u.username, t.score, t.lines_cleared, '
    '       DATE(t.end_time) AS played_at '
    'FROM ('
    '  SELECT g.user_id, g.score, g.lines_cleared, g.end_time, '
    '         ROW_NUMBER() OVER (PARTITION BY g.user_id ORDER BY g.score DESC, g.end_time ASC) AS rn '
    '  FROM game_score g WHERE 1 = 1 {cond}'
    ') t '
    'JOIN `user` u ON u.id = t.user_id AND u.status = 1 '
    'WHERE t.rn = 1'
)


@bp.get('/api/leaderboard')
def get_leaderboard():
    board_type = (request.args.get('type') or 'total').strip()
    if board_type not in TYPE_COND:
        return fail('榜单类型非法，可选 total / day / week', 400)
    page, page_size = parse_pagination(request.args)
    offset = (page - 1) * page_size
    cond = TYPE_COND[board_type]

    # 游客可浏览；若携带了有效 Token，则额外返回当前用户排名用于高亮
    user, _ = load_current_user(required=False)

    total_row = query_one(
        f'SELECT COUNT(DISTINCT g.user_id) AS cnt FROM game_score g '
        f'JOIN `user` u ON u.id = g.user_id AND u.status = 1 WHERE 1 = 1 {cond}'
    )

    rows = query_all(
        f'SELECT * FROM ({RANK_SUBQUERY.format(cond=cond)}) t '
        f'ORDER BY t.`rank` LIMIT %s OFFSET %s',
        (page_size, offset),
    )
    data = [{
        'rank': r['rank'],
        'username': r['username'],
        'score': r['score'],
        'lines_cleared': r['lines_cleared'],
        'played_at': fmt_dt(r['played_at']),
    } for r in rows]

    my_rank = None
    if user is not None:
        mine = query_one(
            f'SELECT `rank`, username FROM ({RANK_SUBQUERY.format(cond=cond)}) t '
            f'WHERE username = %s ORDER BY `rank` LIMIT 1',
            (user['username'],),
        )
        my_rank = mine['rank'] if mine else None

    return success({
        'type': board_type,
        'total': total_row['cnt'],
        'page': page,
        'page_size': page_size,
        'my_rank': my_rank,
        'list': data,
    })
