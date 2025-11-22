import React from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  TooltipProps
} from 'recharts';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  useTheme
} from '@mui/material';

export interface ChartDataPoint {
  name: string;
  value: number;
  [key: string]: any;
}

export interface TimeSeriesDataPoint {
  timestamp: number;
  value: number;
  label?: string;
  [key: string]: any;
}

interface BaseChartProps {
  title?: string;
  height?: number;
  data?: any[];
  loading?: boolean;
  error?: string;
}

interface BarChartProps extends BaseChartProps {
  data: ChartDataPoint[];
  dataKey?: string;
  xAxisDataKey?: string;
  color?: string;
  colors?: string[];
  showLegend?: boolean;
  showGrid?: boolean;
}

interface LineChartProps extends BaseChartProps {
  data: TimeSeriesDataPoint[];
  dataKey?: string;
  xAxisDataKey?: string;
  color?: string;
  strokeWidth?: number;
  showDots?: boolean;
  showGrid?: boolean;
}

interface PieChartProps extends BaseChartProps {
  data: ChartDataPoint[];
  dataKey?: string;
  nameKey?: string;
  colors?: string[];
  showLegend?: boolean;
  innerRadius?: number;
  outerRadius?: number;
}

interface AreaChartProps extends BaseChartProps {
  data: TimeSeriesDataPoint[];
  dataKey?: string;
  xAxisDataKey?: string;
  color?: string;
  strokeWidth?: number;
  showGrid?: boolean;
  opacity?: number;
}

