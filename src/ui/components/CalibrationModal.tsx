import React from 'react';

const CalibrationModal: React.FC = () => {
  const [isOpen] = React.useState(false);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
        <h2 className="text-2xl font-bold mb-4">Voice Calibration</h2>
        <p className="text-gray-600 mb-4">
          Please speak for 5-10 seconds to calibrate your voice profile.
        </p>
        <div className="mb-6">
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: '0%' }}></div>
          </div>
          <p className="text-sm text-gray-500 mt-2">Recording: 0 / 10 seconds</p>
        </div>
        <div className="flex gap-3">
          <button className="flex-1 bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-lg transition duration-200">
            Start Recording
          </button>
          <button className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 font-medium py-2 px-4 rounded-lg transition duration-200">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default CalibrationModal;
