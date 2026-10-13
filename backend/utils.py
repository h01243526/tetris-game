# -*- coding: utf-8 -*-
"""通用工具：统一响应格式、时间解析与格式化、参数校验。"""
from datetime import datetime, date
from flask import jsonify

DT_FMT = '%Y-%m-%d %H:%M:%S'


def success(data=None, message='success', http_status=200):
    """统一成功响应。"""
    return jsonify({'code': 200, 'message': message, 'data': data if data is not None else {}}), http_status


def fail(message, http_status=400, data=None):
    """统一失败响应。"""
    return jsonify({'code': http_status, 'message': message, 'data': data or {}}), http_status


def fmt_dt(value):
    """datetime -> 'YYYY-MM-DD HH:MM:SS'；date -> 'YYYY-MM-DD'。"""
    if isinstance(value, datetime):
        return value.strftime(DT_FMT)
    if isinstance(value, date):
        return value.strftime('%Y-%m-%d')
    return value


def parse_dt(value):
    """解析前端传入的时间字符串，返回 naive datetime；失败返回 None。"""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    # Python 3.11+ 的 fromisoformat 可兼容 'YYYY-MM-DD HH:MM:SS' 与 ISO 两种写法
    try:
        dt = datetime.fromisoformat(text.replace('Z', ''))
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except ValueError:
        pass
    for fmt in (DT_FMT, '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d'):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def to_int(value, field_name, minimum=None, maximum=None, required=True):
    """安全转换整数并做范围校验，返回 (值, 错误信息)。"""
    if value is None or value == '':
        if required:
            return None, f'缺少参数：{field_name}'
        return None, None
    if isinstance(value, bool):
        return None, f'参数 {field_name} 格式错误'
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None, f'参数 {field_name} 必须为整数'
    if minimum is not None and result < minimum:
        return None, f'参数 {field_name} 不能小于 {minimum}'
    if maximum is not None and result > maximum:
        return None, f'参数 {field_name} 不能大于 {maximum}'
    return result, None


def parse_pagination(args, default_size=10, max_size=50):
    """解析分页参数 page / page_size。"""
    page, err = to_int(args.get('page', 1), 'page', minimum=1, required=False)
    if err:
        page = 1
    size, err = to_int(args.get('page_size', default_size), 'page_size', minimum=1, maximum=max_size, required=False)
    if err:
        size = default_size
    return page or 1, size or default_size
