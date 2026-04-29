"use client";

import { useState, type KeyboardEvent } from "react";

interface MeshExpansionInspectorProps {
  terms: string[];
  onTermsChange: (terms: string[]) => void;
}

export default function MeshExpansionInspector({ terms, onTermsChange }: MeshExpansionInspectorProps) {
  const [inputValue, setInputValue] = useState("");

  const addTerm = (term: string) => {
    const trimmed = term.trim();
    if (trimmed && !terms.includes(trimmed)) {
      onTermsChange([...terms, trimmed]);
    }
    setInputValue("");
  };

  const removeTerm = (index: number) => {
    onTermsChange(terms.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTerm(inputValue);
    }
  };

  return (
    <div className="rounded-md border border-gray-200 bg-gray-50 p-4">
      <h4 className="text-sm font-medium text-gray-700 mb-2">Expanded MeSH Terms</h4>
      <div className="flex flex-wrap gap-2 mb-3">
        {terms.map((term, index) => (
          <span
            key={index}
            className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
          >
            {term}
            <button
              type="button"
              onClick={() => removeTerm(index)}
              className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full text-blue-400 hover:bg-blue-200 hover:text-blue-600"
            >
              x
            </button>
          </span>
        ))}
        {terms.length === 0 && (
          <span className="text-xs text-gray-400 italic">No terms detected yet</span>
        )}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Add a MeSH term..."
          className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <button
          type="button"
          onClick={() => addTerm(inputValue)}
          disabled={!inputValue.trim()}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Add
        </button>
      </div>
    </div>
  );
}
