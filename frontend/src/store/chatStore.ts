import { create } from 'zustand';
import type {
  Message,
  ExtractionResult,
  Order,
  ProcessMessageResponse,
  SampleMessage,
  MetricsSummary,
  ConfidenceDistribution,
} from '../types';
import { api } from '../api/client';

interface ChatState {
  // Chat state
  messages: Message[];
  conversationId: number | null;
  isProcessing: boolean;
  error: string | null;

  // Extraction state
  currentExtraction: ExtractionResult | null;
  currentOrder: Order | null;
  routingDecision: string | null;

  // Sample messages
  sampleMessages: SampleMessage[];

  // Metrics
  metrics: MetricsSummary | null;
  confidenceDistribution: ConfidenceDistribution | null;

  // Actions
  sendMessage: (content: string, messageType?: string) => Promise<void>;
  sendClarification: (content: string) => Promise<void>;
  loadSampleMessages: () => Promise<void>;
  useSampleMessage: (sample: SampleMessage) => void;
  loadMetrics: () => Promise<void>;
  resetChat: () => void;
  clearError: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  conversationId: null,
  isProcessing: false,
  error: null,
  currentExtraction: null,
  currentOrder: null,
  routingDecision: null,
  sampleMessages: [],
  metrics: null,
  confidenceDistribution: null,

  sendMessage: async (content: string, messageType: string = 'text') => {
    const { conversationId } = get();

    // Add user message immediately
    const userMessage: Message = {
      id: Date.now(),
      role: 'customer',
      content,
      message_type: messageType,
      created_at: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
      isProcessing: true,
      error: null,
      currentExtraction: null,
      currentOrder: null,
      routingDecision: null,
    }));

    try {
      let response: ProcessMessageResponse;

      if (conversationId) {
        // Continue existing conversation with clarification
        response = await api.submitClarification(conversationId, content);
      } else {
        // Start new conversation
        response = await api.processMessage(content, undefined, messageType);
      }

      // Add assistant response
      const assistantMessages: Message[] = [];

      if (response.confirmation_message) {
        assistantMessages.push({
          id: Date.now() + 1,
          role: 'assistant',
          content: response.confirmation_message,
          message_type: 'text',
          created_at: new Date().toISOString(),
        });
      }

      if (response.error) {
        assistantMessages.push({
          id: Date.now() + 2,
          role: 'system',
          content: `Error: ${response.error}`,
          message_type: 'text',
          created_at: new Date().toISOString(),
        });
      }

      set((state) => ({
        messages: [...state.messages, ...assistantMessages],
        conversationId: response.conversation_id,
        currentExtraction: response.extraction,
        currentOrder: response.order,
        routingDecision: response.routing_decision,
        isProcessing: false,
        error: response.error,
      }));
    } catch (err) {
      set({
        isProcessing: false,
        error: err instanceof Error ? err.message : 'Failed to process message',
      });
    }
  },

  sendClarification: async (content: string) => {
    const { conversationId } = get();

    if (!conversationId) {
      set({ error: 'No active conversation' });
      return;
    }

    // Reuse sendMessage which handles clarifications
    await get().sendMessage(content);
  },

  loadSampleMessages: async () => {
    try {
      const samples = await api.getSampleMessages();
      set({ sampleMessages: samples });
    } catch (err) {
      console.error('Failed to load sample messages:', err);
    }
  },

  useSampleMessage: (_sample: SampleMessage) => {
    // Reset chat - the actual message will be sent by the caller
    set({
      messages: [],
      conversationId: null,
      currentExtraction: null,
      currentOrder: null,
      routingDecision: null,
      error: null,
    });
  },

  loadMetrics: async () => {
    try {
      const [metrics, distribution] = await Promise.all([
        api.getMetricsSummary(),
        api.getConfidenceDistribution(),
      ]);
      set({ metrics, confidenceDistribution: distribution });
    } catch (err) {
      console.error('Failed to load metrics:', err);
    }
  },

  resetChat: () => {
    set({
      messages: [],
      conversationId: null,
      currentExtraction: null,
      currentOrder: null,
      routingDecision: null,
      error: null,
      isProcessing: false,
    });
  },

  clearError: () => {
    set({ error: null });
  },
}));
