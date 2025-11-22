import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Avatar,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  Search,
  Add,
  Refresh,
  Download,
  Visibility,
  Edit,
  Delete,
  Sync as SyncIcon
} from '@mui/icons-material';
import { useApi, useDebounce } from '../../hooks/useApi';
import apiService from '../../services/api';
import {
  DataTable,
  ProductStatusIndicator,
  SyncStatusIndicator,
  type TableColumn,
  type DataTableAction
} from '../../components';
import { Product, ProductFilters } from '../../types';

const Products: React.FC = () => {
  const [filters, setFilters] = useState<ProductFilters>({
    page: 1,
    limit: 20,
    search: '',
    status: undefined,
    sync_status: undefined
  });
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  // 防抖搜索
  const debouncedSearch = useDebounce(filters.search, 300);

  // 获取商品列表
  const {
    data: productsData,
    loading: productsLoading,
    error: productsError,
    execute: fetchProducts
  } = useApi(() => apiService.getProducts({
    ...filters,
    search: debouncedSearch
  }), {
    immediate: true
  });

  // 删除商品
  const [deleteProductId, setDeleteProductId] = useState<number | null>(null);
  const {
    data: deleteResult,
    loading: deleteLoading,
    execute: executeDelete
  } = useApi(() => {
    if (!deleteProductId) throw new Error('Product ID is required');
    return apiService.deleteProduct(deleteProductId);
  });

  // 同步商品
  const [syncProductId, setSyncProductId] = useState<number | null>(null);
  const {
    data: syncResult,
    loading: syncLoading,
    execute: executeSync
  } = useApi(() => {
    if (!syncProductId) throw new Error('Product ID is required');
    return apiService.syncProduct(syncProductId);
  });

  // 当搜索词变化时重新获取数据
  useEffect(() => {
    if (filters.page === 1) {
      fetchProducts();
    } else {
      setFilters(prev => ({ ...prev, page: 1 }));
    }
  }, [debouncedSearch]);

  // 当其他筛选条件变化时重新获取数据
  useEffect(() => {
    fetchProducts();
  }, [filters.status, filters.sync_status, filters.page, filters.limit]);

  // 处理删除成功
  useEffect(() => {
    if (deleteResult) {
      fetchProducts();
    }
  }, [deleteResult]);

  // 处理同步成功
  useEffect(() => {
    if (syncResult) {
      fetchProducts();
    }
  }, [syncResult]);

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setFilters(prev => ({ ...prev, search: event.target.value }));
  };

  const handleStatusFilterChange = (event: any) => {
    setFilters(prev => ({ ...prev, status: event.target.value || undefined }));
  };

  const handleSyncStatusFilterChange = (event: any) => {
    setFilters(prev => ({ ...prev, sync_status: event.target.value || undefined }));
  };

  const handlePageChange = (page: number) => {
    setFilters(prev => ({ ...prev, page: page + 1 }));
  };

  const handleRowsPerPageChange = (rowsPerPage: number) => {
    setFilters(prev => ({ ...prev, limit: rowsPerPage, page: 1 }));
  };

  const handleViewProduct = (product: Product) => {
    setSelectedProduct(product);
    setDetailDialogOpen(true);
  };

  const handleEditProduct = (product: Product) => {
    // TODO: 实现编辑功能
    console.log('编辑商品:', product);
  };

  const handleDeleteProduct = async (product: Product) => {
    if (window.confirm(`确定要删除商品 "${product.title}" 吗？`)) {
      setDeleteProductId(product.id);
      await executeDelete();
    }
  };

  const handleSyncProduct = async (product: Product) => {
    setSyncProductId(product.id);
    await executeSync();
  };

  const handleExport = () => {
    // TODO: 实现导出功能
    console.log('导出商品数据');
  };

  // 表格列定义
  const columns: TableColumn[] = [
    {
      id: 'title',
      label: '商品标题',
      minWidth: 200,
      sortable: true,
      format: (value: string, row: Product) => (
        <Box>
          <Typography variant="body2" fontWeight="medium" noWrap>
            {value}
          </Typography>
          {row.subtitle && (
            <Typography variant="caption" color="text.secondary" noWrap>
              {row.subtitle}
            </Typography>
          )}
        </Box>
      )
    },
    {
      id: 'supplier',
      label: '供应商',
      minWidth: 120,
      format: (value: any) => value?.name || '未知供应商'
    },
    {
      id: 'price_range',
      label: '价格范围',
      minWidth: 100,
      align: 'right',
      format: (value: string, row: Product) => {
        if (row.price_min === row.price_max) {
          return `¥${row.price_min}`;
        }
        return `¥${row.price_min} - ¥${row.price_max}`;
      }
    },
    {
      id: 'moq',
      label: '起订量',
      minWidth: 80,
      align: 'right',
      format: (value: number) => value?.toLocaleString() || '-'
    },
    {
      id: 'sales_count',
      label: '销量',
      minWidth: 80,
      align: 'right',
      sortable: true,
      format: (value: number) => value?.toLocaleString() || 0
    },
    {
      id: 'rating',
      label: '评分',
      minWidth: 80,
      align: 'right',
      format: (value: number) => value?.toFixed(1) || '-'
    },
    {
      id: 'status',
      label: '商品状态',
      minWidth: 100,
      format: (value: string, row: Product) => (
        <ProductStatusIndicator
          productStatus={row.status}
          size="small"
        />
      )
    },
    {
      id: 'sync_status',
      label: '同步状态',
      minWidth: 120,
      format: (value: string, row: Product) => (
        <SyncStatusIndicator
          syncStatus={row.sync_status}
          progress={row.sync_status === 'syncing' ? 50 : undefined}
          size="small"
        />
      )
    },
    {
      id: 'actions',
      label: '操作',
      minWidth: 120,
      align: 'center'
    }
  ];

  // 表格操作按钮
  const actions: DataTableAction[] = [
    {
      label: '查看详情',
      icon: <Visibility />,
      onClick: handleViewProduct,
      color: 'info'
    },
    {
      label: '编辑',
      icon: <Edit />,
      onClick: handleEditProduct,
      color: 'primary'
    },
    {
      label: '同步',
      icon: <SyncIcon />,
      onClick: handleSyncProduct,
      disabled: (row: Product) => row.sync_status === 'syncing',
      color: 'success'
    },
    {
      label: '删除',
      icon: <Delete />,
      onClick: handleDeleteProduct,
      color: 'error'
    }
  ];

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        商品管理
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        管理和维护1688商品信息
      </Typography>

      {/* 筛选和操作栏 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', md: '2fr 1fr 1fr 2fr' },
            gap: 2,
            alignItems: 'center'
          }}>
            <TextField
              fullWidth
              placeholder="搜索商品标题..."
              value={filters.search}
              onChange={handleSearchChange}
              InputProps={{
                startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
              }}
            />
            <FormControl fullWidth>
              <InputLabel>商品状态</InputLabel>
              <Select
                value={filters.status || ''}
                onChange={handleStatusFilterChange}
                label="商品状态"
              >
                <MenuItem value="">全部</MenuItem>
                <MenuItem value="active">在售</MenuItem>
                <MenuItem value="inactive">下架</MenuItem>
                <MenuItem value="discontinued">停产</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>同步状态</InputLabel>
              <Select
                value={filters.sync_status || ''}
                onChange={handleSyncStatusFilterChange}
                label="同步状态"
              >
                <MenuItem value="">全部</MenuItem>
                <MenuItem value="pending">等待中</MenuItem>
                <MenuItem value="syncing">同步中</MenuItem>
                <MenuItem value="completed">已完成</MenuItem>
                <MenuItem value="failed">失败</MenuItem>
              </Select>
            </FormControl>
            <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
              <Tooltip title="刷新">
                <IconButton onClick={fetchProducts} disabled={productsLoading}>
                  <Refresh />
                </IconButton>
              </Tooltip>
              <Tooltip title="导出">
                <IconButton onClick={handleExport} disabled={productsLoading}>
                  <Download />
                </IconButton>
              </Tooltip>
              <Button
                variant="contained"
                startIcon={<Add />}
                // onClick={() => {/* TODO: 打开新建商品对话框 */}}
              >
                新建商品
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <DataTable
        columns={columns}
        data={productsData || []}
        loading={productsLoading}
        totalCount={productsData?.length || 0}
        page={(filters.page || 1) - 1}
        rowsPerPage={filters.limit || 20}
        onPageChange={handlePageChange}
        onRowsPerPageChange={handleRowsPerPageChange}
        onRefresh={fetchProducts}
        onExport={handleExport}
        actions={actions}
        title={`商品列表 (${productsData?.length || 0})`}
        emptyMessage="暂无商品数据"
      />

      {/* 商品详情对话框 */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>商品详情</DialogTitle>
        <DialogContent>
          {selectedProduct && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', md: '1fr 2fr' },
                gap: 2
              }}>
                <Box>
                  {selectedProduct.main_image_url ? (
                    <Avatar
                      src={selectedProduct.main_image_url}
                      variant="rounded"
                      sx={{ width: '100%', height: 200 }}
                    />
                  ) : (
                    <Avatar
                      variant="rounded"
                      sx={{ width: '100%', height: 200, bgcolor: 'grey.200' }}
                    >
                      暂无图片
                    </Avatar>
                  )}
                </Box>
                <Box>
                  <Typography variant="h6" gutterBottom>
                    {selectedProduct.title}
                  </Typography>
                  {selectedProduct.subtitle && (
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      {selectedProduct.subtitle}
                    </Typography>
                  )}
                  <Box sx={{ mb: 2 }}>
                    <Chip
                      label={<ProductStatusIndicator productStatus={selectedProduct.status} />}
                      size="small"
                      sx={{ mr: 1 }}
                    />
                    <Chip
                      label={<SyncStatusIndicator syncStatus={selectedProduct.sync_status} />}
                      size="small"
                    />
                  </Box>
                  <Box sx={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: 2
                  }}>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        价格范围
                      </Typography>
                      <Typography variant="body1">
                        {(selectedProduct as any).price_range || '面议'}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        起订量
                      </Typography>
                      <Typography variant="body1">
                        {selectedProduct.moq?.toLocaleString() || '-'}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        销量
                      </Typography>
                      <Typography variant="body1">
                        {selectedProduct.sales_count?.toLocaleString() || 0}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        评分
                      </Typography>
                      <Typography variant="body1">
                        {selectedProduct.rating?.toFixed(1) || '-'}
                      </Typography>
                    </Box>
                  </Box>
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                      供应商
                    </Typography>
                    <Typography variant="body1">
                      {selectedProduct.supplier?.name || '未知供应商'}
                    </Typography>
                  </Box>
                </Box>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  商品描述
                </Typography>
                <Typography variant="body1">
                  {selectedProduct.description || '暂无描述'}
                </Typography>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialogOpen(false)}>
            关闭
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Products;