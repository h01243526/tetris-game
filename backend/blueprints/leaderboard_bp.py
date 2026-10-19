# -*- coding: utf-8 -*-
"""成绩模块（三）：多维度排行榜（总榜 / 日榜 / 周榜，F-12）。"""
from datetime import datetime, timedelta

from flask import Blueprint, request

from db import query_all, query_one
from utils import success, fail, fmt_dt, parse_pagination
from auth import load_current_user

bp = Blueprint('leaderboard', __name__)


def _type_cond(board_type):
    """返回 (SQL 片段, 参数列表)：日榜=今日 0 点起；周榜=本周一 0 点起。

    日期由 Python 计算后以参数传入，MySQL / SQLite 两种驱动通用。
    """
    today = datetime.now().date()
    if board_type == 'day':
        return 'AND g.end_time >= %s', [today.strftime('%Y-%m-%d')]
    if board_type == 'week':
        monday = today - timedelta(days=today.weekday())
        return 'AND g.end_time >= %s', [monday.strftime('%Y-%m-%d')]
    return '', []

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
    if board_type not in ('total', 'day', 'week'):
        return fail('榜单类型非法，可选 total / day / week', 400)
    page, page_size = parse_pagination(request.args)
    offset = (page - 1) * page_size
    cond, cond_args = _type_cond(board_type)

    # 游客可浏览；若携带了有效 Token，则额外返回当前用户排名用于高亮
    user, _ = load_current_user(required=False)

    total_row = query_one(
        f'SELECT COUNT(DISTINCT g.user_id) AS cnt FROM game_score g '
        f'JOIN `user` u ON u.id = g.user_id AND u.status = 1 WHERE 1 = 1 {cond}',
        cond_args,
    )

    rows = query_all(
        f'SELECT * FROM ({RANK_SUBQUERY.format(cond=cond)}) t '
        f'ORDER BY t.`rank` LIMIT %s OFFSET %s',
        cond_args + [page_size, offset],
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
            cond_args + [user['username']],
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
