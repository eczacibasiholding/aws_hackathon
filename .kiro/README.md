# NEXUS Supply Chain Risk Agent

## Overview
This is a supply chain risk analysis agent for the NEXUS Hackathon. The agent processes disruption signals, calculates risk scores, analyzes impact, and generates mitigation strategies.

## Data Structure

### Input Data (`data/NEXUS_Agent_Veri_Seti_TEKNIK.xlsx`)
- Contains raw signals and data for analysis
- No risk scores or answers (to be computed by agent)
- Analysis reference date: 25.11.2026

### Reference Data (`data/NEXUS_Hackathon_Veri_Seti_AnaVeri.xlsx`)
- Contains answer key and reference values
- Risk scoring formulas and parameters
- Impact analysis benchmarks

## Agent Architecture

### Deterministic Components (Python)
- Risk signal processing
- Probability calculations (weighted scoring)
- Impact estimation (cost, disruption days)
- Strategy evaluation (multi-criteria decision making)

### LLM Components (Text-only)
- Signal explanation generation
- Risk justification
- Strategy rationale
- Agent action recommendations

## Key Metrics
- **Analysis Date (D0)**: 25.11.2026
- **Risk Scale**: 1-25 (Probability × Impact)
- **Risk Levels**: Low (<7), Medium (7-15), High (≥15)

## Project Structure
```
nexus-hackathon/
├── .kiro/
│   ├── settings/     # MCP and agent configuration
│   ├── steering/     # Project steering documentation
│   └── agents/       # Agent-specific configurations
├── data/
│   ├── NEXUS_Agent_Veri_Seti_TEKNIK.xlsx
│   └── NEXUS_Hackathon_Veri_Seti_AnaVeri.xlsx
└── src/              # Python implementation
```

## Implementation Notes
- All calculations are deterministic (no random elements)
- LLM used only for text generation and reasoning
- Risk scoring uses weighted probability formula
- Impact analysis considers financial cost and operational disruption
- Strategy selection uses multi-criteria KPIs