// 自定义Tooltip组件
const CustomTooltip = ({ active, payload, label }: any) => {
  const theme = useTheme();

  if (active && payload && payload.length) {
    return (
      <Paper
        sx={{
          p: 2,
          backgroundColor: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`,
          borderRadius: 1
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
          {label}
        </Typography>
        {payload.map((entry: any, index: number) => (
          <Typography
            key={index}
            variant="body2"
            sx={{ color: entry.color }}
          >
            {`${entry.name}: ${entry.value}`}
          </Typography>
        ))}
      </Paper>
    );
  }
  return null;
};

// 柱状图组件
export const CustomBarChart: React.FC<BarChartProps> = ({
  title,
  height = 300,
  data,
  dataKey = 'value',
  xAxisDataKey = 'name',
  color,
  colors,
  showLegend = true,
  showGrid = true,
  loading,
  error
}) => {
  const theme = useTheme();
  const defaultColors = [
    theme.palette.primary.main,
    theme.palette.secondary.main,
    theme.palette.success.main,
    theme.palette.warning.main,
    theme.palette.error.main,
    theme.palette.info.main
  ];

  const chartColors = colors || (color ? [color] : defaultColors);

  if (loading) {
    return (
      <Card sx={{ height }}>
        <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <Typography>加载中...</Typography>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card sx={{ height }}>
        <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <Typography color="error">加载失败: {error}</Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      {title && (
        <CardContent sx={{ pb: 0 }}>
          <Typography variant="h6" component="div">
            {title}
          </Typography>
        </CardContent>
      )}
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" />}
            <XAxis dataKey={xAxisDataKey} />
            <YAxis />
            <Tooltip content={<CustomTooltip />} />
            {showLegend && <Legend />}
            <Bar dataKey={dataKey} fill={chartColors[0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

// 折线图组件
export const CustomLineChart: React.FC<LineChartProps> = ({
  title,
  height = 300,
  data,
  dataKey = 'value',
  xAxisDataKey = 'timestamp',
  color,
  strokeWidth = 2,
  showDots = true,
  showGrid = true,
  loading,
  error
}) => {
  const theme = useTheme();
  const lineColor = color || theme.palette.primary.main;

  // 格式化时间戳为可读的日期
  const formattedData = data.map(item => ({
    ...item,
    [xAxisDataKey]: new Date(item[xAxisDataKey]).toLocaleDateString()
  }));

  if (loading) {
    return (
      <Card sx={{ height }}>
        <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <Typography>加载中...</Typography>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card sx={{ height }}>
        <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <Typography color="error">加载失败: {error}</Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      {title && (
        <CardContent sx={{ pb: 0 }}>
          <Typography variant="h6" component="div">
            {title}
          </Typography>
        </CardContent>
      )}
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={formattedData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" />}
            <XAxis dataKey={xAxisDataKey} />
            <YAxis />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={lineColor}
              strokeWidth={strokeWidth}
              dot={showDots}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

// 饼图组件
export const CustomPieChart: React.FC<PieChartProps> = ({
  title,
  height = 300,
  data,
  dataKey = 'value',
  nameKey = 'name',
  colors,
  showLegend = true,
  innerRadius = 0,
  outerRadius = 80,
  loading,
  error
}) => {
  const theme = useTheme();
  const defaultColors = [
    theme.palette.primary.main,
    theme.palette.secondary.main,
    theme.palette.success.main,
    theme.palette.warning.main,
    theme.palette.error.main,
    theme.palette.info.main
  ];

  const chartColors = colors || defaultColors;

  if (loading) {
    return (
      <Card sx={{ height }}>
        <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <Typography>加载中...</Typography>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card sx={{ height }}>
        <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <Typography color="error">加载失败: {error}</Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      {title && (
        <CardContent sx={{ pb: 0 }}>
          <Typography variant="h6" component="div">
            {title}
          </Typography>
        </CardContent>
      )}
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={innerRadius}
              outerRadius={outerRadius}
              paddingAngle={2}
              dataKey={dataKey}
              nameKey={nameKey}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={chartColors[index % chartColors.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            {showLegend && <Legend />}
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

// 面积图组件
export const CustomAreaChart: React.FC<AreaChartProps> = ({
  title,
  height = 300,
  data,
  dataKey = 'value',
  xAxisDataKey = 'timestamp',
  color,
  strokeWidth = 2,
  showGrid = true,
  opacity = 0.3,
  loading,
  error
}) => {
  const theme = useTheme();
  const areaColor = color || theme.palette.primary.main;

  // 格式化时间戳为可读的日期
  const formattedData = data.map(item => ({
    ...item,
    [xAxisDataKey]: new Date(item[xAxisDataKey]).toLocaleDateString()
  }));

  if (loading) {
    return (
      <Card sx={{ height }}>
        <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <Typography>加载中...</Typography>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card sx={{ height }}>
        <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <Typography color="error">加载失败: {error}</Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      {title && (
        <CardContent sx={{ pb: 0 }}>
          <Typography variant="h6" component="div">
            {title}
          </Typography>
        </CardContent>
      )}
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <AreaChart data={formattedData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" />}
            <XAxis dataKey={xAxisDataKey} />
            <YAxis />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Area
              type="monotone"
              dataKey={dataKey}
              stroke={areaColor}
              strokeWidth={strokeWidth}
              fill={areaColor}
              fillOpacity={opacity}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
};

// 统计卡片组件
export interface StatCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  color?: 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info';
  icon?: React.ReactNode;
  loading?: boolean;
  error?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  color = 'primary',
  icon,
  loading,
  error
}) => {
  const theme = useTheme();

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Typography color="text.secondary" gutterBottom>
            {title}
          </Typography>
          <Typography variant="h4">
            加载中...
          </Typography>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <Typography color="text.secondary" gutterBottom>
            {title}
          </Typography>
          <Typography variant="h4" color="error">
            错误
          </Typography>
          <Typography variant="body2" color="error">
            {error}
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card
      sx={{
        background: `linear-gradient(135deg, ${theme.palette[color].main}dd, ${theme.palette[color].dark}dd)`,
        color: 'white'
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography sx={{ opacity: 0.8 }} gutterBottom>
              {title}
            </Typography>
            <Typography variant="h4" component="div">
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="body2" sx={{ opacity: 0.8 }}>
                {subtitle}
              </Typography>
            )}
          </Box>
          {icon && (
            <Box sx={{ opacity: 0.8 }}>
              {icon}
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default {
  CustomBarChart,
  CustomLineChart,
  CustomPieChart,
  CustomAreaChart,
  StatCard
};