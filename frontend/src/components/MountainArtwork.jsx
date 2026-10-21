import React from 'react';

export default function MountainArtwork() {
  return (
    <div className="dashboard-artwork" aria-hidden="true">
      <svg viewBox="0 0 280 100" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: '100%', height: '100%' }}>
        {/* Subtle Sun */}
        <circle cx="240" cy="30" r="18" fill="#F4DFC3" opacity="0.85" />
        
        {/* Topographic Mountain Contour Lines */}
        <path d="M120 95 C 160 85, 200 45, 245 42 C 265 40, 275 60, 280 75" stroke="#8C9A90" strokeWidth="1" strokeOpacity="0.5" />
        <path d="M100 95 C 145 80, 185 52, 235 48 C 255 46, 270 65, 280 80" stroke="#8C9A90" strokeWidth="1" strokeOpacity="0.45" />
        <path d="M80 95 C 130 75, 170 58, 220 54 C 245 52, 265 70, 280 85" stroke="#8C9A90" strokeWidth="1" strokeOpacity="0.4" />
        <path d="M60 95 C 115 70, 155 64, 205 60 C 235 58, 260 75, 280 90" stroke="#8C9A90" strokeWidth="1" strokeOpacity="0.35" />
        <path d="M40 95 C 100 65, 140 70, 190 66 C 225 64, 255 80, 280 95" stroke="#8C9A90" strokeWidth="1" strokeOpacity="0.3" />
        <path d="M20 95 C 85 60, 125 76, 175 72 C 215 70, 250 85, 280 98" stroke="#8C9A90" strokeWidth="1" strokeOpacity="0.25" />

        {/* Shading hash marks for hand-drawn woodblock look */}
        <path d="M220 54 L 218 60 M225 53 L 223 59 M230 52 L 228 58 M235 51 L 233 57 M240 50 L 238 56 M245 50 L 243 56" stroke="#8C9A90" strokeWidth="0.8" strokeOpacity="0.4" />
        <path d="M180 66 L 178 72 M185 65 L 183 71 M190 64 L 188 70 M195 63 L 193 69 M200 62 L 198 68" stroke="#8C9A90" strokeWidth="0.8" strokeOpacity="0.3" />
      </svg>
    </div>
  );
}
