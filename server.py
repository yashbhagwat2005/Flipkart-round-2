from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import networkx as nx

from diversion_route_planner import (
    build_graph,
    cluster_hotspots,
    find_diversion_routes,
    officer_instruction,
    SCENARIOS
)

app = FastAPI(title="ASTRAM Routing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow Vite frontend
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data once
DATA_FILE = "Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv"
try:
    df = pd.read_csv(DATA_FILE, low_memory=False)
    df["latitude"]  = pd.to_numeric(df["latitude"],  errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["corridor"]  = df["corridor"].fillna("Non-corridor")
    df = df.dropna(subset=["latitude", "longitude"])
    df = df[(df["latitude"] > 12.7) & (df["latitude"] < 13.2)
          & (df["longitude"] > 77.3) & (df["longitude"] < 77.9)]
    HOTSPOTS = cluster_hotspots(df, eps_km=0.8, min_samples=4)
except Exception as e:
    print(f"Error loading data: {e}")
    HOTSPOTS = []

G = build_graph()
# Precompute node details
NODES_DICT = {n: d for n, d in G.nodes(data=True)}

def get_path_metrics(graph, path):
    if not path:
        return {"distance": 0, "path": []}
    
    dist = 0
    route_details = []
    for u, v in zip(path, path[1:]):
        edge_data = graph.get_edge_data(u, v)
        if edge_data:
            # Get shortest parallel edge
            min_edge = min(edge_data.values(), key=lambda x: x["distance_km"])
            dist += min_edge["distance_km"]
            route_details.append({
                "from": u,
                "to": v,
                "corridor": min_edge["corridor"],
                "distance": min_edge["distance_km"]
            })
    return {"distance": round(dist, 1), "path": route_details}

@app.get("/api/state")
def get_state():
    return {
        "nodes": NODES_DICT,
        "scenarios": SCENARIOS,
        "hotspots": [
            {"lat": h["lat"], "lon": h["lon"], "size": h["count"]}
            for h in HOTSPOTS
        ],
        "edges": [
            {
                "from": u, 
                "to": v, 
                "corridor": data["corridor"], 
                "distance": data["distance_km"]
            }
            for u, v, data in G.edges(data=True)
        ]
    }

@app.get("/api/scenario/{index}")
def run_scenario(index: int):
    if index < 0 or index >= len(SCENARIOS):
        return {"error": "Invalid scenario index"}
        
    scen = SCENARIOS[index]
    primary, secondary = find_diversion_routes(
        G, scen["blocked"], scen["origin"], scen["dest"], HOTSPOTS
    )
    
    instruction = officer_instruction(G, scen["blocked"], scen["origin"], scen["dest"], primary)
    
    p_metrics = get_path_metrics(G, primary)
    s_metrics = get_path_metrics(G, secondary)
    
    return {
        "scenario": scen,
        "primary": p_metrics,
        "secondary": s_metrics,
        "instruction": instruction
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
