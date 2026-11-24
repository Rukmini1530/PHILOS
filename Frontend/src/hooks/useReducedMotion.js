import { useEffect, useState } from "react";

/**
 * Hook to detect and respond to the user's prefers-reduced-motion preference.
 * Returns true if the user prefers reduced motion.
 */
export function useReducedMotion() {
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    // Check initial preference
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mediaQuery.matches);

    // Listen for changes
    const handler = (event) => {
      setReducedMotion(event.matches);
    };

    mediaQuery.addEventListener("change", handler);

    return () => {
      mediaQuery.removeEventListener("change", handler);
    };
  }, []);

  return reducedMotion;
}

export default useReducedMotion;