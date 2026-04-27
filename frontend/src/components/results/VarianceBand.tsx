import type { ScoreVarianceBand } from "@/types/api";

interface VarianceBandProps {
  score: number;
  band: ScoreVarianceBand;
}

export default function VarianceBand({ score, band }: VarianceBandProps) {
  return (
    <div className="flex items-center space-x-2">
      <span className="text-sm font-semibold text-gray-900">
        {score.toFixed(3)}
      </span>
      <span className="text-xs text-gray-500">
        [{band.low.toFixed(3)} - {band.high.toFixed(3)}]
      </span>
    </div>
  );
}
