import { StructureHint } from '../store/sessionStore';

interface Props {
  hint: StructureHint;
}

export function StructureHintCard({ hint }: Props) {
  return (
    <div className="bg-white border-l-4 border-indigo-500 p-4 rounded-lg shadow-md mb-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-bold text-gray-800">{hint.name}</h3>
        <span className="text-xs text-indigo-600 bg-indigo-50 px-2 py-1 rounded border border-indigo-100">
          Structure
        </span>
      </div>
      
      <div className="space-y-2 mb-4">
        {hint.sections.map((section, i) => (
          <div key={i} className="flex items-start text-sm">
            <span className="w-12 font-mono text-xs text-gray-500 pt-0.5">{section.percentage}</span>
            <div className="flex-1">
              <span className="font-semibold text-gray-700">{section.name}:</span>
              <span className="text-gray-600 ml-1">{section.description}</span>
            </div>
          </div>
        ))}
      </div>
      
      <div className="bg-yellow-50 p-2 rounded border border-yellow-100">
        <p className="text-xs font-semibold text-yellow-800 mb-1 flex items-center gap-1">
          <span>💡</span> Pro Tips
        </p>
        <ul className="list-disc list-inside text-xs text-yellow-900/80 space-y-0.5">
          {hint.tips.slice(0, 2).map((tip, i) => (
            <li key={i}>{tip}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
