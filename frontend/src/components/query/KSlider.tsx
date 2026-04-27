"use client";

interface KSliderProps {
  value: number;
  onChange: (value: number) => void;
}

export default function KSlider({ value, onChange }: KSliderProps) {
  return (
    <div>
      <label htmlFor="k-value" className="block text-sm font-medium text-gray-700 mb-1">
        Number of Results (K)
      </label>
      <div className="flex items-center space-x-4">
        <input
          type="range"
          id="k-value"
          min={5}
          max={100}
          step={1}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <input
          type="number"
          min={5}
          max={100}
          value={value}
          onChange={(e) => {
            const v = Number(e.target.value);
            if (v >= 5 && v <= 100) onChange(v);
          }}
          className="w-20 rounded-md border border-gray-300 px-2 py-1 text-sm text-center focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
      <p className="mt-1 text-xs text-gray-500">
        How many ranked candidates to return (5-100).
      </p>
    </div>
  );
}
