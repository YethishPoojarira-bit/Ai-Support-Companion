# Multi-Agent Research & Study Plan Generator

This workflow leverages a chain of specialized AI agents to autonomously research a target job role at a specific company and generate a comprehensive, actionable study plan.

## Workflow Architecture

The system follows a sequential pipeline where the output of one agent serves of the context for the next.

```mermaid
graph TD
    UserInput[User Input: Company & Job Role] --> Agent1
    
    subgraph "Stage 1: Discovery"
        Agent1[**Source Discovery Agent**]
        Agent1 -->|List of Authoritative URLs| Agent2
    end
    
    subgraph "Stage 2: Analysis & Extraction"
        Agent2[**Topic Extraction Agent**]
        Note2[Reads Sources & Identifies Key Themes]
        Agent2 -.-> Note2
        Agent2 -->|JSON: Technical & Behavioral Topics| Agent3
    end
    
    subgraph "Stage 3: Granular Decomposition"
        Agent3[**Atomic Decomposition Agent**]
        Note3[Breaks concepts into testable units]
        Agent3 -.-> Note3
        Agent3 -->|JSON: Atomic Study Units| Agent4
    end
    
    subgraph "Stage 4: Planning"
        Agent4[**Study Plan Agent**]
        Params[timeline: N Weeks] -.-> Agent4
        Agent4 -->|Final Output| Output
    end

    Output[**Week-by-Week Markdown Schedule**]

    style Agent1 fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style Agent2 fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style Agent3 fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style Agent4 fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
```

## Agent Breakdown

### 1. Source Discovery Agent
*   **Goal**: Identify trustworthy web entry points for research.
*   **Input**: `Company Name`, `Job Role`.
*   **Strategy**: Prioritizes official career pages, engineering blogs, and professional networks (LinkedIn, Glassdoor) over generic SEO content.
*   **Output**: A Python list of URLs.

### 2. Research & Topic Extraction Agent
*   **Goal**: Simulate "reading" the sources to identify high-level competency requirements.
*   **Input**: List of URLs from Agent 1.
*   **Logic**:
    *   Classifies findings into **Technical** (Hard skills, functional competencies, domain knowledge) and **Behavioral** (Culture, leadership principles).
    *   Ensures topics are grounded in the actual source text.
*   **Output**: Structured JSON containing high-level topics with importance scores and justifications.

### 3. Atomic Decomposition Agent
*   **Goal**: Turn high-level concepts into study-able units.
*   **Input**: High-level topics JSON.
*   **Logic**:
    *   Explodes broad terms (e.g., "System Design", "Sales Strategy") into granular sub-concepts (e.g., "Load Balancing", "Pipeline Management").
    *   Ensures coverage from beginner to advanced levels.
*   **Output**: JSON list of "Atomic Units".

### 4. Study Plan Scheduler Agent
*   **Goal**: Create a human-friendly execution plan.
*   **Input**: All Atomic Units + `Weeks` timeline.
*   **Logic**:
    *   Distributes topics logically over the timeline.
    *   Balances Technical and Behavioral work each week.
    *   Progresses from Foundations → Advanced → Mock Interview Prep.
*   **Output**: A formatted Markdown Study Schedule.

## How to Run

1.  Open `ResearchBasedAgent.ipynb`.
2.  Set your target in the setup cell:
    ```python
    company_name = "Amazon"
    job_role = "Sales Executive" # or "Software Engineer", etc.
    ```
3.  Run all cells sequentially.
4.  The final cell will print the complete study plan.
