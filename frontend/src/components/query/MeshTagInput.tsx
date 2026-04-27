"use client";

import { useState, type KeyboardEvent } from "react";

interface MeshTagInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
}

export default function MeshTagInput({ tags, onChange }: MeshTagInputProps) {
  const [inputValue, setInputValue] = useState("");

  const addTag = (tag: string) => {
    const trimmed = tag.trim();
    if (trimmed && !tags.includes(trimmed)) {
      onChange([...tags, trimmed]);
    }
    setInputValue("");
  };

  const removeTag = (index: number) => {
    onChange(tags.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(inputValue);
    } else if (e.key === "Backspace" && !inputValue && tags.length > 0) {
      removeTag(tags.length - 1);
    }
  };

  return (
    <div>
      <label htmlFor="mesh-tags" className="block text-sm font-medium text-gray-700 mb-1">
        MeSH Override Tags
      </label>
      <div className="flex flex-wrap gap-2 rounded-md border border-gray-300 bg-white px-3 py-2 focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500">
        {tags.map((tag, index) => (
          <span
            key={index}
            className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(index)}
              className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full text-blue-400 hover:bg-blue-200 hover:text-blue-600"
            >
              x
            </button>
          </span>
        ))}
        <input
          id="mesh-tags"
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => { if (inputValue) addTag(inputValue); }}
          placeholder={tags.length === 0 ? "Type a MeSH term and press Enter..." : ""}
          className="flex-1 min-w-[120px] border-0 bg-transparent text-sm focus:outline-none focus:ring-0"
        />
      </div>
      <p className="mt-1 text-xs text-gray-500">
        Optional. Press Enter or comma to add a tag. These override automatic MeSH expansion.
      </p>
    </div>
  );
}
