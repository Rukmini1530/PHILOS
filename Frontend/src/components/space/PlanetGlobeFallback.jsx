import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "../../hooks/useReducedMotion";

/**
 * Fallback component for when WebGL is unavailable.
 * Renders a static, visually appealing planetary representation using CSS.
 */
const PlanetGlobeFallback = ({
  className = "",
  style = {},
  size = 400,
  showAtmosphere = true,
} = {}) => {
  const reducedMotion = useReducedMotion();
  const [isVisible, setIsVisible] = useState(true);
  const containerRef = useRef(null);
  const sphereRef = useRef(null);

  // Handle visibility for performance
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => setIsVisible(entry.isIntersecting),
      { threshold: 0.1 }
    );
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Subtle rotation animation when not in reduced motion
  useEffect(() => {
    if (reducedMotion || !isVisible || !sphereRef.current) return;

    let startTime = Date.now();
    const animate = () => {
      if (!sphereRef.current) return;
      const elapsed = (Date.now() - startTime) / 1000;
      const rotation = (elapsed * 360) / 120; // 120s per full rotation
      sphereRef.current.style.transform = `rotateX(5deg) rotateY(${rotation - 15}deg)`;
      requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [reducedMotion, isVisible]);

  return (
    <div
      ref={containerRef}
      className={cn("relative flex items-center justify-center", className)}
      style={{
        ...style,
        width: size,
        height: size,
        pointerEvents: "none", // Allow clicks to pass through
      }}
      aria-hidden="true"
      aria-label="Planetary globe (static fallback)"
    >
      {/* Planet sphere - using CSS 3D transform for depth illusion */}
      <div
        ref={sphereRef}
        className="relative rounded-full overflow-hidden"
        style={{
          width: size,
          height: size,
          backgroundImage: "url(/textures/earth_day_4096.jpg)",
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
          borderRadius: "50%",
          boxShadow: `
            inset 0 -${size * 0.3}px ${size * 0.4}px rgba(0, 0, 0, 0.5),
            inset 0 ${size * 0.1}px ${size * 0.2}px rgba(255, 255, 255, 0.1),
            0 0 ${size * 0.15}px rgba(101, 217, 255, 0.2),
            0 0 ${size * 0.3}px rgba(167, 139, 250, 0.1)
          `,
          transform: "rotateX(5deg) rotateY(-15deg)",
          transition: "transform 0.1s linear",
        }}
      >
        {/* Atmospheric glow layer */}
        {showAtmosphere && (
          <div
            className="absolute inset-0 rounded-full"
            style={{
              background: `
                radial-gradient(
                  circle at 30% 30%,
                  rgba(101, 217, 255, 0.15) 0%,
                  rgba(167, 139, 250, 0.1) 40%,
                  transparent 70%
                )
              `,
              borderRadius: "50%",
              pointerEvents: "none",
            }}
            aria-hidden="true"
          />
        )}

        {/* Terminator line suggestion */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: "linear-gradient(90deg, transparent 50%, rgba(0, 0, 0, 0.3) 100%)",
            borderRadius: "50%",
            pointerEvents: "none",
            opacity: 0.3,
          }}
          aria-hidden="true"
        />
      </div>
    </div>
  );
};

const cn = (...classes) => classes.filter(Boolean).join(" ");

export default PlanetGlobeFallback;