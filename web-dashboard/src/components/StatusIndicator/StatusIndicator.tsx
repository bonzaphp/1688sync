import React from 'react';
import {
  Box,
  Chip,
  CircularProgress,
  LinearProgress,
  Tooltip,
  Typography
} from '@mui/material';
import {
  CheckCircle,
  Error,
  Warning,
  Info,
  Sync,
  Schedule,
  Cancel
} from '@mui/icons-material';

export type StatusType =
  | 'success'
  | 'error'
  | 'warning'
  | 'info'
  | 'loading'
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface StatusIndicatorProps {
  status: StatusType;
  label?: string;
  size?: 'small' | 'medium' | 'large';
  variant?: 'chip' | 'progress' | 'icon' | 'text';
  progress?: number;
  tooltip?: string;
  showIcon?: boolean;
}

interface StatusConfig {
  color: 'success' | 'error' | 'warning' | 'info' | 'primary' | 'secondary' | 'default' | 'inherit';
  icon: React.ReactNode;
  label: string;
}

const statusConfigMap: Record<StatusType, StatusConfig> = {
  success: {
    color: 'success',
    icon: <CheckCircle />,
    label: '成功'
  },
  error: {
    color: 'error',
    icon: <Error />,
    label: '失败'
  },
  warning: {
    color: 'warning',
    icon: <Warning />,
    label: '警告'
  },
  info: {
    color: 'info',
    icon: <Info />,
    label: '信息'
  },
  loading: {
    color: 'primary',
    icon: <CircularProgress size={16} />,
    label: '加载中'
  },
  pending: {
    color: 'inherit',
    icon: <Schedule />,
    label: '等待中'
  },
  running: {
    color: 'primary',
    icon: <Sync />,
    label: '运行中'
  },
  completed: {
    color: 'success',
    icon: <CheckCircle />,
    label: '已完成'
  },
  failed: {
    color: 'error',
    icon: <Error />,
    label: '失败'
  },
  cancelled: {
    color: 'secondary',
    icon: <Cancel />,
    label: '已取消'
  }
};

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  label,
  size = 'small',
  variant = 'chip',
  progress,
  tooltip,
  showIcon = true
}) => {
  const config = statusConfigMap[status];
  const displayLabel = label || config.label;

  const content = React.useMemo(() => {
    switch (variant) {
      case 'chip':
        return (
          <Chip
            size={size as 'small' | 'medium'}
            color={config.color as any}
            icon={showIcon ? config.icon as React.ReactElement : undefined}
            label={displayLabel}
            variant="outlined"
          />
        );

      case 'progress':
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 120 }}>
            {showIcon && config.icon}
            <Box sx={{ flex: 1 }}>
              <LinearProgress
                variant="determinate"
                value={progress || 0}
                color={config.color === 'inherit' ? 'primary' : config.color as any}
                sx={{ height: size === 'small' ? 4 : 6 }}
              />
            </Box>
            {progress !== undefined && (
              <Typography variant="body2" color="text.secondary">
                {`${Math.round(progress)}%`}
              </Typography>
            )}
          </Box>
        );

      case 'icon':
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ color: `${config.color}.main` }}>
              {config.icon}
            </Box>
            {displayLabel && (
              <Typography variant="body2" color="text.secondary">
                {displayLabel}
              </Typography>
            )}
          </Box>
        );

      case 'text':
        return (
          <Typography
            variant={size === 'small' ? 'body2' : size === 'large' ? 'h6' : 'body1'}
            color={`${config.color}.main`}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              fontWeight: size === 'large' ? 'bold' : 'normal'
            }}
          >
            {showIcon && config.icon}
            {displayLabel}
          </Typography>
        );

      default:
        return null;
    }
  }, [variant, size, config, showIcon, displayLabel, progress]);

  if (tooltip) {
    return (
      <Tooltip title={tooltip} arrow>
        {content || <span />}
      </Tooltip>
    );
  }

  return <>{content}</>;
};

// 同步状态指示器（专用于同步任务）
export interface SyncStatusIndicatorProps extends Omit<StatusIndicatorProps, 'status'> {
  syncStatus: 'pending' | 'syncing' | 'completed' | 'failed' | 'cancelled';
  progress?: number;
  startTime?: number;
  endTime?: number;
}

export const SyncStatusIndicator: React.FC<SyncStatusIndicatorProps> = ({
  syncStatus,
  progress,
  startTime,
  endTime,
  ...props
}) => {
  const getStatusFromSyncStatus = (): StatusType => {
    switch (syncStatus) {
      case 'pending':
        return 'pending';
      case 'syncing':
        return 'running';
      case 'completed':
        return 'completed';
      case 'failed':
        return 'failed';
      case 'cancelled':
        return 'cancelled';
      default:
        return 'info';
    }
  };

  const getTooltip = (): string | undefined => {
    if (startTime && endTime) {
      const duration = Math.round((endTime - startTime) / 1000);
      return `耗时: ${duration}秒`;
    }
    if (syncStatus === 'syncing' && progress !== undefined) {
      return `同步进度: ${Math.round(progress)}%`;
    }
    return undefined;
  };

  return (
    <StatusIndicator
      status={getStatusFromSyncStatus()}
      progress={progress}
      tooltip={getTooltip()}
      variant={syncStatus === 'syncing' ? 'progress' : 'chip'}
      {...props}
    />
  );
};

// 商品状态指示器
export interface ProductStatusIndicatorProps extends Omit<StatusIndicatorProps, 'status'> {
  productStatus: 'active' | 'inactive' | 'discontinued';
}

export const ProductStatusIndicator: React.FC<ProductStatusIndicatorProps> = ({
  productStatus,
  ...props
}) => {
  const getStatusFromProductStatus = (): StatusType => {
    switch (productStatus) {
      case 'active':
        return 'success';
      case 'inactive':
        return 'warning';
      case 'discontinued':
        return 'error';
      default:
        return 'info';
    }
  };

  const getStatusLabel = (): string => {
    switch (productStatus) {
      case 'active':
        return '在售';
      case 'inactive':
        return '下架';
      case 'discontinued':
        return '停产';
      default:
        return '未知';
    }
  };

  return (
    <StatusIndicator
      status={getStatusFromProductStatus()}
      label={getStatusLabel()}
      {...props}
    />
  );
};

// 供应商认证状态指示器
export interface VerificationStatusIndicatorProps extends Omit<StatusIndicatorProps, 'status'> {
  isVerified: 'Y' | 'N';
  verificationLevel?: string;
}

export const VerificationStatusIndicator: React.FC<VerificationStatusIndicatorProps> = ({
  isVerified,
  verificationLevel,
  ...props
}) => {
  const status: StatusType = isVerified === 'Y' ? 'success' : 'warning';
  const label = isVerified === 'Y'
    ? (verificationLevel ? `已认证(${verificationLevel})` : '已认证')
    : '未认证';

  return (
    <StatusIndicator
      status={status}
      label={label}
      {...props}
    />
  );
};

export default StatusIndicator;