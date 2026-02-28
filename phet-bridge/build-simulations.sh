#!/bin/bash
#
# GamED.AI PhET Simulation Build Script
#
# This script builds self-hosted PhET simulations with the GamED bridge module injected.
# It clones the necessary repositories, builds each simulation, and injects the bridge code.
#
# Usage:
#   ./build-simulations.sh [simulation-name]
#
# If no simulation name is provided, all simulations will be built.
#
# Requirements:
#   - Node.js (v18+)
#   - npm
#   - Git
#   - grunt-cli (npm install -g grunt-cli)
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/phet-build"
OUTPUT_DIR="${SCRIPT_DIR}/dist/simulations"
BRIDGE_JS="${SCRIPT_DIR}/gamed-bridge.js"

# Simulations to build (can be overridden by command line argument)
SIMULATIONS=(
  "projectile-motion"
  "circuit-construction-kit-dc"
  "states-of-matter"
  "energy-skate-park"
  "forces-and-motion-basics"
  "gravity-and-orbits"
  "wave-on-a-string"
  "gas-properties"
  "pendulum-lab"
  "masses-and-springs"
  "faradays-law"
  "balancing-act"
)

# Core PhET dependencies
CORE_REPOS=(
  "chipper"
  "perennial"
  "perennial-alias"
  "axon"
  "scenery"
  "sun"
  "joist"
  "dot"
  "kite"
  "phet-core"
  "scenery-phet"
  "tambo"
  "tandem"
  "utterance-queue"
  "brand"
  "sherpa"
  "assert"
  "phetcommon"
  "query-string-machine"
  "phetmarks"
  "babel"
  "mobius"
  "twixt"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
  log_info "Checking prerequisites..."

  if ! command -v node &> /dev/null; then
    log_error "Node.js is not installed. Please install Node.js v18+."
    exit 1
  fi

  if ! command -v npm &> /dev/null; then
    log_error "npm is not installed."
    exit 1
  fi

  if ! command -v git &> /dev/null; then
    log_error "Git is not installed."
    exit 1
  fi

  if ! command -v grunt &> /dev/null; then
    log_warn "grunt-cli not found. Installing globally..."
    npm install -g grunt-cli
  fi

  if [ ! -f "$BRIDGE_JS" ]; then
    log_error "Bridge module not found at $BRIDGE_JS"
    exit 1
  fi

  log_info "All prerequisites met."
}

# Clone core PhET repositories
clone_core_repos() {
  log_info "Setting up PhET core repositories..."

  mkdir -p "$WORK_DIR"
  cd "$WORK_DIR"

  for repo in "${CORE_REPOS[@]}"; do
    if [ ! -d "$repo" ]; then
      log_info "Cloning $repo..."
      git clone --depth 1 "https://github.com/phetsims/${repo}.git" || {
        log_warn "Failed to clone $repo, trying without depth limit..."
        git clone "https://github.com/phetsims/${repo}.git"
      }
    else
      log_info "$repo already exists, pulling latest..."
      cd "$repo" && git pull && cd ..
    fi
  done

  # Install npm dependencies for chipper and perennial
  log_info "Installing dependencies for chipper..."
  cd chipper && npm install && cd ..

  log_info "Installing dependencies for perennial..."
  cd perennial && npm install && cd ..

  log_info "Core repositories ready."
}

# Clone and build a specific simulation
build_simulation() {
  local sim_name=$1
  log_info "Building simulation: $sim_name"

  cd "$WORK_DIR"

  # Clone simulation if not exists
  if [ ! -d "$sim_name" ]; then
    log_info "Cloning $sim_name..."
    git clone --depth 1 "https://github.com/phetsims/${sim_name}.git" || {
      log_error "Failed to clone $sim_name"
      return 1
    }
  fi

  cd "$sim_name"

  # Install dependencies
  log_info "Installing dependencies for $sim_name..."
  npm install || log_warn "npm install had warnings (continuing anyway)"

  # Build with adapted-from-phet brand
  log_info "Building $sim_name with adapted-from-phet brand..."
  grunt --brands=adapted-from-phet || {
    log_error "Build failed for $sim_name"
    return 1
  }

  # Find the built HTML file
  local build_file="build/adapted-from-phet/${sim_name}_all_adapted-from-phet.html"

  if [ ! -f "$build_file" ]; then
    # Try alternative naming
    build_file=$(find build/adapted-from-phet -name "*.html" | head -1)
  fi

  if [ ! -f "$build_file" ]; then
    log_error "Could not find built HTML file for $sim_name"
    return 1
  fi

  # Inject bridge module
  log_info "Injecting GamED bridge module..."
  inject_bridge "$build_file" "$sim_name"

  log_info "Successfully built $sim_name"
  return 0
}

