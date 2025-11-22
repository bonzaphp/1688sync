import React, { useEffect, useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  Inventory,
  Business,
  Sync,
  CheckCircle,
  Error as ErrorIcon,
  TrendingUp
} from '@mui/icons-material';
import { useApi } from '../../hooks/useApi';
import { useDashboardUpdates } from '../../hooks/useWebSocket';
import apiService from '../../services/api';
import {
  StatCard,
  CustomBarChart,
  CustomLineChart,
  CustomPieChart,
  SyncStatusIndicator
} from '../../components';
import { DashboardStats } from '../../types';

interface QuickStats {
  totalProducts: number;
  totalSuppliers: number;
  activeSyncTasks: number;
  completedSyncsToday: number;
}

const Dashboard: React.FC = () => {
  const [quickStats, setQuickStats] = useState<QuickStats>({
    totalProducts: 0,
    totalSuppliers: 0,
    activeSyncTasks: 0,
    completedSyncsToday: 0
  });

  // 获取仪表板统计数据
  const {
    data: dashboardData,
    loading: dashboardLoading,
    error: dashboardError,
    execute: fetchDashboardData
  } = useApi(() => apiService.getDashboardStats(), {
    immediate: true
  });

  // 获取同步记录用于图表展示
  const {
    data: syncRecords,
    loading: syncLoading,
    execute: fetchSyncRecords
  } = useApi(() => apiService.getSyncRecords({
    page: 1,
    limit: 100,
    start_time_from: Math.floor((Date.now() - 7 * 24 * 60 * 60 * 1000) / 1000) // 最近7天
  }));

  // WebSocket实时更新
  const { dashboardData: realtimeData } = useDashboardUpdates();

  // 更新快速统计数据
  useEffect(() => {
    if (dashboardData) {
      const stats = dashboardData as DashboardStats;
      setQuickStats({
        totalProducts: stats.total_products,
        totalSuppliers: stats.total_suppliers,
        activeSyncTasks: stats.active_sync_tasks,
        completedSyncsToday: stats.completed_syncs_today
      });
    }
  }, [dashboardData]);

  // 处理实时数据更新
  useEffect(() => {
    if (realtimeData) {
      // 刷新仪表板数据
      fetchDashboardData();
      fetchSyncRecords();
    }
  }, [realtimeData, fetchDashboardData, fetchSyncRecords]);

  // 准备图表数据
  const syncStatusData = React.useMemo(() => {
    if (!syncRecords) return [];

    const statusCount = syncRecords.reduce((acc: any, record) => {
      const status = record.status;
      acc[status] = (acc[status] || 0) + 1;
      return acc;
    }, {});

    return [
      { name: '等待中', value: statusCount.pending || 0 },
      { name: '运行中', value: statusCount.running || 0 },
      { name: '已完成', value: statusCount.completed || 0 },
      { name: '失败', value: statusCount.failed || 0 },
      { name: '已取消', value: statusCount.cancelled || 0 }
    ].filter(item => item.value > 0);
  }, [syncRecords]);

  const syncTrendData = React.useMemo(() => {
    if (!syncRecords) return [];

    // 按日期分组统计数据
    const dailyStats = syncRecords.reduce((acc: any, record) => {
      const date = new Date(record.start_time! * 1000).toLocaleDateString();
      if (!acc[date]) {
        acc[date] = {
          timestamp: record.start_time!,
          date,
          completed: 0,
          failed: 0,
          total: 0,
          value: 0
        };
      }
      acc[date].total++;
      acc[date].value = acc[date].total;
      if (record.status === 'completed') acc[date].completed++;
      if (record.status === 'failed') acc[date].failed++;
      return acc;
    }, {});

    return Object.values(dailyStats).slice(-7) as any; // 最近7天
  }, [syncRecords]);

  const topSuppliersData = React.useMemo(() => {
    if (!dashboardData?.top_suppliers) return [];

    return dashboardData.top_suppliers.map((item: any) => ({
      name: item.supplier.name,
      value: item.product_count
    }));
  }, [dashboardData]);

  if (dashboardLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (dashboardError) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        加载仪表板数据失败: {dashboardError.message}
      </Alert>
    );
  }

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        仪表板
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        1688Sync 系统概览和实时监控
      </Typography>

      {/* 快速统计卡片 */}
      <Box sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr 1fr' },
        gap: 3,
        mb: 4
      }}>
        <StatCard
          title="商品总数"
          value={quickStats.totalProducts.toLocaleString()}
          subtitle="已同步的商品"
          color="primary"
          icon={<Inventory />}
        />
        <StatCard
          title="供应商总数"
          value={quickStats.totalSuppliers.toLocaleString()}
          subtitle="已收录的供应商"
          color="secondary"
          icon={<Business />}
        />
        <StatCard
          title="活跃同步任务"
          value={quickStats.activeSyncTasks}
          subtitle="正在执行的任务"
          color="info"
          icon={<Sync />}
        />
        <StatCard
          title="今日完成同步"
          value={quickStats.completedSyncsToday}
          subtitle="今日成功完成任务"
          color="success"
          icon={<CheckCircle />}
        />
      </Box>

      {/* 图表区域 */}
      <Box sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: '1fr 2fr' },
        gap: 3,
        mb: 3
      }}>
        {/* 同步状态分布 */}
        <CustomPieChart
          title="同步状态分布"
          data={syncStatusData}
          height={300}
          loading={syncLoading}
        />

        {/* 同步趋势图 */}
        <CustomLineChart
          title="同步趋势（最近7天）"
          data={syncTrendData}
          dataKey="total"
          xAxisDataKey="date"
          height={300}
          loading={syncLoading}
        />
      </Box>

      <Box sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
        gap: 3,
        mb: 3
      }}>
        {/* 供应商排行榜 */}
        <CustomBarChart
          title="供应商商品数量排行"
          data={topSuppliersData}
          height={350}
          loading={dashboardLoading}
        />

        {/* 存储使用情况 */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              存储使用情况
            </Typography>
            {dashboardData?.storage_usage && (
              <Box sx={{
                display: 'grid',
                gridTemplateColumns: '1fr',
                gap: 2
              }}>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    总存储空间
                  </Typography>
                  <Typography variant="h5">
                    {(dashboardData.storage_usage.total_size / 1024 / 1024).toFixed(2)} MB
                  </Typography>
                </Box>
                <Box sx={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gap: 2
                }}>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      商品数据
                    </Typography>
                    <Typography variant="h6">
                      {(dashboardData.storage_usage.products_size / 1024 / 1024).toFixed(1)} MB
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      图片数据
                    </Typography>
                    <Typography variant="h6">
                      {(dashboardData.storage_usage.images_size / 1024 / 1024).toFixed(1)} MB
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      日志数据
                    </Typography>
                    <Typography variant="h6">
                      {(dashboardData.storage_usage.logs_size / 1024 / 1024).toFixed(1)} MB
                    </Typography>
                  </Box>
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>
      </Box>

      {/* 最近同步记录 */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            最近同步记录
          </Typography>
          {dashboardData?.recent_sync_records && dashboardData.recent_sync_records.length > 0 ? (
            <Box>
              {dashboardData.recent_sync_records.slice(0, 5).map((record: any) => (
                <Box
                  key={record.id}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    py: 1,
                    borderBottom: '1px solid',
                    borderColor: 'divider'
                  }}
                >
                  <Box>
                    <Typography variant="body2" fontWeight="medium">
                      {record.task_name || record.task_id}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(record.start_time! * 1000).toLocaleString()}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <SyncStatusIndicator
                      syncStatus={record.sync_status}
                      progress={record.progress}
                      size="small"
                    />
                    <Typography variant="body2" color="text.secondary">
                      {record.processed_count}/{record.total_count}
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              暂无同步记录
            </Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default Dashboard;