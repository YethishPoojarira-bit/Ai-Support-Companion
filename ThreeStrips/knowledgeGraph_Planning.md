# Product Knowledge Graph: Entity & Relationship Design

## Entities
- **Feature**
- **Requirement**
- **Person**
- **Sprint**
- **Request**
- **Decision**
- **FeatureChange**
- **Risk**
- **Bug**
- **Meeting**

---

## 🧠 Entity → Relationship Map

### 1️⃣ Requirement
**Purpose:** What must be built, and how it depends on other requirements.

```mermaid
graph TD
  Requirement1((Requirement))
  Requirement2((Requirement))
  Feature((Feature))
  Request((Request))
  Decision((Decision))
  Risk((Risk))

  Requirement1 -- DEPENDS_ON --> Requirement2
  Feature -- IMPLEMENTS --> Requirement1
  Request -- CREATED_REQUIREMENT --> Requirement1
  Decision -- APPROVED --> Requirement1
  Risk -- THREATENS --> Requirement1
```

---

### 2️⃣ Feature
**Purpose:** Core product capability with full traceability.

```mermaid
graph TD
  Product((Product))
  Feature((Feature))
  Requirement((Requirement))
  Risk((Risk))
  FeatureChange((FeatureChange))
  Decision((Decision))
  Request((Request))
  Sprint((Sprint))

  Product -- HAS_FEATURE --> Feature
  Feature -- IMPLEMENTS --> Requirement
  Feature -- DEPENDS_ON --> Feature
  Feature -- HAS_RISK --> Risk
  FeatureChange -- UPDATES --> Feature
  Decision -- ABOUT --> Feature
  Request -- JUSTIFIES --> Feature
  Sprint -- DELIVERS --> Feature
```

---

### 3️⃣ Person
**Purpose:** Accountability and ownership.

```mermaid
graph TD
  Person((Person))
  Request((Request))
  Decision((Decision))
  FeatureChange((FeatureChange))
  Bug((Bug))
  Risk((Risk))
  Meeting((Meeting))

  Person -- REQUESTED --> Request
  Person -- MADE --> Decision
  Person -- PROPOSED --> FeatureChange
  Person -- REPORTED --> Bug
  Person -- FIXED --> Bug
  Person -- IDENTIFIED --> Risk
  Person -- ATTENDED --> Meeting
```

---

### 4️⃣ Risk
**Purpose:** Capture uncertainty and threats.

```mermaid
graph TD
  Risk((Risk))
  Feature((Feature))
  Requirement((Requirement))
  Meeting((Meeting))
  Decision((Decision))

  Risk -- AFFECTS --> Feature
  Risk -- THREATENS --> Requirement
  Risk -- IDENTIFIED_IN --> Meeting
  Decision -- MITIGATES --> Risk
```

---

### 5️⃣ Sprint
**Purpose:** Time-boxed execution.

```mermaid
graph TD
  Sprint((Sprint))
  Feature((Feature))
  Bug((Bug))
  Risk((Risk))
  Decision((Decision))

  Sprint -- INCLUDES --> Feature
  Sprint -- RESOLVED --> Bug
  Sprint -- ADDRESSES --> Risk
  Sprint -- BASED_ON --> Decision
```

---

### 6️⃣ Request
**Purpose:** Why something was needed.

```mermaid
graph TD
  Person((Person))
  Request((Request))
  Feature((Feature))
  Requirement((Requirement))
  Meeting((Meeting))

  Person -- REQUESTED --> Request
  Request -- JUSTIFIES --> Feature
  Request -- CREATED_REQUIREMENT --> Requirement
  Request -- DISCUSSED_IN --> Meeting
```

---

### 7️⃣ Decision
**Purpose:** Authority and governance.

```mermaid
graph TD
  Decision((Decision))
  Feature((Feature))
  FeatureChange((FeatureChange))
  Requirement((Requirement))
  Risk((Risk))
  Meeting((Meeting))
  Decision2((Decision))

  Decision -- ABOUT --> Feature
  Decision -- APPROVES --> FeatureChange
  Decision -- APPROVED --> Requirement
  Decision -- MITIGATES --> Risk
  Decision -- SUPERSEDES --> Decision2
  Meeting -- TRIGGERED --> Decision
```

---

### 8️⃣ FeatureChange
**Purpose:** Track evolution without overwriting history.

```mermaid
graph TD
  FeatureChange((FeatureChange))
  Feature((Feature))
  Person((Person))
  Decision((Decision))
  Meeting((Meeting))
  FeatureChange2((FeatureChange))

  FeatureChange -- UPDATES --> Feature
  Person -- PROPOSED --> FeatureChange
  Decision -- APPROVES --> FeatureChange
  FeatureChange -- SUPERSEDES --> FeatureChange2
  FeatureChange -- PROPOSED_IN --> Meeting
```

---

### 9️⃣ Bug / Issue
**Purpose:** Stability and quality tracking.

```mermaid
graph TD
  Bug((Bug))
  Feature((Feature))
  Person((Person))
  Sprint((Sprint))
  FeatureChange((FeatureChange))

  Bug -- AFFECTS --> Feature
  Person -- REPORTED --> Bug
  Person -- FIXED --> Bug
  Sprint -- RESOLVED --> Bug
  Bug -- INTRODUCED_BY --> FeatureChange
  Bug -- INTRODUCED_IN --> Sprint
```

---

### 🔟 Meeting
**Purpose:** Source of truth for discussions and transcripts.

```mermaid
graph TD
  Meeting((Meeting))
  Decision((Decision))
  FeatureChange((FeatureChange))
  Risk((Risk))
  Request((Request))
  Person((Person))

  Meeting -- TRIGGERED --> Decision
  Meeting -- PROPOSED --> FeatureChange
  Meeting -- IDENTIFIED --> Risk
  Meeting -- DISCUSSED --> Request
  Person -- ATTENDED --> Meeting
```

---

## 🧩 Summary View (Mental Model)

| Entity        | Core Purpose     |
| ------------- | ---------------- |
| Requirement   | What must exist  |
| Feature       | What users get   |
| Request       | Why it exists    |
| Decision      | Authority        |
| FeatureChange | Evolution        |
| Bug           | Quality issues   |
| Risk          | Uncertainty      |
| Sprint        | Time execution   |
| Meeting       | Source of change |
| Person        | Accountability   |

---

## ⚠️ Design Rules (Important)

1. **Never overwrite Feature fields** for changes → Always add FeatureChange
2. **Never connect Meeting directly to Feature** → Always go through Decision / FeatureChange
3. **Every Bug should affect something** → No orphan bugs
4. **Every Decision must have a source** → Meeting or Document

---

## 🚀 What This Enables

You can now answer:
- Why does this feature exist?
- Who asked for it?
- Who approved changes?
- What broke after which change?
- Which sprint fixed it?
- Which meeting caused it?