# Inject the bridge module into a built simulation
inject_bridge() {
  local html_file=$1
  local sim_name=$2

  # Create output directory
  mkdir -p "$OUTPUT_DIR/$sim_name"

  local output_file="$OUTPUT_DIR/$sim_name/${sim_name}_gamed.html"

  # Read bridge code
  local bridge_code
  bridge_code=$(cat "$BRIDGE_JS")

  # Escape special characters for sed
  bridge_code=$(echo "$bridge_code" | sed 's/[&/\]/\\&/g')

  # Copy original file
  cp "$html_file" "$output_file"

  # Inject bridge code before </body>
  # Using perl for better multi-line handling
  perl -i -pe "s|</body>|<script>\n// GamED.AI Bridge Module\n${bridge_code}\n</script>\n</body>|" "$output_file" 2>/dev/null || {
    # Fallback to simpler injection if perl fails
    log_warn "Perl injection failed, using alternative method..."

    # Create a temporary file with the injection
    local temp_file=$(mktemp)

    # Read the original HTML
    while IFS= read -r line; do
      if [[ "$line" == *"</body>"* ]]; then
        echo "<script>"
        echo "// GamED.AI Bridge Module"
        cat "$BRIDGE_JS"
        echo "</script>"
      fi
      echo "$line"
    done < "$html_file" > "$temp_file"

    mv "$temp_file" "$output_file"
  }

  # Add attribution comment
  sed -i "1i <!-- Built with GamED.AI PhET Bridge - $(date) -->" "$output_file" 2>/dev/null || true

  log_info "Output: $output_file"
}

# Create an index page for all simulations
create_index_page() {
  log_info "Creating simulation index page..."

  cat > "$OUTPUT_DIR/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GamED.AI PhET Simulations</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
      background: #f5f5f5;
    }
    h1 { color: #333; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 20px;
      margin-top: 20px;
    }
    .card {
      background: white;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .card h3 { margin: 0 0 10px; color: #2196F3; }
    .card a {
      display: inline-block;
      margin-top: 10px;
      padding: 8px 16px;
      background: #2196F3;
      color: white;
      text-decoration: none;
      border-radius: 4px;
    }
    .card a:hover { background: #1976D2; }
    .attribution {
      margin-top: 40px;
      padding: 20px;
      background: #e3f2fd;
      border-radius: 8px;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <h1>GamED.AI PhET Simulations</h1>
  <p>Self-hosted PhET simulations with GamED.AI bridge module for assessment integration.</p>

  <div class="grid" id="sim-grid">
    <!-- Simulations will be listed here -->
  </div>

  <div class="attribution">
    <strong>Attribution:</strong> Based on PhET Interactive Simulations,
    University of Colorado Boulder.
    <a href="https://phet.colorado.edu" target="_blank">https://phet.colorado.edu</a>
    <br>Licensed under CC BY 4.0
  </div>

  <script>
    // List of available simulations
    const simulations = [
EOF

  # Add simulation entries
  local first=true
  for dir in "$OUTPUT_DIR"/*/; do
    if [ -d "$dir" ]; then
      local sim_name=$(basename "$dir")
      if [ "$sim_name" != "index.html" ]; then
        local display_name=$(echo "$sim_name" | sed 's/-/ /g' | sed 's/\b\(.\)/\u\1/g')
        if [ "$first" = true ]; then
          first=false
        else
          echo "," >> "$OUTPUT_DIR/index.html"
        fi
        echo "      { name: '$display_name', dir: '$sim_name', file: '${sim_name}_gamed.html' }" >> "$OUTPUT_DIR/index.html"
      fi
    fi
  done

  cat >> "$OUTPUT_DIR/index.html" << 'EOF'
    ];

    const grid = document.getElementById('sim-grid');
    simulations.forEach(sim => {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `
        <h3>${sim.name}</h3>
        <p>Interactive ${sim.name.toLowerCase()} simulation with assessment integration.</p>
        <a href="${sim.dir}/${sim.file}" target="_blank">Launch Simulation</a>
      `;
      grid.appendChild(card);
    });
  </script>
</body>
</html>
EOF

  log_info "Index page created at $OUTPUT_DIR/index.html"
}

# Main function
main() {
  echo "========================================"
  echo "GamED.AI PhET Simulation Builder"
  echo "========================================"
  echo ""

  check_prerequisites

  # Determine which simulations to build
  local sims_to_build=()
  if [ $# -gt 0 ]; then
    sims_to_build=("$@")
  else
    sims_to_build=("${SIMULATIONS[@]}")
  fi

  # Clone core repositories
  clone_core_repos

  # Build each simulation
  local success_count=0
  local fail_count=0

  for sim in "${sims_to_build[@]}"; do
    echo ""
    echo "----------------------------------------"
    if build_simulation "$sim"; then
      ((success_count++))
    else
      ((fail_count++))
    fi
  done

  # Create index page
  create_index_page

  echo ""
  echo "========================================"
  echo "Build Complete!"
  echo "========================================"
  echo "Successful: $success_count"
  echo "Failed: $fail_count"
  echo "Output directory: $OUTPUT_DIR"
  echo ""
}

# Run main function with all arguments
main "$@"
