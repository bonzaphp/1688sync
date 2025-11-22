import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
  ApiResponse,
  Product,
  Supplier,
  SyncRecord,
  ProductFilters,
  SupplierFilters,
  SyncRecordFilters,
  DashboardStats,
  PaginationParams
} from '../types';

// API基础配置
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 请求拦截器
    this.client.interceptors.request.use(
      (config) => {
        // 可以在这里添加认证token
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // 响应拦截器
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        return response;
      },
      (error) => {
        if (error.response?.status === 401) {
          // 处理认证失败
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // 通用请求方法
  private async request<T>(method: string, url: string, data?: any): Promise<ApiResponse<T>> {
    try {
      const response = await this.client.request({
        method,
        url,
        data,
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || '请求失败');
    }
  }

  // 商品相关API
  async getProducts(filters?: ProductFilters): Promise<ApiResponse<Product[]>> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }
    return this.request('GET', `/products?${params}`);
  }

  async getProduct(id: number): Promise<ApiResponse<Product>> {
    return this.request('GET', `/products/${id}`);
  }

  async createProduct(product: Partial<Product>): Promise<ApiResponse<Product>> {
    return this.request('POST', '/products', product);
  }

  async updateProduct(id: number, product: Partial<Product>): Promise<ApiResponse<Product>> {
    return this.request('PUT', `/products/${id}`, product);
  }

  async deleteProduct(id: number): Promise<ApiResponse<void>> {
    return this.request('DELETE', `/products/${id}`);
  }

  async syncProduct(id: number): Promise<ApiResponse<void>> {
    return this.request('POST', `/products/${id}/sync`);
  }

  // 供应商相关API
  async getSuppliers(filters?: SupplierFilters): Promise<ApiResponse<Supplier[]>> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }
    return this.request('GET', `/suppliers?${params}`);
  }

  async getSupplier(id: number): Promise<ApiResponse<Supplier>> {
    return this.request('GET', `/suppliers/${id}`);
  }

  async createSupplier(supplier: Partial<Supplier>): Promise<ApiResponse<Supplier>> {
    return this.request('POST', '/suppliers', supplier);
  }

  async updateSupplier(id: number, supplier: Partial<Supplier>): Promise<ApiResponse<Supplier>> {
    return this.request('PUT', `/suppliers/${id}`, supplier);
  }

  async deleteSupplier(id: number): Promise<ApiResponse<void>> {
    return this.request('DELETE', `/suppliers/${id}`);
  }

  // 同步记录相关API
  async getSyncRecords(filters?: SyncRecordFilters): Promise<ApiResponse<SyncRecord[]>> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }
    return this.request('GET', `/sync-records?${params}`);
  }

  async getSyncRecord(id: number): Promise<ApiResponse<SyncRecord>> {
    return this.request('GET', `/sync-records/${id}`);
  }

  async createSyncTask(config: {
    operation_type: SyncRecord['operation_type'];
    sync_type: SyncRecord['sync_type'];
    source_filter?: Record<string, any>;
    config?: Record<string, any>;
  }): Promise<ApiResponse<SyncRecord>> {
    return this.request('POST', '/sync-records', config);
  }

  async cancelSyncTask(id: number): Promise<ApiResponse<void>> {
    return this.request('POST', `/sync-records/${id}/cancel`);
  }

  async retrySyncTask(id: number): Promise<ApiResponse<SyncRecord>> {
    return this.request('POST', `/sync-records/${id}/retry`);
  }

  // 仪表板相关API
  async getDashboardStats(): Promise<ApiResponse<DashboardStats>> {
    return this.request('GET', '/dashboard/stats');
  }

  async getSyncProgress(taskId: string): Promise<ApiResponse<SyncRecord>> {
    return this.request('GET', `/sync-records/progress/${taskId}`);
  }

  // 统计数据API
  async getProductStats(params?: {
    date_from?: string;
    date_to?: string;
    group_by?: string;
  }): Promise<ApiResponse<any>> {
    const query = params ? `?${new URLSearchParams(params as any)}` : '';
    return this.request('GET', `/stats/products${query}`);
  }

  async getSupplierStats(params?: {
    date_from?: string;
    date_to?: string;
    group_by?: string;
  }): Promise<ApiResponse<any>> {
    const query = params ? `?${new URLSearchParams(params as any)}` : '';
    return this.request('GET', `/stats/suppliers${query}`);
  }

  async getSyncStats(params?: {
    date_from?: string;
    date_to?: string;
    group_by?: string;
  }): Promise<ApiResponse<any>> {
    const query = params ? `?${new URLSearchParams(params as any)}` : '';
    return this.request('GET', `/stats/sync${query}`);
  }

  // 导出数据API
  async exportProducts(config: {
    format: 'csv' | 'excel' | 'json';
    fields: string[];
    filters?: ProductFilters;
  }): Promise<Blob> {
    const response = await this.client.post('/products/export', config, {
      responseType: 'blob',
    });
    return response.data;
  }

  async exportSuppliers(config: {
    format: 'csv' | 'excel' | 'json';
    fields: string[];
    filters?: SupplierFilters;
  }): Promise<Blob> {
    const response = await this.client.post('/suppliers/export', config, {
      responseType: 'blob',
    });
    return response.data;
  }

  async exportSyncRecords(config: {
    format: 'csv' | 'excel' | 'json';
    fields: string[];
    filters?: SyncRecordFilters;
  }): Promise<Blob> {
    const response = await this.client.post('/sync-records/export', config, {
      responseType: 'blob',
    });
    return response.data;
  }

  // 系统信息API
  async getSystemInfo(): Promise<ApiResponse<{
    version: string;
    uptime: number;
    memory_usage: number;
    cpu_usage: number;
    disk_usage: number;
    database_status: string;
  }>> {
    return this.request('GET', '/system/info');
  }

  async getHealthCheck(): Promise<ApiResponse<{
    status: 'healthy' | 'unhealthy';
    checks: Array<{
      name: string;
      status: 'pass' | 'fail';
      message?: string;
    }>;
  }>> {
    return this.request('GET', '/health');
  }
}

// 创建API服务实例
const apiService = new ApiService();

export default apiService;