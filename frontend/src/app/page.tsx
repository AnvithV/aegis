import QueryForm from "@/components/query/QueryForm";

export default function NewQueryPage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">New Query</h1>
        <p className="mt-2 text-sm text-gray-600">
          Submit a new query to rank researchers for a labeling task.
        </p>
      </div>
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <QueryForm />
      </div>
    </div>
  );
}
