// API Response Types

export interface Message {
  id: number;
  role: 'customer' | 'system' | 'assistant';
  content: string;
  message_type: string;
  created_at: string;
}

export interface ExtractedItem {
  product_name: string;
  quantity: number;
  unit: string;
  confidence: 'high' | 'medium' | 'low';
  original_text: string;
  notes: string | null;
}

export interface ExtractionResult {
  customer_name: string;
  customer_organization: string | null;
  items: ExtractedItem[];
  requested_delivery_date: string | null;
  delivery_urgency: string | null;
  overall_confidence: 'high' | 'medium' | 'low';
  requires_clarification: boolean;
  clarification_needed: string[];
}

export interface Order {
  id: number;
  customer_name: string | null;
  organization: string | null;
  items_json: { items: ExtractedItem[] } | null;
  delivery_date: string | null;
  confidence_score: number;
  overall_confidence: string | null;
  requires_review: boolean;
  requires_clarification: boolean;
  status: string;
  routing_decision: string | null;
  erp_order_id: string | null;
  processing_time_ms: number | null;
  created_at: string;
}

export interface Conversation {
  id: number;
  customer_name: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
  latest_order: Order | null;
}

export interface ConversationListItem {
  id: number;
  customer_name: string | null;
  status: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProcessMessageResponse {
  conversation_id: number;
  message_id: number;
  extraction: ExtractionResult | null;
  confirmation_message: string | null;
  order: Order | null;
  routing_decision: string | null;
  error: string | null;
}

export interface MetricsSummary {
  total_orders: number;
  orders_today: number;
  orders_this_week: number;
  auto_processed_count: number;
  review_queue_count: number;
  manual_count: number;
  auto_process_rate: number;
  average_confidence: number;
  average_processing_time_ms: number;
  total_time_saved_minutes: number;
}

export interface ConfidenceDistribution {
  high: number;
  medium: number;
  low: number;
}

export interface SampleMessage {
  id: string;
  name: string;
  description: string;
  message: string;
  expected_confidence: string;
  language: string;
}

export interface Customer {
  id: number;
  name: string;
  organization: string | null;
  phone: string | null;
  tier: string;
  region: string | null;
}

export interface Product {
  id: number;
  name: string;
  category: string | null;
  unit: string;
  price: number;
  in_stock: boolean;
}
