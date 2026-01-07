import type {
  ProcessMessageResponse,
  Conversation,
  ConversationListItem,
  ConversationState,
  Order,
  MetricsSummary,
  ConfidenceDistribution,
  SampleMessage,
  Customer,
  Product,
  ExcelOrderResponse,
} from '../types';

const API_BASE = '/api';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Messages
  async processMessage(content: string, customerName?: string, messageType: string = 'text'): Promise<ProcessMessageResponse> {
    return fetchJSON(`${API_BASE}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        content,
        customer_name: customerName,
        message_type: messageType,
      }),
    });
  },

  async submitClarification(conversationId: number, content: string): Promise<ProcessMessageResponse> {
    return fetchJSON(`${API_BASE}/conversations/${conversationId}/clarify`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  },

  // Conversations
  async listConversations(limit = 50, offset = 0): Promise<ConversationListItem[]> {
    return fetchJSON(`${API_BASE}/conversations?limit=${limit}&offset=${offset}`);
  },

  async getConversation(id: number): Promise<Conversation> {
    return fetchJSON(`${API_BASE}/conversations/${id}`);
  },

  async getConversationState(id: number): Promise<ConversationState> {
    return fetchJSON(`${API_BASE}/conversations/${id}/state`);
  },

  // Orders
  async listOrders(status?: string, limit = 50, offset = 0): Promise<Order[]> {
    let url = `${API_BASE}/orders?limit=${limit}&offset=${offset}`;
    if (status) url += `&status=${status}`;
    return fetchJSON(url);
  },

  // Metrics
  async getMetricsSummary(): Promise<MetricsSummary> {
    return fetchJSON(`${API_BASE}/metrics/summary`);
  },

  async getConfidenceDistribution(): Promise<ConfidenceDistribution> {
    return fetchJSON(`${API_BASE}/metrics/confidence`);
  },

  // Sample Messages
  async getSampleMessages(): Promise<SampleMessage[]> {
    return fetchJSON(`${API_BASE}/samples`);
  },

  // Customers & Products
  async getCustomers(): Promise<Customer[]> {
    return fetchJSON(`${API_BASE}/customers`);
  },

  async getProducts(): Promise<Product[]> {
    return fetchJSON(`${API_BASE}/products`);
  },

  // Excel Orders
  async uploadExcelOrder(file: File, customerName?: string): Promise<ExcelOrderResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (customerName) {
      formData.append('customer_name', customerName);
    }

    const response = await fetch(`${API_BASE}/excel-order`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },
};
