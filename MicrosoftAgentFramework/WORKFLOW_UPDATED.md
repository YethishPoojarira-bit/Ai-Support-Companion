# Multi-Agent Research & Study Plan Generator

This workflow leverages a chain of specialized AI agents to autonomously research a target job role at a specific company and generate a comprehensive, actionable study plan.

## Workflow Architecture

The system follows a sequential pipeline where data flows from broad research to granular atomic units, finally synthesized into a temporal schedule.

```mermaid
graph TD
    %% Global Inputs
    Input([User Input: Company, Job Role, Weeks]) --> SourceAgent
    
    %% Stage 1: Source Discovery
    subgraph "Stage 1: Discovery Phase"
        direction TB
        SourceAgent[**Source Discovery Agent**]
        
        SourceRules{Search Strategy}
        SourceRules -->|Prioritize| Official[Official Careers/Blogs]
        SourceRules -->|Prioritize| Community[Glassdoor/Blind/LinkedIn]
        SourceRules -->|Seek| ExistingPlans[Existing Roadmaps/GitHub Repos]
        
        SourceAgent -.-> SourceRules
        SourceAgent -->|Output: Python List| Sources[List of Trusted URLs]
    end

    Sources --> TopicAgent

    %% Stage 2: Extraction
    subgraph "Stage 2: Research & Topic Extraction"
        direction TB
        TopicAgent[**Topic Extraction Agent**]
        
        SimulateRead[Simulate Reading Sources]
        IdentifyThemes[Identify Key Themes]
        
        TopicAgent -.-> SimulateRead
        SimulateRead --> IdentifyThemes
        
        IdentifyThemes -->|Categorize| Technical["**Technical/Hard Skills**<br/>(Languages, Tools, Domain Knowledge)"]
        IdentifyThemes -->|Categorize| Behavioral["**Behavioral/Soft Skills**<br/>(Culture, Leadership Principles)"]
        
        TopicAgent -->|Output: Structured JSON| HighLevelTopics[High-Level Topics JSON]
    end

    HighLevelTopics --> AtomicAgent

    %% Stage 3: Decomposition
    subgraph "Stage 3: Atomic Decomposition"
        direction TB
        AtomicAgent[**Atomic Decomposition Agent**]
        
        Decompose[Explode Topics]
        Filter[Filter: Testable/atomic Units]
        Range[Ensure Beginner-to-Advanced Coverage]
        
        AtomicAgent -.-> Decompose
        Decompose --> Filter --> Range
        
        AtomicAgent -->|Output: Comprehensive JSON| AtomicUnits[Atomic Study Units JSON]
    end

    AtomicUnits --> PlanAgent
    Input -.->|Time Constraint| PlanAgent

    %% Stage 4: Scheduling
    subgraph "Stage 4: Strategic Planning"
        direction TB
        PlanAgent[**Study Plan Scheduler Agent**]
        
        Distribute[Distribute Units over Timeline]
        Balance[Balance: Tech + Behavioral]
        Sequence[Sequence: Foundations -> Advanced -> Mock]
        
        PlanAgent -.-> Distribute
        Distribute --> Balance --> Sequence
        
        PlanAgent -->|Final Output| MarkdownPlan[**Week-by-Week Markdown Schedule**]
    end

    %% Styles
    classDef input fill:#f9f9f9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;
    classDef output fill:#ffe0b2,stroke:#ef6c00,stroke-width:2px;
    classDef agent fill:#e3f2fd,stroke:#1565c0,stroke-width:2px;
    classDef data fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px;

    class Input input;
    class MarkdownPlan output;
    class SourceAgent,TopicAgent,AtomicAgent,PlanAgent agent;
    class Sources,HighLevelTopics,AtomicUnits data;
```

## Agent Breakdown

### 1. Source Discovery Agent
*   **Goal**: Identify trustworthy web entry points and existing community roadmaps.
*   **Context**: `Company Name`, `Job Role`.
*   **Updated Logic**: Now explicitly searches for *existing study plans* or roadmaps on GitHub, Medium, or Reddit to leverage community knowledge.
*   **Output**: List of URLs (Python List).

### 2. Research & Topic Extraction Agent
*   **Goal**: Synthesize raw source data into competency buckets.
*   **Context**: List of URLs.
*   **Logic**:
    *   **Technical**: Defines this broadly as "Hard Skills & Domain Knowledge" (e.g., Coding for Eng, Sales Strategy for Sales).
    *   **Behavioral**: Focuses on Company Values (e.g., Amazon LPs) and cultural fit.
*   **Output**: JSON separating `technical_topics` and `behavioral_topics`.

### 3. Atomic Decomposition Agent
*   **Goal**: Break high-level concepts into study-able, testable units.
*   **Context**: High-level JSON.
*   **Logic**:
    *   Explodes broad terms (e.g., "System Design") into specific components (e.g., "Load Balancing", "Sharding").
    *   Ensures an exhaustive list covering beginner to advanced sub-topics.
*   **Output**: JSON list of `atomic_study_plan`.

### 4. Study Plan Scheduler Agent
*   **Goal**: Create a strategic timeline for preparation.
*   **Context**: Atomic Units + `Weeks` input.
*   **Logic**:
    *   **Progression**: Foundations → Core Concepts → Advanced → Mock/Synthesis.
    *   **Balance**: Mixes hard and soft skills weekly.
    *   **Exhaustion**: Ensures **ALL** atomic units are mapped to the schedule (no skipping).
*   **Output**: Formatted Markdown Schedule.
