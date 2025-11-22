"""
通用依赖注入
"""
from typing import Tuple, Optional, Dict, Any
from fastapi import Query, Depends
from datetime import datetime

# from ..schemas.common import PaginationParams  # 简化实现，直接使用元组


def get_pagination_params(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数")
) -> Tuple[int, int]:
    """获取分页参数"""
    return (skip, limit)


def get_search_params(
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序顺序")
) -> Dict[str, Any]:
    """获取搜索参数"""
    return {
        "search": search,
        "sort_by": sort_by,
        "sort_order": sort_order
    }


def get_date_range_params(
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期")
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """获取日期范围参数"""
    if start_date and end_date and start_date > end_date:
        raise ValueError("开始日期不能晚于结束日期")
    return start_date, end_date


def get_id_list_params(
    ids: str = Query(..., description="ID列表，逗号分隔")
) -> list[int]:
    """获取ID列表参数"""
    try:
        id_list = [int(id.strip()) for id in ids.split(",") if id.strip()]
        if not id_list:
            raise ValueError("ID列表不能为空")
        if len(id_list) > 100:  # 限制最大数量
            raise ValueError("ID列表数量不能超过100个")
        return id_list
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError("ID必须为整数")
        raise