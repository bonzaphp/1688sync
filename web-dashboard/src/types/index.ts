// 基础实体类型
export interface BaseEntity {
  id: number;
  created_at: string;
  updated_at: string;
  is_deleted: string;
}

// 商品相关类型
export interface Product extends BaseEntity {
  source_id: string;
  title: string;
  subtitle?: string;
  description?: string;
  price_min?: number;
  price_max?: number;
  currency: string;
  moq?: number;
  price_unit?: string;
  main_image_url?: string;
  detail_images?: string[];
  video_url?: string;
  specifications?: Record<string, any>;
  attributes?: Record<string, any>;
  supplier_id: number;
  sales_count: number;
  review_count: number;
  rating?: number;
  category_id?: string;
  category_name?: string;
  status: 'active' | 'inactive' | 'discontinued';
  sync_status: 'pending' | 'syncing' | 'completed' | 'failed';
  last_sync_time?: number;
  supplier?: Supplier;
  images?: ProductImage[];
}

export interface ProductImage extends BaseEntity {
  product_id: number;
  image_url: string;
  image_type: 'main' | 'detail' | 'thumbnail';
  image_order: number;
  alt_text?: string;
  file_size?: number;
  width?: number;
  height?: number;
  product?: Product;
}

// 供应商相关类型
export interface Supplier extends BaseEntity {
  source_id: string;
  name: string;
  company_name?: string;
  contact_info?: {
    phone?: string;
    email?: string;
    qq?: string;
    wechat?: string;
  };
  location?: string;
  province?: string;
  city?: string;
  rating?: number;
  response_rate?: number;
  product_count: number;
  business_type?: 'manufacturer' | 'trader' | 'individual';
  main_products?: string[];
  established_year?: string;
  is_verified: 'Y' | 'N';
  verification_level?: string;
  products?: Product[];
}

// 同步记录相关类型
export interface SyncRecord extends BaseEntity {
  task_id: string;
  task_name?: string;
  operation_type: 'full' | 'incremental' | 'manual' | 'scheduled';
  sync_type: 'product' | 'supplier' | 'image' | 'all';
  source_filter?: Record<string, any>;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  start_time?: number;
  end_time?: number;
  duration?: number;
  total_count: number;
  processed_count: number;
  success_count: number;
  failed_count: number;
  skipped_count: number;
  error_message?: string;
  error_details?: Array<{
    timestamp: number;
    message: string;
    details?: Record<string, any>;
  }>;
  error_count: number;
  records_per_second?: number;
  memory_usage_mb?: number;
  cpu_usage_percent?: number;
  config?: Record<string, any>;
  batch_size: number;
  max_retries: number;
  summary?: Record<string, any>;
  recommendations?: Array<{
    type: string;
    message: string;
    priority: 'low' | 'medium' | 'high';
  }>;
}

// API响应类型
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  pagination?: {
    page: number;
    limit: number;
    total: number;
    total_pages: number;
  };
}

// 分页请求参数
export interface PaginationParams {
  page?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// 商品筛选参数
export interface ProductFilters extends PaginationParams {
  search?: string;
  category_id?: string;
  supplier_id?: number;
  status?: Product['status'];
  sync_status?: Product['sync_status'];
  price_min?: number;
  price_max?: number;
  rating_min?: number;
}

// 供应商筛选参数
export interface SupplierFilters extends PaginationParams {
  search?: string;
  province?: string;
  city?: string;
  business_type?: Supplier['business_type'];
  is_verified?: Supplier['is_verified'];
  rating_min?: number;
}

// 同步记录筛选参数
export interface SyncRecordFilters extends PaginationParams {
  search?: string;
  task_id?: string;
  operation_type?: SyncRecord['operation_type'];
  sync_type?: SyncRecord['sync_type'];
  status?: SyncRecord['status'];
  start_time_from?: number;
  start_time_to?: number;
}

// 仪表板统计数据
export interface DashboardStats {
  total_products: number;
  total_suppliers: number;
  active_sync_tasks: number;
  completed_syncs_today: number;
  failed_syncs_today: number;
  average_sync_duration: number;
  storage_usage: {
    total_size: number;
    products_size: number;
    images_size: number;
    logs_size: number;
  };
  recent_sync_records: SyncRecord[];
  top_suppliers: Array<{
    supplier: Supplier;
    product_count: number;
  }>;
  sync_status_distribution: Array<{
    status: SyncRecord['status'];
    count: number;
  }>;
}

// 实时更新数据
export interface RealtimeUpdate {
  type: 'sync_progress' | 'sync_completed' | 'sync_failed' | 'new_product' | 'product_updated';
  data: any;
  timestamp: number;
}

// 表格列配置
export interface TableColumn {
  id: string;
  label: string;
  minWidth?: number;
  align?: 'left' | 'center' | 'right';
  format?: (value: any) => string;
  sortable?: boolean;
}

// 图表数据点
export interface ChartDataPoint {
  name: string;
  value: number;
  color?: string;
}

// 时间序列数据点
export interface TimeSeriesDataPoint {
  timestamp: number;
  value: number;
  label?: string;
}

// 导出配置
export interface ExportConfig {
  format: 'csv' | 'excel' | 'json';
  fields: string[];
  filters?: any;
}