import React from 'react';

const ContextLoader: React.FC = () => {
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4">Context Documents</h2>
      <div className="space-y-3">
        <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition duration-200">
          Upload Documents
        </button>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center">
          <p className="text-gray-500 text-sm">Drag and drop files here</p>
          <p className="text-gray-400 text-xs mt-1">PDF, DOCX, TXT supported</p>
        </div>
        <div className="mt-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Loaded Documents:</h3>
          <ul className="text-sm text-gray-600 space-y-1">
            <li className="p-2 bg-gray-50 rounded">No documents loaded</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default ContextLoader;
