import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "../../hooks/useReducedMotion";
import PlanetGlobeFallback from "./PlanetGlobeFallback";

/**
 * Reusable 3D Planetary Globe component using Three.js.
 * Renders a realistic Earth with surface texture, clouds, atmosphere glow, and day/night cycle.
 * Respects prefers-reduced-motion and provides a CSS fallback when WebGL is unavailable.
 */
const PlanetGlobe = ({
  className = "",
  style = {},
  size = 400,
  rotationSpeed = 0.00015,
  showClouds = true,
  showAtmosphere = true,
  showDayNight = true,
  autoRotate = true,
  cameraDistance = 2.5,
} = {}) => {
  const reducedMotion = useReducedMotion();
  const [webglAvailable, setWebglAvailable] = useState(true);
  const containerRef = useRef(null);
  const canvasRef = useRef(null);

  // Three.js objects stored in refs to avoid React re-renders
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const planetRef = useRef(null);
  const cloudsRef = useRef(null);
  const atmosphereRef = useRef(null);
  const animationRef = useRef(null);
  const texturesRef = useRef({});
  const THREEref = useRef(null);

  // Check WebGL availability
  useEffect(() => {
    try {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
      setWebglAvailable(!!gl);
    } catch (e) {
      setWebglAvailable(false);
    }
  }, []);

  // Initialize Three.js scene
  useEffect(() => {
    if (!webglAvailable || !containerRef.current || !canvasRef.current) return;

    const canvas = canvasRef.current;

    // Import Three.js dynamically
    import("three").then((THREE) => {
      THREEref.current = THREE;
      // Renderer setup
      const renderer = new THREEref.current.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: true, // Transparent background
        preserveDrawingBuffer: false,
      });

      renderer.setSize(size, size);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); // Limit DPR for performance
      renderer.toneMapping = THREEref.current.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.0;

      // Scene setup
      const scene = new THREEref.current.Scene();

      // Camera setup
      const camera = new THREEref.current.PerspectiveCamera(45, 1, 0.1, 100);
      camera.position.z = cameraDistance;

      // Lighting - Directional light for sun
      const sunLight = new THREEref.current.DirectionalLight(0xffffff, 1.2);
      sunLight.position.set(5, 3, 5);
      scene.add(sunLight);

      // Ambient light for fill
      const ambientLight = new THREEref.current.AmbientLight(0x334455, 0.3);
      scene.add(ambientLight);

      // Point light for additional highlight
      const rimLight = new THREEref.current.DirectionalLight(0x65d9ff, 0.15);
      rimLight.position.set(-5, -3, -5);
      scene.add(rimLight);

      // Load textures
      const textureLoader = new THREEref.current.TextureLoader();

      const loadTexture = (url) => {
        return new Promise((resolve, reject) => {
          textureLoader.load(url, resolve, undefined, reject);
        });
      };

      Promise.all([
        loadTexture("/textures/earth_day_4096.jpg"),
        showClouds ? loadTexture("/textures/earth_clouds_1024.png") : Promise.resolve(null),
        showAtmosphere ? loadTexture("/textures/earth_atmos_2048.jpg") : Promise.resolve(null),
        showDayNight ? loadTexture("/textures/earth_lights_2048.png") : Promise.resolve(null),
      ])
        .then(([dayTexture, cloudsTexture, atmosTexture, lightsTexture]) => {
          if (!sceneRef.current) return; // Component unmounted

          // Configure day texture
          dayTexture.wrapS = THREEref.current.RepeatWrapping;
          dayTexture.wrapT = THREEref.current.RepeatWrapping;
          dayTexture.colorSpace = THREEref.current.SRGBColorSpace;
          dayTexture.anisotropy = renderer.capabilities.getMaxAnisotropy();
          texturesRef.current.day = dayTexture;

          // Planet geometry and material
          const planetGeometry = new THREEref.current.SphereGeometry(1, 64, 64);
          const planetMaterial = new THREEref.current.MeshStandardMaterial({
            map: dayTexture,
            roughness: 0.8,
            metalness: 0.05,
            color: 0xffffff,
          });

          const planet = new THREEref.current.Mesh(planetGeometry, planetMaterial);
          planet.rotation.y = -Math.PI / 4; // Initial rotation
          scene.add(planet);
          planetRef.current = planet;

          // Clouds layer
          if (showClouds && cloudsTexture) {
            cloudsTexture.wrapS = THREEref.current.RepeatWrapping;
            cloudsTexture.wrapT = THREEref.current.RepeatWrapping;
            cloudsTexture.colorSpace = THREEref.current.SRGBColorSpace;
            texturesRef.current.clouds = cloudsTexture;

            const cloudsGeometry = new THREEref.current.SphereGeometry(1.015, 64, 64);
            const cloudsMaterial = new THREEref.current.MeshStandardMaterial({
              map: cloudsTexture,
              transparent: true,
              opacity: 0.4,
              depthWrite: false,
              side: THREEref.current.DoubleSide,
            });

            const clouds = new THREEref.current.Mesh(cloudsGeometry, cloudsMaterial);
            scene.add(clouds);
            cloudsRef.current = clouds;
          }

          // Atmosphere glow
          if (showAtmosphere && atmosTexture) {
            atmosTexture.wrapS = THREEref.current.RepeatWrapping;
            atmosTexture.wrapT = THREEref.current.RepeatWrapping;
            atmosTexture.colorSpace = THREEref.current.SRGBColorSpace;
            texturesRef.current.atmosphere = atmosTexture;

            const atmosGeometry = new THREEref.current.SphereGeometry(1.15, 32, 32);
            const atmosMaterial = new THREEref.current.MeshBasicMaterial({
              map: atmosTexture,
              transparent: true,
              opacity: 0.25,
              side: THREEref.current.BackSide,
              depthWrite: false,
              blending: THREEref.current.AdditiveBlending,
            });

            const atmosphere = new THREEref.current.Mesh(atmosGeometry, atmosMaterial);
            scene.add(atmosphere);
            atmosphereRef.current = atmosphere;
          }

          // Day/night cycle using lights texture
          if (showDayNight && lightsTexture) {
            lightsTexture.wrapS = THREEref.current.RepeatWrapping;
            lightsTexture.wrapT = THREEref.current.RepeatWrapping;
            lightsTexture.colorSpace = THREEref.current.SRGBColorSpace;
            texturesRef.current.lights = lightsTexture;

            // Update planet material to use emissive map for night lights
            if (planetRef.current) {
              planetRef.current.material.emissiveMap = lightsTexture;
              planetRef.current.material.emissive = new THREEref.current.Color(0x332211);
              planetRef.current.material.emissiveIntensity = 0.3;
              planetRef.current.material.needsUpdate = true;
            }
          }

          // Store refs
          sceneRef.current = scene;
          cameraRef.current = camera;
          rendererRef.current = renderer;

          // Start animation
          animate();
        })
        .catch((error) => {
          console.warn("Failed to load planet textures:", error);
          setWebglAvailable(false); // Fall back to CSS
        });
    });

    // Animation loop
    const animate = (timestamp) => {
      if (!sceneRef.current || !cameraRef.current || !rendererRef.current) return;
      if (reducedMotion) return; // Respect reduced motion

      const planet = planetRef.current;
      const clouds = cloudsRef.current;
      const atmosphere = atmosphereRef.current;

      // Auto-rotate planet
      if (autoRotate && planet) {
        planet.rotation.y += rotationSpeed;
      }

      // Rotate clouds slightly faster
      if (clouds) {
        clouds.rotation.y += rotationSpeed * 1.05;
      }

      // Subtle atmosphere pulse
      if (atmosphere) {
        const pulse = Math.sin(timestamp * 0.0003) * 0.02 + 1;
        atmosphere.scale.setScalar(pulse);
      }

      // Update day/night cycle by rotating the sun light
      if (showDayNight) {
        const sunAngle = timestamp * 0.00002;
        const sunLight = sceneRef.current.children.find(
          (child) => child instanceof THREEref.current.DirectionalLight && child.intensity > 1
        );
        if (sunLight) {
          sunLight.position.x = Math.cos(sunAngle) * 5;
          sunLight.position.z = Math.sin(sunAngle) * 5;
        }
      }

      rendererRef.current.render(sceneRef.current, cameraRef.current);
      animationRef.current = requestAnimationFrame(animate);
    };

    // Handle resize
    const handleResize = () => {
      if (!containerRef.current || !rendererRef.current || !cameraRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const width = rect.width || size;
      const height = rect.height || size;
      rendererRef.current.setSize(width, height);
      cameraRef.current.aspect = width / height;
      cameraRef.current.updateProjectionMatrix();
    };

    window.addEventListener("resize", handleResize);

    // Cleanup
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      window.removeEventListener("resize", handleResize);

      // Dispose Three.js resources
      if (rendererRef.current) {
        rendererRef.current.dispose();
        rendererRef.current.forceContextLoss();
      }

      // Dispose geometries
      if (planetRef.current?.geometry) planetRef.current.geometry.dispose();
      if (cloudsRef.current?.geometry) cloudsRef.current.geometry.dispose();
      if (atmosphereRef.current?.geometry) atmosphereRef.current.geometry.dispose();

      // Dispose materials
      if (planetRef.current?.material) {
        if (Array.isArray(planetRef.current.material)) {
          planetRef.current.material.forEach((m) => m.dispose());
        } else {
          planetRef.current.material.dispose();
        }
      }
      if (cloudsRef.current?.material) cloudsRef.current.material.dispose();
      if (atmosphereRef.current?.material) atmosphereRef.current.material.dispose();

      // Dispose textures
      Object.values(texturesRef.current).forEach((texture) => {
        if (texture && texture.dispose) texture.dispose();
      });
      texturesRef.current = {};

      // Clear refs
      sceneRef.current = null;
      cameraRef.current = null;
      rendererRef.current = null;
      planetRef.current = null;
      cloudsRef.current = null;
      atmosphereRef.current = null;
    };
  }, [webglAvailable, reducedMotion, size, rotationSpeed, showClouds, showAtmosphere, showDayNight, autoRotate, cameraDistance]);

  // If WebGL not available or reduced motion with no auto-rotate, show fallback
  if (!webglAvailable || (reducedMotion && !autoRotate)) {
    return (
      <PlanetGlobeFallback
        className={className}
        style={style}
        size={size}
        showAtmosphere={showAtmosphere}
      />
    );
  }

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
      aria-label="Interactive 3D planetary globe"
    >
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        style={{
          width: "100%",
          height: "100%",
          display: "block",
        }}
      />
    </div>
  );
};

const cn = (...classes) => classes.filter(Boolean).join(" ");

export default PlanetGlobe;