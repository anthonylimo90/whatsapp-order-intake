import { useState, useRef } from 'react';
import { Upload, FileSpreadsheet, X, Check, AlertCircle, Loader2 } from 'lucide-react';

interface ExcelOrderItem {
  category: string;
  subcategory: string | null;
  product_name: string;
  unit: string;
  price: number | null;
  quantity: number;
  row_number: number;
}

interface ExcelOrderSheet {
  category: string;
  items: ExcelOrderItem[];
  total_items: number;
  total_value: number | null;
}

interface ExcelOrderResponse {
  success: boolean;
  filename: string | null;
  customer_name: string | null;
  sheets: ExcelOrderSheet[];
  total_items: number;
  total_categories: number;
  total_value: number | null;
  warnings: string[];
  error: string | null;
  conversation_id: number | null;
  order_id: number | null;
  confirmation_message: string | null;
  routing_decision: string | null;
}

interface ExcelUploadProps {
  onSuccess?: (result: ExcelOrderResponse) => void;
  onClose?: () => void;
}

export function ExcelUpload({ onSuccess, onClose }: ExcelUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [customerName, setCustomerName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<ExcelOrderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && (droppedFile.name.endsWith('.xlsx') || droppedFile.name.endsWith('.xls'))) {
      setFile(droppedFile);
      setError(null);
    } else {
      setError('Please upload an Excel file (.xlsx or .xls)');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    if (customerName) {
      formData.append('customer_name', customerName);
    }

    try {
      const response = await fetch('/api/excel-order', {
        method: 'POST',
        body: formData,
      });

      const data: ExcelOrderResponse = await response.json();

      if (data.success) {
        setResult(data);
        onSuccess?.(data);
      } else {
        setError(data.error || 'Failed to process Excel file');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setCustomerName('');
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-KE', {
      style: 'currency',
      currency: 'KES',
      minimumFractionDigits: 0,
    }).format(value);
  };

  // Show results view
  if (result) {
    return (
      <div className="bg-white rounded-xl shadow-lg max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-green-600 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
              <Check className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-white font-semibold">Excel Order Processed</h2>
              <p className="text-green-100 text-sm">{result.filename}</p>
            </div>
          </div>
          {onClose && (
            <button onClick={onClose} className="text-white/80 hover:text-white">
              <X className="w-6 h-6" />
            </button>
          )}
        </div>

        {/* Summary */}
        <div className="p-6 border-b bg-gray-50">
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-800">{result.total_categories}</p>
              <p className="text-sm text-gray-500">Categories</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-800">{result.total_items}</p>
              <p className="text-sm text-gray-500">Items</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">
                {result.total_value ? formatCurrency(result.total_value) : '-'}
              </p>
              <p className="text-sm text-gray-500">Total Value</p>
            </div>
            <div className="text-center">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                {result.routing_decision?.replace('_', ' ')}
              </span>
              <p className="text-sm text-gray-500 mt-1">Status</p>
            </div>
          </div>
        </div>

        {/* Categories */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="space-y-4">
            {result.sheets.map((sheet) => (
              <div key={sheet.category} className="border rounded-lg overflow-hidden">
                <div className="bg-gray-100 px-4 py-2 flex items-center justify-between">
                  <h3 className="font-medium text-gray-800">{sheet.category}</h3>
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span>{sheet.total_items} items</span>
                    {sheet.total_value && (
                      <span className="font-medium text-gray-700">
                        {formatCurrency(sheet.total_value)}
                      </span>
                    )}
                  </div>
                </div>
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left px-4 py-2 font-medium text-gray-600">Product</th>
                      <th className="text-left px-4 py-2 font-medium text-gray-600">Subcategory</th>
                      <th className="text-right px-4 py-2 font-medium text-gray-600">Qty</th>
                      <th className="text-right px-4 py-2 font-medium text-gray-600">Unit</th>
                      <th className="text-right px-4 py-2 font-medium text-gray-600">Price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sheet.items.map((item, idx) => (
                      <tr key={idx} className="border-t">
                        <td className="px-4 py-2 text-gray-800">{item.product_name}</td>
                        <td className="px-4 py-2 text-gray-500">{item.subcategory || '-'}</td>
                        <td className="px-4 py-2 text-right font-medium">{item.quantity}</td>
                        <td className="px-4 py-2 text-right text-gray-500">{item.unit}</td>
                        <td className="px-4 py-2 text-right">
                          {item.price ? formatCurrency(item.price) : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-gray-50 flex justify-between">
          <button
            onClick={handleReset}
            className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Upload Another
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              Done
            </button>
          )}
        </div>
      </div>
    );
  }

  // Upload view
  return (
    <div className="bg-white rounded-xl shadow-lg max-w-lg w-full mx-4">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-600 to-green-700 px-6 py-4 flex items-center justify-between rounded-t-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
            <FileSpreadsheet className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-white font-semibold">Upload Excel Order</h2>
            <p className="text-green-100 text-sm">Multi-category order file</p>
          </div>
        </div>
        {onClose && (
          <button onClick={onClose} className="text-white/80 hover:text-white">
            <X className="w-6 h-6" />
          </button>
        )}
      </div>

      <div className="p-6">
        {/* Customer Name */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Customer/Lodge Name
          </label>
          <input
            type="text"
            value={customerName}
            onChange={(e) => setCustomerName(e.target.value)}
            placeholder="e.g., Saruni Mara Lodge"
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none"
          />
        </div>

        {/* Drop Zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
            isDragging
              ? 'border-green-500 bg-green-50'
              : file
              ? 'border-green-500 bg-green-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            onChange={handleFileSelect}
            className="hidden"
          />
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <FileSpreadsheet className="w-10 h-10 text-green-600" />
              <div className="text-left">
                <p className="font-medium text-gray-800">{file.name}</p>
                <p className="text-sm text-gray-500">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                }}
                className="p-1 hover:bg-gray-200 rounded"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
          ) : (
            <>
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-600 font-medium">
                Drop Excel file here or click to browse
              </p>
              <p className="text-sm text-gray-400 mt-1">
                Supports .xlsx and .xls files
              </p>
            </>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Expected Format */}
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-800 font-medium mb-1">Expected Format:</p>
          <ul className="text-xs text-blue-700 space-y-1">
            <li>• Each worksheet = one category (Dairy, Produce, etc.)</li>
            <li>• Columns: Subcategory, Product Name, Unit, Price, Opening Order</li>
            <li>• "Opening Order" column contains quantities</li>
          </ul>
        </div>

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={!file || isUploading}
          className={`w-full mt-4 py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition-colors ${
            file && !isUploading
              ? 'bg-green-600 text-white hover:bg-green-700'
              : 'bg-gray-200 text-gray-500 cursor-not-allowed'
          }`}
        >
          {isUploading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Upload className="w-5 h-5" />
              Upload & Process
            </>
          )}
        </button>
      </div>
    </div>
  );
}
