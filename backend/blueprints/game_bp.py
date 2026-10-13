# -*- coding: utf-8 -*-
"""成绩模块（一）：保存对局、个人对局列表、个人最高分（F-10、F-11）。"""
from flask import Blueprint, request, g

from db import query_one, query_all, execute
from utils import success, fail, fmt_dt, parse_dt, parse_pagination, to_int
from auth import token_required

bp = Blueprint('game', __name__)


def _game_dict(row):
    return {
        'id': row['id'],
        'score': row['score'],
        'lines_cleared': row['lines_cleared'],
        'duration': row['duration'],
        'level': row['level'],
        'start_time': fmt_dt(row['start_time']),
        'end_time': fmt_dt(row['end_time']),
    }


@bp.post('/api/games')
@token_required
def save_game():
    """游戏结束后保存对局数据（起止时间、时长、得分、行数、等级）。"""
    body = request.get_json(silent=True) or {}

    start = parse_dt(body.get('start_time'))
    end = parse_dt(body.get('end_time'))
    if start is None or end is None:
        return fail('对局起止时间格式不正确', 400)
    if end < start:
        return fail('对局结束时间不能早于开始时间', 400)

    duration = int((end - start).total_seconds())
    if not (0 <= duration <= 24 * 3600):
        return fail('游戏时长超出合理范围', 400)

    score, err = to_int(body.get('score'), 'score', minimum=0, maximum=10 ** 9)
    if err:
        return fail(err, 400)
    lines, err = to_int(body.get('lines_cleared'), 'lines_cleared', minimum=0, maximum=1000)
    if err:
        return fail(err, 400)
    level, err = to_int(body.get('level'), 'level', minimum=1, maximum=20)
    if err:
        return fail(err, 400)

    game_id = execute(
        'INSERT INTO game_score (user_id, start_time, end_time, duration, '
        'score, lines_cleared, level) VALUES (%s, %s, %s, %s, %s, %s, %s)',
        (g.user['id'], start, end, duration, score, lines, level),
    )
    return success({'game_id': game_id}, '成绩已保存')


@bp.get('/api/games/highscore')
@token_required
def get_highscore():
    row = query_one(
        'SELECT COALESCE(MAX(score), 0) AS highscore FROM game_score WHERE user_id = %s',
        (g.user['id'],),
    )
    return success({'highscore': int(row['highscore'] or 0)})


@bp.get('/api/games')
@token_required
def list_games():
    """按对局时间倒序分页返回当前用户的历史对局记录。"""
    page, page_size = parse_pagination(request.args)
    offset = (page - 1) * page_size

    total_row = query_one(
        'SELECT COUNT(*) AS cnt FROM game_score WHERE user_id = %s',
        (g.user['id'],),
    )
    rows = query_all(
        'SELECT id, score, lines_cleared, duration, level, start_time, end_time '
        'FROM game_score WHERE user_id = %s ORDER BY end_time DESC, id DESC '
        'LIMIT %s OFFSET %s',
        (g.user['id'], page_size, offset),
    )
    return success({
        'total': total_row['cnt'],
        'page': page,
        'page_size': page_size,
        'list': [_game_dict(r) for r in rows],
    })
