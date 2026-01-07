import { create } from 'zustand';
import type {
  Message,
  ExtractionResult,
  Order,
  ProcessMessageResponse,
  SampleMessage,
  MetricsSummary,
  ConfidenceDistribution,
  ExcelOrderResponse,
  CumulativeState,
  Changes,
  OrderSnapshot,
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

  // Cumulative state
  cumulativeState: CumulativeState | null;
  snapshots: OrderSnapshot[];
  latestChanges: Changes | null;
  isHydrating: boolean;

  // Excel order state
  currentExcelOrder: ExcelOrderResponse | null;

  // Sample messages
  sampleMessages: SampleMessage[];

  // Metrics
  metrics: MetricsSummary | null;
  confidenceDistribution: ConfidenceDistribution | null;

  // Actions
  sendMessage: (content: string, messageType?: string) => Promise<void>;
  sendClarification: (content: string) => Promise<void>;
  uploadExcelFile: (file: File) => Promise<void>;
  loadSampleMessages: () => Promise<void>;
  useSampleMessage: (sample: SampleMessage) => void;
  loadMetrics: () => Promise<void>;
  hydrateFromServer: (conversationId: number) => Promise<void>;
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
  cumulativeState: null,
  snapshots: [],
  latestChanges: null,
  isHydrating: false,
  currentExcelOrder: null,
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
      // Don't clear cumulative state - preserve across messages
      latestChanges: null,
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
        // Update cumulative state from response
        cumulativeState: response.cumulative_state || state.cumulativeState,
        latestChanges: response.changes || null,
        snapshots: response.cumulative_state
          ? [
              ...state.snapshots,
              {
                id: Date.now(),
                version: response.cumulative_state.version,
                items: response.cumulative_state.items,
                changes: response.changes || null,
                message_id: response.message_id,
                extraction_confidence: response.extraction?.overall_confidence || null,
                requires_clarification: response.extraction?.requires_clarification || false,
                created_at: new Date().toISOString(),
              },
            ]
          : state.snapshots,
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

  uploadExcelFile: async (file: File) => {
    // Reset chat for new Excel upload
    set({
      messages: [],
      conversationId: null,
      currentExtraction: null,
      currentOrder: null,
      routingDecision: null,
      currentExcelOrder: null,
      cumulativeState: null,
      snapshots: [],
      latestChanges: null,
      error: null,
      isProcessing: true,
    });

    // Add file message immediately
    const fileMessage: Message = {
      id: Date.now(),
      role: 'customer',
      content: `📎 ${file.name}`,
      message_type: 'excel_order',
      created_at: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, fileMessage],
    }));

    try {
      const response = await api.uploadExcelOrder(file);

      if (response.success) {
        // Build concise summary message - items are shown in ExtractionPanel
        const categories = response.sheets.map(s => s.category).join(', ');
        let summaryContent = `✅ Excel order processed successfully!\n\n`;
        summaryContent += `📦 ${response.total_items} items across ${response.total_categories} categories`;
        if (response.total_value) {
          summaryContent += `\n💰 Total: KES ${response.total_value.toLocaleString()}`;
        }
        summaryContent += `\n\n📋 Categories: ${categories}`;
        summaryContent += `\n\n👉 View full order details in the Extraction Results panel`;

        const summaryMessage: Message = {
          id: Date.now() + 1,
          role: 'system',
          content: summaryContent,
          message_type: 'text',
          created_at: new Date().toISOString(),
        };

        const assistantMessages: Message[] = [summaryMessage];

        if (response.confirmation_message) {
          assistantMessages.push({
            id: Date.now() + 2,
            role: 'assistant',
            content: response.confirmation_message,
            message_type: 'text',
            created_at: new Date().toISOString(),
          });
        }

        set((state) => ({
          messages: [...state.messages, ...assistantMessages],
          conversationId: response.conversation_id,
          currentExcelOrder: response,
          routingDecision: response.routing_decision,
          // Populate cumulative state from Excel response for ExtractionPanel display
          cumulativeState: response.cumulative_state,
          snapshots: response.cumulative_state ? [{
            id: Date.now(),
            version: 1,
            items: response.cumulative_state.items,
            changes: {
              added: response.cumulative_state.items,
              modified: [],
              unchanged: [],
            },
            message_id: response.conversation_id || 0,
            extraction_confidence: response.overall_confidence,
            requires_clarification: false,
            created_at: new Date().toISOString(),
          }] : [],
          latestChanges: response.cumulative_state ? {
            added: response.cumulative_state.items,
            modified: [],
            unchanged: [],
          } : null,
          isProcessing: false,
        }));
      } else {
        set((state) => ({
          messages: [...state.messages, {
            id: Date.now() + 1,
            role: 'system',
            content: `❌ Error: ${response.error}`,
            message_type: 'text',
            created_at: new Date().toISOString(),
          }],
          isProcessing: false,
          error: response.error,
        }));
      }
    } catch (err) {
      set((state) => ({
        messages: [...state.messages, {
          id: Date.now() + 1,
          role: 'system',
          content: `❌ Error: ${err instanceof Error ? err.message : 'Upload failed'}`,
          message_type: 'text',
          created_at: new Date().toISOString(),
        }],
        isProcessing: false,
        error: err instanceof Error ? err.message : 'Upload failed',
      }));
    }
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
      cumulativeState: null,
      snapshots: [],
      latestChanges: null,
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

  hydrateFromServer: async (conversationId: number) => {
    set({ isHydrating: true, error: null });

    try {
      const state = await api.getConversationState(conversationId);

      set({
        conversationId: state.conversation_id,
        messages: state.messages,
        cumulativeState: state.cumulative_state,
        snapshots: state.snapshots,
        isHydrating: false,
      });
    } catch (err) {
      set({
        isHydrating: false,
        error: err instanceof Error ? err.message : 'Failed to load conversation',
      });
    }
  },

  resetChat: () => {
    set({
      messages: [],
      conversationId: null,
      currentExtraction: null,
      currentOrder: null,
      routingDecision: null,
      cumulativeState: null,
      snapshots: [],
      latestChanges: null,
      currentExcelOrder: null,
      error: null,
      isProcessing: false,
    });
  },

  clearError: () => {
    set({ error: null });
  },
}));
