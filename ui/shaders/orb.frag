#version 330

uniform float time;
uniform float volume;
uniform vec2 resolution;

out vec4 fragColor;

float noise(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    vec2 uv = (gl_FragCoord.xy - 0.5 * resolution.xy) / min(resolution.y, resolution.x);
    
    float dist = length(uv);
    
    // Base orb shape
    float radius = 0.2 + volume * 0.1;
    float glow = 0.05 / (dist - radius + 0.05);
    glow = clamp(glow, 0.0, 2.0);
    
    // Pulse effect
    float pulse = sin(time * 2.0) * 0.02;
    radius += pulse;
    
    // Colors (Cyan/Blue)
    vec3 color = vec3(0.0, 0.8, 1.0) * glow;
    
    // Add some noise/energy texture
    float n = noise(uv * 10.0 + time * 0.5);
    color += vec3(0.0, 0.4, 0.6) * n * (1.0 - dist * 2.0) * 0.5;
    
    // Inner core
    float core = smoothstep(radius, radius - 0.01, dist);
    color += vec3(0.8, 0.9, 1.0) * core;
    
    // Vignette/Transparency
    float alpha = glow + core;
    fragColor = vec4(color, clamp(alpha, 0.0, 1.0));
}
