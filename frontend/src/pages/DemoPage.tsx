import { useState } from 'react';
import { ChatContainer } from '../components/chat';
import { ExtractionPanel } from '../components/extraction';
import { SampleMessages } from '../components/common';
import { ExcelUpload } from '../components/excel';
import { useChatStore } from '../store/chatStore';
import { MessageSquare, FileText, LayoutGrid, FileSpreadsheet } from 'lucide-react';

type RightPanelTab = 'extraction' | 'samples';

export function DemoPage() {
  const [rightPanelTab, setRightPanelTab] = useState<RightPanelTab>('extraction');
  const [showExcelUpload, setShowExcelUpload] = useState(false);
  const { sendMessage } = useChatStore();

  const handleSampleSelect = (message: string) => {
    sendMessage(message);
    setRightPanelTab('extraction');
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Top Header */}
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-green-600 flex items-center justify-center text-white font-bold">
            K
          </div>
          <div>
            <h1 className="font-bold text-gray-800">Kijani Supplies</h1>
            <p className="text-xs text-gray-500">WhatsApp Order Intake Demo</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowExcelUpload(true)}
            className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg flex items-center gap-2"
          >
            <FileSpreadsheet className="w-4 h-4" />
            Excel Order
          </button>
          <a
            href="/dashboard"
            className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg flex items-center gap-2"
          >
            <LayoutGrid className="w-4 h-4" />
            Dashboard
          </a>
        </div>
      </header>

      {/* Excel Upload Modal */}
      {showExcelUpload && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <ExcelUpload
            onSuccess={() => {
              // Keep modal open to show results
            }}
            onClose={() => setShowExcelUpload(false)}
          />
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Chat */}
        <div className="w-1/2 border-r flex flex-col">
          <ChatContainer />
        </div>

        {/* Right Panel - Extraction/Samples */}
        <div className="w-1/2 flex flex-col bg-white">
          {/* Tabs */}
          <div className="flex border-b">
            <button
              onClick={() => setRightPanelTab('extraction')}
              className={`flex-1 px-4 py-3 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                rightPanelTab === 'extraction'
                  ? 'text-green-600 border-b-2 border-green-600 bg-green-50'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <FileText className="w-4 h-4" />
              Extraction Results
            </button>
            <button
              onClick={() => setRightPanelTab('samples')}
              className={`flex-1 px-4 py-3 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                rightPanelTab === 'samples'
                  ? 'text-green-600 border-b-2 border-green-600 bg-green-50'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              Sample Messages
            </button>
          </div>

          {/* Panel Content */}
          <div className="flex-1 overflow-hidden">
            {rightPanelTab === 'extraction' ? (
              <ExtractionPanel />
            ) : (
              <SampleMessages onSelect={handleSampleSelect} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
