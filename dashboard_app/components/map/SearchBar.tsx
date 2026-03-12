"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Search, MapPin, Loader2 } from "lucide-react";
import { searchPlaces, formatAddress, type PhotonFeature } from "@/lib/geocoding";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  onSelect: (lon: number, lat: number, zoom?: number) => void;
  placeholder?: string;
  className?: string;
}

export function SearchBar({
  onSelect,
  placeholder = "חיפוש רחוב, עיר, כתובת...",
  className = "",
}: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PhotonFeature[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const fetchResults = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    setIsLoading(true);
    try {
      const features = await searchPlaces(q, { limit: 6 });
      setResults(features);
      setSelectedIndex(-1);
    } catch {
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!query.trim()) {
      setResults([]);
      setIsOpen(false);
      return;
    }
    debounceRef.current = setTimeout(() => {
      fetchResults(query);
      setIsOpen(true);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, fetchResults]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (f: PhotonFeature) => {
    const [lon, lat] = f.geometry.coordinates;
    onSelect(lon, lat, 15);
    setQuery(formatAddress(f));
    setResults([]);
    setIsOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => (i < results.length - 1 ? i + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => (i > 0 ? i - 1 : results.length - 1));
    } else if (e.key === "Enter" && selectedIndex >= 0 && results[selectedIndex]) {
      e.preventDefault();
      handleSelect(results[selectedIndex]);
    }
  };

  return (
    <div ref={wrapperRef} className={cn("relative w-full max-w-xl", className)}>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full rounded-xl border border-white/10 bg-zinc-900/90 py-3 pl-10 pr-10 text-sm text-white placeholder-zinc-500 focus:border-cyan-500/50 focus:outline-none focus:ring-2 focus:ring-cyan-500/20"
        />
        {isLoading && (
          <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-cyan-400" />
        )}
      </div>

      {isOpen && results.length > 0 && (
        <ul className="absolute top-full left-0 right-0 z-50 mt-2 max-h-72 overflow-auto rounded-xl border border-white/10 bg-zinc-900/95 py-2 shadow-xl backdrop-blur-xl">
          {results.map((f, i) => {
            const [lon, lat] = f.geometry.coordinates;
            const isSelected = i === selectedIndex;
            return (
                <li key={`${f.properties.osm_id ?? ""}-${lon}-${lat}-${i}`}>
                <button
                  type="button"
                  onClick={() => handleSelect(f)}
                  onMouseEnter={() => setSelectedIndex(i)}
                  className={cn(
                    "flex w-full items-start gap-3 px-4 py-3 text-left transition-colors",
                    isSelected ? "bg-cyan-500/20 text-cyan-400" : "text-zinc-300 hover:bg-white/5"
                  )}
                >
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-zinc-500" />
                  <div>
                    <p className="font-medium">{formatAddress(f)}</p>
                    <p className="text-xs text-zinc-500">
                      {f.properties.type} · {f.properties.country ?? ""}
                    </p>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
