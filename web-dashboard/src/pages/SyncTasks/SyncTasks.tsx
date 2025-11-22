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
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
  Chip
} from '@mui/material';
import {
  Search,
  Add,
  Refresh,
  PlayArrow,
  Pause,
  Stop,
  RestartAlt,
  Visibility
} from '@mui/icons-material';
import { useApi, useDebounce } from '../../hooks/useApi';
import { useSyncTask } from '../../hooks/useWebSocket';
import apiService from '../../services/api';
import {
  DataTable,
  SyncStatusIndicator,
  type TableColumn,
  type DataTableAction
} from '../../components';
import { SyncRecord, SyncRecordFilters } from '../../types';

const SyncTasks: React.FC = () => {
  const [filters, setFilters] = useState<SyncRecordFilters>({
    page: 1,
    limit: 20,
    search: '',
    status: undefined,
    operation_type: undefined
  });
  const [selectedTask, setSelectedTask] = useState<SyncRecord | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newTaskConfig, setNewTaskConfig] = useState({
    operation_type: 'manual' as const,
    sync_type: 'product' as const,
    source_filter: {}
  });

  // 防抖搜索
  const debouncedSearch = useDebounce(filters.search, 300);

  // 获取同步任务列表
  const {
    data: syncTasksData,
    loading: syncTasksLoading,
    error: syncTasksError,
    execute: fetchSyncTasks
  } = useApi(() => apiService.getSyncRecords({
    ...filters,
    search: debouncedSearch
  }), {
    immediate: true
  });

  // 创建同步任务
  const {
    data: createResult,
    loading: createLoading,
    execute: createSyncTask
  } = useApi(() => apiService.createSyncTask(newTaskConfig));

  // 取消同步任务
  const [cancelTaskId, setCancelTaskId] = useState<number | null>(null);
  const {
    data: cancelResult,
    loading: cancelLoading,
    execute: executeCancel
  } = useApi(() => {
    if (!cancelTaskId) throw new Error('Task ID is required');
    return apiService.cancelSyncTask(cancelTaskId);
  });

  // 重试同步任务
  const [retryTaskId, setRetryTaskId] = useState<number | null>(null);
  const {
    data: retryResult,
    loading: retryLoading,
    execute: executeRetry
  } = useApi(() => {
    if (!retryTaskId) throw new Error('Task ID is required');
    return apiService.retrySyncTask(retryTaskId);
  });

  // 当搜索词变化时重新获取数据
  useEffect(() => {
    if (filters.page === 1) {
      fetchSyncTasks();
    } else {
      setFilters(prev => ({ ...prev, page: 1 }));
    }
  }, [debouncedSearch]);

  // 当其他筛选条件变化时重新获取数据
  useEffect(() => {
    fetchSyncTasks();
  }, [filters.status, filters.operation_type, filters.page, filters.limit]);

  // 处理创建成功
  useEffect(() => {
    if (createResult) {
      setCreateDialogOpen(false);
      setNewTaskConfig({
        operation_type: 'manual',
        sync_type: 'product',
        source_filter: {}
      });
      fetchSyncTasks();
    }
  }, [createResult]);

  // 处理取消成功
  useEffect(() => {
    if (cancelResult) {
      fetchSyncTasks();
    }
  }, [cancelResult]);

  // 处理重试成功
  useEffect(() => {
    if (retryResult) {
      fetchSyncTasks();
    }
  }, [retryResult]);

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setFilters(prev => ({ ...prev, search: event.target.value }));
  };

  const handleStatusFilterChange = (event: any) => {
    setFilters(prev => ({ ...prev, status: event.target.value || undefined }));
  };

  const handleOperationTypeFilterChange = (event: any) => {
    setFilters(prev => ({ ...prev, operation_type: event.target.value || undefined }));
  };

  const handlePageChange = (page: number) => {
    setFilters(prev => ({ ...prev, page: page + 1 }));
  };

  const handleRowsPerPageChange = (rowsPerPage: number) => {
    setFilters(prev => ({ ...prev, limit: rowsPerPage, page: 1 }));
  };

  const handleViewTask = (task: SyncRecord) => {
    setSelectedTask(task);
    setDetailDialogOpen(true);
  };

  const handleCancelTask = async (task: SyncRecord) => {
    if (window.confirm(`确定要取消任务 "${task.task_name || task.task_id}" 吗？`)) {
      setCancelTaskId(task.id);
      await executeCancel();
    }
  };

  const handleRetryTask = async (task: SyncRecord) => {
    setRetryTaskId(task.id);
    await executeRetry();
  };

  const handleCreateTask = async () => {
    await createSyncTask();
  };

  // 表格列定义
  const columns: TableColumn[] = [
    {
      id: 'task_name',
      label: '任务名称',
      minWidth: 180,
      sortable: true,
      format: (value: string, row: SyncRecord) => (
        <Box>
          <Typography variant="body2" fontWeight="medium">
            {value || row.task_id}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            ID: {row.task_id}
          </Typography>
        </Box>
      )
    },
    {
      id: 'operation_type',
      label: '操作类型',
      minWidth: 100,
      format: (value: string) => {
        const typeMap: Record<string, string> = {
          'full': '全量同步',
          'incremental': '增量同步',
          'manual': '手动同步',
          'scheduled': '定时同步'
        };
        return typeMap[value] || value;
      }
    },
    {
      id: 'sync_type',
      label: '同步类型',
      minWidth: 100,
      format: (value: string) => {
        const typeMap: Record<string, string> = {
          'product': '商品',
          'supplier': '供应商',
          'image': '图片',
          'all': '全部'
        };
        return typeMap[value] || value;
      }
    },
    {
      id: 'status',
      label: '状态',
      minWidth: 120,
      format: (value: string, row: SyncRecord) => (
        <SyncStatusIndicator
          syncStatus={row.status === 'running' ? 'syncing' : row.status as any}
          progress={row.progress}
          size="small"
        />
      )
    },
    {
      id: 'progress',
      label: '进度',
      minWidth: 120,
      format: (value: number, row: SyncRecord) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <LinearProgress
            variant="determinate"
            value={value}
            sx={{ flex: 1 }}
          />
          <Typography variant="body2" color="text.secondary">
            {value}%
          </Typography>
        </Box>
      )
    },
    {
      id: 'processed_count',
      label: '处理进度',
      minWidth: 120,
      format: (value: number, row: SyncRecord) => (
        <Typography variant="body2">
          {value?.toLocaleString() || 0} / {row.total_count?.toLocaleString() || 0}
        </Typography>
      )
    },
    {
      id: 'start_time',
      label: '开始时间',
      minWidth: 150,
      format: (value: number) => {
        if (!value) return '-';
        return new Date(value * 1000).toLocaleString();
      }
    },
    {
      id: 'duration',
      label: '耗时',
      minWidth: 80,
      format: (value: number, row: SyncRecord) => {
        if (!value && row.status === 'running') {
          const elapsed = Math.floor(Date.now() / 1000) - (row.start_time || 0);
          return `${Math.floor(elapsed / 60)}m`;
        }
        if (!value) return '-';
        return `${Math.floor(value / 60)}m`;
      }
    },
    {
      id: 'success_rate',
      label: '成功率',
      minWidth: 80,
      format: (value: number, row: SyncRecord) => {
        if (!row.processed_count) return '0%';
        const rate = Math.round((row.success_count / row.processed_count) * 100);
        return `${rate}%`;
      }
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
      onClick: handleViewTask,
      color: 'info'
    }
  ];

  // 根据任务状态动态添加操作按钮
  const getDynamicActions = (task: SyncRecord): DataTableAction[] => {
    const dynamicActions: DataTableAction[] = [];

    if (task.status === 'running') {
      dynamicActions.push({
        label: '取消任务',
        icon: <Stop />,
        onClick: () => handleCancelTask(task),
        color: 'error'
      });
    }

    if (task.status === 'failed' || task.status === 'cancelled') {
      dynamicActions.push({
        label: '重试任务',
        icon: <RestartAlt />,
        onClick: () => handleRetryTask(task),
        color: 'warning'
      });
    }

    return [...actions, ...dynamicActions];
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        同步任务管理
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        管理和监控数据同步任务
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
              placeholder="搜索任务名称或ID..."
              value={filters.search}
              onChange={handleSearchChange}
              InputProps={{
                startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
              }}
            />
            <FormControl fullWidth>
              <InputLabel>任务状态</InputLabel>
              <Select
                value={filters.status || ''}
                onChange={handleStatusFilterChange}
                label="任务状态"
              >
                <MenuItem value="">全部</MenuItem>
                <MenuItem value="pending">等待中</MenuItem>
                <MenuItem value="running">运行中</MenuItem>
                <MenuItem value="completed">已完成</MenuItem>
                <MenuItem value="failed">失败</MenuItem>
                <MenuItem value="cancelled">已取消</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>操作类型</InputLabel>
              <Select
                value={filters.operation_type || ''}
                onChange={handleOperationTypeFilterChange}
                label="操作类型"
              >
                <MenuItem value="">全部</MenuItem>
                <MenuItem value="full">全量同步</MenuItem>
                <MenuItem value="incremental">增量同步</MenuItem>
                <MenuItem value="manual">手动同步</MenuItem>
                <MenuItem value="scheduled">定时同步</MenuItem>
              </Select>
            </FormControl>
            <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
              <Tooltip title="刷新">
                <IconButton onClick={fetchSyncTasks} disabled={syncTasksLoading}>
                  <Refresh />
                </IconButton>
              </Tooltip>
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => setCreateDialogOpen(true)}
              >
                新建任务
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <DataTable
        columns={columns}
        data={syncTasksData || []}
        loading={syncTasksLoading}
        totalCount={syncTasksData?.length || 0}
        page={(filters.page || 1) - 1}
        rowsPerPage={filters.limit || 20}
        onPageChange={handlePageChange}
        onRowsPerPageChange={handleRowsPerPageChange}
        onRefresh={fetchSyncTasks}
        actions={actions}
        getRowActions={getDynamicActions}
        title={`同步任务列表 (${syncTasksData?.length || 0})`}
        emptyMessage="暂无同步任务"
      />

      {/* 任务详情对话框 */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>任务详情</DialogTitle>
        <DialogContent>
          {selectedTask && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
                gap: 2
              }}>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    任务ID
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    {selectedTask.task_id}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    任务名称
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    {selectedTask.task_name || '-'}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    操作类型
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    {selectedTask.operation_type}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    同步类型
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    {selectedTask.sync_type}
                  </Typography>
                </Box>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  状态
                </Typography>
                <Box sx={{ my: 1 }}>
                  <SyncStatusIndicator
                    syncStatus={selectedTask.status === 'running' ? 'syncing' : selectedTask.status as any}
                    progress={selectedTask.progress}
                  />
                </Box>
              </Box>
              <Box sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', md: '1fr 1fr 1fr' },
                gap: 2
              }}>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    总数量
                  </Typography>
                  <Typography variant="body1">
                    {selectedTask.total_count?.toLocaleString() || 0}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    已处理
                  </Typography>
                  <Typography variant="body1">
                    {selectedTask.processed_count?.toLocaleString() || 0}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    成功数量
                  </Typography>
                  <Typography variant="body1">
                    {selectedTask.success_count?.toLocaleString() || 0}
                  </Typography>
                </Box>
              </Box>
              {selectedTask.error_message && (
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    错误信息
                  </Typography>
                  <Typography variant="body1" color="error">
                    {selectedTask.error_message}
                  </Typography>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialogOpen(false)}>
            关闭
          </Button>
        </DialogActions>
      </Dialog>

      {/* 新建任务对话框 */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>新建同步任务</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <FormControl fullWidth>
              <InputLabel>操作类型</InputLabel>
              <Select
                value={newTaskConfig.operation_type}
                onChange={(e) => setNewTaskConfig(prev => ({
                  ...prev,
                  operation_type: e.target.value as any
                }))}
                label="操作类型"
              >
                <MenuItem value="manual">手动同步</MenuItem>
                <MenuItem value="incremental">增量同步</MenuItem>
                <MenuItem value="full">全量同步</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>同步类型</InputLabel>
              <Select
                value={newTaskConfig.sync_type}
                onChange={(e) => setNewTaskConfig(prev => ({
                  ...prev,
                  sync_type: e.target.value as any
                }))}
                label="同步类型"
              >
                <MenuItem value="product">商品同步</MenuItem>
                <MenuItem value="supplier">供应商同步</MenuItem>
                <MenuItem value="image">图片同步</MenuItem>
                <MenuItem value="all">全部同步</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>
            取消
          </Button>
          <Button
            onClick={handleCreateTask}
            variant="contained"
            disabled={createLoading}
          >
            创建任务
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SyncTasks;