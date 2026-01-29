# Issue Resolution: Genkit Prompt Variable Collision & Debugging Tooling

This document outlines the root cause of the prompt text corruption issue and the steps taken to resolve it, including the configuration of the Genkit Developer UI.

## 1. The Core Issue: Prompt Variable Collision

### **The Symptom**
The output from the Source Discovery Agent contained malformed text in the `Job Role` field:
```text
Job Role: <<<dotprompt:role:[object Object]>>>
```
Instead of "Business Developer", the prompt rendered an internal object identifier.

### **The Root Cause**
The issue was caused by a **variable name collision** in the Genkit Dotprompt engine.
- You defined an input variable named `role`.
- **`role` is a reserved keyword** in Genkit's template system (used to define message roles like `"system"`, `"user"`, `"model"`).
- When the template engine processed `{{role}}`, it prioritized its internal reserved object over your input string, resulting in the `[object Object]` string representation.

### **The Solution**
We resolved this by **renaming the input variable** to eliminate the ambiguity:
1.  Updated the Zod input schema to use `jobRole` instead of `role`.
2.  Updated the prompt templates to use `{{jobRole}}`.
3.  Updated the code to pass `jobRole` in the input object.

---

## 2. The Tooling Solution: Genkit Developer UI

To debug such issues, inspecting the raw rendered prompt is essential. We encountered an error when trying to launch the Genkit Developer UI.

### **The Command**
```bash
npx genkit start -- npm start
```

### **Why this command is important**
1.  **`npx genkit start`**: Launches the Genkit Developer UI server (usually on port 4000).
2.  **`-- npm start`**: This argument tells the Genkit CLI **how to run your specific application code**.
    *   Without this, Genkit starts but doesn't know about your registered flows or prompts.
    *   By passing `-- npm start` (which runs `ts-node run.ts`), we ensure your code compiles and registers the `researchTopicFlow` with the Genkit runtime so it appears in the UI.

### **Steps we took to enable this:**
1.  **Installed the CLI**: `npm install -D genkit-cli` (The command wasn't found initially).
2.  **Configured `package.json`**: Added a script shortcut `"genkit:start"`.

### **How it helps validation**
Using this command allows you to open the **Inspect** tab in the Developer UI, which shows the **final rendered prompt** sent to the LLM. This confirms that `{{jobRole}}` is correctly replaced with "Business Developer" and that no internal objects are leaking into the text.
