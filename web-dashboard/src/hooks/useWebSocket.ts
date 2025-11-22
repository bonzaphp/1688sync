import { useState, useEffect, useCallback, useRef } from 'react';
import webSocketService from '../services/websocket';
import { RealtimeUpdate } from '../types';

interface UseWebSocketOptions {
  autoConnect?: boolean;
  reconnectOnMount?: boolean;
}

interface UseWebSocketResult {
  connected: boolean;
  connectionStatus: 'connected' | 'connecting' | 'disconnected' | 'reconnecting' | 'failed';
  lastMessage: RealtimeUpdate | null;
  send: (event: string, data?: any) => void;
  subscribe: (event: string, callback: (data: any) => void) => () => void;
  subscribeToSyncTask: (taskId: string) => void;
  unsubscribeFromSyncTask: (taskId: string) => void;
  subscribeToDashboard: () => void;
  unsubscribeFromDashboard: () => void;
  reconnect: () => void;
  disconnect: () => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketResult {
  const { autoConnect = true, reconnectOnMount = false } = options;

  const [connected, setConnected] = useState<boolean>(false);
  const [connectionStatus, setConnectionStatus] = useState<UseWebSocketResult['connectionStatus']>('disconnected');
  const [lastMessage, setLastMessage] = useState<RealtimeUpdate | null>(null);

  const listenersRef = useRef<Map<string, Set<Function>>>(new Map());
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 更新连接状态
  const updateConnectionStatus = useCallback(() => {
    const status = webSocketService.getConnectionStatus();
    const isConnected = webSocketService.isConnected();

    setConnectionStatus(status);
    setConnected(isConnected);
  }, []);

  // 处理连接事件
  useEffect(() => {
    const handleConnected = () => {
      updateConnectionStatus();
    };

    const handleDisconnected = () => {
      updateConnectionStatus();
    };

    const handleError = () => {
      updateConnectionStatus();
    };

    const handleReconnectFailed = () => {
      updateConnectionStatus();
    };

    const handleRealtimeUpdate = (data: RealtimeUpdate) => {
      setLastMessage(data);
    };

    // 注册事件监听器
    webSocketService.on('connected', handleConnected);
    webSocketService.on('disconnected', handleDisconnected);
    webSocketService.on('error', handleError);
    webSocketService.on('reconnect_failed', handleReconnectFailed);
    webSocketService.on('realtime_update', handleRealtimeUpdate);

    // 初始连接状态
    updateConnectionStatus();

    return () => {
      webSocketService.off('connected', handleConnected);
      webSocketService.off('disconnected', handleDisconnected);
      webSocketService.off('error', handleError);
      webSocketService.off('reconnect_failed', handleReconnectFailed);
      webSocketService.off('realtime_update', handleRealtimeUpdate);
    };
  }, [updateConnectionStatus]);

  // 自动连接
  useEffect(() => {
    if (autoConnect && !connected && connectionStatus === 'disconnected') {
      webSocketService.connect();
    }
  }, [autoConnect, connected, connectionStatus]);

  // 重连逻辑
  useEffect(() => {
    if (reconnectOnMount && connectionStatus === 'disconnected') {
      reconnectTimeoutRef.current = setTimeout(() => {
        webSocketService.connect();
      }, 1000);
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [reconnectOnMount, connectionStatus]);

  // 发送消息
  const send = useCallback((event: string, data?: any) => {
    webSocketService.send(event, data);
  }, []);

  // 订阅事件
  const subscribe = useCallback((event: string, callback: (data: any) => void) => {
    webSocketService.on(event, callback);

    // 返回取消订阅函数
    return () => {
      webSocketService.off(event, callback);
    };
  }, []);

  // 订阅同步任务
  const subscribeToSyncTask = useCallback((taskId: string) => {
    webSocketService.subscribeToSyncTask(taskId);
  }, []);

  // 取消订阅同步任务
  const unsubscribeFromSyncTask = useCallback((taskId: string) => {
    webSocketService.unsubscribeFromSyncTask(taskId);
  }, []);

  // 订阅仪表板
  const subscribeToDashboard = useCallback(() => {
    webSocketService.subscribeToDashboard();
  }, []);

  // 取消订阅仪表板
  const unsubscribeFromDashboard = useCallback(() => {
    webSocketService.unsubscribeFromDashboard();
  }, []);

  // 重新连接
  const reconnect = useCallback(() => {
    webSocketService.disconnect();
    setTimeout(() => {
      webSocketService.connect();
    }, 1000);
  }, []);

  // 断开连接
  const disconnect = useCallback(() => {
    webSocketService.disconnect();
  }, []);

  return {
    connected,
    connectionStatus,
    lastMessage,
    send,
    subscribe,
    subscribeToSyncTask,
    unsubscribeFromSyncTask,
    subscribeToDashboard,
    unsubscribeFromDashboard,
    reconnect,
    disconnect
  };
}

// 专门用于同步任务的Hook
export function useSyncTask(taskId?: string) {
  const [syncProgress, setSyncProgress] = useState<any>(null);
  const [isSubscribed, setIsSubscribed] = useState<boolean>(false);

  const {
    connected,
    subscribe,
    subscribeToSyncTask,
    unsubscribeFromSyncTask
  } = useWebSocket();

  // 订阅同步任务更新
  useEffect(() => {
    if (taskId && connected && !isSubscribed) {
      subscribeToSyncTask(taskId);
      setIsSubscribed(true);

      const unsubscribeSyncProgress = subscribe('sync_progress', (data) => {
        if (data.task_id === taskId) {
          setSyncProgress(data);
        }
      });

      const unsubscribeSyncCompleted = subscribe('sync_completed', (data) => {
        if (data.task_id === taskId) {
          setSyncProgress({ ...data, status: 'completed' });
        }
      });

      const unsubscribeSyncFailed = subscribe('sync_failed', (data) => {
        if (data.task_id === taskId) {
          setSyncProgress({ ...data, status: 'failed' });
        }
      });

      return () => {
        unsubscribeSyncProgress();
        unsubscribeSyncCompleted();
        unsubscribeSyncFailed();
        unsubscribeFromSyncTask(taskId);
        setIsSubscribed(false);
      };
    }
  }, [taskId, connected, isSubscribed, subscribe, subscribeToSyncTask, unsubscribeFromSyncTask]);

  return {
    syncProgress,
    isSubscribed
  };
}

// 专门用于仪表板的Hook
export function useDashboardUpdates() {
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [isSubscribed, setIsSubscribed] = useState<boolean>(false);

  const {
    connected,
    subscribe,
    subscribeToDashboard,
    unsubscribeFromDashboard
  } = useWebSocket();

  // 订阅仪表板更新
  useEffect(() => {
    if (connected && !isSubscribed) {
      subscribeToDashboard();
      setIsSubscribed(true);

      const unsubscribeNewProduct = subscribe('new_product', (data: any) => {
        setDashboardData((prev: any) => ({
          ...prev,
          newProducts: [data, ...(prev?.newProducts || [])]
        }));
      });

      const unsubscribeProductUpdated = subscribe('product_updated', (data: any) => {
        setDashboardData((prev: any) => ({
          ...prev,
          updatedProducts: [data, ...(prev?.updatedProducts || [])]
        }));
      });

      const unsubscribeSystemStatus = subscribe('system_status', (data: any) => {
        setDashboardData((prev: any) => ({
          ...prev,
          systemStatus: data
        }));
      });

      return () => {
        unsubscribeNewProduct();
        unsubscribeProductUpdated();
        unsubscribeSystemStatus();
        unsubscribeFromDashboard();
        setIsSubscribed(false);
      };
    }
  }, [connected, isSubscribed, subscribe, subscribeToDashboard, unsubscribeFromDashboard]);

  return {
    dashboardData,
    isSubscribed
  };
}