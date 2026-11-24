import { useEffect, useRef, useState, useCallback } from "react";
import Starfield from "./Starfield";
import { useReducedMotion } from "../../hooks/useReducedMotion";

/**
 * Reusable space background component.
 * Provides a consistent deep-space background across all PHILOS pages.
 * Supports configurable intensity, optional starfield, and reduced motion.
 */
const SpaceBackground = ({
  className = "",
  style = {},
  children,
  intensity = "default",
  showStars = true,
  showGradients = true,
  showSpotlight = false,
  childrenClassName = "",
  childrenStyle = {},
} = {}) => {
  const reducedMotion = useReducedMotion();
  const [isHovering, setIsHovering] = useState(false);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Mouse tracking for spotlight effect
  const handleMouseMove = useCallback((e) => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setMousePosition({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
    }
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener("mousemove", handleMouseMove);
      container.addEventListener("mouseenter", () => setIsHovering(true));
      container.addEventListener("mouseleave", () => setIsHovering(false));
      return () => {
        container.removeEventListener("mousemove", handleMouseMove);
        container.removeEventListener("mouseenter", () => setIsHovering(true));
        container.removeEventListener("mouseleave", () => setIsHovering(false));
      };
    }
  }, [handleMouseMove]);

  // Reduced motion disables interactive effects
  const isHoveringEffective = !reducedMotion && isHovering && showSpotlight;

  return (
    <div
      ref={containerRef}
      className={cn("fixed inset-0 overflow-hidden", className)}
      style={{
        ...style,
        zIndex: 0,
        pointerEvents: "none", // Allow clicks to pass through
      }}
    >
      {/* Base deep space background */}
      <div className="absolute inset-0 bg-[var(--color-bg-void,#030712)]" />

      {/* Atmospheric gradient layers - using design tokens */}
      {showGradients && (
        <>
          <div
            className="absolute top-0 left-1/4 w-[600px] h-[600px] opacity-30"
            style={{
              background:
                "radial-gradient(circle, var(--color-glow-cyan) 0%, transparent 70%)",
              transform: "translate(-50%, -50%)",
            }}
            aria-hidden="true"
          />
          <div
            className="absolute top-1/2 right-0 w-[800px] h-[800px] opacity-30"
            style={{
              background:
                "radial-gradient(circle, var(--color-glow-violet) 0%, transparent 70%)",
              transform: "translate(30%, -50%)",
            }}
            aria-hidden="true"
          />
          <div
            className="absolute bottom-0 left-1/2 w-[700px] h-[700px] opacity-30"
            style={{
              background:
                "radial-gradient(circle, var(--color-glow-rose) 0%, transparent 70%)",
              transform: "translate(-50%, 30%)",
            }}
            aria-hidden="true"
          />
        </>
      )}

      {/* Animated starfield */}
      {showStars && <Starfield intensity={intensity} particleCount={120} />}

      {/* Optional hover spotlight effect (disabled in reduced motion) */}
      {isHoveringEffective && (
        <div
          className="absolute pointer-events-none"
          style={{
            left: mousePosition.x - 150,
            top: mousePosition.y - 150,
            width: 300,
            height: 300,
            background:
              "radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, rgba(124, 58, 237, 0.08) 40%, transparent 70%)",
            borderRadius: "50%",
            position: "absolute",
            pointerEvents: "none",
          }}
          aria-hidden="true"
        />
      )}

      {/* Children content */}
      {children && (
        <div
          className={cn("relative z-10", childrenClassName)}
          style={childrenStyle}
        >
          {children}
        </div>
      )}
    </div>
  );
};

// Utility for class names
const cn = (...classes) => classes.filter(Boolean).join(" ");

export default SpaceBackground;