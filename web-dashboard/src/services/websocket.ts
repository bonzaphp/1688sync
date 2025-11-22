import { io, Socket } from 'socket.io-client';
import { RealtimeUpdate } from '../types';

class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isConnecting = false;

  // 事件监听器
  private listeners: Map<string, Set<Function>> = new Map();

  constructor() {
    this.connect();
  }

  connect(): void {
    if (this.isConnecting || (this.socket && this.socket.connected)) {
      return;
    }

    this.isConnecting = true;

    const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

    this.socket = io(wsUrl, {
      transports: ['websocket'],
      upgrade: false,
      rememberUpgrade: false,
      timeout: 5000,
      forceNew: true,
    });

    this.socket.on('connect', () => {
      console.log('WebSocket连接成功');
      this.isConnecting = false;
      this.reconnectAttempts = 0;
      this.emit('connected');
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket断开连接:', reason);
      this.emit('disconnected', reason);

      if (reason === 'io server disconnect') {
        // 服务器主动断开，需要重新连接
        this.handleReconnect();
      }
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket连接错误:', error);
      this.isConnecting = false;
      this.emit('error', error);
      this.handleReconnect();
    });

    // 监听实时数据更新
    this.socket.on('realtime_update', (data: RealtimeUpdate) => {
      this.emit('realtime_update', data);
    });

    // 监听同步进度更新
    this.socket.on('sync_progress', (data: any) => {
      this.emit('sync_progress', data);
    });

    // 监听同步完成
    this.socket.on('sync_completed', (data: any) => {
      this.emit('sync_completed', data);
    });

    // 监听同步失败
    this.socket.on('sync_failed', (data: any) => {
      this.emit('sync_failed', data);
    });

    // 监听新商品添加
    this.socket.on('new_product', (data: any) => {
      this.emit('new_product', data);
    });

    // 监听商品更新
    this.socket.on('product_updated', (data: any) => {
      this.emit('product_updated', data);
    });

    // 监听系统状态更新
    this.socket.on('system_status', (data: any) => {
      this.emit('system_status', data);
    });
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

      console.log(`尝试重新连接 WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})，延迟 ${delay}ms`);

      setTimeout(() => {
        this.connect();
      }, delay);
    } else {
      console.error('WebSocket重连失败，已达到最大重试次数');
      this.emit('reconnect_failed');
    }
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.listeners.clear();
  }

  // 事件监听
  on(event: string, callback: Function): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  // 移除事件监听
  off(event: string, callback?: Function): void {
    if (!this.listeners.has(event)) {
      return;
    }

    const eventListeners = this.listeners.get(event)!;
    if (callback) {
      eventListeners.delete(callback);
      if (eventListeners.size === 0) {
        this.listeners.delete(event);
      }
    } else {
      this.listeners.delete(event);
    }
  }

  // 触发事件
  private emit(event: string, data?: any): void {
    if (!this.listeners.has(event)) {
      return;
    }

    this.listeners.get(event)!.forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error(`事件监听器执行错误 (${event}):`, error);
      }
    });
  }

  // 发送消息到服务器
  send(event: string, data?: any): void {
    if (this.socket && this.socket.connected) {
      this.socket.emit(event, data);
    } else {
      console.warn('WebSocket未连接，无法发送消息');
    }
  }

  // 订阅特定同步任务的更新
  subscribeToSyncTask(taskId: string): void {
    this.send('subscribe_sync_task', { task_id: taskId });
  }

  // 取消订阅同步任务
  unsubscribeFromSyncTask(taskId: string): void {
    this.send('unsubscribe_sync_task', { task_id: taskId });
  }

  // 订阅仪表板更新
  subscribeToDashboard(): void {
    this.send('subscribe_dashboard');
  }

  // 取消订阅仪表板
  unsubscribeFromDashboard(): void {
    this.send('unsubscribe_dashboard');
  }

  // 获取连接状态
  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  // 获取连接状态描述
  getConnectionStatus(): 'connected' | 'connecting' | 'disconnected' | 'reconnecting' | 'failed' {
    if (this.socket?.connected) {
      return 'connected';
    }
    if (this.isConnecting) {
      return 'connecting';
    }
    if (this.reconnectAttempts > 0 && this.reconnectAttempts < this.maxReconnectAttempts) {
      return 'reconnecting';
    }
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      return 'failed';
    }
    return 'disconnected';
  }
}

// 创建WebSocket服务实例
const webSocketService = new WebSocketService();

export default webSocketService;