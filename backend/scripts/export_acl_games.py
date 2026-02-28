"""Post-process ACL demo games: validate blueprints, compute aggregate metrics.

Usage:
    cd backend && source venv/bin/activate
    PYTHONPATH=. python scripts/export_acl_games.py
"""

import json
import sys
from pathlib import Path

GAMES_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "frontend"
    / "src"
    / "data"
    / "acl-demo"
    / "games"
)
METRICS_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "frontend"
    / "src"
    / "data"
    / "acl-demo"
    / "metrics"
)


def validate_game(game: dict) -> list[str]:
    """Return list of validation warnings for a game entry."""
    warnings = []
    required_keys = [
        "id", "title", "question", "domain", "educationLevel",
        "gameType", "mechanic", "bloomsLevel", "pipelineMetrics", "blueprint",
    ]
    for key in required_keys:
        if key not in game:
            warnings.append(f"Missing required key: {key}")

    bp = game.get("blueprint")
    if not bp:
        warnings.append("Blueprint is empty or null")
    elif isinstance(bp, dict):
        if game["gameType"] == "interactive_diagram":
            if "diagram" not in bp and "scenes" not in bp:
                warnings.append("Interactive diagram blueprint missing 'diagram' or 'scenes'")
        elif game["gameType"] == "algorithm":
            if "scenes" not in bp and "algorithm" not in bp:
                warnings.append("Algorithm blueprint missing 'scenes' or 'algorithm'")

    metrics = game.get("pipelineMetrics", {})
    if not metrics.get("runId"):
        warnings.append("Missing pipeline run ID")
    if metrics.get("totalTokens", 0) == 0:
        warnings.append("Zero tokens reported")

    return warnings


def compute_aggregate(games: list[dict]) -> dict:
    """Compute aggregate metrics across all games."""
    n = len(games)
    if n == 0:
        return {"totalGames": 0}

    def avg(key):
        vals = [g["pipelineMetrics"].get(key, 0) for g in games]
        return round(sum(vals) / n, 4)

    def group_avg(games_list, key):
        vals = [g["pipelineMetrics"].get(key, 0) for g in games_list]
        return round(sum(vals) / len(games_list), 4) if games_list else 0

    def group_by(field):
        groups = {}
        for g in games:
            k = g.get(field, "unknown")
            if k not in groups:
                groups[k] = []
            groups[k].append(g)
        return {
            k: {
                "count": len(v),
                "avgCost": group_avg(v, "totalCost"),
                "avgTokens": round(group_avg(v, "totalTokens")),
                "avgLatency": group_avg(v, "latencySeconds"),
                "avgVPR": group_avg(v, "validationPassRate"),
            }
            for k, v in groups.items()
        }

    total_tokens = sum(g["pipelineMetrics"].get("totalTokens", 0) for g in games)
    total_cost = sum(g["pipelineMetrics"].get("totalCost", 0) for g in games)

    return {
        "totalGames": n,
        "totalTokens": total_tokens,
        "totalCost": round(total_cost, 2),
        "avgTokensPerGame": round(total_tokens / n),
        "avgCostPerGame": round(total_cost / n, 4),
        "avgLatencySeconds": avg("latencySeconds"),
        "avgValidationPassRate": avg("validationPassRate"),
        "byDomain": group_by("domain"),
        "byLevel": group_by("educationLevel"),
        "byMechanic": group_by("mechanic"),
    }


def main():
    if not GAMES_DIR.exists():
        print(f"Games directory not found: {GAMES_DIR}")
        sys.exit(1)

    game_files = sorted(GAMES_DIR.glob("*.json"))
    print(f"Found {len(game_files)} game JSON files in {GAMES_DIR}")

    games = []
    all_warnings = {}

    for path in game_files:
        with open(path) as f:
            game = json.load(f)

        warnings = validate_game(game)
        if warnings:
            all_warnings[game.get("id", path.stem)] = warnings

        games.append(game)

    # Print validation report
    if all_warnings:
        print(f"\nValidation warnings ({len(all_warnings)} games with issues):")
        for game_id, warns in all_warnings.items():
            for w in warns:
                print(f"  [{game_id}] {w}")
    else:
        print("\nAll games passed validation.")

    # Coverage report
    domains = set(g["domain"] for g in games)
    levels = set(g["educationLevel"] for g in games)
    mechanics = set(g["mechanic"] for g in games)
    types = set(g["gameType"] for g in games)

    print(f"\nCoverage:")
    print(f"  Domains ({len(domains)}):    {sorted(domains)}")
    print(f"  Levels ({len(levels)}):     {sorted(levels)}")
    print(f"  Mechanics ({len(mechanics)}):  {sorted(mechanics)}")
    print(f"  Types ({len(types)}):      {sorted(types)}")

    # Compute and save aggregate metrics
    aggregate = compute_aggregate(games)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = METRICS_DIR / "aggregate.json"
    with open(metrics_path, "w") as f:
        json.dump(aggregate, f, indent=2)
    print(f"\nAggregate metrics saved to {metrics_path}")

    # Print summary
    print(f"\nSummary:")
    print(f"  Total games:      {aggregate['totalGames']}")
    print(f"  Total tokens:     {aggregate.get('totalTokens', 0):,}")
    print(f"  Total cost:       ${aggregate.get('totalCost', 0):.2f}")
    print(f"  Avg cost/game:    ${aggregate.get('avgCostPerGame', 0):.4f}")
    print(f"  Avg latency:      {aggregate.get('avgLatencySeconds', 0):.1f}s")
    print(f"  Avg VPR:          {aggregate.get('avgValidationPassRate', 0):.0%}")


if __name__ == "__main__":
    main()
