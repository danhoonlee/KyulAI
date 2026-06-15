#!/bin/bash
# KyulAI Agent Team Launcher
# Launches parallel agent teams in tmux panes (all visible in one screen)

SESSION="kyulai"
PROJECT_DIR="/Users/danlee/KyulAI"

# Kill existing session if any
tmux kill-session -t "$SESSION" 2>/dev/null

# Create new tmux session — first pane becomes the orchestrator
tmux new-session -d -s "$SESSION" -n "agents" -c "$PROJECT_DIR"

# Label the orchestrator pane
tmux send-keys -t "$SESSION:agents" "echo '── Orchestrator ──'" Enter

# ── Pane 1 (right): Research Team (Sonnet) ──
tmux split-window -h -t "$SESSION:agents" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:agents.1" "claude --model sonnet \"$(cat <<'PROMPT'
You are the Research & Paper Analysis Team for the KyulAI project.

PROJECT CONTEXT: Read CLAUDE.md and agents/research-team/team.md first.

KyulAI is building AI models that predict real-world experimental results using CAE simulation data for composite materials (sim-to-real transfer). Simulation tools include: Moldex3D (SMC/RTM), AniForm (Forming), Digimat (Material Modeling), Abaqus (Structural FEA), Simutence (multi-process), cadfil (Filament Winding).

YOUR TASK - Phase 1 Literature Survey:
1. Search for the most relevant and recent papers on:
   - Sim-to-real transfer learning for engineering simulation
   - Physics-Informed Neural Networks (PINNs) applied to composite materials
   - Neural Operators (FNO, DeepONet) for surrogate modeling
   - Domain adaptation methods for scarce experimental data
   - Graph Neural Networks for mesh-based simulation data
   - Multi-fidelity learning combining simulation fidelity levels
   - Uncertainty quantification in ML predictions for engineering

2. For each key paper found, create a summary in research/papers/ with:
   - Problem formulation
   - Model architecture
   - Training strategy
   - Dataset characteristics
   - Reported metrics and results
   - Limitations and gaps

3. After analyzing papers, write a synthesis report in research/syntheses/ recommending the top 3-5 most promising approaches for our sim-to-real composite problem.

4. Write final methodology recommendations in research/recommendations/.

Start by reading the team definition, then begin searching.
PROMPT
)\"" Enter

# ── Pane 2 (bottom-left): Data Engineering Team (Opus) ──
tmux split-window -v -t "$SESSION:agents.0" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION:agents.2" "claude --model opus \"$(cat <<'PROMPT'
You are the Data Engineering Schema Architect for the KyulAI project.

PROJECT CONTEXT: Read CLAUDE.md, agents/data-engineering-team/team.md, and the unified data schema section in docs/architecture/agent-team-architecture.md first.

KyulAI is building AI models for sim-to-real transfer in composite material analysis. Your role is the most foundational: designing the unified data schema that ALL CAE tool data flows through before reaching ML models.

YOUR TASK - Design and Implement the Unified Data Schema:
1. Read the existing schema outline in the architecture doc
2. Design the complete Pydantic-based schema in src/data/schemas/ covering:
   - UnifiedCAERecord: the top-level container
   - Metadata schema (source tool, simulation type, material system, process params)
   - Geometry schema (mesh types: structured, unstructured, point cloud; nodes, elements, BCs)
   - Input fields schema (material properties, loading conditions, process conditions)
   - Output fields schema (scalar/vector/tensor fields, time series)
   - Experimental reference schema (measurements, uncertainty, test conditions)

3. For each of the 6 CAE tools (Moldex3D, AniForm, Digimat, Abaqus, Simutence, cadfil), define:
   - What fields they typically output
   - How those fields map to the unified schema
   - A mapping config in src/data/schemas/tool_mappings/

4. Create the base parser interface in src/data/parsers/base.py that all tool-specific parsers must implement.

5. Write validation logic in src/data/quality/ to verify records conform to the schema.

The schema must be flexible enough to handle all 6 tools but strict enough to guarantee ML models get consistent input. Start by reading the architecture doc, then design.
PROMPT
)\"" Enter

# ── Layout: orchestrator top-left, data-eng bottom-left, research right ──
# Set pane titles for easy identification
tmux select-pane -t "$SESSION:agents.0" -T "orchestrator"
tmux select-pane -t "$SESSION:agents.1" -T "research (sonnet)"
tmux select-pane -t "$SESSION:agents.2" -T "data-eng (opus)"

# Enable pane border labels
tmux set-option -t "$SESSION" pane-border-status top
tmux set-option -t "$SESSION" pane-border-format " #{pane_title} "

# Focus back on orchestrator pane
tmux select-pane -t "$SESSION:agents.0"

echo ""
echo "KyulAI tmux session created — all agents in one window"
echo ""
echo "  Attach:          tmux attach -t kyulai"
echo "  Switch pane:     Ctrl+b arrow-keys"
echo "  Zoom one pane:   Ctrl+b z  (toggle)"
echo "  Resize pane:     Ctrl+b Alt+arrow-keys"
echo ""
