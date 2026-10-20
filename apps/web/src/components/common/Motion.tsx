import { useEffect, useRef, useState, type MouseEvent } from "react";

/** Mouse handler that feeds the `.spotlight` glow its position. */
export function spotlight(e: MouseEvent<HTMLElement>) {
  const el = e.currentTarget;
  const r = el.getBoundingClientRect();
  el.style.setProperty("--mx", `${e.clientX - r.left}px`);
  el.style.setProperty("--my", `${e.clientY - r.top}px`);
}

const reduced = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/**
 * Counts the numeric part of a display string up from zero, keeping its prefix, suffix and precision
 * ("$1.24B", "98.42%", "14,200"). Strings without a number render unchanged.
 */
export function CountUp({ value, duration = 1100 }: { value: string; duration?: number }) {
  const m = value.match(/^([^\d-]*)(-?[\d,]*\.?\d+)(.*)$/);
  const [shown, setShown] = useState(m && !reduced() ? `${m[1]}0${m[3]}` : value);
  const frame = useRef(0);

  useEffect(() => {
    if (!m || reduced()) {
      setShown(value);
      return;
    }
    const [, pre, num, post] = m;
    const target = Number(num.replace(/,/g, ""));
    const decimals = (num.split(".")[1] ?? "").length;
    const grouped = num.includes(",");
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 4);
      const n = target * eased;
      const text = grouped
        ? n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
        : n.toFixed(decimals);
      setShown(`${pre}${text}${post}`);
      if (p < 1) frame.current = requestAnimationFrame(tick);
    };
    frame.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, duration]);

  return <>{shown}</>;
}
