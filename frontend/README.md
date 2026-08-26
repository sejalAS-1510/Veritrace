# VeriTrace Frontend — React Dashboard

Dark-themed surveillance dashboard for detecting GenAI-scripted sleeper agent fraud and synthetic identities.

## Tech Stack
- **React 18** + **Vite**
- **Tailwind CSS** (Dark theme: slate / emerald / rose / cyan)
- **Recharts** (Spend trajectory curves, flag markers, adversarial arms race curves)
- **react-force-graph-2d** (Interactive Cosine Similarity Network Graph)
- **Axios** (API communication with Sentinel backend)
- **Lucide Icons**

## Features
1. **⚡ Live Feed (`src/components/LiveFeed.jsx`)**: Real-time generation of synthetic borrower attempts, telemetry metrics, and sentinel interception verdicts.
2. **📈 Timeline Replay (`src/components/TimelineReplay.jsx`)**: 24-week spend & login trajectory charts with $R^2$ linearity forensics and early intercept warning markers.
3. **⚔️ Arms Race (`src/components/ArmsRaceChart.jsx`)**: Dynamic 10-round visualization of adversarial prompt adaptation vs Sentinel AI model updates.
4. **🕸️ Similarity Graph (`src/components/SimilarityGraph.jsx`)**: Force-directed behavioral graph clustering coordinated fraud rings with adjustable similarity threshold.

## Quickstart

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Run the Vite Dev Server
```bash
npm run dev
```

The frontend dashboard will be running at [http://localhost:5173](http://localhost:5173).
