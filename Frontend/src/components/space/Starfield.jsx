import { useEffect, useRef, useState, useCallback } from "react";
import { useReducedMotion } from "../../hooks/useReducedMotion";

/**
 * Lightweight animated starfield component.
 * Renders a subtle, performant starfield with gentle twinkling and movement.
 * Respects prefers-reduced-motion preference.
 * Adjusts particle count based on screen size and device capabilities.
 */
const Starfield = ({
  className = "",
  style = {},
  particleCount = 100,
  intensity = "default",
  colorVariant = "white",
} = {}) => {
  const reducedMotion = useReducedMotion();
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const animateRef = useRef(null);
  const starsRef = useRef([]);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [devicePixelRatio, setDevicePixelRatio] = useState(
    typeof window !== "undefined" ? window.devicePixelRatio : 1
  );

  // Color variants using design tokens
  const colorVariants = {
    white: { base: "rgba(255, 255, 255, ", accent: "rgba(255, 255, 255, " },
    cyan: { base: "rgba(101, 217, 255, ", accent: "rgba(101, 217, 255, " },
    icy: { base: "rgba(139, 233, 253, ", accent: "rgba(139, 233, 253, " },
    violet: { base: "rgba(167, 139, 250, ", accent: "rgba(167, 139, 250, " },
    mixed: { base: "rgba(255, 255, 255, ", accent: "rgba(101, 217, 255, " },
  };

  const colors = colorVariants[colorVariant] || colorVariants.white;

  // Intensity-based configuration
  const intensityConfig = {
    subtle: { maxParticles: 150, twinkleSpeed: 0.8, driftMultiplier: 0.5 },
    default: { maxParticles: 300, twinkleSpeed: 1.0, driftMultiplier: 1.0 },
    prominent: { maxParticles: 500, twinkleSpeed: 1.2, driftMultiplier: 1.5 },
  }[intensity] || intensityConfig.default;

  // Calculate appropriate particle count based on screen size and device
  const calculateParticleCount = useCallback(() => {
    if (typeof window === "undefined") return particleCount;

    const area = window.innerWidth * window.innerHeight;
    const baseCount = particleCount;

    // Scale particle count based on screen area
    // Base: 100 particles for ~1920x1080
    const referenceArea = 1920 * 1080;
    const scaledCount = Math.round(baseCount * (area / referenceArea));

    // Clamp between reasonable bounds
    const minParticles = 30;
    const maxParticles = intensityConfig.maxParticles;

    // Reduce for mobile or reduced motion
    if (reducedMotion) {
      return Math.min(Math.max(Math.round(scaledCount * 0.3), minParticles), 100);
    }

    // Reduce on mobile devices
    const isMobile = window.innerWidth < 768;
    if (isMobile) {
      return Math.min(Math.max(Math.round(scaledCount * 0.5), minParticles), maxParticles * 0.6);
    }

    return Math.min(Math.max(scaledCount, minParticles), maxParticles);
  }, [particleCount, reducedMotion, intensityConfig.maxParticles]);

  // Generate star data
  const generateStars = useCallback((count, width, height) => {
    const stars = [];
    for (let i = 0; i < count; i++) {
      // Natural distribution with slight clustering
      const clusterFactor = Math.random();
      const x = clusterFactor < 0.3
        ? (Math.random() * width * 0.4) + (width * 0.3)  // Slight center clustering
        : Math.random() * width;
      const y = clusterFactor < 0.3
        ? (Math.random() * height * 0.4) + (height * 0.3)
        : Math.random() * height;

      // Vary star types
      const isAccent = Math.random() < 0.08; // 8% accent color stars
      const baseSize = Math.random() * 1.5 + 0.5;
      const opacity = Math.random() * 0.5 + 0.3;

      stars.push({
        id: i,
        x,
        y,
        baseSize,
        size: baseSize,
        opacity,
        isAccent,
        twinklePhase: Math.random() * Math.PI * 2,
        twinkleSpeed: (0.5 + Math.random() * 1.5) * intensityConfig.twinkleSpeed,
        driftX: (Math.random() - 0.5) * 0.02 * intensityConfig.driftMultiplier,
        driftY: (Math.random() - 0.5) * 0.02 * intensityConfig.driftMultiplier,
      });
    }
    return stars;
  }, [intensityConfig.twinkleSpeed, intensityConfig.driftMultiplier]);

  // Initialize stars
  useEffect(() => {
    if (!dimensions.width || !dimensions.height) return;

    const count = calculateParticleCount();
    starsRef.current = generateStars(count, dimensions.width, dimensions.height);
  }, [dimensions, calculateParticleCount, generateStars]);

  // Handle resize
  useEffect(() => {
    const updateDimensions = () => {
      if (canvasRef.current) {
        const rect = canvasRef.current.getBoundingClientRect();
        setDimensions({ width: rect.width, height: rect.height });
        setDevicePixelRatio(window.devicePixelRatio || 1);
      }
    };

    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
  }, []);

  // Animation loop
  useEffect(() => {
    if (reducedMotion) {
      // In reduced motion mode, just render static stars
      return;
    }

    const canvas = canvasRef.current;

    const animate = (timestamp) => {
      if (!canvas) return;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const width = dimensions.width;
      const height = dimensions.height;
      const dpr = devicePixelRatio;

      // Clear canvas
      ctx.clearRect(0, 0, width * dpr, height * dpr);

      // Update and draw stars
      const stars = starsRef.current;
      const time = timestamp / 1000;

      ctx.save();
      ctx.scale(dpr, dpr);

      for (const star of stars) {
        // Update position with subtle drift
        star.x += star.driftX;
        star.y += star.driftY;

        // Wrap around edges
        if (star.x < 0) star.x = dimensions.width;
        if (star.x > dimensions.width) star.x = 0;
        if (star.y < 0) star.y = dimensions.height;
        if (star.y > dimensions.height) star.y = 0;

        // Calculate twinkle
        const twinkle = Math.sin(star.twinklePhase + time * star.twinkleSpeed * Math.PI * 2);
        const currentOpacity = star.opacity + twinkle * 0.3;
        const currentSize = star.baseSize * (0.8 + twinkle * 0.4);

        // Draw star
        ctx.beginPath();
        ctx.arc(star.x, star.y, currentSize, 0, Math.PI * 2);
        const color = star.isAccent ? colors.accent : colors.base;
        ctx.fillStyle = `${color}${Math.max(0.1, Math.min(1, currentOpacity))})`;
        ctx.fill();
      }

      ctx.restore();

      animationRef.current = requestAnimationFrame(animate);
    };

    // Store animate function in ref for visibility handler
    animateRef.current = animate;

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [dimensions, devicePixelRatio, reducedMotion, colors]);

  // Reduced motion: render static stars once
  useEffect(() => {
    if (!reducedMotion) return;

    const canvas = canvasRef.current;
    if (!canvas || !dimensions.width || !dimensions.height) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = dimensions.width;
    const height = dimensions.height;
    const dpr = devicePixelRatio;

    ctx.clearRect(0, 0, width * dpr, height * dpr);
    ctx.save();
    ctx.scale(devicePixelRatio, devicePixelRatio);

    for (const star of starsRef.current) {
      ctx.beginPath();
      ctx.arc(star.x, star.y, star.baseSize, 0, Math.PI * 2);
      const color = star.isAccent ? colors.accent : colors.base;
      ctx.fillStyle = `${color}${star.opacity})`;
      ctx.fill();
    }
    ctx.restore();
  }, [reducedMotion, dimensions, devicePixelRatio, colors]);

  // Handle visibility change to pause animation when tab is hidden
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
          animationRef.current = null;
        }
      } else if (!reducedMotion && !animationRef.current && animateRef.current) {
        animationRef.current = requestAnimationFrame(animateRef.current);
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [reducedMotion]);

  // Canvas setup
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const updateCanvasSize = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * devicePixelRatio;
      canvas.height = rect.height * devicePixelRatio;
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
    };

    updateCanvasSize();
    window.addEventListener("resize", updateCanvasSize);
    return () => window.removeEventListener("resize", updateCanvasSize);
  }, [devicePixelRatio]);

  if (!dimensions.width || !dimensions.height) {
    return (
      <canvas
        ref={canvasRef}
        className={cn("fixed inset-0 w-full h-full", className)}
        style={{
          ...style,
          display: "block",
        }}
        aria-hidden="true"
      />
    );
  }

  return (
    <canvas
      ref={canvasRef}
      className={cn("fixed inset-0 w-full h-full", className)}
      style={{
        ...style,
        display: "block",
        touchAction: "none",
      }}
      aria-hidden="true"
      aria-label="Animated starfield background"
    />
  );
};

// Simple className utility for this component
const cn = (...classes) => classes.filter(Boolean).join(" ");

export default Starfield;