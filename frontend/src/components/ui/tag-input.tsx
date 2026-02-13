import { useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getAllTags } from "@/services/api/devices";

interface TagInputProps {
  tags: string[];
  onTagsChange: (tags: string[]) => void;
  placeholder?: string;
}

export function TagInput({ tags, onTagsChange, placeholder }: TagInputProps) {
  const [inputValue, setInputValue] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let isMounted = true;
    async function loadTags() {
      try {
        setIsLoading(true);
        const response = await getAllTags();
        if (isMounted) {
          setSuggestions(response.tags);
        }
      } catch (error) {
        console.error("Failed to load tag suggestions:", error);
        if (isMounted) {
          setSuggestions([]);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }
    loadTags();
    return () => {
      isMounted = false;
    };
  }, []);

  const filteredSuggestions = useMemo(() => {
    const query = inputValue.trim().toLowerCase();
    if (!query) return [];
    return suggestions.filter(
      (tag) =>
        tag.toLowerCase().includes(query) &&
        !tags.some((existing) => existing.toLowerCase() === tag.toLowerCase())
    );
  }, [inputValue, suggestions, tags]);

  function addTag(tag: string) {
    const trimmed = tag.trim();
    if (!trimmed) return;
    if (tags.some((existing) => existing.toLowerCase() === trimmed.toLowerCase())) {
      setInputValue("");
      return;
    }
    onTagsChange([...tags, trimmed]);
    setInputValue("");
  }

  function removeTag(tag: string) {
    onTagsChange(tags.filter((t) => t !== tag));
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {tags.length === 0 ? (
          <span className="text-xs text-muted-foreground">No tags</span>
        ) : (
          tags.map((tag) => (
            <Badge key={tag} variant="outline" className="flex items-center gap-1">
              <span>{tag}</span>
              <button
                type="button"
                onClick={() => removeTag(tag)}
                className="text-muted-foreground hover:text-foreground"
                aria-label={`Remove ${tag}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))
        )}
      </div>

      <div className="relative">
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder={placeholder || "Add tag"}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addTag(inputValue);
            } else if (e.key === "Backspace" && !inputValue && tags.length > 0) {
              removeTag(tags[tags.length - 1]);
            }
          }}
        />
        {filteredSuggestions.length > 0 && (
          <div className="absolute z-10 mt-1 w-full rounded-md border border-border bg-background shadow-sm">
            {filteredSuggestions.slice(0, 8).map((tag) => (
              <button
                key={tag}
                type="button"
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-accent"
                onClick={() => addTag(tag)}
              >
                <span>{tag}</span>
              </button>
            ))}
          </div>
        )}
        {isLoading && suggestions.length === 0 && (
          <div className="mt-2 text-xs text-muted-foreground">Loading tags...</div>
        )}
      </div>

      <div className="flex justify-end">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => addTag(inputValue)}
          disabled={!inputValue.trim()}
        >
          Add tag
        </Button>
      </div>
    </div>
  );
}
