interface IntegrityBadgeProps {
  disclosures: string[];
}

export default function IntegrityBadge({ disclosures }: IntegrityBadgeProps) {
  if (disclosures.length === 0) return null;

  return (
    <div className="mt-1">
      {disclosures.map((disclosure, index) => (
        <span
          key={index}
          className="inline-flex items-center rounded-full bg-yellow-50 border border-yellow-200 px-2 py-0.5 text-xs font-medium text-yellow-800 mr-1 mb-1"
          title={disclosure}
        >
          <svg className="h-3 w-3 mr-1 text-yellow-500" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
          </svg>
          {disclosure}
        </span>
      ))}
    </div>
  );
}
