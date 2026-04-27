import type { Artifact } from "@/types/api";

interface ArtifactChipProps {
  artifact: Artifact;
}

const TYPE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  pmid: { bg: "bg-blue-50", text: "text-blue-700", label: "PMID" },
  nct: { bg: "bg-green-50", text: "text-green-700", label: "NCT" },
  patent: { bg: "bg-amber-50", text: "text-amber-700", label: "Patent" },
  grant: { bg: "bg-purple-50", text: "text-purple-700", label: "Grant" },
};

function getArtifactUrl(artifact: Artifact): string {
  if (artifact.url) return artifact.url;

  switch (artifact.type) {
    case "pmid":
      return `https://pubmed.ncbi.nlm.nih.gov/${artifact.id}`;
    case "nct":
      return `https://clinicaltrials.gov/study/${artifact.id}`;
    case "patent":
      return `https://patents.google.com/patent/${artifact.id}`;
    case "grant":
      return `https://reporter.nih.gov/project-details/${artifact.id}`;
    default:
      return "#";
  }
}

export default function ArtifactChip({ artifact }: ArtifactChipProps) {
  const style = TYPE_STYLES[artifact.type] ?? { bg: "bg-gray-50", text: "text-gray-700", label: artifact.type };
  const url = getArtifactUrl(artifact);

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      title={artifact.title}
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style.bg} ${style.text} hover:opacity-80 transition-opacity`}
    >
      <span className="font-semibold mr-1">{style.label}:</span>
      <span className="truncate max-w-[120px]">{artifact.id}</span>
      <svg className="ml-1 h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
      </svg>
    </a>
  );
}
