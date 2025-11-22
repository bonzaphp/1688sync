"""
商品管理路由
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
import logging

from ...database.connection import get_db
from ...database.models import Product, ProductImage
from ..schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse,
    ProductImageResponse, ProductSearchQuery
)
from ..services.product_service import ProductService
from ..deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=ProductListResponse)
async def list_products(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    status: Optional[str] = Query(None, description="商品状态"),
    sync_status: Optional[str] = Query(None, description="同步状态"),
    category: Optional[str] = Query(None, description="商品分类"),
    seller: Optional[str] = Query(None, description="卖家"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取商品列表"""
    try:
        product_service = ProductService(db)

        # 构建查询参数
        filters = {}
        if status:
            filters["status"] = status
        if sync_status:
            filters["sync_status"] = sync_status
        if category:
            filters["category"] = category
        if seller:
            filters["seller"] = seller
        if search:
            filters["search"] = search

        products, total = await product_service.get_products(
            skip=skip,
            limit=limit,
            filters=filters
        )

        return ProductListResponse(
            products=[ProductResponse.from_orm(product) for product in products],
            total=total,
            skip=skip,
            limit=limit
        )

    except Exception as e:
        logger.error(f"获取商品列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取商品列表失败")


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取单个商品详情"""
    try:
        product_service = ProductService(db)
        product = await product_service.get_product_by_id(product_id)

        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        return ProductResponse.from_orm(product)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取商品详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取商品详情失败")


@router.post("/", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """创建新商品"""
    try:
        product_service = ProductService(db)
        product = await product_service.create_product(product_data)

        return ProductResponse.from_orm(product)

    except Exception as e:
        logger.error(f"创建商品失败: {e}")
        raise HTTPException(status_code=500, detail="创建商品失败")


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """更新商品信息"""
    try:
        product_service = ProductService(db)
        product = await product_service.update_product(product_id, product_data)

        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        return ProductResponse.from_orm(product)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新商品失败: {e}")
        raise HTTPException(status_code=500, detail="更新商品失败")


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """删除商品"""
    try:
        product_service = ProductService(db)
        success = await product_service.delete_product(product_id)

        if not success:
            raise HTTPException(status_code=404, detail="商品不存在")

        return {"message": "商品删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除商品失败: {e}")
        raise HTTPException(status_code=500, detail="删除商品失败")


@router.get("/{product_id}/images", response_model=List[ProductImageResponse])
async def get_product_images(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取商品图片列表"""
    try:
        product_service = ProductService(db)
        images = await product_service.get_product_images(product_id)

        return [ProductImageResponse.from_orm(image) for image in images]

    except Exception as e:
        logger.error(f"获取商品图片失败: {e}")
        raise HTTPException(status_code=500, detail="获取商品图片失败")


@router.post("/{product_id}/sync")
async def sync_product(
    product_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """同步商品数据"""
    try:
        product_service = ProductService(db)

        # 检查商品是否存在
        product = await product_service.get_product_by_id(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        # 添加后台同步任务
        task_id = await product_service.sync_product(product_id, background_tasks)

        return {"message": "同步任务已启动", "task_id": task_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"同步商品失败: {e}")
        raise HTTPException(status_code=500, detail="同步商品失败")


@router.post("/batch-sync")
async def batch_sync_products(
    product_ids: List[int],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """批量同步商品"""
    try:
        product_service = ProductService(db)

        # 添加批量同步任务
        task_id = await product_service.batch_sync_products(product_ids, background_tasks)

        return {"message": "批量同步任务已启动", "task_id": task_id}

    except Exception as e:
        logger.error(f"批量同步商品失败: {e}")
        raise HTTPException(status_code=500, detail="批量同步商品失败")